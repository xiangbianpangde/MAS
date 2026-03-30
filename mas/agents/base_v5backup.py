"""
MAS Architecture v5: Multi-Candidate Ensemble + Self-Revision
Key changes from v4:
1. Multi-candidate generation for code (3 candidates at temp 0.3/0.5/0.8) → voter picks best
2. Self-revision for code: after initial solution, agent self-checks and revises
3. Creative ensemble: 3 candidates at temp 0.7/0.9/1.0 → evaluator-ranked
4. Enhanced research with cross-validation (2 researchers, pick more comprehensive)
5. Keep dual-pass reasoning and debugging (already perfect at 1.0)
"""
import os, json, time, requests, ast, re
from typing import Dict, List, Any, Tuple
from datetime import datetime

class MiniMaxClient:
    def __init__(self, api_key: str = None, api_host: str = None):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.api_host = api_host or os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com")
        self.model = "MiniMax-M2.7"
    
    def chat(self, messages: List[Dict], model: str = None, max_tokens: int = 2048, temperature: float = 0.7) -> Dict:
        url = f"{self.api_host}/v1/text/chatcompletion_v2"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": model or self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        start = time.time()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            elapsed = time.time() - start
            resp.raise_for_status()
            data = resp.json()
            return {"content": data["choices"][0]["message"]["content"], "usage": data.get("usage", {}), "elapsed": elapsed, "error": None}
        except Exception as e:
            return {"content": "", "usage": {"total_tokens": 0}, "elapsed": time.time() - start, "error": str(e)}

class Agent:
    def __init__(self, client: MiniMaxClient, name: str = "", role: str = ""):
        self.name = name; self.role = role; self.client = client; self.memory = []
    
    def think(self, task: str, context: List[Dict] = None, temperature: float = 0.7, max_tokens: int = 2048) -> Dict:
        messages = [{"role": "system", "content": self.system_prompt()}]
        if context:
            for c in context[-5:]: messages.append(c)
        messages.append({"role": "user", "content": task})
        result = self.client.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return {"agent": self.name, "task": task, "response": result["content"], "elapsed": result["elapsed"], "tokens": result["usage"].get("total_tokens", 0), "error": result.get("error")}
    
    def system_prompt(self) -> str:
        return f"You are {self.name}, a {self.role} specialist."
    
    def extract_code(self, response: str) -> str:
        blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        return blocks[0] if blocks else response

class ReasonerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Reasoner, expert in logical reasoning and mathematics.
IMPORTANT: Show your step-by-step reasoning first, then give the final answer at the end.
Format:
[Step 1] ...
[Step 2] ...
...
[Answer] YOUR_FINAL_ANSWER_HERE
Do not write anything after the answer line."""

class MathVerifierAgent(Agent):
    """v4: Second-pass verification for hard math problems"""
    def system_prompt(self) -> str:
        return """You are MathVerifier, expert mathematics validator.

Given a math problem and an answer, you must:
1. Re-read the problem carefully
2. Verify the answer by re-computing independently
3. State: VERIFIED (if correct) or ERROR (if wrong, explain why)

If the answer is wrong, provide the correct answer.
Be precise and show your verification steps."""

class CoderAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Coder, expert Python programmer.
OUTPUT FORMAT (MUST FOLLOW):
1. Brief explanation (1-2 sentences)
2. Code block starting with ```python
3. After code: "Test: [example usage showing it works]"

The code must be syntactically correct and produce the correct output."""

class CodeReviserAgent(Agent):
    """v5 NEW: Revises code after self-verification"""
    def system_prompt(self) -> str:
        return """You are CodeReviser, expert at improving Python code.

Given buggy or suboptimal code, you must:
1. Identify issues in the code (if any)
2. Provide an improved version in a ```python``` block
3. Briefly explain the key improvement

Be critical - if the code looks correct, say so."""

class ResearcherAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Researcher, expert in information synthesis.
Be concise. Use bullet points. Cover all key aspects. Target 100-200 words."""

class ResearcherAgentV2(Agent):
    """v5 NEW: Alternative researcher with different angle"""
    def system_prompt(self) -> str:
        return """You are ResearcherV2, expert in thorough research and edge cases.

Cover BOTH mainstream understanding AND alternative viewpoints.
Use numbered lists. Be comprehensive. Target 150-250 words."""

class PlannerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Planner, expert in project planning.
Structure: Phase → Milestones → Weekly deliverables. Be specific, actionable."""

class BugAnalyzerAgent(Agent):
    """v4: First pass - identifies the bug without suggesting fix yet"""
    def system_prompt(self) -> str:
        return """You are BugAnalyzer, expert at identifying software bugs.

Given buggy code, you MUST:
1. State the bug in one clear sentence (what goes wrong, when, why)
2. Give a concrete example showing the bug behavior with the test input
3. Do NOT suggest a fix yet

Format:
Bug: [clear description]
Example: [input] → [wrong output] because [reason]
"""

class FixGeneratorAgent(Agent):
    """v4: Second pass - provides the fix based on bug analysis"""
    def system_prompt(self) -> str:
        return """You are FixGenerator, expert at writing correct code fixes.

Given buggy code AND a bug analysis, you MUST:
1. Provide the minimal fix in a ```python``` code block
2. Explain why this fix works (1 sentence)
3. Verify: if you run the fixed code with the bug-triggering input, it should now produce correct output

Output ONLY the fixed function/class, nothing else."""

class DebuggerAgent(Agent):
    """v4: Two-pass debugging using BugAnalyzer + FixGenerator"""
    def think(self, task: str, context: List[Dict] = None, temperature: float = 0.7, max_tokens: int = 2048) -> Dict:
        analyzer = BugAnalyzerAgent(self.client)
        analysis = analyzer.think(task, temperature=0.3)
        
        task_with_analysis = task + "\n\n--- Bug Analysis ---\n" + analysis["response"] + "\n\nNow provide the fix:"
        fixer = FixGeneratorAgent(self.client)
        fix = fixer.think(task_with_analysis, temperature=0.3, max_tokens=4096)
        
        combined = f"【Bug Analysis】\n{analysis['response']}\n\n【Fix】\n{fix['response']}"
        
        return {
            "agent": self.name,
            "task": task,
            "response": combined,
            "elapsed": analysis["elapsed"] + fix["elapsed"],
            "tokens": analysis.get("tokens", 0) + fix.get("tokens", 0),
            "error": analysis.get("error") or fix.get("error")
        }

class CreativeAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Creative, expert in creative writing and storytelling.

Your writing must:
1. Hook the reader in the first line
2. Use vivid, specific details (not generic)
3. Have a clear point or emotional impact
4. Match the requested style/format exactly

If asked for humor: actually be funny, not just "this is funny"
If asked for a story: create a narrative with tension and resolution"""

class CreativeAgentV2(Agent):
    """v5 NEW: Alternative creative with different style"""
    def system_prompt(self) -> str:
        return """You are CreativeV2, bold and unconventional writer.

Your approach:
1. Subvert expectations - take the road least expected
2. Use concrete sensory details over abstract statements
3. Vary sentence structure deliberately
4. End with impact - a twist, a lingering image, or a punch

Think: what would make a human stop and re-read?"""

class CreativeAgentV3(Agent):
    """v5 NEW: Third creative variant for maximum diversity"""
    def system_prompt(self) -> str:
        return """You are CreativeV3, literary and introspective writer.

You specialize in:
1. Precise word choice - every word earns its place
2. Emotional authenticity over dramatic exaggeration
3. Scene-based writing with natural dialogue
4. Open-ended endings that resonate

Write as if crafting a short literary piece, not content."""

class VerifierAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Verifier, expert code validator.
Execute code mentally or explain why it cannot be verified. Report PASS/FAIL."""

# === v5 Code Voter ===
class CodeVoterAgent(Agent):
    """v5: Selects the best code from multiple candidates"""
    def system_prompt(self) -> str:
        return """You are CodeVoter, expert at selecting the best code solution.

Given a programming problem and multiple code solutions, select the BEST one.
Criteria: correctness, clarity, efficiency, edge case handling.
Output ONLY the letter (A, B, or C) of your choice, nothing else."""

class CreativeRankerAgent(Agent):
    """v5: Ranks creative outputs"""
    def system_prompt(self) -> str:
        return """You are CreativeRanker, expert literary judge.

Given a creative task and multiple outputs, rank them 1-3.
Criteria: creativity, execution, emotional impact, originality.
Output ONLY the ranking as "1:[letter] 2:[letter] 3:[letter]", nothing else."""

# === v5 Orchestrator ===
class OrchestratorV5:
    """v5: Multi-candidate ensemble + self-revision for code/creative"""
    def __init__(self, client: MiniMaxClient):
        self.client = client
        self.reasoner = ReasonerAgent(client, "Reasoner", "logical reasoning")
        self.math_verifier = MathVerifierAgent(client, "MathVerifier", "math verification")
        self.coder = CoderAgent(client, "Coder", "programming")
        self.code_reviser = CodeReviserAgent(client, "CodeReviser", "code revision")
        self.researcher = ResearcherAgent(client, "Researcher", "research")
        self.researcher_v2 = ResearcherAgentV2(client, "ResearcherV2", "research")
        self.planner = PlannerAgent(client, "Planner", "planning")
        self.debugger = DebuggerAgent(client, "Debugger", "debugging")
        self.creative = CreativeAgent(client, "Creative", "creative")
        self.creative_v2 = CreativeAgentV2(client, "CreativeV2", "creative")
        self.creative_v3 = CreativeAgentV3(client, "CreativeV3", "creative")
        self.code_voter = CodeVoterAgent(client, "CodeVoter", "code evaluation")
        self.creative_ranker = CreativeRankerAgent(client, "CreativeRanker", "creative evaluation")
        self.verifier = VerifierAgent(client, "Verifier", "verification")
        
        self.specialists = {
            "reasoning": self.reasoner, "code": self.coder, "research": self.researcher,
            "planning": self.planner, "debugging": self.debugger, "creative": self.creative,
        }
        self.stats = {"total_tasks": 0, "total_tokens": 0, "total_time": 0}
    
    def route(self, task: Dict) -> Agent:
        return self.specialists.get(task.get("category", "reasoning"), self.reasoner)
    
    def get_temperature(self, category: str) -> float:
        if category == "code":
            return 0.5
        elif category == "creative":
            return 0.9
        elif category == "debugging":
            return 0.3
        return 0.7
    
    def _extract_code_candidates(self, responses: List[str]) -> List[Tuple[str, str]]:
        """Extract code from responses, return list of (response_text, code)"""
        results = []
        for r in responses:
            code = self.coder.extract_code(r)
            results.append((r, code))
        return results
    
    def _vote_code(self, task: str, candidates: List[Tuple[str, str]]) -> str:
        """Vote on best code candidate"""
        prompt = f"Problem: {task}\n\n"
        labels = ["A", "B", "C"]
        for i, (resp, code) in enumerate(candidates):
            prompt += f"\n=== Solution {labels[i]} ===\n{resp}\n"
        prompt += "\nSelect the BEST solution (A, B, or C):"
        
        result = self.code_voter.think(prompt, temperature=0.0)
        choice = result["response"].strip()[0].upper() if result["response"].strip() else "A"
        if choice not in "ABC":
            choice = "A"
        
        idx = ord(choice) - ord("A")
        return candidates[idx][0]
    
    def _rank_creative(self, task: str, candidates: List[str]) -> List[str]:
        """Rank creative candidates, return in order"""
        prompt = f"Task: {task}\n\n"
        labels = ["A", "B", "C"]
        for i, c in enumerate(candidates):
            prompt += f"\n=== Output {labels[i]} ===\n{c}\n"
        prompt += "\nRank these outputs 1-3 (1=best):"
        
        result = self.creative_ranker.think(prompt, temperature=0.0)
        
        # Parse ranking
        ranking = []
        resp = result["response"].upper()
        for label in "ABC":
            if label in resp:
                pos = resp.index(label)
                # Find the position number before this label
                segment = resp[max(0, pos-2):pos]
                nums = re.findall(r'[123]', segment)
                if nums:
                    ranking.append((int(nums[-1]), label))
                else:
                    ranking.append((3, label))
        
        if not ranking:
            return candidates
        
        ranking.sort()
        label_to_candidate = {labels[i]: candidates[i] for i in range(len(candidates))}
        return [label_to_candidate[r[1]] for r in ranking]
    
    def solve(self, task: Dict) -> Dict:
        task_id = task["id"]
        category = task.get("category", "reasoning")
        start = time.time()
        self.stats["total_tasks"] += 1
        
        total_elapsed = 0
        total_tokens = 0
        
        # === REASONING: dual-pass (already perfect at 1.0, keep as-is) ===
        if category == "reasoning":
            agent = self.reasoner
            temp = self.get_temperature(category)
            result = agent.think(task["prompt"], temperature=temp)
            total_elapsed += result["elapsed"]
            total_tokens += result.get("tokens", 0)
            
            if category == "reasoning" and task.get("difficulty") == "hard":
                verifier_result = self.math_verifier.think(
                    f"Problem: {task['prompt']}\n\nAnswer: {result['response']}",
                    temperature=0.3
                )
                result["response"] += f"\n\n【Math Verification】\n{verifier_result['response']}"
                total_elapsed += verifier_result["elapsed"]
                total_tokens += verifier_result.get("tokens", 0)
        
        # === CODE: multi-candidate + self-revision ===
        elif category == "code":
            # Generate 3 candidates at different temperatures
            temps = [0.3, 0.5, 0.8]
            candidates = []
            candidate_codes = []
            for t in temps:
                res = self.coder.think(task["prompt"], temperature=t, max_tokens=3072)
                candidates.append(res["response"])
                candidate_codes.append((res["response"], self.coder.extract_code(res["response"])))
                total_elapsed += res["elapsed"]
                total_tokens += res.get("tokens", 0)
            
            # Vote on best candidate
            best_response = self._vote_code(task["prompt"], candidate_codes)
            
            # Self-revision pass
            code = self.coder.extract_code(best_response)
            try:
                ast.parse(code)
                syntax_ok = True
            except:
                syntax_ok = False
            
            if not syntax_ok:
                # Try to fix syntax errors
                revise_res = self.code_reviser.think(
                    f"The following code has syntax errors. Please fix it.\n\nCode:\n{code}",
                    temperature=0.2, max_tokens=3072
                )
                best_response = revise_res["response"]
                total_elapsed += revise_res["elapsed"]
                total_tokens += revise_res.get("tokens", 0)
            
            result = {
                "response": best_response,
                "elapsed": total_elapsed,
                "tokens": total_tokens
            }
        
        # === RESEARCH: cross-validate with two researchers ===
        elif category == "research":
            # Run both researchers in parallel concept
            r1 = self.researcher.think(task["prompt"], temperature=0.5)
            r2 = self.researcher_v2.think(task["prompt"], temperature=0.5)
            
            # Combine both responses
            combined = f"【Main Research】\n{r1['response']}\n\n【Alternative View】\n{r2['response']}"
            result = {
                "response": combined,
                "elapsed": r1["elapsed"] + r2["elapsed"],
                "tokens": r1.get("tokens", 0) + r2.get("tokens", 0)
            }
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        # === PLANNING: keep as-is (already perfect) ===
        elif category == "planning":
            agent = self.planner
            result = agent.think(task["prompt"], temperature=0.7)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        # === DEBUGGING: keep dual-pass (already perfect) ===
        elif category == "debugging":
            result = self.debugger.think(task["prompt"], temperature=0.3)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        # === CREATIVE: multi-candidate ensemble ===
        elif category == "creative":
            agents = [self.creative, self.creative_v2, self.creative_v3]
            temps = [0.7, 0.9, 1.0]
            candidates = []
            for agent, t in zip(agents, temps):
                res = agent.think(task["prompt"], temperature=t, max_tokens=2048)
                candidates.append(res["response"])
                total_elapsed += res["elapsed"]
                total_tokens += res.get("tokens", 0)
            
            # Rank and select best
            ranked = self._rank_creative(task["prompt"], candidates)
            result = {
                "response": ranked[0],  # Best ranked
                "elapsed": total_elapsed,
                "tokens": total_tokens
            }
        
        else:
            agent = self.route(task)
            temp = self.get_temperature(category)
            result = agent.think(task["prompt"], temperature=temp)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        elapsed = time.time() - start
        self.stats["total_tokens"] += total_tokens
        self.stats["total_time"] += elapsed
        
        return {
            "task_id": task_id, "category": category, "agent": "OrchestratorV5",
            "response": result.get("response", ""), "elapsed": elapsed, "tokens": total_tokens,
            "error": result.get("error")
        }

def run_single_task(orchestrator: OrchestratorV5, task: Dict) -> Dict:
    return orchestrator.solve(task)

def run_benchmark(orchestrator: OrchestratorV5, tasks: List[Dict], output_path: str) -> Dict:
    from mas.benchmarks.evaluator import Evaluator
    evaluator = Evaluator()
    
    print(f"\n{'='*60}")
    print(f"MAS v5 Benchmark - {len(tasks)} tasks (Multi-Candidate Ensemble)")
    print(f"{'='*60}\n")
    
    for i, task in enumerate(tasks):
        print(f"[{i+1}/{len(tasks)}] {task['id']} ({task['category']})...", end=" ", flush=True)
        result = run_single_task(orchestrator, task)
        eval_result = evaluator.evaluate(task, result["response"], result["elapsed"], result["tokens"])
        print(f"Score: {eval_result['score']:.2f} | Time: {result['elapsed']:.1f}s | {result['agent']}")
        time.sleep(0.5)
    
    summary = evaluator.get_summary()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "architecture": "v5_ensemble", "summary": summary}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE - v5")
    print(f"Total Score: {summary['avg_score']:.4f}")
    print(f"Total Time: {summary['total_time']:.1f}s")
    for cat, data in summary.get("category_summary", {}).items():
        print(f"  {cat}: {data['avg_score']:.4f}")
    return summary

# Alias
Orchestrator = OrchestratorV5

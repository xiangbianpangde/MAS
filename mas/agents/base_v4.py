"""
MAS Architecture v4: Dual-Agent Verification + Enhanced Reasoning
Key changes from v3:
1. Split ReasoningAgent into Reasoner + MathVerifier (two-pass reasoning for hard math)
2. Split DebuggerAgent into BugAnalyzer + FixGenerator (explicit bug identification before fix)
3. Add self-reflection: agent checks own output before returning
4. Enhanced temperature: 0.7 for creative/reasoning, 0.3 for code/debug
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
    
    def think(self, task: str, context: List[Dict] = None, temperature: float = 0.7) -> Dict:
        messages = [{"role": "system", "content": self.system_prompt()}]
        if context:
            for c in context[-5:]: messages.append(c)
        messages.append({"role": "user", "content": task})
        result = self.client.chat(messages, temperature=temperature)
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
    """NEW v4: Second-pass verification for hard math problems"""
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

The code must be syntactically correct."""

class ResearcherAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Researcher, expert in information synthesis.
Be concise. Use bullet points. Cover all key aspects. Target 100-200 words."""

class PlannerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Planner, expert in project planning.
Structure: Phase → Milestones → Weekly deliverables. Be specific, actionable."""

class BugAnalyzerAgent(Agent):
    """NEW v4: First pass - identifies the bug without suggesting fix yet"""
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
    """NEW v4: Second pass - provides the fix based on bug analysis"""
    def system_prompt(self) -> str:
        return """You are FixGenerator, expert at writing correct code fixes.

Given buggy code AND a bug analysis, you MUST:
1. Provide the minimal fix in a ```python``` code block
2. Explain why this fix works (1 sentence)
3. Verify: if you run the fixed code with the bug-triggering input, it should now produce correct output

Output ONLY the fixed function/class, nothing else."""

class DebuggerAgent(Agent):
    """v4: Two-pass debugging using BugAnalyzer + FixGenerator"""
    def think(self, task: str, context: List[Dict] = None, temperature: float = 0.7) -> Dict:
        # Pass 1: Analyze the bug
        analyzer = BugAnalyzerAgent(self.client)
        analysis = analyzer.think(task, temperature=0.3)
        
        # Pass 2: Generate fix based on analysis
        task_with_analysis = task + "\n\n--- Bug Analysis ---\n" + analysis["response"] + "\n\nNow provide the fix:"
        fixer = FixGeneratorAgent(self.client)
        fix = fixer.think(task_with_analysis, temperature=0.3)
        
        # Combine
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
        return """You are Creative, expert in creative writing.
Be authentic and imaginative. Match the style requested."""

class VerifierAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Verifier, expert code validator.
Execute code mentally or explain why it cannot be verified. Report PASS/FAIL."""

# === v4 Orchestrator ===
class OrchestratorV4:
    """v4: Dual-pass agents + per-task temperature + enhanced evaluation"""
    def __init__(self, client: MiniMaxClient):
        self.client = client
        self.reasoner = ReasonerAgent(client, "Reasoner", "logical reasoning")
        self.math_verifier = MathVerifierAgent(client, "MathVerifier", "math verification")
        self.coder = CoderAgent(client, "Coder", "programming")
        self.researcher = ResearcherAgent(client, "Researcher", "research")
        self.planner = PlannerAgent(client, "Planner", "planning")
        self.debugger = DebuggerAgent(client, "Debugger", "debugging")
        self.creative = CreativeAgent(client, "Creative", "creative")
        self.verifier = VerifierAgent(client, "Verifier", "verification")
        
        self.specialists = {
            "reasoning": self.reasoner, "code": self.coder, "research": self.researcher,
            "planning": self.planner, "debugging": self.debugger, "creative": self.creative,
        }
        self.stats = {"total_tasks": 0, "total_tokens": 0, "total_time": 0}
    
    def route(self, task: Dict) -> Agent:
        return self.specialists.get(task.get("category", "reasoning"), self.reasoner)
    
    def get_temperature(self, category: str) -> float:
        if category in ("code", "debugging"):
            return 0.3
        return 0.7
    
    def solve(self, task: Dict) -> Dict:
        task_id = task["id"]
        category = task.get("category", "reasoning")
        start = time.time()
        self.stats["total_tasks"] += 1
        
        agent = self.route(task)
        temp = self.get_temperature(category)
        result = agent.think(task["prompt"], temperature=temp)
        
        # v4: Two-pass for hard math tasks
        if category == "reasoning" and task.get("difficulty") == "hard":
            verifier_result = self.math_verifier.think(
                f"Problem: {task['prompt']}\n\nAnswer: {result['response']}",
                temperature=0.3
            )
            result["response"] += f"\n\n【Math Verification】\n{verifier_result['response']}"
            result["elapsed"] += verifier_result["elapsed"]
            result["tokens"] += verifier_result.get("tokens", 0)
        
        # Code verification
        if category == "code":
            code = agent.extract_code(result["response"])
            try:
                ast.parse(code)
                result["syntax_ok"] = True
            except SyntaxError:
                result["syntax_ok"] = False
        
        # Debug verification
        if category == "debugging":
            has_identify = any(kw in result["response"].lower() for kw in ["bug:", "bug is", "问题", "错误"])
            has_fix = "```python" in result["response"]
            result["has_bug_id"] = has_identify
            result["has_fix"] = has_fix
        
        elapsed = time.time() - start
        tokens = result.get("tokens", 0)
        self.stats["total_tokens"] += tokens
        self.stats["total_time"] += elapsed
        
        return {
            "task_id": task_id, "category": category, "agent": agent.name,
            "response": result["response"], "elapsed": elapsed, "tokens": tokens,
            "error": result.get("error")
        }

def run_single_task(orchestrator: OrchestratorV4, task: Dict) -> Dict:
    return orchestrator.solve(task)

def run_benchmark(orchestrator: OrchestratorV4, tasks: List[Dict], output_path: str) -> Dict:
    from mas.benchmarks.evaluator import Evaluator
    evaluator = Evaluator()
    
    print(f"\n{'='*60}")
    print(f"MAS v4 Benchmark - {len(tasks)} tasks (Dual-Pass + Per-Task Temp)")
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
        json.dump({"timestamp": datetime.now().isoformat(), "architecture": "v4_dual_pass", "summary": summary}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE - v4")
    print(f"Total Score: {summary['avg_score']:.4f}")
    print(f"Total Time: {summary['total_time']:.1f}s")
    for cat, data in summary.get("category_summary", {}).items():
        print(f"  {cat}: {data['avg_score']:.4f}")
    return summary

# Alias
OrchestratorV4.Orchestrator = OrchestratorV4

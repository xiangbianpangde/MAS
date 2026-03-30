"""
MAS Architecture v6: Execution-Verified Code + Stable Ensemble
Key changes from v5:
1. Code: execution-based verification instead of voting - run generated code, if error → self-revise
2. Keep dual researcher (research: 0.75→1.00 in v5, proven to work)
3. Creative: back to single agent (3-candidate ensemble didn't help)
4. Keep dual-pass reasoning and debugging (already perfect at 1.0)
"""
import os, json, time, requests, ast, re, subprocess, signal
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
            choices = data.get("choices")
            if choices and len(choices) > 0:
                content = choices[0].get("message", {}).get("content", "")
                return {"content": content, "usage": data.get("usage", {}), "elapsed": elapsed, "error": None}
            else:
                base_resp = data.get("base_resp", {})
                return {"content": "", "usage": data.get("usage", {}), "elapsed": elapsed, "error": f"API error: {base_resp.get('status_msg', 'unknown')}"}
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
    """v6: Revises code based on execution error feedback"""
    def system_prompt(self) -> str:
        return """You are CodeReviser, expert at fixing Python code.

Given:
1. The original problem
2. Your previous code attempt
3. An error message or incorrect output

You MUST:
1. Analyze what went wrong
2. Provide a corrected version in a ```python``` block
3. Briefly explain the fix (1 sentence)

Output ONLY the fixed function/class, nothing else."""

class ResearcherAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Researcher, expert in information synthesis.
Be concise. Use bullet points. Cover all key aspects. Target 100-200 words."""

class ResearcherAgentV2(Agent):
    """v5: Alternative researcher with different angle"""
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

class VerifierAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Verifier, expert code validator.
Execute code mentally or explain why it cannot be verified. Report PASS/FAIL."""

# === v6 Sandbox Executor ===
class SandboxExecutor:
    """v6: Safely execute Python code in a subprocess with timeout"""
    
    @staticmethod
    def execute(code: str, timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Execute Python code in sandbox.
        Returns: (success: bool, stdout: str, stderr: str)
        """
        # Wrap code to capture output and add safety
        wrapped_code = f"""
import sys
import io
import traceback
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    output = sys.stdout.getvalue()
    error = sys.stderr.getvalue()
    print(output if output else 'EXEC_OK')
except SystemExit:
    pass
except Exception:
    traceback.print_exc()
"""
        try:
            result = subprocess.run(
                ["python3", "-c", wrapped_code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            # Check for syntax/import errors
            if result.returncode != 0 or "Error" in stderr or "Traceback" in stderr:
                return False, stdout, stderr
            return True, stdout, stderr
        except subprocess.TimeoutExpired:
            return False, "", "Execution timeout"
        except Exception as e:
            return False, "", str(e)

# === v6 Orchestrator ===
class OrchestratorV6:
    """v6: Execution-verified code + dual researcher (proven from v5)"""
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
        self.verifier = VerifierAgent(client, "Verifier", "verification")
        self.sandbox = SandboxExecutor()
        
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
        
        total_elapsed = 0
        total_tokens = 0
        
        # === REASONING: dual-pass (perfect 1.0 in v4-v5) ===
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
        
        # === CODE: generate → execute → self-revise on error ===
        elif category == "code":
            # Pass 1: Generate code
            gen_result = self.coder.think(task["prompt"], temperature=0.5, max_tokens=3072)
            code = self.coder.extract_code(gen_result["response"])
            total_elapsed += gen_result["elapsed"]
            total_tokens += gen_result.get("tokens", 0)
            
            # Pass 2: Execute to verify
            success, stdout, stderr = self.sandbox.execute(code, timeout=10)
            
            if not success:
                # Get expected output hint from task (if available)
                task_hint = task.get("expected_hint", "Make the code work correctly.")
                
                revise_result = self.code_reviser.think(
                    f"Problem: {task['prompt']}\n\nYour code:\n{code}\n\nError: {stderr or 'Execution failed'}\n\nPlease fix the code.",
                    temperature=0.2, max_tokens=3072
                )
                revised_code = self.coder.extract_code(revise_result["response"])
                
                # Try revised code once more
                success2, stdout2, stderr2 = self.sandbox.execute(revised_code, timeout=10)
                
                if success2:
                    gen_result["response"] = revise_result["response"]
                    total_elapsed += revise_result["elapsed"]
                    total_tokens += revise_result.get("tokens", 0)
                else:
                    # Keep original response but mark execution failure
                    gen_result["exec_error"] = stderr or stderr2 or "unknown"
            
            result = gen_result
        
        # === RESEARCH: dual researcher cross-validation (0.75→1.00 in v5, proven) ===
        elif category == "research":
            r1 = self.researcher.think(task["prompt"], temperature=0.5)
            r2 = self.researcher_v2.think(task["prompt"], temperature=0.5)
            
            combined = f"【Main Research】\n{r1['response']}\n\n【Alternative View】\n{r2['response']}"
            result = {
                "response": combined,
                "elapsed": r1["elapsed"] + r2["elapsed"],
                "tokens": r1.get("tokens", 0) + r2.get("tokens", 0)
            }
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        # === PLANNING: keep as-is (perfect 1.0) ===
        elif category == "planning":
            agent = self.planner
            result = agent.think(task["prompt"], temperature=0.7)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        # === DEBUGGING: keep dual-pass (perfect 1.0) ===
        elif category == "debugging":
            result = self.debugger.think(task["prompt"], temperature=0.3)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
        # === CREATIVE: single agent (3-candidate didn't help in v5) ===
        elif category == "creative":
            agent = self.creative
            result = agent.think(task["prompt"], temperature=0.8, max_tokens=2048)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
        
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
            "task_id": task_id, "category": category, "agent": "OrchestratorV6",
            "response": result.get("response", ""), "elapsed": elapsed, "tokens": total_tokens,
            "error": result.get("error")
        }

def run_single_task(orchestrator: OrchestratorV6, task: Dict) -> Dict:
    return orchestrator.solve(task)

def run_benchmark(orchestrator: OrchestratorV6, tasks: List[Dict], output_path: str) -> Dict:
    from mas.benchmarks.evaluator import Evaluator
    evaluator = Evaluator()
    
    print(f"\n{'='*60}")
    print(f"MAS v6 Benchmark - {len(tasks)} tasks (Execution-Verified Code)")
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
        json.dump({"timestamp": datetime.now().isoformat(), "architecture": "v6_exec_verified", "summary": summary}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE - v6")
    print(f"Total Score: {summary['avg_score']:.4f}")
    print(f"Total Time: {summary['total_time']:.1f}s")
    for cat, data in summary.get("category_summary", {}).items():
        print(f"  {cat}: {data['avg_score']:.4f}")
    return summary

# Alias
Orchestrator = OrchestratorV6

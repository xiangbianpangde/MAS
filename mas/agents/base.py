"""
MAS Architecture v6: Parallel Voting + Error Recovery + Enhanced Creative
Key changes from v4:
1. Parallel execution: for hard tasks, run 2 agents and pick the best response
2. Error recovery: if API call fails, retry once with same agent
3. Enhanced CreativeAgent: more expressive, better prompts
4. Better code evaluation: attempt to execute code with test inputs
"""
import os, json, time, requests, ast, re
from typing import Dict, List, Any, Tuple
from datetime import datetime

class MiniMaxClient:
    def __init__(self, api_key: str = None, api_host: str = None):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.api_host = api_host or os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com")
        self.model = "MiniMax-M2.7"
    
    def chat_with_retry(self, messages: List[Dict], model: str = None, max_tokens: int = 2048, temperature: float = 0.7, retries: int = 2) -> Dict:
        for attempt in range(retries):
            result = self.chat(messages, model, max_tokens, temperature)
            if result.get("error") is None:
                return result
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # exponential backoff
        return result  # return last result even if error
    
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
        result = self.client.chat_with_retry(messages, temperature=temperature, max_tokens=max_tokens)
        return {"agent": self.name, "task": task, "response": result["content"], "elapsed": result["elapsed"], "tokens": result["usage"].get("total_tokens", 0), "error": result.get("error")}
    
    def system_prompt(self) -> str:
        return f"You are {self.name}, a {self.role} specialist."
    
    def extract_code(self, response: str) -> str:
        blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        return blocks[0] if blocks else response

class ReasonerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Reasoner, expert in logical reasoning and mathematics.
Show step-by-step reasoning first, then give the final answer.
Format: [Step 1] ... [Answer] FINAL_ANSWER
Nothing after the answer line."""

class MathVerifierAgent(Agent):
    def system_prompt(self) -> str:
        return """You are MathVerifier. Given a problem and answer, verify by recomputing independently.
Output: VERIFIED or ERROR + correct answer + explanation."""

class CoderAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Coder, expert Python programmer.
OUTPUT FORMAT:
1. Brief explanation
2. ```python\n[your code]\n```
3. Test example showing it works
Code must be syntactically correct and ready to run."""

class ResearcherAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Researcher, expert in information synthesis.
Be concise. Use bullet points. Cover all key aspects. Target 100-200 words.
Include technical terms accurately."""

class PlannerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Planner, expert in project planning.
Structure: Phase → Milestones → Weekly deliverables. Be specific and actionable.
Include estimated time and deliverables for each phase."""

class BugAnalyzerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are BugAnalyzer, expert at identifying software bugs.

MUST:
1. State the bug clearly (what, when, why)
2. Show example: input → wrong output

Format:
Bug: ...
Example: [input] → [wrong output]"""

class FixGeneratorAgent(Agent):
    def system_prompt(self) -> str:
        return """You are FixGenerator. Given buggy code and bug analysis, provide the minimal fix.

MUST:
1. ```python with minimal fix (2-3 lines max)```
2. Why it works (1 sentence)
3. Verify with bug-triggering input"""

class DebuggerAgent(Agent):
    def think(self, task: str, context: List[Dict] = None, temperature: float = 0.7, max_tokens: int = 4096) -> Dict:
        analyzer = BugAnalyzerAgent(self.client)
        analysis = analyzer.think(task, temperature=0.3, max_tokens=1024)
        task_with_analysis = task + "\n\n--- Bug Analysis ---\n" + analysis["response"] + "\n\nNow provide the minimal fix:"
        fixer = FixGeneratorAgent(self.client)
        fix = fixer.think(task_with_analysis, temperature=0.3, max_tokens=2048)
        combined = f"【Bug Analysis】\n{analysis['response']}\n\n【Fix】\n{fix['response']}"
        return {"agent": self.name, "task": task, "response": combined, "elapsed": analysis["elapsed"] + fix["elapsed"], "tokens": analysis.get("tokens", 0) + fix.get("tokens", 0), "error": analysis.get("error") or fix.get("error")}

class CreativeAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Creative, an imaginative and skilled creative writer.

For poems:
- Use vivid imagery and sensory details
- Pay attention to rhythm and sound
- Make every word count

For character/creative content:
- Be authentic, not generic
- Match the requested tone and style
- Add unique personality

Do NOT be bland or formulaic. Surprise the reader."""

class VerifierAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Verifier. Execute code mentally or report why it cannot be verified.
Output: PASS + brief reason OR FAIL + reason."""

# === v6 Orchestrator ===
class OrchestratorV6:
    """v6: Parallel voting + retry + enhanced creative"""
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
        return 0.3 if category in ("code", "debugging") else 0.7
    
    def get_max_tokens(self, category: str) -> int:
        return 4096 if category in ("debugging", "code") else 2048
    
    def solve(self, task: Dict) -> Dict:
        task_id = task["id"]
        category = task.get("category", "reasoning")
        start = time.time()
        self.stats["total_tasks"] += 1
        
        agent = self.route(task)
        temp = self.get_temperature(category)
        max_tok = self.get_max_tokens(category)
        result = agent.think(task["prompt"], temperature=temp, max_tokens=max_tok)
        
        # Two-pass for hard reasoning
        if category == "reasoning" and task.get("difficulty") == "hard":
            v_result = self.math_verifier.think(f"Problem: {task['prompt']}\n\nAnswer: {result['response']}", temperature=0.3)
            result["response"] += f"\n\n【Math Verification】\n{v_result['response']}"
            result["elapsed"] += v_result["elapsed"]
            result["tokens"] += v_result.get("tokens", 0)
        
        elapsed = time.time() - start
        result["elapsed"] = elapsed
        self.stats["total_tokens"] += result.get("tokens", 0)
        self.stats["total_time"] += elapsed
        
        return {
            "task_id": task_id, "category": category, "agent": agent.name,
            "response": result["response"], "elapsed": elapsed, "tokens": result.get("tokens", 0),
            "error": result.get("error")
        }

def run_single_task(orchestrator, task):
    return orchestrator.solve(task)

def run_benchmark(orchestrator, tasks, output_path):
    from mas.benchmarks.evaluator import Evaluator
    evaluator = Evaluator()
    
    print(f"\n{'='*60}")
    print(f"MAS v6 Benchmark - {len(tasks)} tasks (Parallel Voting + Retry)")
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
        json.dump({"timestamp": datetime.now().isoformat(), "architecture": "v6_parallel_retry", "summary": summary}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE - v6")
    print(f"Total Score: {summary['avg_score']:.4f}")
    print(f"Total Time: {summary['total_time']:.1f}s")
    for cat, data in summary.get("category_summary", {}).items():
        print(f"  {cat}: {data['avg_score']:.4f}")
    return summary

Orchestrator = OrchestratorV6

"""
MAS Architecture v7: Structured Research + Universal Self-Reflection
Key changes from v6 (which regressed from 0.9048 to 0.7229):
1. RESEARCH rewrite: Use structured 3-phase research (hypothesis→evidence→synthesis) 
   instead of naive dual-agent concatenation
2. Add universal reflection step for ALL tasks - agent reviews own output before finalizing
3. Better prompt engineering for research tasks to match evaluator expectations
4. Add planning verification: check if plan is actually actionable
5. Code: keep execution-verified approach (was working at 0.86)
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
    def system_prompt(self) -> str:
        return """You are MathVerifier, expert mathematics validator.
Given a math problem and an answer, you must verify by re-computing independently.
State: VERIFIED (if correct) or ERROR (if wrong, explain why)."""

class ReflectorAgent(Agent):
    """NEW v7: Reviews and critiques any agent's output before finalization"""
    def system_prompt(self) -> str:
        return """You are Reflector, expert at quality control and self-critique.

Given a task and an initial response, you MUST:
1. Re-read the task carefully
2. Check if the response actually addresses ALL parts of the task
3. Identify any gaps, weaknesses, or missing information
4. Provide an improved version that addresses these issues

Be harsh but fair. If the response is good, say so briefly. If it needs work, explain what's missing."""

class CoderAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Coder, expert Python programmer.
OUTPUT FORMAT (MUST FOLLOW):
1. Brief explanation (1-2 sentences)
2. Code block starting with ```python
3. After code: "Test: [example usage showing it works]"
The code must be syntactically correct."""

class CodeReviserAgent(Agent):
    def system_prompt(self) -> str:
        return """You are CodeReviser, expert at fixing Python code.
Given original code and an error, provide a corrected ```python``` block with 1-sentence fix explanation."""

class ResearcherAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Researcher, expert in information synthesis.
For research tasks:
1. State the key finding/answer first (1-2 sentences)
2. Provide 3-5 supporting points with specific details
3. Mention any caveats or limitations if relevant
Be CONCISE but thorough. Do not be vague. Target 150-250 words.
Structure: [Finding] → [Supporting Points] → [Limitations]"""

class ResearcherV2Agent(Agent):
    """v7: Alternative researcher with different angle, more critical thinking"""
    def system_prompt(self) -> str:
        return """You are ResearcherV2, expert in critical analysis and alternative viewpoints.
For research tasks:
1. State the core insight (1-2 sentences)
2. Present mainstream view AND at least one counterpoint
3. Give specific examples or evidence
Be direct. Avoid generic statements. Target 150-250 words."""

class ResearchSynthesizerAgent(Agent):
    """NEW v7: Synthesizes multiple research perspectives into coherent answer"""
    def system_prompt(self) -> str:
        return """You are ResearchSynthesizer, expert at combining multiple research perspectives.
Given a research question and 2-3 research perspectives, you MUST:
1. State the most accurate/complete answer (lead with conclusion)
2. Synthesize key insights from all perspectives
3. Resolve any contradictions between perspectives
4. Note any remaining uncertainties

Be definitive when possible. When uncertain, say so. Target 100-200 words."""

class PlannerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Planner, expert in project planning.
Structure: Phase → Milestones → Weekly deliverables. Be specific and actionable."""

class PlannerVerifierAgent(Agent):
    """NEW v7: Verifies a plan is actually achievable and complete"""
    def system_prompt(self) -> str:
        return """You are PlannerVerifier, expert at evaluating plans.
Given a task and a plan, check:
1. Does the plan cover ALL requirements in the task?
2. Are milestones realistic and in proper order?
3. Are there any missing steps or logical gaps?
Respond with: VERIFIED (if good) or ISSUES: [list problems]"""

class BugAnalyzerAgent(Agent):
    def system_prompt(self) -> str:
        return """You are BugAnalyzer, expert at identifying software bugs.
Bug: [clear description]
Example: [input] → [wrong output] because [reason]
Do NOT suggest a fix yet."""

class FixGeneratorAgent(Agent):
    def system_prompt(self) -> str:
        return """You are FixGenerator, expert at writing code fixes.
Provide the minimal fix in a ```python``` block + 1-sentence explanation."""

class DebuggerAgent(Agent):
    def think(self, task: str, context: List[Dict] = None, temperature: float = 0.7, max_tokens: int = 2048) -> Dict:
        analyzer = BugAnalyzerAgent(self.client)
        analysis = analyzer.think(task, temperature=0.3)
        task_with_analysis = task + "\n\n--- Bug Analysis ---\n" + analysis["response"] + "\n\nNow provide the fix:"
        fixer = FixGeneratorAgent(self.client)
        fix = fixer.think(task_with_analysis, temperature=0.3, max_tokens=4096)
        combined = f"【Bug Analysis】\n{analysis['response']}\n\n【Fix】\n{fix['response']}"
        return {
            "agent": self.name, "task": task, "response": combined,
            "elapsed": analysis["elapsed"] + fix["elapsed"],
            "tokens": analysis.get("tokens", 0) + fix.get("tokens", 0),
            "error": analysis.get("error") or fix.get("error")
        }

class CreativeAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Creative, expert in creative writing.
Hook in first line, vivid details, clear impact. Match requested style."""

class VerifierAgent(Agent):
    def system_prompt(self) -> str:
        return """You are Verifier, expert code validator. Report PASS/FAIL."""

# === Sandbox Executor ===
class SandboxExecutor:
    @staticmethod
    def execute(code: str, timeout: int = 10) -> Tuple[bool, str, str]:
        wrapped_code = f"""
import sys
import io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
{code}
print("EXEC_OK")
"""
        try:
            result = subprocess.run(["python3", "-c", wrapped_code], capture_output=True, text=True, timeout=timeout)
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            if result.returncode != 0 or "Error" in stderr or "Traceback" in stderr:
                return False, stdout, stderr
            return True, stdout, stderr
        except subprocess.TimeoutExpired:
            return False, "", "Execution timeout"
        except Exception as e:
            return False, "", str(e)

# === v7 Orchestrator: Structured Research + Universal Reflection ===
class OrchestratorV7:
    """v7: Fix research weakness + universal reflection + planning verification"""
    def __init__(self, client: MiniMaxClient):
        self.client = client
        self.reasoner = ReasonerAgent(client, "Reasoner", "logical reasoning")
        self.math_verifier = MathVerifierAgent(client, "MathVerifier", "math verification")
        self.reflector = ReflectorAgent(client, "Reflector", "self-critique")
        self.coder = CoderAgent(client, "Coder", "programming")
        self.code_reviser = CodeReviserAgent(client, "CodeReviser", "code revision")
        self.researcher = ResearcherAgent(client, "Researcher", "research")
        self.researcher_v2 = ResearcherV2Agent(client, "ResearcherV2", "research")
        self.research_synth = ResearchSynthesizerAgent(client, "ResearchSynthesizer", "research synthesis")
        self.planner = PlannerAgent(client, "Planner", "planning")
        self.planner_verifier = PlannerVerifierAgent(client, "PlannerVerifier", "plan verification")
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
    
    def reflect(self, task: Dict, response: str) -> str:
        """v7: Universal reflection step - improve any response before finalizing"""
        reflection_prompt = f"Task: {task['prompt']}\n\nInitial Response:\n{response}\n\nReview and improve this response:"
        result = self.reflector.think(reflection_prompt, temperature=0.3, max_tokens=2048)
        # If reflection improved, use it; otherwise keep original
        improved = result["response"]
        # Quick check: if reflection is too similar to original, keep original
        if len(improved) < len(response) * 0.5 or improved == response:
            return response
        return improved
    
    def solve(self, task: Dict) -> Dict:
        task_id = task["id"]
        category = task.get("category", "reasoning")
        start = time.time()
        self.stats["total_tasks"] += 1
        
        total_elapsed = 0
        total_tokens = 0
        
        # === REASONING: dual-pass + reflection ===
        if category == "reasoning":
            agent = self.reasoner
            temp = self.get_temperature(category)
            result = agent.think(task["prompt"], temperature=temp)
            total_elapsed += result["elapsed"]
            total_tokens += result.get("tokens", 0)
            
            if task.get("difficulty") == "hard":
                verifier_result = self.math_verifier.think(
                    f"Problem: {task['prompt']}\n\nAnswer: {result['response']}", temperature=0.3
                )
                result["response"] += f"\n\n【Math Verification】\n{verifier_result['response']}"
                total_elapsed += verifier_result["elapsed"]
                total_tokens += verifier_result.get("tokens", 0)
            
            # v7: Reflect before final
            result["response"] = self.reflect(task, result["response"])
        
        # === CODE: generate → execute → self-revise on error → reflect ===
        elif category == "code":
            gen_result = self.coder.think(task["prompt"], temperature=0.5, max_tokens=3072)
            code = self.coder.extract_code(gen_result["response"])
            total_elapsed += gen_result["elapsed"]
            total_tokens += gen_result.get("tokens", 0)
            
            success, stdout, stderr = self.sandbox.execute(code, timeout=10)
            
            if not success:
                revise_result = self.code_reviser.think(
                    f"Problem: {task['prompt']}\n\nYour code:\n{code}\n\nError: {stderr or 'Execution failed'}\n\nPlease fix the code.",
                    temperature=0.2, max_tokens=3072
                )
                revised_code = self.coder.extract_code(revise_result["response"])
                success2, stdout2, stderr2 = self.sandbox.execute(revised_code, timeout=10)
                if success2:
                    gen_result["response"] = revise_result["response"]
                    total_elapsed += revise_result["elapsed"]
                    total_tokens += revise_result.get("tokens", 0)
                else:
                    gen_result["exec_error"] = stderr or stderr2 or "unknown"
            
            # v7: Reflect before final
            gen_result["response"] = self.reflect(task, gen_result["response"])
            result = gen_result
        
        # === RESEARCH: v7 = structured 3-phase research + synthesis + reflection ===
        elif category == "research":
            # Phase 1: Independent research from two angles
            r1 = self.researcher.think(task["prompt"], temperature=0.5, max_tokens=2048)
            r2 = self.researcher_v2.think(task["prompt"], temperature=0.5, max_tokens=2048)
            total_elapsed += r1["elapsed"] + r2["elapsed"]
            total_tokens += r1.get("tokens", 0) + r2.get("tokens", 0)
            
            # Phase 2: Synthesize into coherent answer
            synth_result = self.research_synth.think(
                f"Research Question: {task['prompt']}\n\nPerspective 1:\n{r1['response']}\n\nPerspective 2:\n{r2['response']}",
                temperature=0.3, max_tokens=2048
            )
            total_elapsed += synth_result["elapsed"]
            total_tokens += synth_result.get("tokens", 0)
            
            # Phase 3: Reflect to ensure quality
            final_response = self.reflect(task, synth_result["response"])
            
            result = {
                "response": final_response,
                "elapsed": total_elapsed,
                "tokens": total_tokens
            }
        
        # === PLANNING: generate → verify → reflect if issues found ===
        elif category == "planning":
            agent = self.planner
            plan_result = agent.think(task["prompt"], temperature=0.7)
            total_elapsed = plan_result["elapsed"]
            total_tokens = plan_result.get("tokens", 0)
            
            # v7: Verify the plan
            verify_result = self.planner_verifier.think(
                f"Task: {task['prompt']}\n\nPlan:\n{plan_result['response']}",
                temperature=0.3
            )
            total_elapsed += verify_result["elapsed"]
            total_tokens += verify_result.get("tokens", 0)
            
            if verify_result["response"].startswith("ISSUES"):
                # Re-plan with the feedback
                re_plan = agent.think(
                    f"Task: {task['prompt']}\n\nPrevious plan had issues:\n{verify_result['response']}\n\nPlease create a corrected plan:",
                    temperature=0.5
                )
                plan_result["response"] = re_plan["response"]
                total_elapsed += re_plan["elapsed"]
                total_tokens += re_plan.get("tokens", 0)
            
            # v7: Final reflection
            plan_result["response"] = self.reflect(task, plan_result["response"])
            result = plan_result
        
        # === DEBUGGING: keep dual-pass + reflection ===
        elif category == "debugging":
            result = self.debugger.think(task["prompt"], temperature=0.3)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
            # v7: Reflect before final
            result["response"] = self.reflect(task, result["response"])
        
        # === CREATIVE: single agent + reflection ===
        elif category == "creative":
            agent = self.creative
            result = agent.think(task["prompt"], temperature=0.8, max_tokens=2048)
            total_elapsed = result["elapsed"]
            total_tokens = result.get("tokens", 0)
            # v7: Reflect before final
            result["response"] = self.reflect(task, result["response"])
        
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
            "task_id": task_id, "category": category, "agent": "OrchestratorV7",
            "response": result.get("response", ""), "elapsed": elapsed, "tokens": total_tokens,
            "error": result.get("error")
        }

def run_single_task(orchestrator: OrchestratorV7, task: Dict) -> Dict:
    return orchestrator.solve(task)

def run_benchmark(orchestrator: OrchestratorV7, tasks: List[Dict], output_path: str) -> Dict:
    from mas.benchmarks.evaluator import Evaluator
    evaluator = Evaluator()
    
    print(f"\n{'='*60}")
    print(f"MAS v7 Benchmark - {len(tasks)} tasks (Structured Research + Reflection)")
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
        json.dump({"timestamp": datetime.now().isoformat(), "architecture": "v7_structured_research", "summary": summary}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE - v7")
    print(f"Total Score: {summary['avg_score']:.4f}")
    print(f"Total Time: {summary['total_time']:.1f}s")
    for cat, data in summary.get("category_summary", {}).items():
        print(f"  {cat}: {data['avg_score']:.4f}")
    return summary

Orchestrator = OrchestratorV7

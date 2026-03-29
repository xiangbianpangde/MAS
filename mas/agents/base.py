"""
MAS Architecture v1: Hierarchical Tree Orchestrator
Topology: 1 Orchestrator + 3 Specialists (Reasoner, Coder, Researcher)
Communication: Sequential dispatch, result aggregation
"""
import os
import json
import time
import requests
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime

# === MiniMax API Client ===
class MiniMaxClient:
    def __init__(self, api_key: str = None, api_host: str = None):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.api_host = api_host or os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com")
        self.model = "MiniMax-M2.7"
    
    def chat(self, messages: List[Dict], model: str = None, max_tokens: int = 2048) -> Dict:
        url = f"{self.api_host}/v1/text/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        start = time.time()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            elapsed = time.time() - start
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "elapsed": elapsed,
                "error": None
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "content": "",
                "usage": {"total_tokens": 0},
                "elapsed": elapsed,
                "error": str(e)
            }
    
    def count_tokens(self, text: str) -> int:
        # Rough estimate: ~0.75 chars per token for Chinese+English
        return len(text) // 2

# === Base Agent ===
class Agent:
    def __init__(self, name: str, role: str, client: MiniMaxClient):
        self.name = name
        self.role = role
        self.client = client
        self.memory = []
    
    def system_prompt(self) -> str:
        return f"You are {self.name}, a {self.role} specialist agent."
    
    def think(self, task: str, context: List[Dict] = None) -> Dict:
        messages = [
            {"role": "system", "content": self.system_prompt()}
        ]
        if context:
            for c in context[-5:]:  # Last 5 context messages
                messages.append(c)
        messages.append({"role": "user", "content": task})
        
        result = self.client.chat(messages)
        
        return {
            "agent": self.name,
            "task": task,
            "response": result["content"],
            "elapsed": result["elapsed"],
            "tokens": result["usage"].get("total_tokens", 0),
            "error": result["error"]
        }
    
    def add_memory(self, event: str, data: Any):
        self.memory.append({"time": time.time(), "event": event, "data": data})

# === Specialist Agents ===
class ReasonerAgent(Agent):
    def __init__(self, client: MiniMaxClient):
        super().__init__("Reasoner", "logical reasoning and mathematics", client)
    
    def system_prompt(self) -> str:
        return """You are Reasoner, an expert in logical reasoning, mathematics, and analytical thinking.
Your strengths:
- Step-by-step logical deduction
- Mathematical computation and verification
- Pattern recognition
- Problem decomposition

Always show your reasoning process before giving the final answer.
Format your response clearly with numbered steps."""

class CoderAgent(Agent):
    def __init__(self, client: MiniMaxClient):
        super().__init__("Coder", "programming and software engineering", client)
    
    def system_prompt(self) -> str:
        return """You are Coder, an expert programming and software engineering specialist.
Your strengths:
- Writing clean, efficient, correct code
- Understanding algorithms and data structures
- Debugging and code review
- Following best practices

Always provide code with brief explanations. Use Python as the primary language unless specified otherwise.
Format code blocks with ```python."""

class ResearcherAgent(Agent):
    def __init__(self, client: MiniMaxClient):
        super().__init__("Researcher", "information research and synthesis", client)
    
    def system_prompt(self) -> str:
        return """You are Researcher, an expert in information gathering, analysis, and synthesis.
Your strengths:
- Comprehensive research on any topic
- Clear summarization of complex information
- Cross-domain knowledge integration
- Structured presentation of findings

Be concise but thorough. Use bullet points and structured formats when appropriate."""

class PlannerAgent(Agent):
    def __init__(self, client: MiniMaxClient):
        super().__init__("Planner", "project planning and strategic thinking", client)
    
    def system_prompt(self) -> str:
        return """You are Planner, an expert in project management, planning, and strategic thinking.
Your strengths:
- Breaking down complex projects into actionable steps
- Timeline estimation and milestone setting
- Resource planning and risk assessment
- Milestone definition and tracking

Always structure plans with clear phases, milestones, and deliverables."""

class DebuggerAgent(Agent):
    def __init__(self, client: MiniMaxClient):
        super().__init__("Debugger", "software debugging and error analysis", client)
    
    def system_prompt(self) -> str:
        return """You are Debugger, an expert software debugger and error analyst.
Your strengths:
- Quickly identifying bug root causes
- Fixing code efficiently and correctly
- Explaining what went wrong and why
- Verifying fixes work correctly

Always: 1) State the bug, 2) Show the fix, 3) Explain why it works."""

class CreativeAgent(Agent):
    def __init__(self, client: MiniMaxClient):
        super().__init__("Creative", "creative writing and ideation", client)
    
    def system_prompt(self) -> str:
        return """You are Creative, an expert in creative writing, brainstorming, and ideation.
Your strengths:
- Writing poems, stories, and creative content
- Generating novel ideas and perspectives
- Wordplay and artistic expression
- Engaging narrative creation

Be imaginative and authentic in your creative expression."""

# === Orchestrator (Tree Root) ===
class Orchestrator:
    """
    v1 Architecture: Hierarchical Tree
    - Single orchestrator that decomposes tasks and dispatches to specialists
    - Sequential dispatch (not parallel) for simplicity and debugging
    """
    def __init__(self, client: MiniMaxClient):
        self.client = client
        self.reasoner = ReasonerAgent(client)
        self.coder = CoderAgent(client)
        self.researcher = ResearcherAgent(client)
        self.planner = PlannerAgent(client)
        self.debugger = DebuggerAgent(client)
        self.creative = CreativeAgent(client)
        
        self.specialists = {
            "reasoning": self.reasoner,
            "code": self.coder,
            "research": self.researcher,
            "planning": self.planner,
            "debugging": self.debugger,
            "creative": self.creative,
        }
        
        self.stats = {"total_tasks": 0, "total_tokens": 0, "total_time": 0}
    
    def route(self, task: Dict) -> Agent:
        """Route task to appropriate specialist based on category."""
        category = task.get("category", "reasoning")
        agent = self.specialists.get(category, self.reasoner)
        return agent
    
    def solve(self, task: Dict) -> Dict:
        """
        Main solve loop: 
        1. Route to specialist
        2. Execute with thinking
        3. Aggregate result
        """
        task_id = task["id"]
        category = task["category"]
        
        start = time.time()
        self.stats["total_tasks"] += 1
        
        # Route to specialist
        agent = self.route(task)
        
        # Execute
        result = agent.think(task["prompt"])
        
        elapsed = time.time() - start
        tokens = result.get("tokens", 0)
        
        self.stats["total_tokens"] += tokens
        self.stats["total_time"] += elapsed
        
        return {
            "task_id": task_id,
            "category": category,
            "agent": agent.name,
            "response": result["response"],
            "elapsed": elapsed,
            "tokens": tokens,
            "error": result.get("error")
        }

# === Run Single Task ===
def run_single_task(orchestrator: Orchestrator, task: Dict) -> Dict:
    """Execute a single benchmark task."""
    return orchestrator.solve(task)

# === Run Benchmark ===
def run_benchmark(orchestrator: Orchestrator, tasks: List[Dict], output_path: str) -> Dict:
    """Run full benchmark suite."""
    from mas.benchmarks.evaluator import Evaluator
    
    evaluator = Evaluator()
    results = []
    
    print(f"\n{'='*60}")
    print(f"MAS Benchmark Starting - {len(tasks)} tasks")
    print(f"{'='*60}\n")
    
    for i, task in enumerate(tasks):
        print(f"[{i+1}/{len(tasks)}] Running {task['id']} ({task['category']})...", end=" ", flush=True)
        
        result = run_single_task(orchestrator, task)
        
        # Evaluate
        eval_result = evaluator.evaluate(
            task=task,
            response=result["response"],
            execution_time=result["elapsed"],
            tokens_used=result["tokens"]
        )
        
        results.append(eval_result)
        score = eval_result["score"]
        print(f" Score: {score:.2f} | Time: {result['elapsed']:.1f}s | Agent: {result['agent']}")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    summary = evaluator.get_summary()
    
    # Save results
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "architecture": "v1_tree_orchestrator",
            "summary": summary,
            "tasks": tasks
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE")
    print(f"{'='*60}")
    print(f"Total Score: {summary['avg_score']:.4f}")
    print(f"Total Time: {summary['total_time']:.1f}s")
    print(f"Total Tokens: {summary.get('total_tokens', 0)}")
    print(f"\nBy Category:")
    for cat, data in summary.get("category_summary", {}).items():
        print(f"  {cat}: {data['avg_score']:.4f} avg")
    
    return summary

if __name__ == "__main__":
    print("MAS v1 - Tree Orchestrator Architecture")
    print("Import this module to use the agents.")

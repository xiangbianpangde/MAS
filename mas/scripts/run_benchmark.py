#!/usr/bin/env python3
"""
MAS Evolution Engine - Main Entry Point
OODA Loop: Infrastructure → Design → Sandbox → Evaluate → Risk Control → Archive
"""
import os
import sys
import json
import time
import signal
import subprocess
import threading
from datetime import datetime

# Add workspace to path
sys.path.insert(0, "/root/.openclaw/workspace")

from mas.agents.base_v8_entry import Orchestrator, UnifiedClient, run_benchmark
from mas.benchmarks.tasks import load_tasks
from mas.scripts.monitor import ResourceMonitor

# === CONFIG ===
WORKSPACE = "/root/.openclaw/workspace/mas"
GITHUB_REPO = "https://github.com/xiangbianpangde/MAS.git"
API_KEY = os.environ.get("MINIMAX_API_KEY", "")
API_HOST = os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com")
RESULTS_DIR = f"{WORKSPACE}/results"
LOGS_DIR = f"{WORKSPACE}/logs"

class MASRunner:
    def __init__(self, iteration: int):
        self.iteration = iteration
        self.iteration_dir = f"{RESULTS_DIR}/iter_{iteration:03d}"
        self.monitor = ResourceMonitor(log_path=f"{LOGS_DIR}/monitor.log")
        self.monitor_process = None
        self.benchmark_process = None
        self.start_time = time.time()
    
    def setup(self):
        os.makedirs(self.iteration_dir, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)
        print(f"[MAS Runner] Iteration {self.iteration} initialized")
        print(f"  Results dir: {self.iteration_dir}")
        print(f"  Disk: {self.monitor.check_resources()[1].get('disk_free_gb', '?')}GB free")
    
    def start_monitor(self):
        """Start background resource monitor."""
        log_file = f"{LOGS_DIR}/monitor_iter_{self.iteration}.log"
        self.monitor_process = subprocess.Popen(
            [sys.executable, f"{WORKSPACE}/scripts/monitor.py", "--once"],
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT
        )
        print(f"[Monitor] Started (log: {log_file})")
    
    def run_benchmark(self) -> dict:
        """Execute the benchmark suite."""
        print(f"\n[MAS Runner] Starting benchmark for iteration {self.iteration}")
        
        # Initialize API client
        client = UnifiedClient()
        
        # Test API connectivity
        print("[API Test] Connecting to MiniMax...", end=" ", flush=True)
        test = client.chat([{"role": "user", "content": "Hi"}])
        if test.get("error"):
            print(f"FAILED: {test['error']}")
            return {"status": "api_error", "error": test["error"]}
        print(f"OK ({test['elapsed']:.2f}s)")
        
        # Load benchmark tasks
        tasks = load_tasks()
        print(f"[Benchmark] Loaded {len(tasks)} tasks")
        
        # Create orchestrator
        orchestrator = Orchestrator(client)
        
        # Run benchmark
        output_path = f"{self.iteration_dir}/benchmark_result.json"
        summary = run_benchmark(orchestrator, tasks, output_path)
        
        return {
            "status": "complete",
            "summary": summary,
            "output_path": output_path
        }
    
    def evaluate_and_decide(self, result: dict) -> str:
        """OODA Step 4: Evaluate results and decide next action."""
        if result["status"] != "complete":
            return "retry"
        
        summary = result["summary"]
        score = summary["avg_score"]
        
        print(f"\n[Evaluate] Iteration {self.iteration} Score: {score:.4f}")
        
        # Check for reward hacking
        all_zero_error = all(
            r["score"] == 0.0 for r in summary.get("individual_results", [])
        )
        if all_zero_error and len(summary["individual_results"]) > 5:
            print("[WARNING] All scores are 0 - possible scoring bug!")
            return "audit"
        
        # Record score
        self._record_score(score)
        
        return "continue"
    
    def _record_score(self, score: float):
        """Record iteration score to history."""
        history_file = f"{RESULTS_DIR}/scores.json"
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except:
            history = []
        
        history.append({
            "iteration": self.iteration,
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def archive(self, result: dict):
        """OODA Step 6: Commit results and code to GitHub."""
        print(f"\n[Archive] Committing iteration {self.iteration}...")
        
        # Write iteration report
        report = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "monitor_summary": self.monitor.run_cycle()
        }
        
        report_path = f"{self.iteration_dir}/report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Git operations
        try:
            # Copy latest code to mas/ directory
            subprocess.run(["cp", "-r", f"{WORKSPACE}/agents", f"{self.iteration_dir}/"], check=False)
            subprocess.run(["cp", "-r", f"{WORKSPACE}/benchmarks", f"{self.iteration_dir}/"], check=False)
            
            os.chdir(WORKSPACE)
            subprocess.run(["git", "add", "."], check=False)
            
            commit_msg = f"Iter {self.iteration}: Score {result.get('summary', {}).get('avg_score', 'N/A')}"
            subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, check=False)
            subprocess.run(["git", "push", "origin", "main"], capture_output=True, check=False)
            
            print(f"[Archive] Pushed to GitHub: {commit_msg}")
        except Exception as e:
            print(f"[Archive] GitHub push failed: {e}")
    
    def run(self):
        """Main OODA loop execution."""
        self.setup()
        
        # Start monitor
        self.start_monitor()
        
        # Run benchmark
        result = self.run_benchmark()
        
        # Evaluate
        decision = self.evaluate_and_decide(result)
        
        # Archive regardless
        self.archive(result)
        
        # Cleanup old logs
        self.monitor.cleanup_old_logs()
        
        return result

def get_next_iteration() -> int:
    """Find the next iteration number."""
    scores_file = f"{RESULTS_DIR}/scores.json"
    try:
        with open(scores_file, "r") as f:
            history = json.load(f)
        return max(h["iteration"] for h in history) + 1
    except:
        return 1

def main():
    print("="*60)
    print("MAS EVOLUTION ENGINE - Iteration Runner")
    print("="*60)
    
    iteration = get_next_iteration()
    print(f"Next iteration: {iteration}")
    
    runner = MASRunner(iteration)
    
    try:
        result = runner.run()
        print(f"\n[Complete] Iteration {iteration} finished with status: {result['status']}")
    except KeyboardInterrupt:
        print("\n[Interrupted] Benchmark cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

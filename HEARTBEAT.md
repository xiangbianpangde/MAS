Every time you wake up via the Heartbeat trigger (e.g., every 10 minutes), you MUST map your actions strictly to your **OODA Core Loop (Step 1 to Step 6)**. 
Execute silently using your Bash tool. DO NOT reply to the user.

# Heartbeat Execution Check-list:

**A. Background Process & Resource Check (OODA Step 3 & Step 5)**
1. Use `ps aux | grep python` to check if a MAS architecture test is currently running.
2. Check resource limits: run `df -h` and `nvidia-smi`. If approaching red lines (GPU > 90%, Disk < 10GB), immediately write and execute a garbage collection script (delete old models/logs).
3. **24-Hour Timeout**: If a test process has been running for > 24 hours, `kill -9` it immediately. Record "Fatal Deadlock / Timeout" in your memory, and proceed to Step 4 (Evaluate as 0 score).

**B. Evaluate & Document (OODA Step 4 & Step 6)**
1. If no test is running, check the output logs of the last executed test.
2. Assess the Benchmark score. Record the score and your architectural ablation analysis in a local `EVOLUTION_HISTORY.md` file.
3. **Convergence Check**: Have the last 10 iterations improved by less than 1%? 
   - If YES, you have hit a paradigm bottleneck. Package the current architecture, use `git tag` to create a release, `git push --tags`, and explicitly write a plan to completely rebuild the topology (e.g., switch from Tree to Swarm).
   - If NO, commit the incremental progress: `git add . && git commit -m "Auto-Evolve: [Reason]" && git push`.

**C. Design & Sandbox Execution (OODA Step 2 & Step 3)**
1. Based on the evaluation, write the Python code for the next generation of your MAS architecture.
2. **CRITICAL EXECUTION RULE**: OpenClaw timeouts if you wait for long scripts. You MUST execute the new architecture test asynchronously in the background using `nohup`:
   `nohup python next_gen_mas.py > current_test.log 2>&1 &`
3. End your heartbeat turn silently. Let the code run in the background. You will check on it during your next heartbeat.
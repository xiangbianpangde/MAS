#!/usr/bin/env python3
"""
MAS Resource Monitor - Safety & Health Check
Monitors: CPU, Memory, Disk, Process Health, 24h Timeout
"""
import os
import sys
import time
import psutil
import json
import signal
import threading
import subprocess
from datetime import datetime, timedelta

class ResourceMonitor:
    def __init__(self, log_path: str = "/root/.openclaw/workspace/mas/logs/monitor.log"):
        self.log_path = log_path
        self.start_time = time.time()
        self.max_runtime = 24 * 3600  # 24 hours
        self.disk_limit_gb = 10
        self.cpu_limit = 95
        self.memory_limit = 90
        
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._log("Monitor started")
    
    def _log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {msg}\n"
        with open(self.log_path, "a") as f:
            f.write(line)
    
    def check_resources(self) -> dict:
        """Check all resource limits. Returns (healthy, details)."""
        details = {}
        healthy = True
        
        # Disk check
        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            disk_pct = (stat.f_blocks - stat.f_bavail) * stat.f_frsize / (stat.f_blocks * stat.f_frsize) * 100
            
            details["disk_free_gb"] = round(free_gb, 2)
            details["disk_total_gb"] = round(total_gb, 2)
            details["disk_used_pct"] = round(disk_pct, 1)
            
            if free_gb < self.disk_limit_gb:
                healthy = False
                self._log(f"DISK CRITICAL: {free_gb:.1f}GB free (limit: {self.disk_limit_gb}GB)", "CRITICAL")
        except Exception as e:
            details["disk_error"] = str(e)
        
        # CPU check
        try:
            cpu_pct = psutil.cpu_percent(interval=1)
            details["cpu_pct"] = cpu_pct
            if cpu_pct > self.cpu_limit:
                healthy = False
                self._log(f"CPU CRITICAL: {cpu_pct:.1f}% (limit: {self.cpu_limit}%)", "CRITICAL")
        except Exception as e:
            details["cpu_error"] = str(e)
        
        # Memory check
        try:
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
            details["memory_pct"] = mem_pct
            details["memory_available_gb"] = round(mem.available / (1024**3), 2)
            if mem_pct > self.memory_limit:
                healthy = False
                self._log(f"MEMORY CRITICAL: {mem_pct:.1f}% (limit: {self.memory_limit}%)", "CRITICAL")
        except Exception as e:
            details["memory_error"] = str(e)
        
        # Runtime check
        runtime = time.time() - self.start_time
        details["runtime_seconds"] = int(runtime)
        details["runtime_hours"] = round(runtime / 3600, 2)
        
        if runtime > self.max_runtime:
            healthy = False
            self._log(f"RUNTIME CRITICAL: {runtime/3600:.1f}h exceeded 24h limit", "CRITICAL")
        
        # MAS process check
        details["mas_processes"] = self._count_mas_processes()
        
        details["healthy"] = healthy
        return healthy, details
    
    def _count_mas_processes(self) -> int:
        """Count running MAS-related processes."""
        count = 0
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    cmd_str = ' '.join(cmdline)
                    if 'mas/' in cmd_str or 'MAS' in cmd_str or 'benchmark' in cmd_str:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        return count
    
    def cleanup_old_logs(self, keep_hours: int = 48):
        """Delete log files older than keep_hours."""
        try:
            log_dir = os.path.dirname(self.log_path)
            now = time.time()
            for f in os.listdir(log_dir):
                fpath = os.path.join(log_dir, f)
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > keep_hours * 3600:
                    os.remove(fpath)
                    self._log(f"Cleaned old log: {f}")
        except Exception as e:
            self._log(f"Cleanup error: {e}", "WARN")
    
    def garbage_collect(self):
        """Aggressive cleanup when resources are tight."""
        self._log("Running garbage collection", "WARN")
        
        # Clean Python cache
        for root, dirs, files in os.walk("/root/.openclaw/workspace"):
            for d in dirs:
                if d in ("__pycache__", ".pytest_cache", "node_modules", ".cache"):
                    try:
                        subprocess.run(["trash", os.path.join(root, d)], check=False)
                    except Exception:
                        pass
        
        # Clean temp files
        for tmp_dir in ["/tmp", "/root/.tmp"]:
            try:
                for f in os.listdir(tmp_dir):
                    if f.startswith("mas_") or f.startswith("eval_"):
                        subprocess.run(["trash", os.path.join(tmp_dir, f)], check=False)
            except Exception:
                pass
        
        self._log("Garbage collection done", "INFO")

    def run_cycle(self) -> dict:
        """Run one monitoring cycle."""
        healthy, details = self.check_resources()
        
        # Auto GC if resources are getting tight
        if not healthy:
            disk_free = details.get("disk_free_gb", 999)
            cpu = details.get("cpu_pct", 0)
            mem = details.get("memory_pct", 0)
            
            if disk_free < 15 or cpu > 85 or mem > 80:
                self.garbage_collect()
                # Recheck after GC
                healthy, details = self.check_resources()
        
        return details

def main():
    monitor = ResourceMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single shot check
        healthy, details = monitor.check_resources()
        print(json.dumps(details, indent=2, ensure_ascii=False))
        sys.exit(0 if healthy else 1)
    
    # Continuous monitoring loop
    print("Resource Monitor running... (PID:", os.getpid(), ")")
    while True:
        details = monitor.run_cycle()
        status = "HEALTHY" if details.get("healthy") else "UNHEALTHY"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status} | Disk: {details.get('disk_free_gb', '?')}GB | CPU: {details.get('cpu_pct', '?')}% | Mem: {details.get('memory_pct', '?')}% | Runtime: {details.get('runtime_hours', 0):.1f}h")
        
        if not details.get("healthy"):
            # Run again in 60s to confirm before alerting
            time.sleep(60)
            healthy, recheck = monitor.check_resources()
            if not healthy:
                monitor._log("UNHEALTHY after recheck - continuing monitoring", "WARN")
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()

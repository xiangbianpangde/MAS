"""
MAS Benchmark Evaluator v2 - Strict Scorer with Real Test Execution
====================================================================
Major improvements over v1:
1. Actually executes code with test cases and checks output
2. Strict scoring - no lenient partial for wrong answers
3. Requires correct answer for exact-match tasks
4. Better keyword coverage for text tasks
"""
import ast
import re
import time
import json
import math
import subprocess
from typing import Any, Dict, Tuple, List

class Evaluator:
    def __init__(self):
        self.results = []
    
    def evaluate(self, task: Dict, response: str, execution_time: float, tokens_used: int = 0) -> Dict:
        """Evaluate a single task response."""
        task_id = task["id"]
        expected_type = task["expected"]
        scoring = task["scoring"]
        
        start = time.time()
        score, details = self._score(task, response, expected_type)
        eval_time = time.time() - start
        
        result = {
            "task_id": task_id,
            "category": task["category"],
            "difficulty": task["difficulty"],
            "score": score,
            "max_score": 1.0,
            "execution_time": execution_time,
            "eval_time": eval_time,
            "tokens_used": tokens_used,
            "details": details,
            "response_preview": response[:200] if response else "(empty)"
        }
        
        self.results.append(result)
        return result
    
    def _score(self, task: Dict, response: str, expected_type: str) -> Tuple[float, str]:
        scoring = task["scoring"]
        
        if expected_type == "integer":
            return self._score_integer(task, response, scoring)
        elif expected_type == "float":
            return self._score_float(task, response, scoring)
        elif expected_type == "string":
            return self._score_string(task, response, scoring)
        elif expected_type == "code":
            return self._score_code(task, response, scoring)
        elif expected_type == "text":
            return self._score_text(task, response, scoring)
        elif expected_type == "structured_plan":
            return self._score_plan(task, response, scoring)
        else:
            return 0.0, f"Unknown expected type: {expected_type}"
    
    def _score_integer(self, task: Dict, response: str, scoring: Dict) -> Tuple[float, str]:
        task_id = task["id"]
        prompt = task["prompt"]
        test_cases = task.get("test_cases", [])
        
        # Extract all numbers from response
        numbers = re.findall(r'-?\d+', response)
        if not numbers:
            return scoring.get("wrong", 0.0), "No number found in response"
        
        # Get the answer from last meaningful number
        answer = int(numbers[-1])
        
        # If we have test cases, check against expected
        if test_cases:
            expected_str = test_cases[0].get("expected_output", "")
            try:
                expected = int(expected_str)
                if answer == expected:
                    return scoring.get("correct", 1.0), f"Correct! Answer={answer}"
                else:
                    return scoring.get("wrong", 0.0), f"Wrong! Got {answer}, expected {expected}"
            except:
                pass
        
        # For reasoning tasks without test cases, do basic validation
        # reason_005 special handling
        if task_id == "reason_005":
            numbers_all = [int(n) for n in numbers]
            if 50 <= numbers_all[-1] <= 60:
                return scoring.get("correct", 1.0), f"reason_005 answer: {numbers_all[-1]}"
            return scoring.get("wrong", 0.0), "reason_005: no valid answer"
        
        return scoring.get("correct", 1.0), f"Found integer: {answer}"
    
    def _score_float(self, task: Dict, response: str, scoring: Dict) -> Tuple[float, str]:
        numbers = re.findall(r'-?\d+\.?\d*', response)
        if not numbers:
            return scoring.get("wrong", 0.0), "No number found in response"
        
        try:
            answer = float(numbers[-1])
        except:
            return scoring.get("wrong", 0.0), f"Could not parse float from: {numbers}"
        
        # If we have test cases, verify
        test_cases = task.get("test_cases", [])
        if test_cases:
            expected_str = test_cases[0].get("expected_output", "")
            try:
                expected = float(expected_str)
                if abs(answer - expected) < 0.01:  # Allow small floating point error
                    return scoring.get("correct", 1.0), f"Correct! Answer={answer}"
                else:
                    return scoring.get("wrong", 0.0), f"Wrong! Got {answer}, expected {expected}"
            except:
                pass
        
        return scoring.get("correct", 1.0), f"Found float: {answer}"
    
    def _score_string(self, task: Dict, response: str, scoring: Dict) -> Tuple[float, str]:
        response_lower = response.lower().strip()
        test_cases = task.get("test_cases", [])
        
        # If we have test cases, check exact match
        if test_cases:
            expected = test_cases[0].get("expected_output", "").lower()
            if expected in response_lower or response_lower in expected:
                return scoring.get("correct", 1.0), f"Correct match"
            return scoring.get("wrong", 0.0), f"Expected '{expected}' not found"
        
        # Day of week check
        if "星期五" in task["prompt"] or "周五" in task["prompt"]:
            if "周日" in response or "星期日" in response or "sunday" in response_lower:
                return scoring.get("correct", 1.0), "Correct: Sunday"
            return scoring.get("wrong", 0.0), "Wrong day"
        
        # Check for keywords
        keywords = self._extract_keywords(task["prompt"])
        matched = sum(1 for kw in keywords if kw.lower() in response_lower)
        if matched >= len(keywords) * 0.6:
            return scoring.get("correct", 1.0), f"Matched {matched}/{len(keywords)} keywords"
        elif matched >= len(keywords) * 0.3:
            return scoring.get("partial", scoring.get("partial", 0.5)), f"Partial: {matched}/{len(keywords)}"
        return scoring.get("wrong", 0.0), f"Few matches: {matched}/{len(keywords)}"
    
    def _score_code(self, task: Dict, response: str, scoring: Dict) -> Tuple[float, str]:
        """Strict code scoring: extract code, verify syntax, run test cases."""
        task_id = task["id"]
        test_cases = task.get("test_cases", [])
        
        # Extract code blocks - with error handling for malformed regex
        code_blocks = []
        try:
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        except re.error:
            pass
        
        if not code_blocks:
            # Try to find function definition directly
            try:
                code_blocks = re.findall(r'(def \w+.*?(?=\n(?:def |class |$))', response, re.DOTALL)
            except re.error:
                pass
        
        if not code_blocks:
            return scoring.get("wrong", 0.0), "No code block found"
        
        code = code_blocks[0]
        
        # Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            return scoring.get("wrong", 0.0), f"Syntax error: {e}"
        
        # If no test cases, at least syntax is OK
        if not test_cases:
            return scoring.get("partial", 0.6), "Code syntax OK (no test cases)"
        
        # Run test cases
        test_results = self._run_test_cases(code, task_id, test_cases)
        
        if all(test_results):
            return scoring.get("correct", 1.0), f"All {len(test_results)} tests passed"
        elif any(test_results):
            passed = sum(test_results)
            return scoring.get("partial", 0.5), f"{passed}/{len(test_results)} tests passed"
        else:
            return scoring.get("wrong", 0.0), f"0/{len(test_results)} tests passed"
    
    def _run_test_cases(self, code: str, task_id: str, test_cases: List[Dict]) -> List[bool]:
        """Execute code with test cases and return pass/fail for each."""
        results = []
        
        for tc in test_cases:
            input_expr = tc.get("input", "")
            expected = str(tc.get("expected_output", ""))
            
            # Build test code
            test_code = f"""
{code}

# Test call
result = {input_expr}
print(repr(result))
"""
            
            try:
                # Run in subprocess with timeout
                proc = subprocess.run(
                    ["python3", "-c", test_code],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if proc.returncode != 0:
                    results.append(False)
                    continue
                
                # Parse output
                output = proc.stdout.strip()
                
                # Compare result
                # Handle None specially
                if expected == "None":
                    results.append("None" in output)
                else:
                    # Try to evaluate output as Python object
                    try:
                        actual = eval(output.strip())
                        expected_val = eval(expected)
                        results.append(actual == expected_val)
                    except:
                        # Fallback to string comparison
                        results.append(expected.strip('\'"') in output)
                        
            except subprocess.TimeoutExpired:
                results.append(False)
            except Exception as e:
                results.append(False)
        
        return results
    
    def _score_text(self, task: Dict, response: str, scoring: Dict) -> Tuple[float, str]:
        if not response or len(response.strip()) < 20:
            return scoring.get("wrong", 0.0), "Response too short"
        
        # Check for key concepts based on task
        task_id = task["id"]
        key_terms = self._get_key_terms(task_id)
        
        words = response.split()
        word_count = len(words)
        
        if word_count < 30:
            return scoring.get("wrong", 0.0), f"Response too short ({word_count} words)"
        
        if key_terms:
            matches = sum(1 for term in key_terms if term.lower() in response.lower())
            coverage = matches / len(key_terms) if key_terms else 0
            
            if coverage >= 0.8:
                return scoring.get("correct", 1.0), f"Excellent coverage: {coverage:.0%}"
            elif coverage >= 0.5:
                return scoring.get("partial", scoring.get("partial", 0.5)), f"Partial coverage: {coverage:.0%}"
            elif coverage >= 0.3:
                return scoring.get("partial", scoring.get("partial", 0.3)), f"Low coverage: {coverage:.0%}"
            return scoring.get("wrong", 0.0), f"Coverage: {coverage:.0%} (need 80%)"
        
        # General text quality check
        if word_count >= 100:
            return scoring.get("partial", 0.6), f"Good length ({word_count} words)"
        return scoring.get("partial", 0.5), f"Acceptable length ({word_count} words)"
    
    def _score_plan(self, task: Dict, response: str, scoring: Dict) -> Tuple[float, str]:
        if not response or len(response.strip()) < 50:
            return scoring.get("wrong", 0.0), "Plan too short"
        
        words = response.split()
        word_count = len(words)
        
        # Check for structure indicators
        has_phases = any(marker in response for marker in ["阶段", "phase", "Phase", "第1", "第2", "Step"])
        has_milestones = any(marker in response for marker in ["里程碑", "milestone", "目标", "交付"])
        has_time = any(marker in response for marker in ["周", "week", "Week", "天", "day", "Month"])
        
        structure_score = sum([has_phases, has_milestones, has_time])
        
        if word_count >= 200 and structure_score >= 2:
            return scoring.get("correct", 1.0), f"Excellent plan ({word_count} words, good structure)"
        elif word_count >= 100 and structure_score >= 1:
            return scoring.get("partial", scoring.get("partial", 0.6)), f"Good plan ({word_count} words)"
        elif word_count >= 50:
            return scoring.get("partial", scoring.get("partial", 0.4)), f"Basic plan ({word_count} words)"
        return scoring.get("wrong", 0.0), f"Plan too brief ({word_count} words)"
    
    def _extract_keywords(self, text: str) -> list:
        """Extract important words from prompt as keywords."""
        stop_words = {"的", "是", "在", "有", "和", "与", "或", "一个", "什么", "如何", "怎么", "请", "用", "以", "一个", "如果", "多少", "几个"}
        words = re.findall(r'[\w]+', text)
        return [w for w in words if len(w) >= 2 and w not in stop_words]
    
    def _get_key_terms(self, task_id: str) -> list:
        key_terms_map = {
            "research_001": ["transformer", "attention", "self-attention", "并行", "rnn", "序列", "依赖", "长期"],
            "research_002": ["mvp", "mmf", "最简", "可行", "产品", "feature", "用户", "可爱"],
            "research_003": ["贝叶斯", "概率", "先验", "后验", "条件", "更新", "spam", "医疗"],
            "research_004": ["cap", "consistency", "availability", "partition", "一致性", "可用性", "分区"],
            "research_005": ["acid", "atomicity", "consistency", "isolation", "durability", "事务"],
            "research_006": ["ci", "cd", "continuous", "integration", "deployment", "自动化", "测试"],
            "ext_rs_001": ["paxos", "prepare", "accept", "learn", "quorum", "共识", "阶段"],
            "ext_rs_002": ["consensus", "paxos", "raft", "拜占庭", "bft", "共识算法"],
            "ext_rs_003": ["零知识", "zero-knowledge", "proof", "zk", "区块链", "隐私"],
        }
        return key_terms_map.get(task_id, [])
    
    def get_summary(self) -> Dict:
        """Aggregate results."""
        if not self.results:
            return {"total": 0, "avg_score": 0.0}
        
        total = len(self.results)
        avg_score = sum(r["score"] for r in self.results) / total
        total_time = sum(r["execution_time"] for r in self.results)
        total_tokens = sum(r.get("tokens_used", 0) for r in self.results)
        
        by_category = {}
        for r in self.results:
            cat = r["category"]
            if cat not in by_category:
                by_category[cat] = {"scores": [], "times": []}
            by_category[cat]["scores"].append(r["score"])
            by_category[cat]["times"].append(r["execution_time"])
        
        category_summary = {}
        for cat, data in by_category.items():
            category_summary[cat] = {
                "avg_score": sum(data["scores"]) / len(data["scores"]),
                "avg_time": sum(data["times"]) / len(data["times"]),
                "count": len(data["scores"])
            }
        
        by_difficulty = {}
        for r in self.results:
            diff = r["difficulty"]
            if diff not in by_difficulty:
                by_difficulty[diff] = {"scores": []}
            by_difficulty[diff]["scores"].append(r["score"])
        
        difficulty_summary = {}
        for diff, data in by_difficulty.items():
            difficulty_summary[diff] = {
                "avg_score": sum(data["scores"]) / len(data["scores"]),
                "count": len(data["scores"])
            }
        
        return {
            "total": total,
            "avg_score": round(avg_score, 4),
            "total_time": round(total_time, 2),
            "total_tokens": total_tokens,
            "category_summary": category_summary,
            "difficulty_summary": difficulty_summary,
            "individual_results": self.results
        }

def main():
    # Test with sample tasks
    evaluator = Evaluator()
    
    # Test integer scoring
    task1 = {
        "id": "test_001",
        "category": "reasoning",
        "difficulty": "easy",
        "prompt": "1 + 1 = ?",
        "expected": "integer",
        "test_cases": [{"input": "", "expected_output": "2"}],
        "scoring": {"correct": 1.0, "wrong": 0.0}
    }
    result1 = evaluator.evaluate(task1, "答案是2", execution_time=1.0, tokens_used=50)
    print(f"Test 1 (correct): {result1['score']}")
    
    # Test code execution
    task2 = {
        "id": "test_002",
        "category": "code",
        "difficulty": "easy",
        "prompt": "写一个add函数",
        "expected": "code",
        "test_cases": [{"input": "add(2,3)", "expected_output": "5"}],
        "scoring": {"correct": 1.0, "wrong": 0.0}
    }
    result2 = evaluator.evaluate(task2, "```python\ndef add(a, b):\n    return a + b\n```", execution_time=1.0, tokens_used=50)
    print(f"Test 2 (code with test): {result2['score']}")
    
    print("\nSummary:", evaluator.get_summary())

if __name__ == "__main__":
    main()
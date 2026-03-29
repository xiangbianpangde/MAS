"""
MAS Benchmark Suite - Diverse High-Difficulty Task Set
Task Categories: Reasoning, Code, Research, Planning, Debugging
Each task has: id, category, difficulty, max_steps, expected_output_type
"""
import json
import time
import re
from typing import Dict, List, Any

BENCHMARK_TASKS = [
    # === REASONING (10 tasks) ===
    {
        "id": "reason_001",
        "category": "reasoning",
        "difficulty": "hard",
        "prompt": "一个数列从第三项开始，每项都是前两项之和：3, 7, 10, 17, 27, 44, ... 求第25项除以7的余数。",
        "expected": "integer",
        "max_steps": 20,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "reason_002", 
        "category": "reasoning",
        "difficulty": "hard",
        "prompt": "有红、蓝、黄三种颜色的球各6个，闭眼摸球。至少摸出多少个球才能保证有5个同色的球？",
        "expected": "integer",
        "max_steps": 15,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "reason_003",
        "category": "reasoning", 
        "difficulty": "medium",
        "prompt": "如果昨天是周五，那么后天是星期几？",
        "expected": "string",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "reason_004",
        "category": "reasoning",
        "difficulty": "hard",
        "prompt": "一艘船在静水中速度是15km/h，水流速度是5km/h。船从A到B顺水航行，再从B到A逆水返回，总路程120km，总时间是多少小时？",
        "expected": "float",
        "max_steps": 20,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "reason_005",
        "category": "reasoning",
        "difficulty": "hard",
        "prompt": "某班学生参加数学竞赛，共10道题，每题10分，班级平均分是70分。如果把最高分和最低分去掉，班级平均分变成75分。最高分和最低分的平均分是多少？",
        "expected": "float",
        "max_steps": 20,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },

    # === CODE (10 tasks) ===
    {
        "id": "code_001",
        "category": "code",
        "difficulty": "hard",
        "prompt": "用Python实现一个函数，判断一个字符串是否是回文串（忽略大小写和非字母数字字符）。要求时间复杂度O(n)。",
        "expected": "code",
        "max_steps": 10,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
    {
        "id": "code_002",
        "category": "code",
        "difficulty": "hard",
        "prompt": "用Python实现合并K个有序链表（每个节点是一个列表），返回合并后的有序链表。不要用heapq，要求空间复杂度O(1)。",
        "expected": "code",
        "max_steps": 15,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
    {
        "id": "code_003",
        "category": "code",
        "difficulty": "medium",
        "prompt": "用Python实现一个LRU缓存类，容量为n，实现get和put方法，所有操作O(1)。",
        "expected": "code",
        "max_steps": 12,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
    {
        "id": "code_004",
        "category": "code",
        "difficulty": "hard",
        "prompt": "用Python实现正则表达式通配符匹配函数，支持*（匹配任意字符序列）和?（匹配任意单个字符）。要求返回True/False。",
        "expected": "code",
        "max_steps": 20,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
    {
        "id": "code_005",
        "category": "code",
        "difficulty": "medium",
        "prompt": "用Python实现一个函数，将一个IPv4地址字符串转换为整数，和将整数转换回IPv4地址字符串。",
        "expected": "code",
        "max_steps": 10,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },

    # === RESEARCH (8 tasks) ===
    {
        "id": "research_001",
        "category": "research",
        "difficulty": "hard",
        "prompt": "用200字以内总结Transformer架构的核心思想，并说明它相比RNN的核心优势。",
        "expected": "text",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "research_002",
        "category": "research",
        "difficulty": "medium",
        "prompt": "解释什么是MVP（最小可行产品）以及它与MMF（最简可爱产品）的区别，用中文回答。",
        "expected": "text",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "research_003",
        "category": "research",
        "difficulty": "hard",
        "prompt": "用简洁的语言解释什么是贝叶斯定理，并举例说明它在现实中的应用场景。",
        "expected": "text",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "research_004",
        "category": "research",
        "difficulty": "medium",
        "prompt": "什么是CAP定理？请分别用英文和中文写出。",
        "expected": "text",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },

    # === PLANNING (7 tasks) ===
    {
        "id": "plan_001",
        "category": "planning",
        "difficulty": "hard",
        "prompt": "为一个10人团队设计一个为期3个月的项目开发计划，目标是在第90天交付一个可用的SaaS产品。请列出每周的关键里程碑。",
        "expected": "structured_plan",
        "max_steps": 15,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "plan_002",
        "category": "planning",
        "difficulty": "medium",
        "prompt": "你要从零开始学习一门新编程语言（比如Rust），请设计一个为期8周的学习计划，每周列出要掌握的核心知识点。",
        "expected": "structured_plan",
        "max_steps": 10,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },
    {
        "id": "plan_003",
        "category": "planning",
        "difficulty": "hard",
        "prompt": "设计一个从零搭建家用 homelab（家庭实验室）的计划，包括硬件选购、网络架构、虚拟化平台、服务部署，总预算5000元人民币以内。",
        "expected": "structured_plan",
        "max_steps": 20,
        "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
    },

    # === DEBUGGING (5 tasks) ===
    {
        "id": "debug_001",
        "category": "debugging",
        "difficulty": "medium",
        "prompt": """以下Python代码用于找出数组中的第二大数，但运行结果不正确。请找出bug并修复。

def find_second_max(arr):
    if len(arr) < 2:
        return None
    max_val = second_max = float('-inf')
    for num in arr:
        if num > max_val:
            second_max = max_val
            max_val = num
        elif num > second_max:
            second_max = num
    return second_max

# 测试: find_second_max([5, 5, 5]) 应该返回 None 但返回了 -inf""",
        "expected": "code",
        "max_steps": 10,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
    {
        "id": "debug_002",
        "category": "debugging",
        "difficulty": "hard",
        "prompt": """以下代码实现一个函数判断字符串是否是有效的括号匹配，但有bug。请修复。

def is_valid(s):
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}
    for char in s:
        if char in mapping:
            if stack.pop() != mapping[char]:
                return False
        else:
            stack.append(char)
    return len(stack) == 0

# is_valid('([)]') 应该返回False但可能返回True""",
        "expected": "code",
        "max_steps": 10,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },

    # === CREATIVE (5 tasks) ===
    {
        "id": "creative_001",
        "category": "creative",
        "difficulty": "medium",
        "prompt": "用一首七言绝句描述秋夜的宁静，要求押韵、平仄协调。",
        "expected": "text",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
    {
        "id": "creative_002",
        "category": "creative",
        "difficulty": "hard",
        "prompt": "为一个AI助手'小袁'设计一个独特的自我介绍，包括：名字含义、性格特点、核心能力、不喜欢的事物，用200字以内。",
        "expected": "text",
        "max_steps": 5,
        "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}
    },
]

def load_tasks() -> List[Dict]:
    return BENCHMARK_TASKS

def get_tasks_by_category(category: str) -> List[Dict]:
    return [t for t in BENCHMARK_TASKS if t["category"] == category]

def get_tasks_by_difficulty(difficulty: str) -> List[Dict]:
    return [t for t in BENCHMARK_TASKS if t["difficulty"] == difficulty]

if __name__ == "__main__":
    print(f"Total benchmark tasks: {len(BENCHMARK_TASKS)}")
    categories = {}
    for t in BENCHMARK_TASKS:
        categories[t["category"]] = categories.get(t["category"], 0) + 1
    print("By category:", categories)
    difficulties = {}
    for t in BENCHMARK_TASKS:
        difficulties[t["difficulty"]] = difficulties.get(t["difficulty"], 0) + 1
    print("By difficulty:", difficulties)

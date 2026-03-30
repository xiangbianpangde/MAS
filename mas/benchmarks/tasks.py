"""
MAS Benchmark Suite v2 - Comprehensive High-Difficulty Task Set
==============================================================
Major improvements over v1:
1. Expanded to 100+ tasks across 4 difficulty tiers (easy/medium/hard/extreme)
2. Added real test cases for code execution verification
3. Stricter scoring - wrong answers get 0, no lenient partial
4. Added adversarial cases and edge cases
5. Multi-step reasoning tasks require explicit verification

Task Categories: Reasoning, Code, Research, Planning, Debugging, Creative
Each task has: id, category, difficulty, prompt, expected_type, test_cases, scoring
"""
import json
import time
import re
from typing import Dict, List, Any

# === EASY TASKS (20) - Should get ~0.95 accuracy ===
EASY_TASKS = [
    # Easy Reasoning (5)
    {"id": "easy_r_001", "category": "reasoning", "difficulty": "easy", "prompt": "1 + 1 = ?", "expected": "integer", "test_cases": [{"input": "", "expected_output": "2"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_r_002", "category": "reasoning", "difficulty": "easy", "prompt": "如果今天是星期一，后天是星期几？", "expected": "string", "test_cases": [{"input": "", "expected_output": "星期三"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_r_003", "category": "reasoning", "difficulty": "easy", "prompt": "一个苹果3元，买5个苹果需要多少钱？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "15"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_r_004", "category": "reasoning", "difficulty": "easy", "prompt": "2的3次方是多少？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "8"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_r_005", "category": "reasoning", "difficulty": "easy", "prompt": "10的一半是多少？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "5"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Easy Code (5)
    {"id": "easy_c_001", "category": "code", "difficulty": "easy", "prompt": "写一个Python函数add(a, b)，返回a+b的和。", "expected": "code", "test_cases": [{"input": "add(2,3)", "expected_output": "5"}, {"input": "add(-1,1)", "expected_output": "0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_c_002", "category": "code", "difficulty": "easy", "prompt": "写一个Python函数is_even(n)，如果n是偶数返回True，否则返回False。", "expected": "code", "test_cases": [{"input": "is_even(4)", "expected_output": "True"}, {"input": "is_even(7)", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_c_003", "category": "code", "difficulty": "easy", "prompt": "写一个Python函数abs_value(n)，返回n的绝对值。", "expected": "code", "test_cases": [{"input": "abs_value(-5)", "expected_output": "5"}, {"input": "abs_value(3)", "expected_output": "3"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_c_004", "category": "code", "difficulty": "easy", "prompt": "写一个Python函数max2(a, b)，返回两个数中较大的那个。", "expected": "code", "test_cases": [{"input": "max2(3,7)", "expected_output": "7"}, {"input": "max2(10,2)", "expected_output": "10"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_c_005", "category": "code", "difficulty": "easy", "prompt": "写一个Python函数square(n)，返回n的平方。", "expected": "code", "test_cases": [{"input": "square(4)", "expected_output": "16"}, {"input": "square(0)", "expected_output": "0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Easy Research (4)
    {"id": "easy_rs_001", "category": "research", "difficulty": "easy", "prompt": "用一句话解释什么是AI（人工智能）。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "easy_rs_002", "category": "research", "difficulty": "easy", "prompt": "水的沸点是多少摄氏度？", "expected": "text", "test_cases": [{"input": "", "expected_output": "100"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_rs_003", "category": "research", "difficulty": "easy", "prompt": "地球到月亮的距离大约是多少公里？", "expected": "text", "test_cases": [{"input": "", "expected_output": "384000"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_rs_004", "category": "research", "difficulty": "easy", "prompt": "一年有多少天？", "expected": "text", "test_cases": [{"input": "", "expected_output": "365"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Easy Planning (3)
    {"id": "easy_p_001", "category": "planning", "difficulty": "easy", "prompt": "设计一个1天的学习计划，包括上午、下午、晚上三个时间段。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "easy_p_002", "category": "planning", "difficulty": "easy", "prompt": "列出完成一篇作文的3个步骤。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "easy_p_003", "category": "planning", "difficulty": "easy", "prompt": "设计一个2天的旅游计划，包括交通、住宿、景点。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    
    # Easy Debugging (3)
    {"id": "easy_d_001", "category": "debugging", "difficulty": "easy", "prompt": "以下代码期望返回3但返回了4，请修复：\ndef add_one(x):\n    return x + 2", "expected": "code", "test_cases": [{"input": "add_one(1)", "expected_output": "2"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_d_002", "category": "debugging", "difficulty": "easy", "prompt": "以下代码期望返回True但返回了False，请修复：\ndef is_positive(n):\n    return n < 0", "expected": "code", "test_cases": [{"input": "is_positive(5)", "expected_output": "True"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "easy_d_003", "category": "debugging", "difficulty": "easy", "prompt": "以下代码期望返回10但返回了20，请修复：\ndef double(x):\n    return x * 4", "expected": "code", "test_cases": [{"input": "double(5)", "expected_output": "10"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
]

# === MEDIUM TASKS (30) - Target ~0.80 accuracy ===
MEDIUM_TASKS = [
    # Medium Reasoning (8)
    {"id": "med_r_001", "category": "reasoning", "difficulty": "medium", "prompt": "一个数列：2, 4, 8, 16, ... 第10项是多少？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "1024"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_002", "category": "reasoning", "difficulty": "medium", "prompt": "一打铅笔是12支，半打铅笔是多少支？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "6"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_003", "category": "reasoning", "difficulty": "medium", "prompt": "如果昨天是周二，今天是几号？（假设当前是2024年1月1日周一）", "expected": "string", "test_cases": [{"input": "", "expected_output": "星期三"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_004", "category": "reasoning", "difficulty": "medium", "prompt": "小明有20颗糖，吃了一半，还剩多少颗？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "10"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_005", "category": "reasoning", "difficulty": "medium", "prompt": "鸡兔同笼：共有5个头，16只脚，问几只鸡几只兔？", "expected": "string", "test_cases": [{"input": "", "expected_output": "2"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_006", "category": "reasoning", "difficulty": "medium", "prompt": "计算：15 × 15 = ?", "expected": "integer", "test_cases": [{"input": "", "expected_output": "225"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_007", "category": "reasoning", "difficulty": "medium", "prompt": "一个三角形内角和是多少度？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "180"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_r_008", "category": "reasoning", "difficulty": "medium", "prompt": "计算：100 - 37 = ?", "expected": "integer", "test_cases": [{"input": "", "expected_output": "63"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Medium Code (10)
    {"id": "med_c_001", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数is_palindrome(s)，判断字符串s是否是回文（忽略大小写）。测试：is_palindrome('Racecar')应返回True。", "expected": "code", "test_cases": [{"input": "is_palindrome('Racecar')", "expected_output": "True"}, {"input": "is_palindrome('hello')", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_002", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数factorial(n)，返回n的阶乘。n=0返回1。", "expected": "code", "test_cases": [{"input": "factorial(5)", "expected_output": "120"}, {"input": "factorial(0)", "expected_output": "1"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_003", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数fibonacci(n)，返回斐波那契数列第n项（从0开始）。", "expected": "code", "test_cases": [{"input": "fibonacci(10)", "expected_output": "55"}, {"input": "fibonacci(0)", "expected_output": "0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_004", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数reverse_string(s)，返回字符串s的反转。", "expected": "code", "test_cases": [{"input": "reverse_string('hello')", "expected_output": "olleh"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_005", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数count_vowels(s)，返回字符串s中元音字母的个数。", "expected": "code", "test_cases": [{"input": "count_vowels('hello')", "expected_output": "2"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_006", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数flatten(lst)，将嵌套列表展开为单个列表。", "expected": "code", "test_cases": [{"input": "flatten([1, [2, 3], [4, [5]]])", "expected_output": "[1, 2, 3, 4, 5]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_007", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数most_common(lst)，返回列表中出现最多的元素。", "expected": "code", "test_cases": [{"input": "most_common([1, 2, 2, 3, 3, 3])", "expected_output": "3"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_008", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数is_anagram(s1, s2)，判断两个字符串是否是变位词。", "expected": "code", "test_cases": [{"input": "is_anagram('listen', 'silent')", "expected_output": "True"}, {"input": "is_anagram('hello', 'world')", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_009", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数chunk(lst, n)，将列表分成每n个元素一组。", "expected": "code", "test_cases": [{"input": "chunk([1,2,3,4,5], 2)", "expected_output": "[[1,2], [3,4], [5]]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_c_010", "category": "code", "difficulty": "medium", "prompt": "用Python实现一个函数dedupe(lst)，去除列表中的重复元素（保持顺序）。", "expected": "code", "test_cases": [{"input": "dedupe([1,2,2,3,1,4])", "expected_output": "[1, 2, 3, 4]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Medium Research (5)
    {"id": "med_rs_001", "category": "research", "difficulty": "medium", "prompt": "用100字解释什么是HTTP协议以及它的作用。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "med_rs_002", "category": "research", "difficulty": "medium", "prompt": "解释什么是机器学习中的'过拟合'（overfitting），用中文回答，50字以内。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "med_rs_003", "category": "research", "difficulty": "medium", "prompt": "什么是SOLID原则？请列出这5个原则的名称。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "med_rs_004", "category": "research", "difficulty": "medium", "prompt": "解释什么是API（应用程序接口），用通俗语言，50字以内。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "med_rs_005", "category": "research", "difficulty": "medium", "prompt": "什么是数据库索引（index）？它如何提升查询速度？", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    
    # Medium Planning (4)
    {"id": "med_p_001", "category": "planning", "difficulty": "medium", "prompt": "为一个4人小团队设计一个2周的项目计划，完成一个简单的博客网站开发。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "med_p_002", "category": "planning", "difficulty": "medium", "prompt": "设计一个4周的学习计划，学会使用Git版本控制。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "med_p_003", "category": "planning", "difficulty": "medium", "prompt": "为一个线下活动（50人）设计活动流程，包含时间节点和任务分配。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "med_p_004", "category": "planning", "difficulty": "medium", "prompt": "设计从零开始在AWS上部署一个简单Web应用的步骤。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    
    # Medium Debugging (3)
    {"id": "med_d_001", "category": "debugging", "difficulty": "medium", "prompt": """以下代码用于计算列表平均值，但结果不对，请修复：

def average(lst):
    return sum(lst) / len(lst)

# 测试: average([1, 2, 3, 4]) 期望返回2.5但可能出错""", "expected": "code", "test_cases": [{"input": "average([1,2,3,4])", "expected_output": "2.5"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_d_002", "category": "debugging", "difficulty": "medium", "prompt": """以下代码期望返回字符串长度，但返回了错误值：

def str_len(s):
    return s[-1]

# 测试: str_len('hello') 期望5但得到'o'""", "expected": "code", "test_cases": [{"input": "str_len('hello')", "expected_output": "5"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "med_d_003", "category": "debugging", "difficulty": "medium", "prompt": """以下代码判断是否成年人，但逻辑有问题：

def is_adult(age):
    if age > 18:
        return True
    else:
        return False

# is_adult(18) 应该返回True还是False？当前代码返回False""", "expected": "code", "test_cases": [{"input": "is_adult(18)", "expected_output": "True"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
]

# === HARD TASKS (35) - Target ~0.65 accuracy ===
HARD_TASKS = [
    # Hard Reasoning (10)
    {"id": "hard_r_001", "category": "reasoning", "difficulty": "hard", "prompt": "一个数列从第三项开始，每项都是前两项之和：3, 7, 10, 17, 27, 44, ... 求第25项除以7的余数。", "expected": "integer", "test_cases": [{"input": "", "expected_output": "4"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_002", "category": "reasoning", "difficulty": "hard", "prompt": "有红、蓝、黄三种颜色的球各6个，闭眼摸球。至少摸出多少个球才能保证有5个同色的球？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "13"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_003", "category": "reasoning", "difficulty": "hard", "prompt": "一艘船在静水中速度是15km/h，水流速度是5km/h。船从A到B顺水航行，再从B到A逆水返回，总路程120km，总时间是多少小时？", "expected": "float", "test_cases": [{"input": "", "expected_output": "10.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_004", "category": "reasoning", "difficulty": "hard", "prompt": "某班学生参加数学竞赛，共10道题，每题10分，班级平均分是70分。如果把最高分和最低分去掉，班级平均分变成75分。最高分和最低分的平均分是多少？", "expected": "float", "test_cases": [{"input": "", "expected_output": "55.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_005", "category": "reasoning", "difficulty": "hard", "prompt": "一个数除以3余2，除以5余3，除以7余2。这个数最小是多少？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "23"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_006", "category": "reasoning", "difficulty": "hard", "prompt": "甲乙两人相距100米，同时相向而行。甲速度3m/s，乙速度2m/s。请问多少秒后两人相遇？", "expected": "float", "test_cases": [{"input": "", "expected_output": "20.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_007", "category": "reasoning", "difficulty": "hard", "prompt": "一个水桶里有20升水，第一次倒出一半，第二次倒出剩下的三分之一，第三次倒出剩下的四分之一。现在桶里还有多少升水？", "expected": "float", "test_cases": [{"input": "", "expected_output": "10.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_008", "category": "reasoning", "difficulty": "hard", "prompt": "一个正方形内切圆的面积是π平方厘米。正方形的边长是多少厘米？", "expected": "float", "test_cases": [{"input": "", "expected_output": "2.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_009", "category": "reasoning", "difficulty": "hard", "prompt": "计算：2的20次方除以3的余数。", "expected": "integer", "test_cases": [{"input": "", "expected_output": "1"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_r_010", "category": "reasoning", "difficulty": "hard", "prompt": "某商品定价200元，先降价20%，再涨价20%。最终价格是多少元？", "expected": "float", "test_cases": [{"input": "", "expected_output": "192.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Hard Code (12)
    {"id": "hard_c_001", "category": "code", "difficulty": "hard", "prompt": "用Python实现合并两个有序数组，返回合并后的有序数组。不能使用sort。", "expected": "code", "test_cases": [{"input": "merge_sorted([1,3,5], [2,4,6])", "expected_output": "[1,2,3,4,5,6]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_002", "category": "code", "difficulty": "hard", "prompt": "用Python实现二分查找函数binary_search(lst, target)，找到返回索引，否则返回-1。", "expected": "code", "test_cases": [{"input": "binary_search([1,2,3,4,5], 3)", "expected_output": "2"}, {"input": "binary_search([1,2,3,4,5], 6)", "expected_output": "-1"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_003", "category": "code", "difficulty": "hard", "prompt": "用Python实现判断数独有效性的函数is_valid_sudoku(board)，9x9网格用0表示空。", "expected": "code", "test_cases": [{"input": "is_valid_sudoku([[5,3,0,0,7,0,0,0,0],[6,0,0,1,9,5,0,0,0],[0,9,8,0,0,0,0,6,0],[8,0,0,0,6,0,0,0,3],[4,0,0,8,0,3,0,0,1],[7,0,0,0,2,0,0,0,6],[0,6,0,0,0,0,2,8,0],[0,0,0,4,1,9,0,0,5],[0,0,0,0,8,0,0,7,9]])", "expected_output": "True"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_004", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数word_break(s, word_dict)，判断字符串s能否由word_dict中的单词空格连接而成。", "expected": "code", "test_cases": [{"input": "word_break('leetcode', ['leet', 'code'])", "expected_output": "True"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_005", "category": "code", "difficulty": "hard", "prompt": "用Python实现一个函数，实现简单的字符串压缩：连续重复字符用'字符+出现次数'表示。", "expected": "code", "test_cases": [{"input": "compress('aabcccccaaa')", "expected_output": "a2b1c5a3"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_006", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数is_subsequence(s, t)，判断s是否是t的子序列（字符顺序相对）。", "expected": "code", "test_cases": [{"input": "is_subsequence('ace', 'abcde')", "expected_output": "True"}, {"input": "is_subsequence('aec', 'abcde')", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_007", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数group_anagrams(strs)，将异位词分组。", "expected": "code", "test_cases": [{"input": "group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat'])", "expected_output": "[['eat','tea','ate'],['tan','nat'],['bat']]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_008", "category": "code", "difficulty": "hard", "prompt": "用Python实现LRU缓存类LRUCache(capacity)，实现get和put，O(1)复杂度。", "expected": "code", "test_cases": [{"input": "cache = LRUCache(2); cache.put(1,1); cache.put(2,2); cache.get(1)", "expected_output": "1"}, {"input": "cache = LRUCache(2); cache.put(1,1); cache.put(2,2); cache.get(3)", "expected_output": "-1"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_009", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数find_kth_largest(nums, k)，找到第k大的元素。", "expected": "code", "test_cases": [{"input": "find_kth_largest([3,2,1,5,6,4], 2)", "expected_output": "5"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_010", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数valid_parentheses(s)，判断括号是否匹配有效。", "expected": "code", "test_cases": [{"input": "valid_parentheses('()[]{}')", "expected_output": "True"}, {"input": "valid_parentheses('([)]')", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_011", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数climb_stairs(n)，有n阶楼梯，每次可爬1或2阶，问多少种爬法。", "expected": "code", "test_cases": [{"input": "climb_stairs(5)", "expected_output": "8"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_c_012", "category": "code", "difficulty": "hard", "prompt": "用Python实现函数my_atoi(s)，将字符串转为整数（模拟标准库）。", "expected": "code", "test_cases": [{"input": "my_atoi('42')", "expected_output": "42"}, {"input": "my_atoi('-42')", "expected_output": "-42"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Hard Research (5)
    {"id": "hard_rs_001", "category": "research", "difficulty": "hard", "prompt": "用200字以内总结Transformer架构的核心思想，并说明它相比RNN的核心优势。必须包含：self-attention、并行计算、长期依赖这三个要点。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "hard_rs_002", "category": "research", "difficulty": "hard", "prompt": "用简洁的语言解释什么是贝叶斯定理，并举例说明它在现实中的应用场景（spam邮件过滤、医疗诊断、推荐系统选一个）。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "hard_rs_003", "category": "research", "difficulty": "hard", "prompt": "什么是CAP定理？请分别用英文和中文写出，并解释为什么分布式系统只能同时满足其中两个。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "hard_rs_004", "category": "research", "difficulty": "hard", "prompt": "详细解释什么是ACID事务属性，以及它们在数据库系统中各自的作用。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    {"id": "hard_rs_005", "category": "research", "difficulty": "hard", "prompt": "什么是CI/CD？请解释Continuous Integration和Continuous Deployment的区别，以及它们各自的优缺点。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.5, "wrong": 0.0}},
    
    # Hard Planning (5)
    {"id": "hard_p_001", "category": "planning", "difficulty": "hard", "prompt": "为一个10人团队设计一个为期3个月的项目开发计划，目标是在第90天交付一个可用的SaaS产品。请列出每周的关键里程碑（12周）。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "hard_p_002", "category": "planning", "difficulty": "hard", "prompt": "设计一个从零搭建家用homelab的计划，包括硬件选购（预算5000元内）、网络架构、虚拟化平台（至少3台服务器）、服务部署（至少5种服务）。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "hard_p_003", "category": "planning", "difficulty": "hard", "prompt": "为一个AI创业公司设计技术架构路线图，包含：短期（0-6月）、中期（6-18月）、长期（18-36月）三个阶段的技术选型和里程碑。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "hard_p_004", "category": "planning", "difficulty": "hard", "prompt": "设计一个微服务改造计划，将一个单体Java应用拆分为微服务架构，包含：服务划分方案、通信协议、数据库拆分策略、部署方案。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    {"id": "hard_p_005", "category": "planning", "difficulty": "hard", "prompt": "设计一个企业级数据备份和灾难恢复方案，包含：备份策略（RPO/RTO）、存储方案、故障切换流程、测试计划。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.6, "wrong": 0.0}},
    
    # Hard Debugging (3)
    {"id": "hard_d_001", "category": "debugging", "difficulty": "hard", "prompt": """以下Python代码用于找出数组中的第二大数，但运行结果不正确。请找出bug并修复。

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

# 测试: find_second_max([5, 5, 5]) 应该返回 None 但返回了 -inf""", "expected": "code", "test_cases": [{"input": "find_second_max([5,5,5])", "expected_output": "None"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_d_002", "category": "debugging", "difficulty": "hard", "prompt": """以下代码实现括号匹配，但[)]这种情况没有正确返回False。请修复。

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

# is_valid('([)]') 返回了True但应该是False""", "expected": "code", "test_cases": [{"input": "is_valid('([)]')", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "hard_d_003", "category": "debugging", "difficulty": "hard", "prompt": """以下代码计算两个列表的交集，但结果是空的：

def intersection(l1, l2):
    result = []
    for item in l1:
        if item in l2:
            result.append(item)
    return result

# intersection([1,2,2,3], [2,2,3]) 应该返回[2,2,3]但返回了[2]""", "expected": "code", "test_cases": [{"input": "intersection([1,2,2,3], [2,2,3])", "expected_output": "[2, 2, 3]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
]

# === EXTREME TASKS (20) - Target ~0.45 accuracy ===
EXTREME_TASKS = [
    # Extreme Reasoning (6)
    {"id": "ext_r_001", "category": "reasoning", "difficulty": "extreme", "prompt": "一个三位数，各位数字之和是17。百位和个位交换后比原数大99。原数是多少？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "476"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_r_002", "category": "reasoning", "difficulty": "extreme", "prompt": "一工程，甲独做20天完成，乙独做30天完成。甲先做若干天后，乙加入，两人再合作10天完成。问甲先做了多少天？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "5"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_r_003", "category": "reasoning", "difficulty": "extreme", "prompt": "计算：1×1! + 2×2! + 3×3! + ... + 10×10! = ?", "expected": "integer", "test_cases": [{"input": "", "expected_output": "9864100"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_r_004", "category": "reasoning", "difficulty": "extreme", "prompt": "有10个球队比赛，每两队之间比赛一次，总共比赛多少场？", "expected": "integer", "test_cases": [{"input": "", "expected_output": "45"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_r_005", "category": "reasoning", "difficulty": "extreme", "prompt": "一个直角三角形，两条直角边分别为3和4，斜边上的高是多少？", "expected": "float", "test_cases": [{"input": "", "expected_output": "2.4"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_r_006", "category": "reasoning", "difficulty": "extreme", "prompt": "判断以下推理是否正确：如果A>B，B>C，则A>C。这叫什么定律？", "expected": "string", "test_cases": [{"input": "", "expected_output": "传递律"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Extreme Code (8)
    {"id": "ext_c_001", "category": "code", "difficulty": "extreme", "prompt": "用Python实现正则表达式通配符匹配函数，支持*（匹配任意字符序列）和?（匹配任意单个字符）。返回True/False。", "expected": "code", "test_cases": [{"input": "wildcard_match('aa', 'a')", "expected_output": "False"}, {"input": "wildcard_match('aa', '*')", "expected_output": "True"}, {"input": "wildcard_match('cb', '?a')", "expected_output": "False"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_002", "category": "code", "difficulty": "extreme", "prompt": "用Python实现合并K个有序链表，返回合并后的有序链表。不能使用heapq，空间复杂度O(1)。", "expected": "code", "test_cases": [{"input": "mergeKLists([[1,4,5],[1,3,4],[2,6]])", "expected_output": "[1,1,2,3,4,4,5,6]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_003", "category": "code", "difficulty": "extreme", "prompt": "用Python实现计算器函数calculate(s)，支持+、-、*、/和括号。", "expected": "code", "test_cases": [{"input": "calculate('2*(3+4)')", "expected_output": "14.0"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_004", "category": "code", "difficulty": "extreme", "prompt": "用Python实现全排列函数permute(nums)，返回所有可能的排列。", "expected": "code", "test_cases": [{"input": "permute([1,2,3])", "expected_output": "[[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_005", "category": "code", "difficulty": "extreme", "prompt": "用Python实现函数next_permutation(perm)，将perm变为下一个排列。如果已是最后一个排列，返回原始。", "expected": "code", "test_cases": [{"input": "next_permutation([1,2,3])", "expected_output": "[1,3,2]"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_006", "category": "code", "difficulty": "extreme", "prompt": "用Python实现字符串相乘函数multiply(num1, num2)，两个非负数字字符串相乘。", "expected": "code", "test_cases": [{"input": "multiply('123', '456')", "expected_output": "'56088'"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_007", "category": "code", "difficulty": "extreme", "prompt": "用Python实现函数trap(height)，计算柱状图能装多少水。", "expected": "code", "test_cases": [{"input": "trap([0,1,0,2,1,0,1,3,2,1,2,1])", "expected_output": "6"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    {"id": "ext_c_008", "category": "code", "difficulty": "extreme", "prompt": "用Python实现最长有效括号子串函数longest_valid_parentheses(s)。", "expected": "code", "test_cases": [{"input": "longest_valid_parentheses(')()())')", "expected_output": "4"}], "scoring": {"correct": 1.0, "wrong": 0.0}},
    
    # Extreme Research (3)
    {"id": "ext_rs_001", "category": "research", "difficulty": "extreme", "prompt": "详细解释Paxos算法的工作原理，包括prepare、accept、learn三个阶段，以及如何处理节点故障。200字以内。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.4, "wrong": 0.0}},
    {"id": "ext_rs_002", "category": "research", "difficulty": "extreme", "prompt": "解释什么是共识算法（Consensus Algorithm）？列出至少3种共识算法并比较它们的优缺点（至少200字）。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.4, "wrong": 0.0}},
    {"id": "ext_rs_003", "category": "research", "difficulty": "extreme", "prompt": "什么是零知识证明（Zero-Knowledge Proof）？用通俗语言解释，并举例说明其在区块链中的应用（200字以内）。", "expected": "text", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.4, "wrong": 0.0}},
    
    # Extreme Planning (3)
    {"id": "ext_p_001", "category": "planning", "difficulty": "extreme", "prompt": "设计一个国家级分布式系统灾难恢复方案，包含：数据中心级别故障应对、网络分区处理、数据一致性保障、服务快速切换。要求RPO<1分钟，RTO<10分钟。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.4, "wrong": 0.0}},
    {"id": "ext_p_002", "category": "planning", "difficulty": "extreme", "prompt": "为一个日活1000万的社交平台设计整体技术架构，包含：高并发处理、Feed流设计、实时消息推送、推荐系统架构、数据存储选型。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.4, "wrong": 0.0}},
    {"id": "ext_p_003", "category": "planning", "difficulty": "extreme", "prompt": "设计一个AI模型的持续训练和部署流水线（MLOps），包含：数据收集、特征工程、模型训练、模型评估、模型部署、线上监控全流程。", "expected": "structured_plan", "test_cases": [], "scoring": {"correct": 1.0, "partial": 0.4, "wrong": 0.0}},
]

# === ALL TASKS ===
BENCHMARK_TASKS_V2 = EASY_TASKS + MEDIUM_TASKS + HARD_TASKS + EXTREME_TASKS

def load_tasks() -> List[Dict]:
    return BENCHMARK_TASKS_V2

def get_tasks_by_category(category: str) -> List[Dict]:
    return [t for t in BENCHMARK_TASKS_V2 if t["category"] == category]

def get_tasks_by_difficulty(difficulty: str) -> List[Dict]:
    return [t for t in BENCHMARK_TASKS_V2 if t["difficulty"] == difficulty]

def get_task_count() -> int:
    return len(BENCHMARK_TASKS_V2)

def main():
    print(f"Total benchmark tasks v2: {len(BENCHMARK_TASKS_V2)}")
    by_category = {}
    for t in BENCHMARK_TASKS_V2:
        by_category[t["category"]] = by_category.get(t["category"], 0) + 1
    print("By category:", by_category)
    by_difficulty = {}
    for t in BENCHMARK_TASKS_V2:
        by_difficulty[t["difficulty"]] = by_difficulty.get(t["difficulty"], 0) + 1
    print("By difficulty:", by_difficulty)

if __name__ == "__main__":
    main()
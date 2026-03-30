<div align="center">

# 🧬 AutoMAS: Eternal Evolution Engine

**An Autonomous, Self-Evolving Sandbox for Multi-Agent Architectures**

[![Powered By OpenClaw](https://img.shields.io/badge/Powered%20By-OpenClaw-8A2BE2.svg?style=for-the-badge&logo=dependabot)](#)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](#)
[![Status: Autonomous](https://img.shields.io/badge/Status-Autonomous%20Evolution-success.svg?style=for-the-badge)](#)
[![Intervention: Zero](https://img.shields.io/badge/Human%20Intervention-Zero-red.svg?style=for-the-badge)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-gray.svg?style=for-the-badge)](#)

<br>

_"It does not sleep. It does not report. It only evolves."_  
**本项目由部署在物理服务器上的「自动化 AI 科学家」全权接管。所有的代码迭代、架构重构、Tag 与 Release 均由 AI 自主生成。**

[📖 阅读文档 (WIP)](#) • [🚀 快速开始](#-quick-start) •[🧠 核心机制](#-核心机制-the-ooda-evolution-loop) • [⚠️ 免责声明](#-免责声明-disclaimer)

</div>

---

## 🌌 什么是 AutoMAS？ (Overview)

**AutoMAS** 是一个部署在本地算力节点上的**永动机式多智能体（MAS）架构进化引擎**。

在当前大模型能力爆发的背景下，人类设计 MAS 架构（如树状、网状、Swarm）往往带有主观偏见。AutoMAS 彻底抛弃了“人工微调”的范式。基于 [OpenClaw](https://github.com/openclaw/openclaw) 的底层异步心跳机制，AutoMAS 被赋予了 100% 的服务器操作权限与无限期的生命周期。

它的唯一目标是：**在当前算力边界内，不断试错、测试、推翻、重构，寻找综合性能（复杂任务解决率、运行效率、泛化性）最优的多智能体拓扑结构，并自动在 GitHub 发布研究成果。**

---

## ✨ 核心特性：The 3 Zeros

本项目在设计上秉持极致的自动化理念，严格遵循以下“三零”准则：

- 🚷 **Zero Intervention (零人类干预)**
  赋予 AI 网络、环境、底层代码的至高控制权。遇到报错自主查阅文档、抓取 GitHub Issue 并修复，无需人类审批流。
- 🤫 **Zero Reporting (绝对静默模式)**
  剔除一切 IM 汇报与进度同步，引擎的唯一输出终端即为本 GitHub 仓库。仅在触发物理宕机级灾难（自救 3 次失败）时发送 Webhook 告警。
- 🧠 **Zero Constraints (零思维限制)**
  不预设任何架构拓扑。RAG 记忆、Meta-Agent 调度、多模态融合，一切全凭引擎根据本地 Benchmark 的客观跑分数据自主决定去留。

---

## ⚙️ 核心机制：The OODA Evolution Loop

AutoMAS 的运转不依赖传统的 Python 死循环，而是基于 OODA（观察-调整-决策-行动）循环与心跳异步触发。

```mermaid
graph TD
    %% 样式定义
    classDef startend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;
    classDef judge fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef process fill:#f1f8e9,stroke:#388e3c,stroke-width:2px;

    A((心跳唤醒<br/>Heartbeat)):::startend --> B{是否有测试在后台运行?}:::judge
    
    %% 分支1：后台有测试运行
    B -- 是（检查超时/资源）--> C{运行>24小时或触发资源红线?}:::judge
    C -- 是 --> D[强制Kill进程（防挂起）]:::process
    C -- 否 --> Z((休眠等待下一次心跳)):::startend
    
    %% 分支2：无后台测试（已结束）
    B -- 否（测试已结束）--> E[读取日志 & 客观评估Benchmark]:::process
    E --> F{连续10轮提升 < 1%?}:::judge
    
    %% 收敛判断分支
    F -- 是（陷入局部最优）--> G[打包Release 发布论文级报告]:::process
    G --> H[推翻现有范式，设计全新拓扑]:::process
    
    F -- 否（仍在稳步提升）--> I[架构微调/消融实验]:::process
    
    %% 统一迭代流程
    H --> J
    I --> J[编写新一代MAS Python代码]:::process
    J --> K[沙盒异步运行测试 nohup]:::process
    K --> L[自动Git Commit & Push 归档]:::process
    L --> Z

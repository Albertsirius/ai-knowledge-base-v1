# AI Knowledge Base (AI知识库助手)

## 项目概述

AI知识库助手是一个基于多Agent协作的AI/LLM/Agent领域知识采集与管理工具。系统自动从GitHub Trending和Hacker News等数据源采集高质量开源项目和技术文章，通过Agent协作流水线完成**采集 → 分析 → 整理**三阶段处理，最终由AI分析后结构化存储为结构化、可检索的知识条目。

## 项目结构

```
ai-knowledge-base-v1/
├── AGENTS.md                       # 项目文档（本文件）
├── .opencode/
│   ├── agents/                     # Agent角色定义
│   |   ├── collector.md            # 采集 Agent 角色定义
|   |   ├── analyzer.md             # 分析 Agent 角色定义
|   |   └── organizer.md            # 整理 Agent 角色定义
│   └── skills/                     # Agent技能脚本
└── knowledge/
    ├── raw/                        # 原始采集数据
    │   └── {source}-{YYYY-MM-DD}.json
    └── articles/                   # 结构化知识条目
        └── {YYYY-MM-DD}-{slug}.json
```

## 文件命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 原始数据 | `knowledge/raw/{source}-{YYYY-MM-DD}.json` | `knowledge/raw/github-trending-2026-06-18.json`<br>`knowledge/raw/hackernews-2026-06-18.json` |
| 知识条目 | `knowledge/articles/{YYYY-MM-DD}-{slug}.json` | `knowledge/articles/2026-06-18-llama3-paper.json` |
| 索引文件 | `knowledge/articles/index.json` |

## 技术栈

- **运行环境**: Python 3.13
- **AI编排**: OpenCode（Agent协作框架）
- **大模型**: 国产大模型（通过OpenCode Provider接入）
- **数据格式**: JSON

## Agent协作
### 三阶段流水线

```
[Collector] ──采集──→ knowledge/raw/
                          │
[Analyzer]  ──分析──→ knowledge/raw/ (enriched)
                          │
[Organizer] ──整理──→ knowledge/articles/
```

### Agent角色概览

| 阶段 | Agent角色 | 英文名 | 职责描述 | 输入 | 输出 |
|------|-----------|--------|----------|------|------|
| 采集 | 采集Agent | Collector | 从GitHub Trending和Hacker News抓取AI/LLM/Agent相关的高质量项目和文章，过滤噪音，输出原始数据。 | 数据源配置、日期范围 | `knowledge/raw/{source}-{date}.json` |
| 分析 | 分析Agent | Analyzer | 对原始采集数据进行AI驱动的深度分析与解读，提取核心观点、技术亮点、适用场景，生成分析摘要。 | 原始数据JSON | 分析摘要（内嵌于条目中） |
| 整理 | 整理Agent | Organizer | 将分析后的数据整合为结构化知识条目，生成slug、分类标签、关联关系，持久化写入JSON文件。 | 分析摘要 | `knowledge/articles/{date}-{slug}.json` |

## 数据源

| 数据源 | 采集目标 | 过滤条件 |
|--------|----------|----------|
| GitHub Trending | 当日/本周热门开源仓库 | 语言: Python/TypeScript/Rust/C++/Java/Go；主题: AI, LLM, Agent, Machine Learning, NLP |
| Hacker News | AI/LLM相关热门文章和讨论 | 关键词: AI, LLM, GPT, Agent, Machine Learning, Deep Learning, Transformer |



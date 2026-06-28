---
name: tech-summary
description: 当需要对采集的技术内容进行分析时使用此 skill。读取 knowledge/raw/ 中的原始采集数据，逐条进行分析、生成摘要、评分、提取标签，输出分析结果。
allowed-tools:
  - read
  - glob
  - grep
  - webfetch
---

# 技术分析摘要生成

读取 `knowledge/raw/` 目录中最新的采集数据，对每条技术项目进行 AI 驱动的分析、摘要生成、评分和标签提取。

## 使用场景

- 对 GitHub Trending / Hacker News 采集的原始数据进行深度解读
- 评估开源项目的技术深度、实用价值和创新性
- 提取核心观点，识别适用场景和潜在局限
- 为知识库整理阶段准备结构化的分析数据

## 输入

- **数据文件**: `knowledge/raw/` 目录下最新日期的 JSON 文件（如 `knowledge/raw/github-trending-2026-06-21.json`）
- **数据格式**: 包含 `items` 数组，每条记录含 `title`、`url`、`description`、`stars`、`language`、`topics` 等字段

## 执行步骤

### 1. 定位最新采集文件

```bash
ls -t knowledge/raw/*.json | head -1
```

选取最近日期的原始采集数据文件，跳过 `filtered-*.json`（过滤日志）。

### 2. 读取原始数据

读取完整的 JSON 数据，解析 `items` 数组。如果条目数超过 10 条，优先选取 `stars` 最高的前 10 条进行深度分析，其余做快速摘要。

### 3. 生成技术摘要(summary)

**摘要长度**：100-200 个中文字符

**结构要求**（不需要显式标注，自然融入）：
1. **定位**（1 句）：这个项目/文章解决什么问题
2. **核心内容**（2-3 句）：关键技术方案、架构特点、主要创新
3. **价值判断**（1 句）：对 AI 工程师的实际意义

**写作规范**：
- 第一句直接点明核心，不要 "本项目是..."、"这篇文章介绍了..." 等模板开头
- 技术术语保留英文原文，如 RAG、MCP、Fine-tuning
- 避免空洞的形容词（"强大的"、"创新性的"）——用具体信息替代
- 如果能写出具体数字（性能提升、模型大小等），优先使用数字

**示例**：

好的摘要：
> 基于 Tree-of-Thought 推理框架，让 LLM 在复杂数学推理任务上的准确率从
> 54% 提升到 74%。核心思路是将单次推理拆分为多步搜索树，每步生成多个候选
> 并通过 LLM 自评估剪枝。实现代码不到 500 行 Python，可直接集成到现有
> LangChain 管道中。

差的摘要：
> 这是一个非常创新的项目，使用了先进的 AI 技术来提升推理能力。
> 它采用了一种新颖的方法，在多个基准测试中取得了很好的效果。
> 对于 AI 从业者来说值得关注。

### 4. 评分

对每条记录进行 5 维度评分（1-10 分）：

| 维度 | 权重 | 说明 |
|------|:----:|------|
| `technical_depth` | 25% | 架构设计精巧度、工程实现复杂度 |
| `practical_value` | 30% | 解决实际问题的能力、落地可行性 |
| `community_activity` | 20% | Stars、Forks、Issues、活跃贡献者数 |
| `innovation` | 25% | 是否带来新思路或解决新问题 |

`composite` = 加权和，四舍五入保留 1 位小数。

**评分标准**：

| 分数区间 | 含义 |
|----------|------|
| 9.0 - 10.0 | 领域标杆，技术突破性 |
| 8.0 - 8.9 | 优秀，有显著创新或极高实用价值 |
| 7.0 - 7.9 | 良好，值得关注和尝试 |
| 6.0 - 6.9 | 有潜力，但存在明显短板 |
| 5.0 - 5.9 | 一般，特定场景有价值 |
| < 5.0 | 质量存疑，实用价值有限 |

### 5. 提取标签

为每个条目生成 3-5 个标签：

**标签词库**（优先使用，保持一致性）：
- 领域：`large-language-model`, `agent-framework`, `rag`, `mcp`, `fine-tuning`, `prompt-engineering`, `multi-agent`, `code-generation`
- 技术：`transformer`, `attention`, `embedding`, `vector-database`, `knowledge-graph`
- 工具：`langchain`, `llamaindex`, `openai`, `anthropic`, `deepseek`, `huggingface`
- 场景：`chatbot`, `code-assistant`, `data-analysis`, `document-qa`, `workflow-automation`

如果条目涉及词库中没有的概念，可以新增标签，但必须遵循小写连字符格式。

### 6. 输出分析结果

将每个条目追加以下字段：

```json
{
  "analyzed_at": "2026-06-21T10:00:00Z",
  "summary": "摘要",
  "score": 8.5,
  "score_breakdown": {
    "technical_depth": 9,
    "practical_value": 8,
    "community_activity": 9,
    "innovation": 8
  },
  "tags": ["agent-framework", "multi-agent", "python"]
}
```

## 输出

- 将注入分析字段后的完整数据**返回给主 Agent 写入**原文件
- 不创建新文件，所有分析字段追加到原有 `items[i]` 条目中
- 保持原有字段完整不丢失

## 注意事项

- **深度优于速度**：优先使用 `webfetch` 访问项目 README 和文档，基于一手信息进行分析，而非仅凭摘要猜测
- **客观公正**：不因项目 star 数高低而预设偏见，低 star 项目若有强创新性也应如实评价
- **评分一致性**：同维度评分标准应在所有条目间保持一致，避免主观波动
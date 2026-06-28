---
name: github-trending
description: 当需要采集 GitHub 热门开源项目时使用此 skill。从 GitHub Trending 抓取 AI/LLM/Agent 领域的高质量开源仓库，过滤噪音后输出结构化 JSON。
allowed-tools:
  - webfetch
  - read
  - grep
  - glob
---

# GitHub Trending 采集

从 GitHub 搜索 API 采集指定时间窗口内的热门开源项目，聚焦 AI/LLM/Agent 领域，经过过滤、去重后输出结构化 JSON 数据。

## 使用场景

- 用户要求查看 GitHub 热门 AI 项目
- 需要采集本周/本月的高质量开源仓库
- 构建 AI 领域知识库的数据采集流水线
- 监测 AI/LLM/Agent 生态的技术趋势

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `language` | string / array | 否 | 编程语言过滤，如 `["Python", "TypeScript", "Rust", "C++", "Java", "Go"]`，默认不限 |
| `topics` | string / array | 否 | 主题关键词过滤，如 `["ai", "llm", "agent", "machine-learning", "nlp", "deep-learning", "transformer"]` |
| `date_range` | string | 否 | 时间窗口，可选 `today`（默认）、`this-week`、`this-month` |

## 执行步骤

### 1. 搜索热门仓库

使用 GitHub Search API 构建查询：

```
GET https://api.github.com/search/repositories
  ?q={topic}+language:{lang}+created:>{date}
  &sort=stars
  &order=desc
  &per_page=30
```

**查询策略**：对每对 (topic × language) 组合分别请求，取并集以覆盖更广。

**日期范围**：
- 本周：`created:>={当前日期 - 7天}`
- 本月：`created:>={当前日期 - 30天}`

**注意**：GitHub API 对未认证请求有速率限制（60 次/小时），必要时使用 `gh api` 命令以利用已认证会话。

### 2. 提取信息

从 API 响应中提取每个仓库的以下字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| `name` | `full_name` | 仓库全名（owner/repo） |
| `title` | `name` | 仓库名 |
| `url` | `html_url` | 仓库主页链接 |
| `description` | `description` | 仓库描述（必须为非空的英文描述） |
| `stars` | `stargazers_count` | Star 数量 |
| `language` | `language` | 主要编程语言 |
| `topics` | `topics` | GitHub Topics 数组 |
| `created_at` | `created_at` | 仓库创建时间 |

### 3. 过滤

按以下规则逐条过滤，仅保留符合条件的仓库：

**纳入规则（全部满足）**：
- ✅ 主题或描述包含 AI/LLM/Agent 关键词（`ai`, `llm`, `agent`, `machine-learning`, `nlp`, `deep-learning`, `transformer`, `rag`）
- ✅ 有非空的英文 `description`
- ✅ `stargazers_count` > 50

**排除规则（任一命中即排除）**：
- ❌ 标题/描述匹配 awesome-list 模式（`awesome`, `awesome-list`, `curated list`）
- ❌ 标记为 fork 仓库（`fork: true`）
- ❌ 课程作业类项目（描述含 `course`, `homework`, `assignment`, `tutorial project`）
- ❌ 个人笔记/博客类（描述含 `my notes`, `personal`, `learning log`）
- ❌ 算命/占卜/非技术类（`fortune-telling`, `horoscope`, `divination`）
- ❌ 镜像仓库（`mirror`, `backup`, `archive`）
- ❌ 空壳/资源收集类（`resources`, `collection`, `cheatsheet`）
- ❌ 已归档仓库（`archived: true`）

### 4. 去重

- 基于 `name`（owner/repo）字段去重
- 保留 `stars` 最高的重复记录
- 确保每个仓库只出现一次

### 5. 排序与截断

- 按 `stars` 降序排列
- 默认输出 Top 10，可根据用户指定调整（上限 50）

### 6. 输出 JSON

- 将结果写入 `knowledge/raw/github-trending-YYYY-MM-DD.json`
- 顶层包含 `source`, `collected_at`, `count`, `items`
- 编码格式: UTF-8

## 注意事项

- **限速处理**：GitHub API 未认证限制为 60 req/h，使用 `gh api` 可继承登录态提高限额（5000 req/h）。必要时在请求间添加 1-2 秒延迟
- **数据完整性**：API 返回的 `description` 可能为 `null`——需检查并跳过空描述的仓库
- **时间一致性**：`collected_at` 使用 ISO 8601 UTC 时间戳
- **重试机制**：API 请求失败（429/5xx）时等待后重试，最多重试 3 次
- **不分析不整理**：此 skill 仅负责采集原始数据。后续分析由 Analyzer Agent 完成，整理由 Organizer Agent 完成
- **文件可覆写**：如果目标文件已存在（同一天多次采集），直接覆盖更新

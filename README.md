# AI 知识库 （多Agents实战营作业）

## 项目说明
AI知识库助手是一个基于多Agent协作的AI/LLM/Agent领域知识采集与管理工具。系统自动从GitHub Trending和Hacker News等数据源采集高质量开源项目和技术文章，通过Agent协作流水线完成**采集 → 分析 → 整理**三阶段处理，最终由AI分析后结构化存储为结构化、可检索的知识条目。

## 版本更新

### V1.0 - 初始版本
- 任务：2-3
- 内容：建立AGENTS.md项目整体功能和规范，新建Collector、Analyzer、Oragnizer三个子Agent，整个项目正确跑跑起来。

### V1.1 - SKILL
- 任务：4
- 内容: 新增两个SKILL，github-trending和tech-summary，将Collector和Analyzer里面的关键动作抽成SKILL，利用渐进式加载减少Token量

### V1.2 - Hooks
- 任务：5
- 内容：新增两个校验Hooks程序check_quality.py和validate_json.py，均通过AI生成，校验收集的知识是否符合要求

### V1.2.1 - Hooks
- 任务：5
- 内容：新增plugins：validate.ts，通过AI生产，自动处罚校验

### V2.0 - Pipeline
- 任务：6
 

   


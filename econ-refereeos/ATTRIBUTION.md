# ATTRIBUTION.md — EconRefereeOS by 安书伟

## 1. Fork source

| | |
|---|---|
| Base project | **RefereeOS** — AG2 Hackathon 2026 科学赛道第一名 |
| Base repo URL | https://github.com/VJDiPaola/RefereeOS |
| Base captain | Vincent DiPaola |
| My repo URL | https://github.com/Anshuwei/build-with-ag2/tree/main/econ-refereeos |
| Track inheritance | base `scientific` → mine: `scientific` |

Note: 未直接 fork RefereeOS 仓库。吸取了其 6-agent 流水线架构和 evidence-board 概念，用 AG2 0.9.7 + DeepSeek 重新实现，聚焦经济学论文审稿场景。

## 2. AG2 documentation references

| File | Lines | Source doc | Verbatim / Adapted |
|------|-------|------------|--------------------|
| `src/orchestrator.py` | L35-L41 | AG2 0.9.7 LLMConfig docs | adapted: DeepSeek API 配置 |
| `src/orchestrator.py` | L92-L100 | AG2 0.9.7 `ConversableAgent` + `initiate_chat` | adapted: 接力对话流水线 |
| `src/orchestrator.py` | L118-L155 | RefereeOS `backend/agents/orchestrator.py` `_run_step` | adapted: 简化为顺序执行 |

## 3. Code reused from sample repos

| Source repo | Source file | Used in my repo | Notes |
|---|---|---|---|
| RefereeOS | `backend/agents/orchestrator.py` | `src/orchestrator.py` | 借鉴 6-agent 流水线架构 + evidence board 思路，简化为 4-agent 经济学版 |
| RefereeOS | `backend/agents/orchestrator.py` `_packet_markdown` | `src/orchestrator.py` `_format_packet` | 借鉴审稿包 Markdown 模板结构 |
| build-with-ag2 `.agents/skills/` | ag2-quickstart, ag2-subagent-delegation, ag2-structured-output | 架构参考 | Beta API 不可用（0.9.7），作为设计模式参考 |

## 4. Prompt fragments

| Used in | Source | Verbatim / Adapted |
|---------|--------|--------------------|
| INTAKE_PROMPT | original — 基于 RefereeOS intake_agent 思路 + 经济学领域知识 | adapted |
| METHODS_PROMPT | original — 经济学方法论：DID/IV/RDD + 稳健性检验 | — |
| LITERATURE_PROMPT | original — 经济学文献评估 + 过度宣称风险 | — |
| SYNTHESIS_PROMPT | original — 三段式审稿意见 + 编辑建议 | — |

## 5. What I added

- **经济学领域专业化** — 4 个 prompt 全部针对经济学论文设计（DID/IV/RDD 因果识别、文献边际贡献、过度宣称风险）
- **零外部依赖** — 去掉 Daytona/OpenAI/Gemini，纯 DeepSeek API 运行
- **内置示例论文** — 最低工资 DID 研究，可零配置运行
- **中文审稿输出** — 面向中国经济学学术社区
- **16 个 `.agents/skills/`** — 作为 AG2 Beta 架构参考

## 6. License compatibility

| Source | License | Compatible? |
|--------|---------|-------------|
| RefereeOS | MIT | ✅ |
| build-with-ag2 | Apache 2.0 | ✅ |
| AG2 framework | Apache 2.0 | ✅ |

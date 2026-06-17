# EconRefereeOS — 经济学论文审稿多智能体系统

> 基于 AG2 0.9.7 + DeepSeek | C5-AG2 挑战提交 | 安书伟

4 个专业 Agent 协作审稿：Intake（提取主张）→ Methods（方法论评估）→ Literature（文献检查）→ Synthesis（编辑建议）。输入经济学论文，输出结构化审稿报告。

**Fork 来源**: [RefereeOS](https://github.com/VJDiPaola/RefereeOS) — AG2 Hackathon 2026 科学赛道第一名

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env  # 填入 DEEPSEEK_API_KEY
python src/orchestrator.py
```

## Agent 架构

```
经济学论文 (md/txt)
       │
       ▼
┌──────────────┐
│ Intake Agent │  提取研究问题、核心主张、子领域
└──────┬───────┘
       ▼
┌──────────────┐
│Methods Agent │  因果识别、样本、稳健性、内生性
└──────┬───────┘
       ▼
┌─────────────────┐
│Literature Agent │  文献覆盖、边际贡献、过度宣称
└──────┬──────────┘
       ▼
┌────────────────┐
│Synthesis Agent │  总体评价 + 优点/问题 + 编辑建议
└────────┬───────┘
         ▼
   结构化审稿报告 (Markdown)
```

## 新增 Agent（相对 RefereeOS）

| 原 RefereeOS Agent | 本系统改动 |
|---|---|
| intake_agent | 改为经济学论文定制（子领域猜测 + 证据来源提取） |
| methods_statistics_agent | 聚焦经济学方法：DID/IV/RDD 识别 + 稳健性 |
| novelty_literature_agent | 改为经济学文献评估：边际贡献 + 过度宣称风险 |
| area_chair_agent | 简化为 Synthesis Agent，输出中文三段式审稿意见 |
| integrity_agent (removed) | 经济学论文 prompt injection 风险低，移除 |
| reproducibility_agent (removed) | Daytona 沙箱依赖外部服务，改为 Methods Agent 内的方法论复现建议 |

## 运行示例

```bash
# 内置经济学论文
python src/orchestrator.py

# 自定义论文
python src/orchestrator.py --paper examples/my_paper.md --output report.md
```

## 技术栈

- **AG2 0.9.7**: `ConversableAgent` + 接力对话流水线
- **LLM**: DeepSeek-chat (OpenAI 兼容)
- **输入**: Markdown/文本格式经济学论文
- **输出**: 结构化中文审稿报告

## 致谢

- [RefereeOS](https://github.com/VJDiPaola/RefereeOS) — Vincent DiPaola, AG2 Hackathon 2026 科学赛道第一名
- [build-with-ag2](https://github.com/ag2ai/build-with-ag2) — 15 个 `.agents/skills/` 作为架构参考
- AG2 框架 — `ag2ai/ag2`

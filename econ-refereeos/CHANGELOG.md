# Changelog · EconRefereeOS

## [1.0.0] — 2026-05-11

### Added
- 4-agent 经济学论文审稿流水线: Intake → Methods → Literature → Synthesis
- 内置经济学示例论文（最低工资 DID 面板数据研究）
- CLI 支持自定义论文 (`--paper`, `--title`, `--output`)
- 16 个 `.agents/skills/` 作为架构参考
- 烟雾测试 `tests/test_smoke.py`
- 一键复现脚本 `scripts/reproduce.sh`
- ATTRIBUTION.md + AI_LOG.md (6 iterations)

### Adapted from
- RefereeOS (VJDiPaola/RefereeOS) — 6-agent 审稿架构，AG2 Hackathon 2026 科学赛道第一名
- 去掉 Daytona/OpenAI/Gemini 外部依赖，全部改用 DeepSeek
- 通用论文审稿 → 经济学论文垂直化
- 6 agent → 4 agent（合并 integrity + 去掉 reproducibility）

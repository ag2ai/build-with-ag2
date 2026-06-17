# G1 交叉验证背书 · EconRefereeOS

> 被验证人：安书伟 | 验证时间：[待填写]

## 验证步骤（5 分钟）

```bash
git clone https://github.com/Anshuwei/build-with-ag2.git
cd build-with-ag2/econ-refereeos
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
pip install -r requirements.txt
python src/orchestrator.py
```

## 检查清单

| # | 检查项 | 状态 | 备注 |
|---|---|---|---|
| 1 | `python src/orchestrator.py` 正常运行 | ☐ | 4 个 agent 依次执行 |
| 2 | Intake Agent 提取了 5 个主张 | ☐ | 标注类型 causal/empirical/methodological |
| 3 | Methods Agent 给出风险评级 | ☐ | LOW/MEDIUM/HIGH |
| 4 | Literature Agent 列出文献缺口 | ☐ | 3+ 条缺口 |
| 5 | Synthesis Agent 生成编辑建议 | ☐ | 小修/大修/退稿 |
| 6 | 审稿报告为中文 | ☐ | |
| 7 | `.env` 不在 Git 中 | ☐ | `.gitignore` 已排除 |
| 8 | `.agents/skills/` 16 个技能存在 | ☐ | |

## 验证人意见

> [在此填写：代码是否跑通？4 个 agent 是否正常输出？]

## 改进建议

> [在此填写]

## 签名

- **姓名**: [待填写]
- **日期**: [待填写]

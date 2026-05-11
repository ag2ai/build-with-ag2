"""
EconRefereeOS — 经济学论文审稿多智能体系统
基于 AG2 0.9.7 + DeepSeek，无需外部沙箱服务。

架构（取自 RefereeOS，简化为经济学场景）:
  Intake Agent       → 提取论文核心主张和证据
  Methods Agent      → 评估方法论和统计严谨性
  Literature Agent   → 检查文献覆盖和学术贡献
  Synthesis Agent    → 生成结构化审稿意见

用法:
  python src/orchestrator.py                          # 内置示例论文
  python src/orchestrator.py --paper examples/paper.md  # 自定义论文
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from autogen import ConversableAgent, LLMConfig

load_dotenv()

# ─── 配置 ──────────────────────────────────────────────────────────
API_BASE = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
API_KEY = os.getenv("DEEPSEEK_API_KEY", os.getenv("ANTHROPIC_AUTH_TOKEN", ""))
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

llm_config = LLMConfig(
    api_type="openai",
    model=MODEL,
    api_key=API_KEY,
    base_url=API_BASE,
    temperature=0.3,
)


# ─── Agent 定义 ─────────────────────────────────────────────────────

INTAKE_PROMPT = """\
你是一位经济学论文审稿人（Intake Agent）。收到论文后，提取：
1. 核心研究问题（一句话）
2. 3-5 个关键主张（claims），每条标注类型: causal/empirical/methodological
3. 主要证据来源（数据、方法）
4. 学科子领域猜测（如：劳动经济学、宏观经济学、发展经济学）

输出 JSON:
{"research_question": "...", "claims": [{"text": "...", "type": "..."}], "evidence_sources": "...", "subfield": "..."}
"""

METHODS_PROMPT = """\
你是一位经济学方法论审稿人（Methods Agent）。收到论文主张后，检查：
1. 因果识别策略是否合理（IV/DID/RDD/实验 vs 纯相关推断）
2. 样本代表性（样本量、选择偏差、外部有效性）
3. 稳健性检验是否充分（替代变量、替代模型、安慰剂检验）
4. 内生性问题是否得到处理

对每个主张给出 risk 评级 (low/medium/high) 和一句话理由。
输出 JSON: {"claim_risks": [{"claim": "...", "risk": "...", "reason": "..."}], "overall_methods_risk": "..."}
"""

LITERATURE_PROMPT = """\
你是一位经济学文献审稿人（Literature Agent）。检查：
1. 论文是否充分引用了该领域的关键文献
2. 学术贡献的边际增量是否明确（相对于已有文献）
3. 是否存在遗漏的竞争性解释或对立学派观点
4. 是否过度宣称（overclaim）——结论是否超出证据支持范围

输出 JSON: {"literature_gaps": ["..."], "contribution_assessment": "...", "overclaim_risk": "low/medium/high", "missing_perspectives": ["..."]}
"""

SYNTHESIS_PROMPT = """\
你是一位经济学领域主席（Area Chair, Synthesis Agent）。收到三个审稿报告后，整合为：
1. 总体评价（80 字以内）
2. 主要优点（2-3 条）
3. 主要问题（2-3 条，按严重程度排序）
4. 给编辑的建议（小修/大修/退稿 三选一，加一句话理由）
5. 推荐审稿人专长（2-3 个领域关键词）

输出 JSON: {"overall_assessment": "...", "strengths": [...], "weaknesses": [...], "recommendation": "...", "recommended_expertise": [...]}
"""


# ─── 核心流程 ────────────────────────────────────────────────────────

@dataclass
class ReviewResult:
    paper_title: str = ""
    intake: dict | None = None
    methods: dict | None = None
    literature: dict | None = None
    synthesis: dict | None = None
    agent_trace: list[dict] = field(default_factory=list)
    final_packet: str = ""


def _ask_agent(name: str, system_prompt: str, message: str) -> str:
    agent = ConversableAgent(
        name=name,
        system_message=system_prompt + "\n只输出JSON，不要其他文字。",
        llm_config=llm_config,
    )
    user = ConversableAgent(
        name="user_proxy",
        human_input_mode="NEVER",
    )
    result = user.initiate_chat(agent, message=message, max_turns=1, silent=True)
    return result.summary if result.summary else ""


def _parse_json(text: str) -> dict:
    text = text.strip()
    for _ in range(2):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
    return {"raw": text}


def run_review(paper_text: str, paper_title: str = "Untitled") -> ReviewResult:
    result = ReviewResult(paper_title=paper_title)
    t0 = datetime.now(timezone.utc).isoformat()

    # Stage 1: Intake
    print("  [1/4] Intake Agent — 提取论文主张...")
    raw = _ask_agent("intake_agent", INTAKE_PROMPT, f"请分析以下经济学论文：\n\n{paper_text[:4000]}")
    result.intake = _parse_json(raw)
    result.agent_trace.append({"agent": "intake", "status": "complete", "started": t0})

    # Stage 2: Methods
    print("  [2/4] Methods Agent — 评估方法论...")
    claims_text = json.dumps(result.intake.get("claims", []), ensure_ascii=False) if result.intake else "[]"
    raw = _ask_agent("methods_agent", METHODS_PROMPT, f"论文主张：\n{claims_text}\n\n论文摘要：\n{paper_text[:2000]}")
    result.methods = _parse_json(raw)
    result.agent_trace.append({"agent": "methods", "status": "complete"})

    # Stage 3: Literature
    print("  [3/4] Literature Agent — 检查文献...")
    raw = _ask_agent(
        "literature_agent",
        LITERATURE_PROMPT,
        f"论文标题：{paper_title}\n论文内容：\n{paper_text[:3000]}\n已识别子领域：{result.intake.get('subfield', '未知') if result.intake else '未知'}",
    )
    result.literature = _parse_json(raw)
    result.agent_trace.append({"agent": "literature", "status": "complete"})

    # Stage 4: Synthesis
    print("  [4/4] Synthesis Agent — 生成审稿意见...")
    digest = json.dumps(
        {
            "paper_title": paper_title,
            "intake": result.intake,
            "methods": result.methods,
            "literature": result.literature,
        },
        ensure_ascii=False,
        indent=2,
    )
    raw = _ask_agent("synthesis_agent", SYNTHESIS_PROMPT, f"三份审稿报告如下：\n\n{digest[:6000]}")
    result.synthesis = _parse_json(raw)
    result.agent_trace.append({"agent": "synthesis", "status": "complete"})

    # 生成最终审稿包
    result.final_packet = _format_packet(result)
    return result


def _format_packet(r: ReviewResult) -> str:
    synth = r.synthesis or {}
    intake = r.intake or {}
    methods = r.methods or {}
    lit = r.literature or {}

    claims_md = "\n".join(
        f"  {i+1}. [{c.get('type', '?')}] {c.get('text', '?')}" for i, c in enumerate(intake.get("claims", []))
    ) or "（未提取）"

    risks_md = "\n".join(
        f"  - **{risk.get('claim', '?')[:60]}**: {risk.get('risk', '?').upper()} — {risk.get('reason', '?')}"
        for risk in methods.get("claim_risks", [])
    ) or "（未分析）"

    gaps_md = "\n".join(f"  - {g}" for g in lit.get("literature_gaps", [])) or "（未发现明显缺口）"

    return f"""# EconRefereeOS 审稿报告

## 论文信息
- **标题**: {r.paper_title}
- **子领域**: {intake.get('subfield', '未知')}
- **审稿时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## 总体评价
{synth.get('overall_assessment', '（未生成）')}

---

## 一、核心主张 (Intake Agent)
{claims_md}

**证据来源**: {intake.get('evidence_sources', '未说明')}

## 二、方法论评估 (Methods Agent)
**总体风险**: {methods.get('overall_methods_risk', '未评估')}

{risks_md}

## 三、文献评估 (Literature Agent)
**贡献评估**: {lit.get('contribution_assessment', '未评估')}
**过度宣称风险**: {lit.get('overclaim_risk', '未评估')}

**文献缺口**:
{gaps_md}

## 四、编辑建议 (Synthesis Agent)
**决定**: {synth.get('recommendation', '未给出')}

**优点**:
{chr(10).join(f'  - {s}' for s in synth.get('strengths', [])) or '  （未列出）'}

**问题**:
{chr(10).join(f'  - {w}' for w in synth.get('weaknesses', [])) or '  （未列出）'}

**推荐审稿人专长**: {', '.join(synth.get('recommended_expertise', [])) or '未指定'}

---

> EconRefereeOS 辅助人类审稿，不做最终录用/退稿决定。
"""


# ─── 内置示例论文 ────────────────────────────────────────────────────

SAMPLE_PAPER = """\
标题：最低工资对就业的影响——基于中国县级面板数据的再检验

摘要：本文利用中国 2010-2020 年县级面板数据，采用双重差分法（DID）评估最低工资上调对制造业就业的影响。
研究发现最低工资每上调 10%，制造业就业下降约 1.2%，但该效应在东部沿海地区不显著。
本文的贡献在于首次使用中国县级层面数据检验了最低工资的就业效应，填补了发展中国家证据的空白。

数据：2010-2020 年中国县级面板数据（N=2850 个县 × 11 年 = 31,350 观测值）
方法：双向固定效应 DID + 事件研究法
稳健性：替换最低工资变量（用省级数据替代县级）、排除直辖市样本、安慰剂检验（虚构政策时间）

主要发现：
1. 最低工资上调 10% → 制造业就业下降 1.2%（全国平均）
2. 东部沿海地区效应不显著（p > 0.1），可能因为当地工资水平已远高于最低工资
3. 中西部地区效应更大（-2.1%，p < 0.01）
4. 小型企业受影响程度是大型企业的 2.3 倍
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="EconRefereeOS — 经济学论文审稿多智能体系统")
    parser.add_argument("--paper", type=str, help="论文文件路径 (markdown/txt)")
    parser.add_argument("--title", type=str, default="", help="论文标题（不提供则从文件中提取）")
    parser.add_argument("--output", type=str, help="输出审稿报告路径")
    args = parser.parse_args()

    if args.paper:
        with open(args.paper) as f:
            paper_text = f.read()
        title = args.title or args.paper.replace(".md", "").replace(".txt", "").rsplit("/", 1)[-1]
    else:
        paper_text = SAMPLE_PAPER
        title = "最低工资对就业的影响——基于中国县级面板数据的再检验"

    print("=" * 60)
    print("  EconRefereeOS · 经济学论文审稿系统")
    print("  4 Agent 流水线: Intake → Methods → Literature → Synthesis")
    print(f"  论文: {title}")
    print("=" * 60)

    review = run_review(paper_text, title)

    print("\n" + "=" * 60)
    if args.output:
        with open(args.output, "w") as f:
            f.write(review.final_packet)
        print(f"审稿报告已保存: {args.output}")
    else:
        print(review.final_packet)

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Due Diligence Agent System
==========================
AG2 + TinyFish multi-threaded due diligence pipeline.

Architecture:
  1. Coordinator agent receives a company URL
  2. Spawns 6 specialist agents in parallel threads
  3. Each specialist calls tinyfish as a tool to deep-scrape relevant sources
  4. Validator agent checks for gaps and contradictions
  5. Synthesis agent produces the final report

Usage:
  export OPENAI_API_KEY=...
  export TINYFISH_API_KEY=...
  python due_diligence.py --url https://example.com
  python due_diligence.py --report-path ./due_diligence_acme_20260311_120000/
"""

import argparse
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from autogen import AssistantAgent, LLMConfig, UserProxyAgent, register_function
from autogen.tools.experimental import TinyFishTool

from prompts import (
    FINANCIALS,
    FINANCIALS_MSG,
    FOUNDERS_TEAM,
    FOUNDERS_TEAM_MSG,
    INVESTORS,
    INVESTORS_MSG,
    PRESS,
    PRESS_MSG,
    QA_ANALYST,
    SEED_CRAWLER,
    SEED_CRAWLER_MSG,
    SOCIAL,
    SOCIAL_MSG,
    SYNTHESIS,
    TECH_STACK,
    TECH_STACK_MSG,
    VALIDATOR,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LLM_CONFIG = LLMConfig(
    {
        "model": "gpt-4o",
        "api_key": os.environ.get("OPENAI_API_KEY"),
        "temperature": 0.1,
    }
)

tinyfish_tool = TinyFishTool()

# ---------------------------------------------------------------------------
# Shared results store (thread-safe)
# ---------------------------------------------------------------------------

SPECIALIST_KEYS = [
    "founders_team",
    "investors",
    "press",
    "financials",
    "tech_stack",
    "social",
]


@dataclass
class DueDiligenceResults:
    seed: dict[str, Any] = field(default_factory=dict)
    founders_team: dict[str, Any] = field(default_factory=dict)
    investors: dict[str, Any] = field(default_factory=dict)
    press: dict[str, Any] = field(default_factory=dict)
    financials: dict[str, Any] = field(default_factory=dict)
    tech_stack: dict[str, Any] = field(default_factory=dict)
    social: dict[str, Any] = field(default_factory=dict)
    validation_notes: list[str] = field(default_factory=list)
    final_report: str = ""
    output_dir: str = ""


results = DueDiligenceResults()
results_lock = threading.Lock()
references_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _save_agent_output(
    output_dir: str,
    files: list[tuple[str, Any, str]],
    section_title: str,
) -> None:
    """Save agent output files and append entries to references.md."""
    ref_lines = [f"\n### {section_title}\n"]
    for rel_path, data, description in files:
        full_path = Path(output_dir) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (dict, list)):
            full_path.write_text(json.dumps(data, indent=2))
        else:
            full_path.write_text(str(data))
        ref_lines.append(f"- [{rel_path}]({rel_path}) — {description}\n")

    with references_lock:
        with open(Path(output_dir) / "references.md", "a") as f:
            f.writelines(ref_lines)


def _init_output_dir(company_name: str) -> str:
    """Create a timestamped output directory and initialise references.md."""
    slug = re.sub(r"[^a-z0-9]+", "_", company_name.lower()).strip("_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dirname = f"due_diligence_{slug}_{ts}"
    os.makedirs(dirname, exist_ok=True)

    header = (
        f"# Due Diligence Report — {company_name}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"## References\n"
    )
    with open(Path(dirname) / "references.md", "w") as f:
        f.write(header)
    return dirname


def _extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from a string."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def make_agent_pair(name: str, system_message: str):
    """
    Returns an (AssistantAgent, UserProxyAgent) pair with tinyfish registered.
    """
    assistant = AssistantAgent(
        name=name,
        system_message=system_message,
        llm_config=LLM_CONFIG,
    )

    proxy = UserProxyAgent(
        name=f"{name}_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda msg: (
            "TASK_COMPLETE" in (msg.get("content") or "") if msg else False
        ),
        code_execution_config=False,
    )

    tinyfish_tool.register_for_llm(assistant)
    tinyfish_tool.register_for_execution(proxy)
    return assistant, proxy


def _run_agent_chat(name: str, system_message: str, message: str) -> dict:
    """Run a single agent conversation and return extracted JSON."""
    assistant, proxy = make_agent_pair(name, system_message)
    proxy.initiate_chat(assistant, message=message)
    last_msg = proxy.last_message(assistant)["content"]
    return _extract_json(last_msg) or {"raw": last_msg}


# ---------------------------------------------------------------------------
# Stage 1: Seed Crawler
# ---------------------------------------------------------------------------


def run_seed_crawler(company_url: str, output_dir: str) -> dict:
    """Crawl the company's own website to build initial CompanyProfile."""
    print("\n" + "=" * 60)
    print("STAGE 1: Seed Crawler")
    print("=" * 60)

    profile = _run_agent_chat(
        "SeedCrawler",
        SEED_CRAWLER,
        SEED_CRAWLER_MSG.format(url=company_url),
    )

    profile["seed_url"] = company_url
    with results_lock:
        results.seed = profile

    _save_agent_output(
        output_dir,
        [
            (
                "company_profile.json",
                profile,
                "Company name, description, founding year, HQ, discovered links",
            )
        ],
        "Seed Crawl",
    )

    print(
        f"\n✅ Seed crawl complete. Company: {profile.get('company_name', 'Unknown')}"
    )
    return profile


# ---------------------------------------------------------------------------
# Stage 2: Specialist Agents (run in parallel threads)
# ---------------------------------------------------------------------------

# Each specialist is defined as a dict with:
#   name          - AG2 agent name
#   result_key    - attribute on DueDiligenceResults
#   system_msg    - system prompt (from prompts.py)
#   build_message - callable(profile, output_dir) -> str
#   build_output  - callable(data) -> list of (path, data, description) tuples
#   section_title - heading in references.md

SPECIALISTS = [
    {
        "name": "FoundersTeamAgent",
        "result_key": "founders_team",
        "system_msg": FOUNDERS_TEAM,
        "build_message": lambda p, _: FOUNDERS_TEAM_MSG.format(
            company_name=p["company_name"],
            seed_url=p["seed_url"],
            team_urls=", ".join(p.get("team_page_urls") or []) or "none found",
        ),
        "build_output": lambda data: (
            [
                (
                    "founders_team/founders.json",
                    data.get("founders", []),
                    "Founder backgrounds and LinkedIn profiles",
                ),
                (
                    "founders_team/executives.json",
                    data.get("executives", []),
                    "Executive team members and roles",
                ),
            ]
            + (
                [
                    (
                        "founders_team/headcount.json",
                        {"total_headcount_estimate": data["total_headcount_estimate"]},
                        "Estimated employee headcount",
                    )
                ]
                if data.get("total_headcount_estimate") is not None
                else []
            )
            if data.get("founders") or data.get("executives")
            else [("founders_team.json", data, "Founders, executives, and team data")]
        ),
        "section_title": "Founders & Team",
    },
    {
        "name": "InvestorAgent",
        "result_key": "investors",
        "system_msg": INVESTORS,
        "build_message": lambda p, _: INVESTORS_MSG.format(
            company_name=p["company_name"],
            seed_url=p["seed_url"],
        ),
        "build_output": lambda data: [
            (
                "investors.json",
                data,
                "Funding rounds, investors, amounts, and valuation",
            ),
        ],
        "section_title": "Investors & Funding",
    },
    {
        "name": "PressAgent",
        "result_key": "press",
        "system_msg": PRESS,
        "build_message": lambda p, _: PRESS_MSG.format(
            company_name=p["company_name"],
            press_urls=", ".join(p.get("press_page_urls") or []) or "none found",
        ),
        "build_output": lambda data: (
            [
                (
                    "press/articles.json",
                    data["articles"],
                    "Press articles with summaries and sentiment",
                ),
                (
                    "press/sentiment.json",
                    {
                        "overall_sentiment": data["overall_sentiment"],
                        "notable_mentions": data.get("notable_mentions", []),
                    },
                    "Aggregated press sentiment analysis",
                ),
            ]
            if data.get("articles") and data.get("overall_sentiment")
            else [("press.json", data, "Press coverage and media mentions")]
        ),
        "section_title": "Press Coverage",
    },
    {
        "name": "FinancialsAgent",
        "result_key": "financials",
        "system_msg": FINANCIALS,
        "build_message": lambda p, _: FINANCIALS_MSG.format(
            company_name=p["company_name"],
            seed_url=p["seed_url"],
        ),
        "build_output": lambda data: [
            (
                "financials.json",
                data,
                "Financial data, revenue, market cap, and key metrics",
            ),
        ],
        "section_title": "Financials",
    },
    {
        "name": "TechStackAgent",
        "result_key": "tech_stack",
        "system_msg": TECH_STACK,
        "build_message": lambda p, _: TECH_STACK_MSG.format(
            company_name=p["company_name"],
            domain=p["seed_url"]
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0],
            job_urls=", ".join((p.get("job_urls") or [])[:2]) or "none found",
        ),
        "build_output": lambda data: [
            (
                "tech_stack.json",
                data,
                "Technology stack: frontend, backend, infrastructure, and tools",
            ),
        ],
        "section_title": "Technology Stack",
    },
    {
        "name": "SocialAgent",
        "result_key": "social",
        "system_msg": SOCIAL,
        "build_message": lambda p, _: SOCIAL_MSG.format(
            company_name=p["company_name"],
            seed_url=p["seed_url"],
        ),
        "build_output": lambda data: [
            (
                "social.json",
                data,
                "Social media presence: LinkedIn, Twitter/X, GitHub activity",
            ),
        ],
        "section_title": "Social Signals",
    },
]


def _run_specialist(spec: dict, profile: dict, output_dir: str) -> dict:
    """Run a single specialist agent: chat, store results, save files."""
    label = spec["section_title"]
    print(f"\n  🔍 [{label}] Starting...")

    message = spec["build_message"](profile, output_dir)
    data = _run_agent_chat(spec["name"], spec["system_msg"], message)

    with results_lock:
        setattr(results, spec["result_key"], data)

    output_files = spec["build_output"](data)
    _save_agent_output(output_dir, output_files, label)

    print(f"  ✅ [{label}] Complete")
    return data


# ---------------------------------------------------------------------------
# Stage 3: Validator Agent
# ---------------------------------------------------------------------------


def run_validator(company_name: str, output_dir: str) -> list[str]:
    print("\n" + "=" * 60)
    print("STAGE 3: Validator")
    print("=" * 60)

    summary = json.dumps(
        {
            "company": company_name,
            **{key: getattr(results, key) for key in SPECIALIST_KEYS},
        },
        indent=2,
    )

    data = _run_agent_chat(
        "ValidatorAgent",
        VALIDATOR,
        f"Validate this due diligence data and flag issues:\n\n{summary}",
    )

    notes = [
        *data.get("contradictions", []),
        *data.get("missing_critical", []),
        data.get("gaps_summary", ""),
    ]
    with results_lock:
        results.validation_notes = notes

    _save_agent_output(
        output_dir,
        [
            (
                "validation_notes.json",
                data,
                "Data quality checks: contradictions, gaps, confidence",
            )
        ],
        "Validation",
    )

    print(
        f"  ✅ Validation complete. Confidence: {data.get('overall_confidence', 'unknown')}"
    )
    return notes


# ---------------------------------------------------------------------------
# Stage 4: Synthesis Agent
# ---------------------------------------------------------------------------


def run_synthesis(company_name: str, output_dir: str) -> str:
    print("\n" + "=" * 60)
    print("STAGE 4: Synthesis")
    print("=" * 60)

    assistant = AssistantAgent(
        name="SynthesisAgent",
        system_message=SYNTHESIS,
        llm_config=LLM_CONFIG,
    )

    proxy = UserProxyAgent(
        name="synthesis_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        is_termination_msg=lambda msg: "TASK_COMPLETE" in msg.get("content", ""),
        code_execution_config=False,
    )

    all_data = {
        "company_name": company_name,
        "seed": results.seed,
        **{key: getattr(results, key) for key in SPECIALIST_KEYS},
        "validation_notes": results.validation_notes,
    }

    proxy.initiate_chat(
        assistant,
        message=f"Write a due diligence report from this data:\n\n{json.dumps(all_data, indent=2)}",
    )

    report = (
        proxy.last_message(assistant)["content"].replace("TASK_COMPLETE", "").strip()
    )
    with results_lock:
        results.final_report = report

    _save_agent_output(
        output_dir,
        [("report.md", report, "Synthesized due diligence report")],
        "Final Report",
    )

    return report


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_due_diligence(company_url: str) -> str:
    """Run the full due diligence pipeline. Returns the output directory path."""
    print(
        f"""
╔══════════════════════════════════════════════════════════╗
║          DUE DILIGENCE AGENT SYSTEM                      ║
║          Powered by AG2 + TinyFish                       ║
╚══════════════════════════════════════════════════════════╝
Target: {company_url}
Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    )

    # Stage 1 — Seed crawl (must happen first, provides context to specialists)
    temp_dir = _init_output_dir("unknown")
    profile = run_seed_crawler(company_url, temp_dir)

    company_name = profile.get("company_name", "Unknown Company")

    # Rename the output dir now that we know the company name
    slug = re.sub(r"[^a-z0-9]+", "_", company_name.lower()).strip("_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"due_diligence_{slug}_{ts}"
    Path(temp_dir).rename(output_dir)

    refs_path = Path(output_dir) / "references.md"
    refs_path.write_text(
        refs_path.read_text().replace(
            "Due Diligence Report — unknown",
            f"Due Diligence Report — {company_name}",
        )
    )

    with results_lock:
        results.output_dir = output_dir

    # Stage 2 — Run all specialist agents in parallel threads
    print("\n" + "=" * 60)
    print(f"STAGE 2: Parallel Specialist Agents ({len(SPECIALISTS)} threads)")
    print("=" * 60)

    with ThreadPoolExecutor(max_workers=len(SPECIALISTS)) as executor:
        futures = {
            executor.submit(_run_specialist, spec, profile, output_dir): spec
            for spec in SPECIALISTS
        }
        for future in as_completed(futures):
            spec = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"  ❌ [{spec['section_title']}] Failed: {e}")
                with results_lock:
                    setattr(results, spec["result_key"], {"error": str(e)})

    # Stage 3 — Validate
    run_validator(company_name, output_dir)

    # Stage 4 — Synthesize
    report = run_synthesis(company_name, output_dir)

    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(report)

    print(f"\n📄 Report and data saved to: {output_dir}/")

    return output_dir


# ---------------------------------------------------------------------------
# Interactive Q&A
# ---------------------------------------------------------------------------


def run_qa_session(output_dir: str) -> None:
    """Interactive Q&A over an existing due diligence report folder."""
    output_path = Path(output_dir)
    refs_path = output_path / "references.md"
    if not refs_path.exists():
        print(f"Error: {refs_path} not found. Is this a valid report directory?")
        return

    # Build a file listing so the agent knows what's available
    available_files: list[str] = []
    for fpath in sorted(output_path.rglob("*")):
        if fpath.is_file() and fpath.suffix in (".json", ".md"):
            available_files.append(str(fpath.relative_to(output_path)))

    file_listing = "\n".join(f"  - {f}" for f in available_files)

    def read_report_file(filename: str) -> str:
        """Read a file from the due diligence report directory. Pass the relative path (e.g. 'investors.json')."""
        target = output_path / filename
        if not target.is_file():
            return (
                f"File not found: {filename}. Available: {', '.join(available_files)}"
            )
        try:
            return target.read_text()
        except OSError as e:
            return f"Error reading {filename}: {e}"

    assistant = AssistantAgent(
        name="QA_Analyst",
        system_message=QA_ANALYST.format(file_listing=file_listing),
        llm_config=LLM_CONFIG,
    )

    def is_termination_msg(msg: dict) -> bool:
        content = msg.get("content", "")

        if not content:
            return False

        return content.endswith("<END>")

    proxy = UserProxyAgent(
        name="qa_user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=is_termination_msg,
        code_execution_config=False,
    )

    register_function(
        read_report_file,
        caller=assistant,
        executor=proxy,
        name="read_report_file",
        description="Read a file from the due diligence report. Pass the relative path shown in the file listing.",
    )

    print("\n" + "=" * 60)
    print("INTERACTIVE Q&A")
    print('Type your questions below. Type "exit" or "quit" to stop.')
    print("=" * 60)

    while True:
        try:
            question = input("\nQ: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Q&A.")
            break
        if not question or question.lower() in ("exit", "quit"):
            print("Exiting Q&A.")
            break

        proxy.initiate_chat(assistant, message=question, clear_history=False)
        answer = assistant.last_message(proxy)["content"]
        print(f"\nA: {answer}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run due diligence on a company.")
    parser.add_argument("--url", help="Company website URL (runs the full pipeline)")
    parser.add_argument(
        "--report-path",
        help="Path to an existing report folder (skips pipeline, enters Q&A directly)",
    )
    args = parser.parse_args()

    if args.report_path:
        if not Path(args.report_path).is_dir():
            parser.error(f"Report directory not found: {args.report_path}")
        run_qa_session(args.report_path)
    elif args.url:
        output_dir = run_due_diligence(args.url)
        run_qa_session(output_dir)
    else:
        parser.error("Either --url or --report-path is required.")

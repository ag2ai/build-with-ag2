"""
Terminal mode: run GPT Researcher from the command line.

Install dependencies and run:
    pip install -r requirements.txt
    python main.py
"""
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from gpt_researcher import GPTResearcher

load_dotenv()


def load_task() -> dict:
    return json.loads(Path("task.json").read_text())


async def main() -> None:
    task = load_task()
    query = task["query"]
    report_type = task.get("report_type", "research_report")

    print(f"\nResearching: {query}\n")

    researcher = GPTResearcher(query=query, report_type=report_type)
    await researcher.conduct_research()
    report = await researcher.write_report()

    print("\n--- Research Complete ---\n")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())

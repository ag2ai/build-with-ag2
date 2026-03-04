"""
Terminal mode: run the GPT Researcher multi-agent pipeline from the command line.

Prerequisites:
    This sample depends on the multi_agents_ag2 module from the GPT Researcher repo.
    Clone it and run from the gpt-researcher root, or add the path to PYTHONPATH:

        git clone https://github.com/assafelovic/gpt-researcher.git
        cd gpt-researcher
        pip install -r requirements.txt
        pip install -r multi_agents_ag2/requirements.txt
        pip install -r /path/to/this/sample/requirements.txt

    Then copy (or symlink) this sample's files into the gpt-researcher folder and run:
        python -m main
"""
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def load_task() -> dict:
    return json.loads(Path("task.json").read_text())


async def main() -> None:
    # Import here so the module is resolved from PYTHONPATH at runtime
    from multi_agents_ag2.agents.orchestrator import ChiefEditorAgent

    task = load_task()
    print(f"\nResearching: {task['query']}\n")

    chief_editor = ChiefEditorAgent(task)
    result = await chief_editor.run_research_task()

    report = result.get("report", "")
    print("\n--- Research Complete ---\n")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())

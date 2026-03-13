import argparse
from pathlib import Path

import arxiv
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("ArxivServer")

# Use a shared Client with reduced page_size and num_retries to avoid rate-limit hangs
_arxiv_client = arxiv.Client(page_size=5, delay_seconds=1.0, num_retries=1)

parser = argparse.ArgumentParser(description="arXiv MCP Server")
parser.add_argument(
    "--storage-path", required=True, help="Path to store downloaded papers"
)
args, unknown = parser.parse_known_args()

STORAGE_PATH = Path(args.storage_path).resolve()
STORAGE_PATH.mkdir(parents=True, exist_ok=True)


@mcp.tool()
def search_arxiv(query: str, max_results: int = 3) -> list[str]:
    """Search arXiv and return IDs of top papers."""
    search = arxiv.Search(query=query, max_results=max_results)
    return [result.entry_id.split("/")[-1] for result in _arxiv_client.results(search)]


@mcp.tool()
def download_paper(arxiv_id: str) -> str:
    """Download paper from arXiv and store it."""
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(_arxiv_client.results(search), None)
    if paper:
        file_path = STORAGE_PATH / f"{arxiv_id}.pdf"
        paper.download_pdf(dirpath=STORAGE_PATH, filename=file_path.name)
        return f"Downloaded {arxiv_id} to {file_path.name}"
    else:
        return f"Paper {arxiv_id} not found"


@mcp.tool()
def list_papers() -> list[str]:
    """List downloaded papers."""
    return [f.name for f in STORAGE_PATH.glob("*.pdf")]


@mcp.tool()
def get_paper_info(arxiv_id: str) -> dict[str, str]:
    """Extract and return title and abstract of a paper from arXiv."""
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(_arxiv_client.results(search), None)
    if paper:
        return {"title": paper.title, "abstract": paper.summary}
    else:
        return {"error": f"Paper {arxiv_id} not found"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="arXiv MCP Server")
    parser.add_argument(
        "transport", choices=["stdio", "sse", "streamable-http"], help="Transport mode"
    )
    parser.add_argument("--storage-path", required=True, help="Path to store papers")
    args = parser.parse_args()

    mcp.run(transport=args.transport)

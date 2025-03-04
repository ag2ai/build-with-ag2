import asyncio
from dataclasses import dataclass
from typing import Callable, Awaitable, Any, List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Review:
    review_summary: str = ""

    initial_review: str = "" # no web search, quick go through and decide to discard or not

    full_review: str = "" # always do this after initial review

    # optional?
    deep_verify_review: str = ""
    observe_review: str = ""
    simulation_review: str = ""


@dataclass
class Hypothesis:
    hid: str = "" # unique id
    rating: float =  1200.0 # ELO rating

    selected_articles: List[Dict] = field(default_factory=list) # {"name": "article_name", "review": "literature_review", "link": "article_link"}
    original_hypothesis: str = "" # A detailed version of the hypothesis # after literature review
    review: Review = field(default_factory=Review) # review of the hypothesis

    # after finalized_hypothesis is filled, this hypothesis should be marked as archived
    debate_logs : List[str] = field(default_factory=list) # logs of the debate
    finalized_hypothesis: str = "" # after simulated scientific debate

    # lock per hypothesis
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    hypo_version: int = 0 # version of the hypothesis
    review_version: int = 0 # version of the hypothesis

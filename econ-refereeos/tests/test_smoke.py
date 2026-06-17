"""EconRefereeOS 烟雾测试。验证模块可导入，Agent 可创建。不实际调用 LLM。"""

import importlib
import pytest


def test_orchestrator_imports() -> None:
    """核心函数可导入。"""
    from src.orchestrator import run_review, ReviewResult, SAMPLE_PAPER
    assert callable(run_review)
    assert len(SAMPLE_PAPER) > 200


def test_review_result_dataclass() -> None:
    """ReviewResult 数据类可实例化。"""
    from src.orchestrator import ReviewResult
    r = ReviewResult(paper_title="test")
    assert r.paper_title == "test"
    assert r.intake is None
    assert r.agent_trace == []

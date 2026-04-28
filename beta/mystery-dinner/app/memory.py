import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InterrogationTurn:
    suspect: str
    question: str
    answer: str
    timestamp: float
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class VerifiedFact:
    suspect: str
    data_source: str
    query: dict
    result: Any
    timestamp: float

    def describe(self) -> str:
        window = ""
        if isinstance(self.query, dict):
            s = self.query.get("start_time")
            e = self.query.get("end_time")
            if s or e:
                window = f" [{s or '?'}–{e or '?'}]"
        return f"{self.suspect} · {self.data_source}{window}"


@dataclass
class CaseMemory:
    interrogation_log: list[InterrogationTurn] = field(default_factory=list)
    verified_facts: list[VerifiedFact] = field(default_factory=list)

    # Change listeners for the notebook SSE route
    _listeners: list[Any] = field(default_factory=list, repr=False)

    def add_turn(self, turn: InterrogationTurn) -> None:
        self.interrogation_log.append(turn)
        self._notify("turn", turn)

    def add_fact(self, fact: VerifiedFact) -> None:
        self.verified_facts.append(fact)
        self._notify("fact", fact)

    def reset(self) -> None:
        self.interrogation_log.clear()
        self.verified_facts.clear()
        self._notify("snapshot", {"turns": [], "facts": []})

    def subscribe(self, cb) -> None:
        self._listeners.append(cb)

    def unsubscribe(self, cb) -> None:
        try:
            self._listeners.remove(cb)
        except ValueError:
            pass

    def _notify(self, kind: str, payload: Any) -> None:
        data = _to_plain(payload)
        for cb in list(self._listeners):
            try:
                cb(kind, data)
            except Exception:
                pass


def _to_plain(obj: Any) -> Any:
    if isinstance(obj, InterrogationTurn):
        return {
            "suspect": obj.suspect,
            "question": obj.question,
            "answer": obj.answer,
            "timestamp": obj.timestamp,
            "tool_calls": obj.tool_calls,
        }
    if isinstance(obj, VerifiedFact):
        return {
            "suspect": obj.suspect,
            "data_source": obj.data_source,
            "query": obj.query,
            "result": obj.result,
            "timestamp": obj.timestamp,
            "label": obj.describe(),
        }
    return obj


# Module-level single-session memory (Slice 2 is single-user)
CASE_MEMORY = CaseMemory()


def now() -> float:
    return time.time()


def parse_json_args(s: str) -> dict:
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}

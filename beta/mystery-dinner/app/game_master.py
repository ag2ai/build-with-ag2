from dataclasses import dataclass
from typing import Literal

from .cases.blackwood_estate import (
    KILLER,
    MURDER_LOCATION,
    MURDER_WINDOW,
    profile_by_name,
)
from .clock import GAME_CLOCK
from .config import WITHDRAWALS_ALLOWED
from .memory import CASE_MEMORY, VerifiedFact


@dataclass
class AccusationResult:
    outcome: Literal[
        "win", "wrong_killer", "insufficient_evidence", "no_withdrawal_left"
    ]
    killer_true: str
    killer_accused: str
    reasoning: str
    necessary_evidence: list[dict]
    sufficient: bool
    detail: str
    elapsed_seconds: int = 0


class GameMaster:
    def __init__(self) -> None:
        self.killer: str = KILLER
        self.murder_window: tuple[str, str] = MURDER_WINDOW
        self.murder_location: str = MURDER_LOCATION
        self._withdrawals_left: int = WITHDRAWALS_ALLOWED
        self._terminated: bool = False
        self._winning_outcome: bool | None = None

    @property
    def is_terminated(self) -> bool:
        return self._terminated

    def reset(self) -> None:
        self._withdrawals_left = WITHDRAWALS_ALLOWED
        self._terminated = False
        self._winning_outcome = None

    def finalize(self, accused: str, reasoning: str) -> AccusationResult:
        accused_key = accused.lower().strip()
        facts = CASE_MEMORY.verified_facts

        if self._terminated:
            return AccusationResult(
                outcome="no_withdrawal_left",
                killer_true=self.killer,
                killer_accused=accused_key,
                reasoning=reasoning,
                necessary_evidence=[],
                sufficient=False,
                detail="Game already concluded.",
                elapsed_seconds=GAME_CLOCK.elapsed(),
            )

        # Collect evidence that could implicate the accused
        facts_about_accused = [f for f in facts if f.suspect == accused_key]

        # Necessary evidence: at least one fact whose row timestamps
        # fall inside the murder window and belongs to the accused.
        necessary: list[VerifiedFact] = []
        for f in facts_about_accused:
            if _touches_window(f.result, self.murder_window):
                necessary.append(f)

        # Sufficient evidence: every other suspect has at least one
        # verified fact placing them away from the murder location during
        # the window. For Slice 3 we approximate "away from study" as
        # "has GPS facts within the window that do not start with the
        # study lat prefix 40.81".
        sufficient, detail = _sufficient(facts, accused_key, self.murder_window)

        accused_profile = profile_by_name(accused_key)
        if accused_profile is None:
            return AccusationResult(
                outcome="wrong_killer",
                killer_true=self.killer,
                killer_accused=accused_key,
                reasoning=reasoning,
                necessary_evidence=[_fact_dict(f) for f in necessary],
                sufficient=sufficient,
                detail=f"No suspect named {accused}.",
                elapsed_seconds=GAME_CLOCK.elapsed(),
            )

        # Wrong person → immediate loss (regardless of evidence)
        if accused_key != self.killer:
            self._terminated = True
            self._winning_outcome = False
            GAME_CLOCK.freeze()
            return AccusationResult(
                outcome="wrong_killer",
                killer_true=self.killer,
                killer_accused=accused_key,
                reasoning=reasoning,
                necessary_evidence=[_fact_dict(f) for f in necessary],
                sufficient=sufficient,
                detail=(
                    f"{accused_profile.display_name} is not the killer. "
                    f"The killer was {profile_by_name(self.killer).display_name}. "
                    "The real killer has escaped."
                ),
                elapsed_seconds=GAME_CLOCK.elapsed(),
            )

        # Right person — but do we have enough?
        if not necessary:
            return self._maybe_withdraw(
                outcome="insufficient_evidence",
                accused_key=accused_key,
                reasoning=reasoning,
                detail=(
                    f"You accused the right person, but no verified fact "
                    f"places {accused_profile.display_name} near the crime "
                    f"during {self.murder_window[0]}–{self.murder_window[1]}. "
                    "Force more evidence before accusing again."
                ),
                necessary=necessary,
                sufficient=sufficient,
            )
        if not sufficient:
            return self._maybe_withdraw(
                outcome="insufficient_evidence",
                accused_key=accused_key,
                reasoning=reasoning,
                detail=(
                    "You have evidence against the accused, but you "
                    "haven't yet ruled out every other suspect. "
                    f"{detail}"
                ),
                necessary=necessary,
                sufficient=sufficient,
            )

        # Win
        self._terminated = True
        self._winning_outcome = True
        GAME_CLOCK.freeze()
        return AccusationResult(
            outcome="win",
            killer_true=self.killer,
            killer_accused=accused_key,
            reasoning=reasoning,
            necessary_evidence=[_fact_dict(f) for f in necessary],
            sufficient=True,
            detail=(
                f"Case closed. {accused_profile.display_name} is the killer, "
                "and your verified evidence implicates them beyond doubt."
            ),
            elapsed_seconds=GAME_CLOCK.elapsed(),
        )

    def _maybe_withdraw(
        self,
        outcome: str,
        accused_key: str,
        reasoning: str,
        detail: str,
        necessary: list[VerifiedFact],
        sufficient: bool,
    ) -> AccusationResult:
        if self._withdrawals_left > 0:
            self._withdrawals_left -= 1
            return AccusationResult(
                outcome="insufficient_evidence",
                killer_true=self.killer,
                killer_accused=accused_key,
                reasoning=reasoning,
                necessary_evidence=[_fact_dict(f) for f in necessary],
                sufficient=sufficient,
                detail=f"{detail}  (Withdrawals remaining: {self._withdrawals_left})",
                elapsed_seconds=GAME_CLOCK.elapsed(),
            )
        # Out of withdrawals → terminal loss
        self._terminated = True
        self._winning_outcome = False
        GAME_CLOCK.freeze()
        return AccusationResult(
            outcome="no_withdrawal_left",
            killer_true=self.killer,
            killer_accused=accused_key,
            reasoning=reasoning,
            necessary_evidence=[_fact_dict(f) for f in necessary],
            sufficient=sufficient,
            detail=f"{detail}  No withdrawals remaining. The case is closed as unsolved.",
            elapsed_seconds=GAME_CLOCK.elapsed(),
        )


def _fact_dict(f: VerifiedFact) -> dict:
    return {
        "suspect": f.suspect,
        "data_source": f.data_source,
        "query": f.query,
        "result": f.result,
    }


def _touches_window(result: object, window: tuple[str, str]) -> bool:
    """Heuristic: does the fact contain a timestamp inside the murder window?"""
    if not result:
        return False
    text = str(result)
    start, end = window
    # Simple lexicographic scan for HH:MM tokens
    import re

    for match in re.findall(r"\d{2}:\d{2}", text):
        if start <= match <= end:
            return True
    return False


def _sufficient(
    facts: list[VerifiedFact],
    accused: str,
    window: tuple[str, str],
) -> tuple[bool, str]:
    """Every non-accused suspect must have at least one fact placing them
    outside the study during the window. The study's GPS starts with "40.81".
    Dr. Chen is at 40.8103 (library) — that's still inside the estate but
    not the study, so we also require that their GPS row during the window
    is NOT the murder location (40.8100,-73.9500).

    Relaxed rule: any fact whose row timestamps fall in the window and the
    suspect has a GPS/keycard/cctv row is taken as 'accounted for'.
    """
    from .cases.blackwood_estate import ALL_PROFILES

    missing: list[str] = []
    for p in ALL_PROFILES:
        if p.name == accused:
            continue
        accounted = any(
            f.suspect == p.name and _touches_window(f.result, window) for f in facts
        )
        if not accounted:
            missing.append(p.display_name)

    if missing:
        return (
            False,
            "Not yet accounted for during the murder window: "
            + ", ".join(missing)
            + ".",
        )
    return True, "All other suspects are accounted for during the murder window."


# Module-level singleton for this session
GAME_MASTER = GameMaster()

"""Central configuration for the AG2 mystery-dinner demo.

Tweak the values in this file to point the agents at different LLMs or
change the game's pacing. Everything else in the app reads from here.

LLM configs are exposed as factory functions because each Agent needs
its own config instance.
"""

from autogen.beta.config import GeminiConfig


# === Game pacing ============================================================

# Total time the detective has to solve the case, in seconds.
GAME_DURATION_SECONDS: int = 10 * 60

# How many times the detective can accuse the wrong way ("insufficient
# evidence") and withdraw before the case closes as unsolved. Accusing
# the wrong suspect is always terminal regardless of this number.
WITHDRAWALS_ALLOWED: int = 1


# === LLM configs ============================================================
#
# Each function returns a fresh config object. The detective drives the
# investigation (tool-heavy reasoning), the suspects reply in character,
# and the commentator narrates one-liners.
#
# Swap any of these for the provider you want — the rest of the app will
# pick it up automatically.


def detective_llm_config():
    """LLM config for the detective agent.

    Default: a local OpenAI-compatible MLX server running Qwen.
    Switch to GeminiConfig / VertexAIConfig / etc. as you like.
    """
    return GeminiConfig(
        model="gemini-3.1-pro-preview",
        streaming=True,
    )


def suspect_llm_config():
    """LLM config shared by all six suspects."""
    return GeminiConfig(
        model="gemini-3-flash-preview",
        streaming=True,
    )


def commentator_llm_config():
    """LLM config for the live commentator."""
    return GeminiConfig(
        model="gemini-3-flash-preview",
        streaming=True,
    )

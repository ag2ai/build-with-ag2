from autogen.beta import Agent

from ..cases.blackwood_estate import ELEANOR
from .suspect import build_suspect


def build_eleanor() -> Agent:
    return build_suspect(ELEANOR)

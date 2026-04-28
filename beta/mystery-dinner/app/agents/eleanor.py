from autogen.beta import Actor

from ..cases.blackwood_estate import ELEANOR
from .suspect import build_suspect


def build_eleanor() -> Actor:
    return build_suspect(ELEANOR)

import time

from .config import GAME_DURATION_SECONDS


class GameClock:
    def __init__(self, duration_seconds: int = GAME_DURATION_SECONDS) -> None:
        self.duration = duration_seconds
        self.start_ts = time.time()
        self._expired = False
        self._frozen_remaining: int | None = None

    def remaining(self) -> int:
        if self._frozen_remaining is not None:
            return self._frozen_remaining
        rem = int(self.duration - (time.time() - self.start_ts))
        if rem <= 0:
            self._expired = True
            return 0
        return rem

    def elapsed(self) -> int:
        return max(0, self.duration - self.remaining())

    @property
    def expired(self) -> bool:
        if self._frozen_remaining is not None:
            return False
        return self.remaining() == 0

    @property
    def frozen(self) -> bool:
        return self._frozen_remaining is not None

    def freeze(self) -> None:
        if self._frozen_remaining is None:
            self._frozen_remaining = self.remaining()

    def reset(self, duration_seconds: int | None = None) -> None:
        if duration_seconds is not None:
            self.duration = duration_seconds
        self.start_ts = time.time()
        self._expired = False
        self._frozen_remaining = None


GAME_CLOCK = GameClock()

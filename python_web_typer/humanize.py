"""
Randomised numbers that mimic human variability.

A `Humanized` value is drawn anew at every use, so delays, quotas and counts
never repeat the exact same figure run after run.
"""

import random
from dataclasses import dataclass
from typing import Union

__all__ = ["Humanized", "Number", "draw", "upper_bound"]


@dataclass(frozen=True)
class Humanized:
    """
    A number drawn from a triangular distribution peaking at `mean`, on the
    bracket [2*mean - max, max] clipped to `min`.

    - `max` is a hard cap: never exceeded.
    - The average of the draws is `mean`, as long as the bracket isn't clipped
      by `min` too much (then the average is slightly above `mean`).
    - Integer `mean` and `max` give integer draws.
    """

    mean: float
    max: float
    min: float = 0

    def __post_init__(self):
        if not self.min <= self.mean <= self.max:
            raise ValueError(f"Humanized needs min <= mean <= max, got {self}")

    @property
    def is_integer(self) -> bool:
        return isinstance(self.mean, int) and isinstance(self.max, int)

    def draw(self) -> Union[int, float]:
        low = max(self.min, 2 * self.mean - self.max)
        high = self.max
        # Mode keeping the distribution mean at `mean` ((low + high + mode) / 3)
        mode = min(max(3 * self.mean - low - high, low), high)
        value = random.triangular(low, high, mode)
        if self.is_integer:
            return min(max(int(round(value)), int(low)), int(high))
        return value


Number = Union[int, float, Humanized]


def draw(value: Number) -> Union[int, float]:
    """A fresh random value for a Humanized, plain numbers are returned as is."""
    return value.draw() if isinstance(value, Humanized) else value


def upper_bound(value: Number) -> Union[int, float]:
    """The hard cap of a Humanized, or the plain number itself."""
    return value.max if isinstance(value, Humanized) else value

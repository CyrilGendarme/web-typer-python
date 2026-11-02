"""Parsing of follower counts as displayed by the platforms ("1.2K followers", "1,2 k abonnés"...)."""

import re
from typing import Iterable, Optional

__all__ = ["FOLLOWER_WORDS", "parse_count", "find_follower_count"]

# Lowercase, longest variants first so "followers" wins over "follower"
FOLLOWER_WORDS = (
    "subscribers",
    "subscriber",
    "followers",
    "follower",
    "abonnenten",
    "abonnées",
    "abonnés",
    "abonnee",
    "abonnée",
    "abonné",
    "abonnees",
    "volgers",
    "volger",
    "seguidores",
)

_MULTIPLIERS = {
    "k": 1e3,
    "tsd": 1e3,
    "mil": 1e3,
    "m": 1e6,
    "mio": 1e6,
    "mln": 1e6,
    "b": 1e9,
    "md": 1e9,
    "mrd": 1e9,
}

# Digits with thousands/decimal separators (never newlines: "12\n30" are two numbers)
_NUMBER = r"(?<![\w.,])(\d(?:[\d.,'   ]*\d)?)"
_SUFFIX = r"(?:[   ]*(" + "|".join(sorted(_MULTIPLIERS, key=len, reverse=True)) + r")(?![a-zà-ÿ])\.?)?"


def parse_count(number: str, suffix: Optional[str] = None) -> int:
    """parse_count("1,2", "k") -> 1200, parse_count("12.345") -> 12345"""
    digits = re.sub(r"[\s'  ]", "", number)
    if suffix:
        # With a multiplier the last separator is the decimal one
        parts = re.split(r"[.,]", digits)
        value = float(f"{''.join(parts[:-1])}.{parts[-1]}" if len(parts) > 1 else digits)
        return int(round(value * _MULTIPLIERS[suffix.lower()]))
    return int(re.sub(r"[.,]", "", digits))


def _words_pattern(words: Iterable[str]) -> str:
    return "(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")(?![a-zà-ÿ])"


def find_follower_count(
    text: Optional[str], words: Iterable[str] = FOLLOWER_WORDS
) -> Optional[int]:
    """
    Finds the follower count in a block of page text, in either order:
    "1.2K followers" / "1,2 k abonnés" or "Followers\\n1,234" (SoundCloud).
    """
    if not text:
        return None
    lowered = text.lower()
    words_re = _words_pattern(words)

    number_first = re.search(_NUMBER + _SUFFIX + r"[   ]*" + words_re, lowered)
    if number_first:
        return parse_count(number_first.group(1), number_first.group(2))

    word_first = re.search(words_re + r"\s*:?\s*" + _NUMBER + _SUFFIX, lowered)
    if word_first:
        return parse_count(word_first.group(1), word_first.group(2))

    return None

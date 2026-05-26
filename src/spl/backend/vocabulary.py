"""Loader for the SPL vocabulary.

The word-lists live in plain-text data files under `data/` (one entry per line); this module
only loads them and exposes typed, case-insensitive lookups. The lists were extracted from the
reference grammar (zmbc/shakespearelang's `shakespeare.ebnf`) so they can be diffed against it.

Classification rules: positive and neutral nouns contribute +1, negative nouns -1; any adjective
doubles the magnitude (so adjective polarity is not tracked here). See the backend analyzer for
how these feed constant-value computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

_DATA = Path(__file__).parent / "data"


@dataclass(frozen=True)
class Vocabulary:
    """The loaded word-lists, all stored case-folded for case-insensitive lookup."""

    positive_nouns: frozenset[str]
    neutral_nouns: frozenset[str]
    negative_nouns: frozenset[str]
    adjectives: frozenset[str]
    character_names: frozenset[str]

    def noun_value(self, word: str) -> int | None:
        """+1 for a positive/neutral noun, -1 for a negative noun, None if not a known noun."""
        folded = word.casefold()
        if folded in self.positive_nouns or folded in self.neutral_nouns:
            return 1
        if folded in self.negative_nouns:
            return -1
        return None

    def is_adjective(self, word: str) -> bool:
        return word.casefold() in self.adjectives

    def is_character_name(self, name: str) -> bool:
        return name.casefold() in self.character_names


def _load_set(filename: str) -> frozenset[str]:
    text = (_DATA / filename).read_text(encoding="utf-8")
    return frozenset(line.strip().casefold() for line in text.splitlines() if line.strip())


@cache
def load() -> Vocabulary:
    """Load the vocabulary from the data files (cached for the process lifetime)."""
    return Vocabulary(
        positive_nouns=_load_set("positive_nouns.txt"),
        neutral_nouns=_load_set("neutral_nouns.txt"),
        negative_nouns=_load_set("negative_nouns.txt"),
        adjectives=_load_set("adjectives.txt"),
        character_names=_load_set("character_names.txt"),
    )

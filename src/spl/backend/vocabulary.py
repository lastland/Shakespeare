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
from importlib.resources import files

# Resolve the data directory via importlib.resources rather than `__file__` so the word-lists
# load whether the package is installed as a wheel, run from source, or imported from a zip.
_DATA = files("spl.backend.data")


@dataclass(frozen=True)
class Vocabulary:
    """The loaded word-lists, all stored case-folded for case-insensitive lookup.

    `positive_adjectives` and `negative_adjectives` are disjoint subsets of `adjectives` (the
    reference EBNF's `positive_adjective` / `negative_adjective` lists); the remaining adjectives
    are the neutral ones. Adjective polarity is irrelevant to a constant's value (any adjective
    just doubles the magnitude); it matters only for `more <adjective> than`, whose direction is
    less-than for a negative adjective, greater-than for a positive adjective, and rejected for a
    neutral one (matching the reference, which admits `more` only with a positive/negative
    adjective).
    """

    positive_nouns: frozenset[str]
    neutral_nouns: frozenset[str]
    negative_nouns: frozenset[str]
    adjectives: frozenset[str]
    positive_adjectives: frozenset[str]
    negative_adjectives: frozenset[str]
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

    def is_positive_adjective(self, word: str) -> bool:
        """True for an adjective in the reference's `positive_adjective` list.

        Used to classify `more <adjective> than`: a positive adjective means greater-than. A
        neutral adjective (in `adjectives` but neither positive nor negative) is rejected, matching
        the reference (which admits `more` only with a positive/negative adjective).
        """
        return word.casefold() in self.positive_adjectives

    def is_negative_adjective(self, word: str) -> bool:
        """True for an adjective in the reference's `negative_adjective` list.

        Used to classify `more <adjective> than`: a negative adjective means less-than.
        """
        return word.casefold() in self.negative_adjectives

    def is_character_name(self, name: str) -> bool:
        return name.casefold() in self.character_names


def _load_set(filename: str) -> frozenset[str]:
    text = _DATA.joinpath(filename).read_text(encoding="utf-8")
    return frozenset(line.strip().casefold() for line in text.splitlines() if line.strip())


@cache
def load() -> Vocabulary:
    """Load the vocabulary from the data files (cached for the process lifetime)."""
    return Vocabulary(
        positive_nouns=_load_set("positive_nouns.txt"),
        neutral_nouns=_load_set("neutral_nouns.txt"),
        negative_nouns=_load_set("negative_nouns.txt"),
        adjectives=_load_set("adjectives.txt"),
        positive_adjectives=_load_set("positive_adjectives.txt"),
        negative_adjectives=_load_set("negative_adjectives.txt"),
        character_names=_load_set("character_names.txt"),
    )

"""Tests for the vocabulary loader."""

from __future__ import annotations

from spl.backend.vocabulary import load


def test_lists_are_non_empty() -> None:
    vocab = load()
    assert vocab.positive_nouns
    assert vocab.neutral_nouns
    assert vocab.negative_nouns
    assert vocab.adjectives
    assert vocab.character_names


def test_noun_values() -> None:
    vocab = load()
    assert vocab.noun_value("flower") == 1  # positive
    assert vocab.noun_value("cat") == 1  # neutral
    assert vocab.noun_value("pig") == -1  # negative
    assert vocab.noun_value("florp") is None  # unknown


def test_noun_lookup_is_case_insensitive() -> None:
    vocab = load()
    assert vocab.noun_value("Hell") == -1
    assert vocab.noun_value("hell") == -1


def test_adjectives() -> None:
    vocab = load()
    assert vocab.is_adjective("amazing")
    assert vocab.is_adjective("AMAZING")
    assert not vocab.is_adjective("flower")


def test_negative_adjectives_are_a_subset() -> None:
    vocab = load()
    assert vocab.is_negative_adjective("rotten")  # negative
    assert vocab.is_negative_adjective("ROTTEN")  # case-insensitive
    assert not vocab.is_negative_adjective("cunning")  # positive
    assert not vocab.is_negative_adjective("big")  # neutral
    assert not vocab.is_negative_adjective("flower")  # not an adjective
    # Every negative adjective is also a (general) adjective.
    assert vocab.negative_adjectives <= vocab.adjectives


def test_character_names() -> None:
    vocab = load()
    assert vocab.is_character_name("Romeo")
    assert vocab.is_character_name("juliet")  # case-insensitive
    assert not vocab.is_character_name("Florp")


def test_load_is_cached() -> None:
    assert load() is load()

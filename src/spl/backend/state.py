"""Runtime character + stage model.

Each `Character` is a mutable cell holding the integer it currently represents (plus a stack
for the push/pop ("Remember"/"Recall") phase added later). The `Stage` tracks who is currently
on stage and enforces SPL's defining constraint: a character may only address ONE other, so
addressing is well-defined only when exactly two are present.

Dynamic faults (entering someone already present, exiting someone absent, addressing when not
exactly two are on stage) raise `RuntimeSplError` per ADR-0001.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from spl.errors import RuntimeSplError


@dataclass
class Character:
    """A named value-holder. Mutable: assignment and arithmetic update `value` in place.

    Each Character also owns a LIFO `stack`, manipulated only by Remember (push) and Recall (pop).
    """

    value: int = 0
    stack: list[int] = field(default_factory=list[int])

    def push(self, value: int) -> None:
        """Push `value` onto this character's stack (the Remember operation)."""
        self.stack.append(value)

    def pop(self) -> None:
        """Pop the top of the stack into `value` (the Recall operation).

        Popping an empty stack is a runtime error (ADR-0001; matches the reference's
        "Tried to pop from an empty stack.").
        """
        if not self.stack:
            raise RuntimeSplError("tried to recall from an empty stack")
        self.value = self.stack.pop()


class Stage:
    """The set of characters currently on stage, in entry order.

    At most two characters interact at once; `addressee` enforces this dynamically.
    """

    def __init__(self) -> None:
        # Ordered list (entry order) used as a set; small, so linear scans are fine.
        self._on_stage: list[str] = []

    def enter(self, *names: str) -> None:
        """Bring one or more characters on stage. Raise if any is already present (or repeated)."""
        for name in names:
            if name in self._on_stage:
                raise RuntimeSplError(f"{name} is already on stage")
            self._on_stage.append(name)

    def exit_character(self, name: str) -> None:
        """Remove one character. Raise if they are not on stage."""
        if name not in self._on_stage:
            raise RuntimeSplError(f"{name} is not on stage")
        self._on_stage.remove(name)

    def exeunt(self, *names: str) -> None:
        """Remove the named characters (each must be on stage); with no names, clear the stage."""
        if not names:
            self._on_stage.clear()
            return
        # Validate all before mutating so a bad name leaves the stage unchanged.
        for name in names:
            if name not in self._on_stage:
                raise RuntimeSplError(f"{name} is not on stage")
        for name in names:
            self._on_stage.remove(name)

    def on_stage(self) -> tuple[str, ...]:
        """Current occupants, in the order they entered."""
        return tuple(self._on_stage)

    def addressee(self, speaker: str) -> str:
        """Return the other on-stage character `speaker` addresses.

        Raise if `speaker` is not on stage, or if the number on stage is not exactly two.
        """
        if speaker not in self._on_stage:
            raise RuntimeSplError(f"{speaker} is not on stage and cannot speak")
        if len(self._on_stage) != 2:
            raise RuntimeSplError(
                f"{speaker} has no unique addressee: {len(self._on_stage)} character(s) on stage"
            )
        first, second = self._on_stage
        return second if speaker == first else first

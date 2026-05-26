# Shakespeare Programming Language interpreter

The domain language for an interpreter of the Shakespeare Programming Language (SPL),
an esoteric language whose programs are written as Shakespeare-style plays. This glossary
fixes the vocabulary the codebase uses for SPL's program structure and runtime model.

## Language

**Character**:
A named variable, drawn from a fixed set of Shakespearean character names. Holds a signed
integer *value* (arbitrary precision, initially 0) and — from phase 2 — a LIFO *stack*.
_Avoid_: variable, actor, register

**Value**:
The current signed integer held by a Character. Read and written through dialogue.
_Avoid_: contents, data

**Stage**:
The set of Characters currently "on stage" (in scope for interaction), mutated by Enter/Exit/Exeunt.
At most two Characters may be on stage when they interact; more is a runtime error.
_Avoid_: scope, frame, environment

**Speaker**:
The Character delivering a line of dialogue; referred to in-language as "I", "me", "myself".
_Avoid_: subject, self

**Addressee**:
The other on-stage Character a line is spoken to; referred to as "you", "thee", "thou".
Operations read and write the Addressee's Value unless the line says otherwise.
_Avoid_: target, listener, object

**Act**:
A Roman-numeral-labelled top-level section. Acts and Scenes are the *only* goto targets.
The text after the label is a comment.
_Avoid_: section, block, label (use "Act"/"Scene" specifically)

**Scene**:
A Roman-numeral-labelled subsection within an Act, and a goto target.
_Avoid_: section, block

**Dramatis Personae**:
The declaration block at the top of a play listing every Character used. Each Character's
description is a comment.
_Avoid_: header, preamble, declarations block (use "Dramatis Personae")

**Constant**:
A value literal written as `article? adjective* noun`. The noun contributes +1 (positive or
neutral noun) or −1 (negative noun); each adjective doubles the magnitude; "nothing" is 0.
_Avoid_: literal, number, term

**Question**:
A comparison line ("better than", "worse than", "as ADJ as") that sets a boolean. The following
"If so" / "If not" line executes conditionally on the most recent Question's result.
_Avoid_: condition, test, predicate

**Character reference**:
Using a Character's name in an expression to read that Character's current Value (e.g. "the sum
of Romeo and a flower"). Distinct from a Constant noun; the analyzer tells them apart by whether
the word names a declared Character.
_Avoid_: variable lookup, dereference

**Breakpoint**:
The stage direction `[A pause]` — a debugger pause. This interpreter parses it for fidelity and
otherwise ignores it.
_Avoid_: halt, stop

## Example dialogue

> **Dev:** When Romeo says "You are as lovely as the sum of a flower and a happy cat", who gets assigned?
> **Domain expert:** Romeo is the *Speaker*, so "you" is the *Addressee* — the other Character on stage.
> The Addressee's *Value* is set to the *Constant* sum: a flower is +1, a happy cat is +1 doubled by
> one adjective = +2, total +3.
>
> **Dev:** And if three Characters are on stage when that line is spoken?
> **Domain expert:** That's a runtime error — "you" is ambiguous. Only two Characters may be on the
> *Stage* together to interact.
>
> **Dev:** "Let us proceed to scene II" — that jumps where?
> **Domain expert:** To that *Scene*'s label. Acts and Scenes are the only goto targets; nothing else
> in the play names a jump destination.

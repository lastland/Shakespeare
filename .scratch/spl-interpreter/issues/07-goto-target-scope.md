# Decide goto target scope: act+scene superset vs scene-only

Status: resolved

Our grammar accepts gotos to both **acts and scenes** (`Let us proceed to act II` /
`... to scene II`). The `shakespearelang` reference grammar only allows **scene** targets
(`goto = let_us proceed_to "scene" ...`); the original spec / esolangs description allows acts too.

We currently match the broader spec. Decide whether to:
- keep the superset (more permissive; documented in ADR-0002 consequences), or
- restrict to scenes for strict reference parity.

No code change if we keep it; this is a conformance decision to record. If we restrict, drop the
`act` target from the grammar + analyzer + `Goto` handling and update tests.

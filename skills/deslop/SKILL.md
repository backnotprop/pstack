---
name: deslop
description: Remove AI-generated slop from the current diff before commit.
disable-model-invocation: true
---

# Deslop

Review the diff against the base branch (`git diff $(git merge-base HEAD main)`; use the repo's default branch). Remove what a careful human author would not have written, and nothing else:

- Comments that narrate the code, restate a name, or mark a change ("added", "now", "fix"). Leave comments that record a real constraint. Run the **no-comments** skill for a full pass.
- Defensive code the surrounding code does not use: redundant null checks, try/catch that swallows, fallbacks for states the types rule out. Keep guards at system boundaries.
- Casts and escape hatches (`any`, `as`, `# type: ignore`, `unwrap` on fallible input) added to silence a type error. Fix the type.
- Abstractions with one caller, wrapper layers, speculative options, and new helpers that duplicate an existing one. Prefer the smallest change (see **principle-laziness-protocol**).
- Style that differs from the file: naming, error handling, logging, formatting.
- Unrelated edits, renamed symbols, and reformatted lines outside the change.

Then check behavior: run the project's tests or the repro for the change. Report what you removed in one short list; do not describe unchanged code.

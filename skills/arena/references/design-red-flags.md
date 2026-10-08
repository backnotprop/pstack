# Design red flags

Screen every candidate for these failure modes before synthesis.

- A change looks correct in one file but leaves another caller, route, or schema on a different contract.
- A new helper or layer adds indirection without removing duplicated rules, branches, or invalid states.
- One domain rule is copied into multiple modules, so later edits can make behavior diverge.
- A type permits combinations that the behavior cannot support, or hides a required value behind an optional field.
- Business decisions move into a framework adapter or persistence mapper without a boundary reason.
- The HTTP schema and use-case return type disagree, or a legacy response changes without an explicit contract decision.
- The design keeps obsolete callers, aliases, or compatibility paths instead of migrating callers and deleting the old path.
- The public interface exposes internal sequencing or forces callers to know helper implementation details.
- The sketch omits a consumer-visible edge case, error, state transition, or verification path.

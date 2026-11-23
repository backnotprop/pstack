# pstack in Devin

Devin installs pstack as one plugin. Skills are available as `/pstack:<name>`; for example, `/pstack:poteto-mode`. When a skill refers to another pstack skill by its unqualified name, invoke the corresponding `/pstack:<name>` skill or read `skills/<name>/SKILL.md` in this plugin and follow it. Use the installed skill's own path for relative references, not the project working directory.

## Subagents

- Map Cursor `Task` to Devin's `run_subagent` and use the tool's actual schema; do not pass Cursor-only fields. Use `read_subagent` to collect background results. The operator still owns their work and must review it.
- In the CLI and Desktop, use the plugin profiles `pstack:poteto-agent` and `pstack:comment-sicko` when the skill calls for them. Give poteto-agent the absolute path to the installed `skills/poteto-mode/SKILL.md`, and include the worker kickoff required by that skill. The shared profile does not pin a Cursor model.
- Plugin subagents do not load in Devin cloud sessions. If an equivalent general subagent is available, use it with the same instructions: give it the absolute path to poteto-mode for poteto-agent, or the full `skills/no-comments/references/comment-sicko.md` prompt for Comment Sicko. If subagents are unavailable or disabled, do the work sequentially and report that the independent review could not run.
- Use `subagent_general` for work that edits files and `subagent_explore` for read-only exploration. Explore has restricted tools and a separately selected model. Background workers can use only pre-approved tools; if a required tool is denied, resume in the foreground or do the work locally. Give simultaneous writers separate worktrees or non-overlapping output paths.

## Models and review panels

Devin's `run_subagent` takes a profile, not a per-call model. The general profile uses the parent's model; explore and unpinned custom profiles use Devin's default subagent model, which may be router-selected or configured by an administrator. Do not pass Cursor model slugs, claim that a role ran on a particular model without evidence, or treat the pstack per-role settings file as controlling Devin. `/pstack:setup-pstack` explains this limitation instead of writing ineffective settings.

For `/pstack:arena` and `/pstack:interrogate`, independent workers can still provide separate perspectives, but distinct model vendors and a cross-vendor judge are not guaranteed. State that limitation and skip any vendor-dependent judgment that cannot be verified; do not report a cross-model comparison. If independent workers are unavailable, report the limitation rather than presenting serial self-review as an independent panel.

## Other mappings

Use Devin's available question and task-list tools when present; otherwise ask in chat and keep the checklist in the response. Devin CLI reads project skills from `.devin/skills/` or `.agents/skills/`, and user skills from `~/.config/devin/skills/` or `~/.agents/skills/` (on Windows, the Devin user directory is under `%APPDATA%`). Plugin skills stay in the installed plugin. Cursor-only integrations such as `cursor-team-kit` are not bundled here; follow the fallbacks in poteto-mode.

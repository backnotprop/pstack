# Syncing this mirror

This repo mirrors [`cursor/plugins/pstack`](https://github.com/cursor/plugins/tree/main/pstack) and adds its own edits: the top of `README.md` and harness-neutral rewrites in some skills.

Two branches keep those edits safe:

- `upstream` holds Cursor's files exactly, with no local edits.
- `main` is `upstream` plus this mirror's edits.

Never copy Cursor's files onto `main` directly. That erases the edits.

## Steps

1. Copy Cursor's latest `pstack/` folder onto the `upstream` branch:

   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/cursor/plugins.git /tmp/cursor-plugins
   git -C /tmp/cursor-plugins sparse-checkout set pstack
   git switch upstream
   rsync -a --delete --exclude .git --exclude MIRROR.md /tmp/cursor-plugins/pstack/ ./
   git add -A
   git commit -m "upstream: cursor/plugins/pstack @ $(git -C /tmp/cursor-plugins rev-parse --short HEAD)"
   ```

2. Merge it into `main`. Git applies only what changed upstream and keeps the mirror's edits:

   ```bash
   git switch main
   git merge upstream
   ```

   A conflict means Cursor changed a line this mirror also changed. Keep Cursor's new meaning and reapply the harness-neutral wording.

3. Refresh the bundled Comment Sicko prompt, then check that no new Cursor-only instructions arrived:

   ```bash
   cp agents/comment-sicko.md skills/no-comments/references/comment-sicko.md
   git diff upstream@{1} upstream -- skills | grep -nE '\.cursor/|agent-transcripts|cursor-team-kit|create-skill|Task'
   ```

   Rewrite any new hits the same way as the existing edits. The Harness section in `skills/poteto-mode/SKILL.md` lists the mappings.

4. Push both branches:

   ```bash
   git push origin main upstream
   ```

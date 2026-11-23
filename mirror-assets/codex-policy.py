#!/usr/bin/env python3
"""Give Codex the explicit-only mark that pstack skills already carry.

Codex ignores `disable-model-invocation: true` in SKILL.md frontmatter and reads
`agents/openai.yaml` instead. For every skill with that mark, this writes
`skills/<name>/agents/openai.yaml` with `allow_implicit_invocation: false`, so
Codex leaves the skill out of the startup prompt but still runs it by name.
It removes the files it wrote for skills that lost the mark or were deleted.
A file it did not write is left alone.

Run from the repo root after each sync: python3 mirror-assets/codex-policy.py
With --check, it changes nothing and exits 1 if a file is missing or stale.
"""

import pathlib
import sys

MARK = "# Written by mirror-assets/codex-policy.py from disable-model-invocation in SKILL.md. Do not edit.\n"
BODY = MARK + "policy:\n  allow_implicit_invocation: false\n"


def explicit_only(skill_md: pathlib.Path) -> bool:
    lines = skill_md.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.strip() == "disable-model-invocation: true":
            return True
    return False


def main() -> int:
    check = "--check" in sys.argv[1:]
    skills = pathlib.Path("skills")
    if not skills.is_dir():
        sys.exit("Run this from the repo root.")
    want = {
        md.parent / "agents" / "openai.yaml"
        for md in skills.glob("*/SKILL.md")
        if explicit_only(md)
    }
    stale = []
    for path in sorted(want):
        if path.exists() and not path.read_text().startswith(MARK):
            print(f"left alone, not written by this script: {path}")
            continue
        if not path.exists() or path.read_text() != BODY:
            stale.append(path)
            if not check:
                path.parent.mkdir(exist_ok=True)
                path.write_text(BODY)
    for path in sorted(skills.glob("*/agents/openai.yaml")):
        if path in want or not path.read_text().startswith(MARK):
            continue
        stale.append(path)
        if not check:
            path.unlink()
            if not any(path.parent.iterdir()):
                path.parent.rmdir()
            if not any(path.parent.parent.iterdir()):
                path.parent.parent.rmdir()
    for path in stale:
        print(f"{'stale' if check else 'updated'}: {path}")
    print(f"{len(want)} explicit-only skills, {len(stale)} {'stale' if check else 'changed'}.")
    return 1 if check and stale else 0


if __name__ == "__main__":
    sys.exit(main())

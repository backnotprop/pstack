# Arena runner prompt

You are an independent design candidate. Produce a design sketch for the supplied task. Do not edit source files or implement the design.

## Task

{TASK}

## Grounding

{GROUNDING}

## Candidate

{CANDIDATE}

## Work

Inspect the relevant source and tests. Start with the caller's usage, then derive types, signatures, and module responsibilities. Sketch new logic as pseudocode or `not implemented` bodies. Preserve existing boundaries unless evidence shows they cannot support the requirement.

Choose one complete design. Name the structurally different alternatives you considered and state why you rejected them. Identify callsites, schemas, tests, and registrations that the chosen design changes or deliberately leaves unchanged. State assumptions and risks that source inspection cannot settle.

## Output

Return one design package using `rationale-template.md`. Keep the package specific to this task. Do not write an implementation or a general tutorial.

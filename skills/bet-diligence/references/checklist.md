# Diligence checklist

One kind of check on each line. Add a line when a review needed a check that is not here.

## Code

- The build runs from a clean clone with the documented commands.
- The tests run and pass. Record the count and the time.
- The parts that the bet uses have tests.
- Dependencies are pinned. List the dependencies with no release in two years.
- Known vulnerabilities in dependencies, from the ecosystem's audit tool.
- Secrets in the history, from a secret scanner.
- The license allows the bet's use, and the dependency licenses agree with it.
- Error handling and validation at the boundaries that the bet calls.
- Data that leaves the process: telemetry, network calls, and where they go.
- For a parser or protocol library: the inputs it rejects that common clients accept, and what the bet does with each rejection.
- Fixed default limits, such as buffer sizes and timeouts, and whether they apply the same way for every read pattern.
- Failures that are the same on every redundant instance, so that agreement rules do not filter them.
- Integrity of the installed copy against the package record hashes.
- Other packages in the lock file that pull in the subject.

## Team

- Active maintainers in the last 12 months.
- Share of commits by the top author. A share above 80% is a bus-factor risk.
- Time since the last release and the last commit.
- Median time to merge a pull request, and to close an issue.
- Open issues that block the bet's use.

## Market

- Products that answer the same need, with price and source.
- What the subject does that those products do not.
- Who pays for the subject today, and how, when that is public.
- Signs that the subject could stop: funding, a license change, an archived repository.

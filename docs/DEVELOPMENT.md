# Development workflow

This workflow applies to future work. It does not reconstruct or relabel past
commits as if they followed this process. Keep real commit dates and history.

## From question to review

1. **Issue:** state the observed problem or research question and link existing evidence.
2. **Hypothesis / purpose:** record the proposed change, expected effect, alternatives,
   assumptions and acceptance criteria before running a new experiment. Identify
   who proposed the idea, who reviewed it, and what remains uncertain.
3. **Small implementation:** use a focused branch and avoid unrelated changes.
   Record AI assistance where relevant, including suggestions rejected or corrected.
4. **Test:** check behavior and information boundaries. Preserve training-only
   preprocessing, forecast-only decisions, explicit oracle benchmarks and physical constraints.
5. **Experiment:** fix the data period, parameters, comparison and metrics before
   evaluation. Use separate output directories; retain published experiments.
   Once results inform a choice, use new validation/out-of-sample data for further claims.
6. **Result:** save configuration, source/data hashes, environment, full comparisons
   and failure cases. Separate observed numbers from explanations and hypotheses.
7. **PR:** summarize purpose, final change, tests, experiment evidence, limitations,
   authorship/AI contributions and unresolved questions. Check CI before merging.

For documentation-only changes, state that no new experiment is needed and verify
that numerical evidence and executable behavior are unchanged. Avoid unnecessary reruns.

## Decision record template

```text
Issue / question:
Proposed by (author / AI suggestion / literature):
Author's rationale and alternatives considered:
Reviewed by / confirmation date:
Expected effect and acceptance criteria:
Information available at decision time:
Implementation / tests:
Experiment configuration and evidence:
Observed results, including adverse outcomes:
Interpretation / remaining uncertainty:
PR:
```

Do not convert an AI-proposed explanation into a first-person decision without
confirmation. Use `TODO(author): confirm rationale` until the author has reviewed
it, then record what was actually accepted and why. A commit approval is not a
claim that every scientific detail was independently derived or verified.

## Private study material

Keep personal interview preparation and study scripts outside the repository,
for example in a local ignored `private_notes/` directory. Technical methodology,
results and reproducibility evidence belong in the public documentation.
Removing a file from the current tree does not erase it from historical commits;
this workflow does not rewrite history.

[Design decisions](DESIGN_DECISIONS.md) · [Publication workflow](PUBLISHING.md)

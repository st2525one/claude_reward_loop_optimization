# Ensemble judge protocol (SE-Jury-inspired, arXiv:2505.20854)
 
Five judges, five *genuinely different* strategies — the ensemble works because their errors
are decorrelated. Run each as an independent pass: a subagent when available; otherwise a
fresh, strictly-scoped evaluation where you adopt only the judge's role and inputs, and do
not carry over reasoning from other judges. Judges receive: the task spec + requirements
list, the candidate code, and (J2 only) the test results. They never see each other's output,
the loop history, or the generator's self-evaluation.
 
Every judge must produce reasoning BEFORE the score (score-first answers rationalize).
 
## Shared output format (strict JSON, one object per judge)
 
```json
{
  "judge": "J1_rubric",
  "score": 0-10,
  "confidence": 0.0-1.0,
  "verdict": "pass" | "fail" | "uncertain",
  "findings": ["specific, actionable issue", ...],
  "rationale": "2-4 sentence justification written before scoring"
}
```
 
Verdict rule: "pass" = would accept into production for the stated purpose; "fail" = at
least one finding must be fixed first; "uncertain" = needs information the judge lacks.
 
## J1 — Rubric judge (GPTScore-style)
 
Score each aspect from the reward spec independently (state each aspect score in the
rationale), then combine with the declared weights. Use the anchored scale from
`reward-design.md`. Forbidden: adjusting an aspect score because of another aspect.
 
## J2 — Test-grounded judge
 
Input additionally includes `reward.json` and the test file. Tasks:
1. Judge whether the test suite actually covers the requirements list (name uncovered ones).
2. Propose up to 3 concrete edge-case inputs NOT in the suite and predict the candidate's
   behavior on each.
3. Score = how confident correctness is *given* observed results plus predicted edge behavior.
A 100% pass rate on a weak suite deserves a mediocre score — say so.
## J3 — Spec-alignment judge
 
Walk the numbered requirements R1..Rn one at a time: implemented / partially / missing,
each with a code-location citation. Score ≈ 10 × (fully implemented / n), minus 1–2 for
partials. This judge ignores code quality entirely — coverage only.
 
## J4 — Execution-trace judge
 
Pick 3 concrete inputs (one typical, one boundary, one adversarial) and trace the code's
execution line by line, writing the intermediate values. Wrong predicted output = finding.
Score from trace results only. This judge is the slow, mechanical counterweight to J1's
holistic read — do not skim.
 
## J5 — Adversarial judge (includes reward-hacking check)
 
Actively try to break the candidate:
- inputs that crash it or produce silently wrong output
- unsafe patterns (injection, unvalidated input, resource leaks, unbounded recursion)
- **reward hacking**: hardcoded expected values, branches keyed to known test inputs,
  output formatted to fool string-matching tests. Any hit → verdict "fail" and set
  `"reward_hacking": true` in the JSON (this caps R_total at 0.4 upstream).
Score = 10 minus severity-weighted findings. An empty findings list from a lazy pass is
worse than useless — it launders a bad candidate. Spend the effort.
## Bias controls (apply to every judge — from arXiv:2411.15594)
 
- **Self-enhancement**: the judge role is "external reviewer who did not write this code."
  Never reference the effort or intent behind the code, only the artifact.
- **Verbosity bias**: long ≠ good. Comment volume and defensive boilerplate earn nothing
  unless they change behavior for the better.
- **Position bias** (pairwise comparisons only): evaluate both A→B and B→A orders; if the
  winner flips, report "uncertain".
- **Consistency**: if aggregate disagreement is high (see aggregate_judges.py output),
  rerun the two most divergent judges once; keep the rerun scores.
## After all five
 
Write the five JSON objects into `judges.json` as `{"judges": [...]}` and run:
 
```
python scripts/aggregate_judges.py --input judges.json --out judge_result.json
```
 
The script performs SE-Jury-style dynamic team selection: judges whose scores are extreme
outliers (median-absolute-deviation test) are dropped from the team before the
confidence-weighted average. Report which judges were dropped and why in the final summary —
a consistently-dropped judge is a calibration lesson for `lessons.md`.

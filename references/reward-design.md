# Reward design (GPTScore-inspired)
 
GPTScore's core idea (arXiv:2302.04166): evaluation quality improves when you tell the
evaluator *what aspect* to measure via explicit natural-language instruction, instead of
asking for a single holistic score. Apply that here by decomposing the reward.
 
## Structure
 
```
R_total = w_exec * R_exec + w_judge * R_judge        default w = 0.6 / 0.4 for code
```
 
Deterministic first: anything checkable by execution or static analysis goes into R_exec,
never into a judged aspect. Judges are for what machines can't check.
 
### R_exec (computed by scripts/reward.py)
 
```
R_exec = 0.85 * pass_rate + 0.15 * static_score
```
 
- `pass_rate` — fraction of spec-derived tests passing (pytest, stdlib fallback).
- `static_score` — 1.0 if syntax-clean and no pyflakes-detected defects; scaled down per defect.
- A candidate that fails to parse scores 0 outright.
### R_judge aspects (scored 0–10 by the ensemble, normalized to 0–1)
 
Default aspect set for code — adjust per task, and say so when you do:
 
| Aspect | Weight | What it measures |
|---|---|---|
| correctness | 0.40 | Logic correct beyond the given tests |
| robustness | 0.20 | Edge cases, invalid input, error handling |
| spec_coverage | 0.20 | Every numbered requirement implemented |
| readability | 0.10 | Clear naming, structure, docs |
| efficiency | 0.10 | Reasonable complexity for stated scale |
 
## Writing anchored scales
 
Unanchored scores drift (a survey-documented judge failure). Define anchors once and reuse:
 
- **10** — no defects found under adversarial reading
- **7** — minor defects, none affecting correctness on valid inputs
- **4** — at least one defect that produces wrong output on plausible input
- **1** — fails the primary use case
## Rules that prevent reward hacking
 
1. Tests are written from the spec **before** implementations exist.
2. The generator never edits tests to make them pass; a wrong test is fixed only with an
   explicit note in the run log.
3. Judge J5 explicitly checks for special-casing of known test inputs; a hit caps
   R_total at 0.4 regardless of other scores.
## Adapting to non-code tasks
 
Set w_exec = 0, w_judge = 1, and swap the aspect table (GPTScore-style): e.g. for analytical
writing — factual_accuracy 0.35, coverage 0.25, reasoning_quality 0.20, clarity 0.20.
Everything else (loop, ensemble, lessons) is unchanged. Deterministic checks that DO exist
for text (word counts, required sections, verifiable numbers via a script) still go in R_exec
with a small weight rather than being judged.

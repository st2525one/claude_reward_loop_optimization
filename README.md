# claude_reward_loop_optimization
claudeを用いたコーディングの質・精度を向上させるスキル
 
# Code Reward Loop — 報酬最大化 × 自己評価 × LLM-as-a-Judge
 
Turn one-shot code generation into a measurable optimization problem: define a reward,
maximize it with a generate→evaluate→refine loop, audit the result with an ensemble of
independent judges, and bank what you learned.
 
Theoretical basis (cite these when explaining the method to the user):
 
- **GPTScore** (Fu et al., arXiv:2302.04166) — instruction-driven, multi-aspect evaluation:
  decompose "quality" into named aspects and score each one, instead of one vague number.
- **A Survey on LLM-as-a-Judge** (Gu et al., arXiv:2411.15594) — reliability engineering for
  judges: bias mitigation, consistency via multiple passes, separating generator and judge.
- **SE-Jury** (Zhou et al., arXiv:2505.20854) — an *ensemble* of judges with distinct
  evaluation strategies plus dynamic team selection beats any single judge for code correctness.
Respond in the user's language (the pipeline artifacts below stay machine-readable JSON).
 
## Why a loop instead of one careful answer
 
A single generation pass conflates writing and checking. Splitting them gives you:
(1) a deterministic reward signal (tests either pass or they don't) that anchors the
subjective parts, (2) independent judges that don't share the generator's blind spots,
and (3) a written trail that lets the *next* task start from accumulated lessons instead
of zero. That last part is the self-improvement: the model can't update its weights, but
it can update its context.
 
## Phase 0 — Setup and memory
 
1. Locate or create the lessons file in the user's working directory:
   `./.code-reward-loop/lessons.md` (copy `assets/lessons-template.md` if missing).
   Read it BEFORE generating anything and apply relevant lessons.
2. Restate the task spec as a numbered requirements list (R1, R2, ...). Ambiguities you
   resolve by assumption must be written down — judges will check against this list.
## Phase 1 — Define the reward function
 
Read `references/reward-design.md` for the full method. In short, build:
 
```
R_total = w_exec * R_exec + w_judge * R_judge          (defaults: 0.6 / 0.4)
R_exec  = test pass rate + static checks               (deterministic, scripts/reward.py)
R_judge = confidence-weighted ensemble judge score     (Phase 3, scripts/aggregate_judges.py)
```
 
State the reward spec (aspects + weights) in one short block before generating. If the
user gave explicit acceptance criteria, encode them as test cases and rubric aspects.
 
**Write the test suite FIRST, from the spec only** — before any implementation exists.
Tests written after seeing the code inherit its blind spots, and an implementation tuned
to post-hoc tests is reward hacking, not correctness.
 
## Phase 2 — Reward-maximization inner loop
 
Run up to 3 iterations (more only if reward is still climbing):
 
1. **Generate k=2–3 diverse candidates** (different algorithms/structures, not cosmetic
   variants). Diversity is what makes best-of-n better than try-again.
2. **Score deterministically**: for each candidate run
   `python scripts/reward.py --solution cand_i.py --tests test_spec.py --out reward_i.json`
3. **Self-evaluate the best candidate** against the requirements list: for each Rn state
   pass/fail with a one-line reason. Be adversarial with yourself — the point of this pass
   is to find the failure the tests didn't encode.
4. **Refine**: fix the identified failures (or merge strengths of two candidates), re-score.
5. **Record** each iteration:
   `python scripts/loop_state.py record --state loop_state.json --iteration N --candidate cand_i --reward <R_exec>`
Exit the inner loop when R_exec = 1.0, or `loop_state.py decide` reports a plateau.
 
## Phase 3 — Ensemble LLM-as-a-judge audit
 
Never ship the inner-loop winner unaudited: the generator grading its own work is the
self-enhancement bias the survey warns about. Read `references/judge-protocol.md` and run
all five judges on the best candidate:
 
| Judge | Strategy |
|---|---|
| J1 rubric | Multi-aspect rubric scoring (GPTScore-style) |
| J2 test-grounded | Reasons from test results; proposes missing edge cases |
| J3 spec-alignment | Requirement-by-requirement coverage check |
| J4 trace | Mentally executes the code on concrete inputs |
| J5 adversarial | Hunts bugs, unsafe patterns, and **reward hacking** (test-gaming) |
 
Rules that keep the judges honest (from the survey — details in `references/reliability.md`):
run each judge as an independent pass (subagent if available, otherwise a fresh strictly-scoped
prompt), require chain-of-thought *before* the score, use the anchored 0–10 scale, and never
let a judge see another judge's output before scoring.
 
Collect the five JSON verdicts into `judges.json`, then aggregate with dynamic team selection
(outlier judges are dropped, SE-Jury style):
 
```
python scripts/aggregate_judges.py --input judges.json --out judge_result.json
```
 
If the result has `escalate_to_human: true` (high disagreement), show the user the split
opinions instead of papering over them.
 
## Phase 4 — Combine, decide, iterate
 
1. `R_total = 0.6 * R_exec + 0.4 * final_score` (from judge_result.json).
2. `python scripts/loop_state.py record ... --judge-score <final_score>` then
   `python scripts/loop_state.py decide --state loop_state.json --target 0.9`
3. If `decide` says continue AND judges reported *fixable* issues: apply the fixes, add a
   regression test for each judge-found bug, and return to Phase 2 (targeted, not from scratch).
4. If a judge found reward hacking (special-cased tests, hardcoded expected values), that
   overrides the numeric score — fix it regardless of R_total.
## Phase 5 — Self-improvement (the part that compounds)
 
Before reporting, distill judge rationales and loop history into lessons:
 
- Only **generalized** lessons go into `./.code-reward-loop/lessons.md` — "off-by-one in
  pagination boundaries; always test empty and single-element inputs" is a lesson;
  "line 42 had a bug" is not.
- Append with date + task type using the template's entry format. Prune duplicates.
- Also record judge-calibration notes (e.g., "J4 trace consistently harsher than execution
  reality on recursion") — these tune future aggregation.
## Final report format
 
```
## 結果 / Result
[the final code]
 
## Reward
| Component | Score |
|---|---|
| R_exec (tests) | x.xx |
| R_judge (ensemble, team=[...]) | x.xx |
| **R_total** | **x.xx** |
Iterations: N, trajectory: 0.55 → 0.80 → 0.95
 
## Judge findings addressed
- [issue → fix, one line each]
 
## Lessons banked
- [what was appended to lessons.md]
```
 
## Scope notes
 
- Primary target is code generation. For non-code text tasks the same loop applies with
  w_exec = 0 and all-judge reward — see the last section of `references/reward-design.md`.
- Keep total artifacts in a `./.code-reward-loop/run-<timestamp>/` directory so reruns
  don't clobber each other; only `lessons.md` lives at the top level and persists.
- scripts/ require only Python 3 stdlib; `pytest` is used if installed (fallback included).

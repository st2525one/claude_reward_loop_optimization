# Judge reliability checklist (from A Survey on LLM-as-a-Judge, arXiv:2411.15594)
 
Consult when judge results look suspicious, or when adapting the protocol to a new domain.
 
## Known biases and the mitigation used in this skill
 
| Bias | Symptom | Mitigation here |
|---|---|---|
| Self-enhancement | Generator rates own output high | Judges are separate passes with external-reviewer role; generator's self-eval is never a reward input |
| Position | Pairwise winner depends on order | Both orders evaluated; flip → "uncertain" |
| Verbosity | Longer output scores higher | Explicit instruction: length earns nothing |
| Score drift / leniency | Everything gets 7-8 | Anchored scale (10/7/4/1 definitions) |
| Rationalization | Score chosen first, reasons invented | Reasoning required before score |
| Herding | Judges converge after seeing peers | Judges never see each other's output |
 
## Consistency techniques
 
- **Ensemble + dynamic team selection** (SE-Jury): decorrelated strategies, MAD-based
  outlier dropping. This is the primary consistency mechanism.
- **Self-consistency rerun**: on high disagreement, rerun the two most divergent judges
  once. Do not rerun until agreement appears — that's p-hacking; rerun once, keep result.
- **Escalation**: `escalate_to_human: true` means the disagreement is signal, not noise.
  Show the user the split, with each side's strongest finding.
## Calibration over time (feeds Phase 5)
 
- When ground truth later emerges (user accepts/rejects, bug found in production), record
  in `lessons.md` which judges were right. Persistently wrong judges get their confidence
  down-weighted in future runs; persistently dropped-but-right judges get protected.
- Judge-human agreement is the metric that matters (SE-Jury's headline result). If the
  user regularly overrides the ensemble, the aspect weights — not the user — are wrong;
  revise the reward spec and note it.
## When NOT to trust the ensemble
 
- Tasks where correctness is fully machine-checkable: trust R_exec, use judges only for
  the residual aspects (readability etc.).
- Domains requiring expertise the judges lack (cryptography, medical dosing, legal text):
  say so explicitly and recommend human expert review instead of quietly scoring.

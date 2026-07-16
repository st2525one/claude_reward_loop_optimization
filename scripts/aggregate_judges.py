#!/usr/bin/env python3
"""SE-Jury-style aggregation of ensemble judge verdicts (arXiv:2505.20854 inspired).
 
Dynamic team selection: drop judges whose normalized score is a median-absolute-deviation
outlier, then compute a confidence-weighted mean over the remaining team.
 
Input JSON: {"judges": [{"judge": str, "score": 0-10, "confidence": 0-1,
                          "verdict": "pass"|"fail"|"uncertain",
                          "findings": [...], "rationale": str,
                          "reward_hacking": bool (optional)}]}
 
Usage:
  python aggregate_judges.py --input judges.json [--out judge_result.json]
      [--mad-k 2.5] [--min-team 3] [--disagreement-threshold 0.18]
"""
import argparse
import json
import statistics
 
 
def median_abs_deviation(values):
    med = statistics.median(values)
    return med, statistics.median([abs(v - med) for v in values])
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--mad-k", type=float, default=2.5)
    ap.add_argument("--min-team", type=int, default=3)
    ap.add_argument("--disagreement-threshold", type=float, default=0.18)
    args = ap.parse_args()
 
    with open(args.input, encoding="utf-8") as f:
        judges = json.load(f)["judges"]
    if not judges:
        raise SystemExit("no judges in input")
 
    for j in judges:
        j["norm"] = max(0.0, min(1.0, float(j["score"]) / 10.0))
        j.setdefault("confidence", 0.5)
        j.setdefault("findings", [])
 
    # --- dynamic team selection (MAD outlier drop) ---
    scores = [j["norm"] for j in judges]
    med, mad = median_abs_deviation(scores)
    team, dropped = [], []
    if mad == 0:
        team = judges[:]
    else:
        for j in judges:
            if abs(j["norm"] - med) <= args.mad_k * mad:
                team.append(j)
            else:
                dropped.append(j)
    if len(team) < args.min_team:  # never shrink below quorum
        team, dropped = judges[:], []
 
    # --- confidence-weighted aggregate ---
    wsum = sum(j["confidence"] for j in team) or len(team)
    final = sum(j["norm"] * j["confidence"] for j in team) / wsum
    team_scores = [j["norm"] for j in team]
    disagreement = statistics.pstdev(team_scores) if len(team_scores) > 1 else 0.0
 
    verdicts = [j["verdict"] for j in team]
    n_fail = verdicts.count("fail")
    verdict = ("fail" if n_fail * 2 >= len(verdicts)
               else "uncertain" if "uncertain" in verdicts or n_fail
               else "pass")
 
    reward_hacking = any(j.get("reward_hacking") for j in judges)
    if reward_hacking:
        final = min(final, 0.4)
        verdict = "fail"
 
    escalate = disagreement > args.disagreement_threshold or (
        verdict == "uncertain" and n_fail > 0)
 
    result = {
        "final_score": round(final, 4),
        "verdict": verdict,
        "disagreement": round(disagreement, 4),
        "escalate_to_human": escalate,
        "reward_hacking_detected": reward_hacking,
        "team": [j["judge"] for j in team],
        "dropped_outliers": [
            {"judge": j["judge"], "score": j["norm"],
             "reason": f"MAD outlier (median={med:.2f}, mad={mad:.2f})"}
            for j in dropped
        ],
        "all_findings": [
            {"judge": j["judge"], "finding": f}
            for j in judges for f in j["findings"]
        ],
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
 
 
if __name__ == "__main__":
    main()

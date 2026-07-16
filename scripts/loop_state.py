#!/usr/bin/env python3
"""Track reward-maximization iterations; decide continue/stop.
 
record: append an iteration entry.
  python loop_state.py record --state loop_state.json --iteration 1 \
      --candidate cand_a --reward 0.83 [--judge-score 0.7] [--notes "..."]
 
decide: recommendation based on trajectory.
  python loop_state.py decide --state loop_state.json \
      [--target 0.9] [--epsilon 0.02] [--patience 2] [--max-iter 6] \
      [--w-exec 0.6] [--w-judge 0.4]
 
Stop when: target reached, plateau (best total improved < epsilon for `patience`
consecutive iterations), or max-iter hit. Otherwise continue.
"""
import argparse
import json
import os
 
 
def load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"iterations": []}
 
 
def total(entry, w_exec, w_judge):
    r = entry.get("reward", 0.0)
    js = entry.get("judge_score")
    if js is None:
        return r  # inner loop: deterministic only
    return w_exec * r + w_judge * js
 
 
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
 
    r = sub.add_parser("record")
    r.add_argument("--state", required=True)
    r.add_argument("--iteration", type=int, required=True)
    r.add_argument("--candidate", required=True)
    r.add_argument("--reward", type=float, required=True)
    r.add_argument("--judge-score", type=float, default=None)
    r.add_argument("--notes", default="")
 
    d = sub.add_parser("decide")
    d.add_argument("--state", required=True)
    d.add_argument("--target", type=float, default=0.9)
    d.add_argument("--epsilon", type=float, default=0.02)
    d.add_argument("--patience", type=int, default=2)
    d.add_argument("--max-iter", type=int, default=6)
    d.add_argument("--w-exec", type=float, default=0.6)
    d.add_argument("--w-judge", type=float, default=0.4)
 
    args = ap.parse_args()
    state = load(args.state)
 
    if args.cmd == "record":
        state["iterations"].append({
            "iteration": args.iteration, "candidate": args.candidate,
            "reward": args.reward, "judge_score": args.judge_score,
            "notes": args.notes,
        })
        with open(args.state, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(json.dumps({"recorded": len(state["iterations"])}))
        return
 
    # decide
    its = state["iterations"]
    if not its:
        print(json.dumps({"recommendation": "continue",
                          "reason": "no iterations recorded yet"}))
        return
 
    totals = [total(e, args.w_exec, args.w_judge) for e in its]
    best_i = max(range(len(totals)), key=totals.__getitem__)
    best = its[best_i]
    best_total = totals[best_i]
 
    # running best and plateau detection
    running_best, stalls = [], 0
    for t in totals:
        running_best.append(t if not running_best else max(running_best[-1], t))
    for i in range(1, len(running_best)):
        stalls = stalls + 1 if running_best[i] - running_best[i - 1] < args.epsilon else 0
 
    if best_total >= args.target:
        rec, reason = "stop", f"target {args.target} reached ({best_total:.3f})"
    elif len(its) >= args.max_iter:
        rec, reason = "stop", f"max iterations ({args.max_iter}) reached"
    elif stalls >= args.patience:
        rec, reason = "stop", (f"plateau: best improved <{args.epsilon} for "
                               f"{stalls} consecutive iterations")
    else:
        rec, reason = "continue", "reward still improving and below target"
 
    print(json.dumps({
        "recommendation": rec, "reason": reason,
        "best_candidate": best["candidate"],
        "best_total": round(best_total, 4),
        "best_iteration": best["iteration"],
        "trajectory": [round(t, 4) for t in totals],
    }, indent=2, ensure_ascii=False))
 
 
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deterministic reward for a generated code candidate.
 
R_exec = 0.85 * pass_rate + 0.15 * static_score
Candidates that fail to parse score 0.
 
Usage:
  python reward.py --solution cand.py --tests test_spec.py [--timeout 60] [--out reward.json]
 
Requires only stdlib. Uses pytest if installed; otherwise falls back to running the
test file directly (its assertions / unittest cases still count pass/fail as a whole).
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
 
 
def check_syntax(path):
    try:
        with open(path, encoding="utf-8") as f:
            ast.parse(f.read())
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
 
 
def static_score(path):
    """1.0 minus 0.2 per pyflakes-detected defect (floor 0). 1.0 if pyflakes absent."""
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pyflakes", path],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1.0, []
    if p.returncode not in (0, 1):  # pyflakes not installed / crashed
        return 1.0, []
    issues = [ln for ln in p.stdout.splitlines() if ln.strip()]
    return max(0.0, 1.0 - 0.2 * len(issues)), issues
 
 
def has_pytest():
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True, timeout=20,
        )
        return p.returncode == 0
    except Exception:
        return False
 
 
def run_pytest(test_path, timeout, cwd):
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line",
           "-p", "no:cacheprovider", os.path.abspath(test_path)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 0, "errors": 1, "timeout": True, "raw": "TIMEOUT"}
    out = p.stdout + p.stderr
    def count(word):
        return sum(int(n) for n in re.findall(r"(\d+) " + word, out))
    return {"passed": count("passed"), "failed": count("failed"),
            "errors": count("error") + count("errors"), "timeout": False,
            "raw": out[-3000:]}
 
 
def run_fallback(test_path, timeout, cwd):
    """No pytest: run the test file as a script. All-or-nothing pass signal."""
    try:
        p = subprocess.run([sys.executable, os.path.abspath(test_path)],
                           capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 0, "errors": 1, "timeout": True, "raw": "TIMEOUT"}
    ok = p.returncode == 0
    return {"passed": 1 if ok else 0, "failed": 0 if ok else 1, "errors": 0,
            "timeout": False, "raw": (p.stdout + p.stderr)[-3000:]}
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solution", required=True)
    ap.add_argument("--tests", required=True)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", default=None)
    ap.add_argument("--w-pass", type=float, default=0.85)
    ap.add_argument("--w-static", type=float, default=0.15)
    args = ap.parse_args()
 
    result = {"solution": args.solution, "tests": args.tests}
 
    ok, err = check_syntax(args.solution)
    result["syntax_ok"] = ok
    if not ok:
        result.update({"syntax_error": err, "pass_rate": 0.0,
                       "static_score": 0.0, "r_exec": 0.0})
    else:
        cwd = os.path.dirname(os.path.abspath(args.solution)) or "."
        runner = run_pytest if has_pytest() else run_fallback
        t = runner(args.tests, args.timeout, cwd)
        total = t["passed"] + t["failed"] + t["errors"]
        pass_rate = t["passed"] / total if total else 0.0
        s_score, s_issues = static_score(args.solution)
        result.update({
            "test_runner": runner.__name__,
            "tests_passed": t["passed"], "tests_failed": t["failed"],
            "tests_errors": t["errors"], "timed_out": t["timeout"],
            "pass_rate": round(pass_rate, 4),
            "static_score": round(s_score, 4), "static_issues": s_issues,
            "r_exec": round(args.w_pass * pass_rate + args.w_static * s_score, 4),
            "test_output_tail": t["raw"],
        })
 
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
 
 
if __name__ == "__main__":
    main()

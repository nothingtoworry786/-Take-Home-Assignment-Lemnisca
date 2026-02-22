#!/usr/bin/env python3
"""
Eval harness: run test queries against the ClearPath API and report pass/fail.
Expects backend running at API_URL. Uses POST /query (non-streaming).

Usage (from project root):
  python scripts/run_eval.py
  python scripts/run_eval.py --output eval_report.md
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Script dir: run from project root or from backend/ — cases path is relative to script
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CASES = SCRIPT_DIR / "eval_cases.json"
API_URL = "http://localhost:8000/query"
REFUSAL_PHRASES = [
    "i cannot", "i don't know", "i do not know", "not mentioned",
    "cannot find", "not available in the documentation", "not in the documentation",
    "not in the context", "outside the documentation", "cannot assist",
    "not related to", "not covered", "contact support", "beyond the scope",
    "don't have information", "no information", "documentation doesn't",
    "not applicable", "outside my", "not part of the",
]


def load_cases(path: str) -> list:
    p = Path(path)
    if not p.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def post_query(question: str) -> dict:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"question": question}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def check_refusal(answer: str) -> bool:
    low = answer.lower()
    return any(p in low for p in REFUSAL_PHRASES)


def run_eval(cases: list, verbose: bool = True) -> list:
    results = []
    for case in cases:
        q = case.get("query", "")
        expected_contains = case.get("expected_contains") or []
        expected_refusal = case.get("expected_refusal", False)
        case_id = case.get("id", "unknown")
        try:
            data = post_query(q)
        except Exception as e:
            results.append({
                "id": case_id,
                "query": q,
                "pass": False,
                "error": str(e),
                "answer": None,
            })
            if verbose:
                print(f"FAIL {case_id}: {e}")
            continue
        answer = (data.get("answer") or "").strip()
        if expected_refusal:
            passed = check_refusal(answer)
            results.append({
                "id": case_id,
                "query": q,
                "pass": passed,
                "expected": "refusal",
                "answer": answer[:200] + ("..." if len(answer) > 200 else ""),
            })
        else:
            low = answer.lower()
            missing = [s for s in expected_contains if s.lower() not in low]
            passed = len(missing) == 0
            results.append({
                "id": case_id,
                "query": q,
                "pass": passed,
                "expected_contains": expected_contains,
                "missing": missing if not passed else [],
                "answer": answer[:200] + ("..." if len(answer) > 200 else ""),
            })
        if verbose:
            status = "PASS" if results[-1]["pass"] else "FAIL"
            print(f"{status} {case_id}: {q[:50]}...")
    return results


def main():
    ap = argparse.ArgumentParser(description="Run eval harness against ClearPath API")
    ap.add_argument("--cases", default=str(DEFAULT_CASES), help="Path to eval_cases.json")
    ap.add_argument("--output", "-o", default="", help="Write report to this file (e.g. eval_report.md)")
    ap.add_argument("--quiet", "-q", action="store_true", help="Less stdout")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    print(f"Running {len(cases)} eval cases against {API_URL}...")
    results = run_eval(cases, verbose=not args.quiet)
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")

    if args.output:
        lines = [
            "# Eval Harness Report",
            "",
            f"**Results: {passed}/{total} passed**",
            "",
            "| ID | Query | Pass | Notes |",
            "|----|-------|------|-------|",
        ]
        for r in results:
            q_short = (r["query"][:40] + "...") if len(r["query"]) > 40 else r["query"]
            pass_str = "✓" if r["pass"] else "✗"
            note = r.get("error") or r.get("missing") or ("refusal expected" if r.get("expected") == "refusal" and not r["pass"] else "")
            lines.append(f"| {r['id']} | {q_short} | {pass_str} | {note} |")
        lines.extend(["", "## Per-case details", ""])
        for r in results:
            lines.append(f"### {r['id']} ({'PASS' if r['pass'] else 'FAIL'})")
            lines.append(f"- **Query:** {r['query']}")
            lines.append(f"- **Answer (excerpt):** {r.get('answer', 'N/A')}")
            lines.append("")
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report written to {args.output}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

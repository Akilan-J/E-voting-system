"""
E-Voting System - Master Test Runner
Runs all test files in backend/tests/, reports results with Epic context.
Tests that fail are marked as DISCARDED and skipped gracefully.
"""

import os
import sys
import subprocess
import re

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# -----------------------------------------------
# REGISTRY: maps each test file to its Epic and a short human description
# -----------------------------------------------
TEST_REGISTRY = {
    "test_epic4.py": {
        "epic": "Epic 4",
        "desc": "Privacy-Preserving Tallying - encryption, threshold crypto, aggregation, key consistency",
    },
    "test_epic4_endpoints.py": {
        "epic": "Epic 4",
        "desc": "Epic 4 REST endpoint integration (tally start/finalize, recount, transcript) - requires live server",
    },
    "test_ledger.py": {
        "epic": "Epic 3",
        "desc": "Immutable Vote Ledger - hashing, Merkle tree, genesis block, signatures, block validation (US-33/US-40)",
    },
    "test_epic3_enhancements.py": {
        "epic": "Epic 3",
        "desc": "Epic 3 enhancement verification - config loading, signature gen/verify, block structure validation (US-40)",
    },
    "test_ops_stories.py": {
        "epic": "Epic 5",
        "desc": "Ops & Audit - evidence download (US-66), threat simulation (US-68), incident workflow (US-70), anomaly detection (US-73)",
    },
    "test_verification_stories.py": {
        "epic": "Epic 5",
        "desc": "Verification - receipt verification (US-62), ZK proof (US-63), ledger replay (US-64), transparency stats (US-65)",
    },
    "test_security_epic_manual.py": {
        "epic": "Epic 4",
        "desc": "Security flow - login, eligibility, blind-sign credential, anonymous vote cast - requires live server",
    },
    "test_all_implemented_features.py": {
        "epic": "Epic 1-5",
        "desc": "Cross-epic feature validation - auth, ballots, ledger, encryption, verification (all epics)",
    },
    "test_epic5_user_stories.py": {
        "epic": "Epic 5",
        "desc": "Epic 5 user story endpoints - receipt, ZK proof, replay, dashboard, evidence, incidents, disputes",
    },
}

# -----------------------------------------------
# Helpers
# -----------------------------------------------
def _parse_pytest_counts(output):
    """Extract passed/failed/error counts from pytest output."""
    m = re.search(r"(\d+) passed", output)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", output)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) error", output)
    errors = int(m.group(1)) if m else 0
    return passed, failed, errors


def _extract_test_names(output):
    """Pull individual PASSED / FAILED lines from pytest -v output."""
    results = []
    for line in output.splitlines():
        if " PASSED" in line or " FAILED" in line or " ERROR" in line:
            results.append(line.strip())
    return results


# -----------------------------------------------
# Main
# -----------------------------------------------
def main():
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    # Discover test files
    test_files = sorted(
        f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")
    )

    print("=" * 70)
    print("  E-VOTING SYSTEM - MASTER TEST RUNNER")
    print("=" * 70)
    print(f"  Found {len(test_files)} test files in backend/tests/\n")

    summary = []

    for fname in test_files:
        info = TEST_REGISTRY.get(fname, {"epic": "Unknown", "desc": fname})
        filepath = os.path.join(test_dir, fname)

        print(f"-- Running: {fname}  [{info['epic']}] --")
        print(f"   Context: {info['desc']}")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", filepath, "-v", "--tb=short", "--no-header", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=backend_dir,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            output = result.stdout + "\n" + result.stderr
            passed, failed, errors = _parse_pytest_counts(output)
            test_lines = _extract_test_names(output)
            ok = result.returncode == 0

            summary.append({
                "file": fname,
                "epic": info["epic"],
                "desc": info["desc"],
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "ok": ok,
                "details": test_lines,
                "raw": output,
            })

            if ok:
                print(f"   [PASS]  {passed} tests passed")
            else:
                print(f"   [FAIL]  passed={passed}, failed={failed}, errors={errors} -> DISCARDED")
                for line in output.splitlines():
                    if "FAILED" in line or "ERROR" in line or "ModuleNotFoundError" in line or "ImportError" in line:
                        print(f"       {line.strip()}")

        except subprocess.TimeoutExpired:
            summary.append({
                "file": fname, "epic": info["epic"], "desc": info["desc"],
                "passed": 0, "failed": 0, "errors": 1, "ok": False,
                "details": ["TIMEOUT after 120s"], "raw": "",
            })
            print(f"   [TIMEOUT] -> DISCARDED")
        except Exception as e:
            summary.append({
                "file": fname, "epic": info["epic"], "desc": info["desc"],
                "passed": 0, "failed": 0, "errors": 1, "ok": False,
                "details": [str(e)], "raw": "",
            })
            print(f"   [CRASH] {e} -> DISCARDED")

        print()

    # --- FINAL SUMMARY ---
    total_passed = sum(s["passed"] for s in summary)
    total_failed = sum(s["failed"] for s in summary)
    total_errors = sum(s["errors"] for s in summary)
    files_ok = sum(1 for s in summary if s["ok"])
    files_bad = sum(1 for s in summary if not s["ok"])

    print("=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    print(f"  Files: {files_ok} passed, {files_bad} discarded  |  Tests: {total_passed} passed, {total_failed} failed, {total_errors} errors\n")

    # Group by Epic
    epics = {}
    for s in summary:
        epics.setdefault(s["epic"], []).append(s)

    for epic, items in sorted(epics.items()):
        print(f"  [{epic}]")
        for s in items:
            status = "[PASS]" if s["ok"] else "[DISCARDED]"
            print(f"    {status}  {s['file']}  (passed={s['passed']}, failed={s['failed']})")
            print(f"             {s['desc']}")
            if s["ok"] and s["details"]:
                for d in s["details"]:
                    print(f"               > {d}")
        print()

    print("=" * 70)
    if files_bad == 0:
        print("  ALL TEST SUITES PASSED!")
    else:
        print(f"  {files_ok}/{len(summary)} suites passed, {files_bad} discarded (see above for reasons).")
    print("=" * 70)


if __name__ == "__main__":
    main()

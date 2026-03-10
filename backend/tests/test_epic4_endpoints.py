"""Test all new EPIC 4 endpoints — requires a running backend server.
Skipped automatically in CI (no live server in backend-tests job).
"""
import requests
import json
import pytest

BASE = "http://localhost:8000"
ELECTION = "00000000-0000-0000-0000-000000000001"


def _server_reachable():
    try:
        requests.get(f"{BASE}/health", timeout=2)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _server_reachable(), reason="Backend server not running at localhost:8000")
def test():
    # Login as admin
    r = requests.post(f"{BASE}/auth/login", json={"credential": "admin", "password": "admin123"})
    token = r.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Login: {r.status_code}")

    # New static endpoints
    r = requests.get(f"{BASE}/api/tally/election-types")
    types = r.json()
    print(f"Election types: {r.status_code} — {list(types.keys())}")

    r = requests.get(f"{BASE}/api/tally/isolation-status")
    iso = r.json()
    print(f"Isolation: {r.status_code} — enforcement={iso.get('enforcement_level')}")

    r = requests.get(f"{BASE}/api/tally/circuit-breaker/{ELECTION}")
    cb = r.json()
    print(f"Circuit breaker: {r.status_code} — state={cb.get('state')}")

    # Setup test data
    r = requests.post(f"{BASE}/api/mock/setup-trustees", headers=headers)
    print(f"Setup trustees: {r.status_code}")
    r = requests.post(f"{BASE}/api/mock/generate-votes", json={"count": 10}, headers=headers)
    print(f"Generate votes: {r.status_code}")

    # Manifest
    r = requests.get(f"{BASE}/api/tally/manifest/{ELECTION}")
    m = r.json()
    print(f"Manifest: {r.status_code} — ballots={m.get('ballot_count', 0)}")

    # Start tally
    r = requests.post(f"{BASE}/api/tally/start", json={"election_id": ELECTION}, headers=headers)
    print(f"Start tally: {r.status_code}")
    if r.status_code != 200:
        print(f"  Error: {r.text[:200]}")
        return

    # Login as trustee
    r3 = requests.post(f"{BASE}/auth/login", json={"credential": "trustee", "password": "trustee123"})
    t_token = r3.json().get("access_token", "")
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # Get trustees and decrypt
    r2 = requests.get(f"{BASE}/api/trustees", headers=headers)
    trustees = r2.json()

    for i, t in enumerate(trustees[:3]):
        tid = t["trustee_id"]
        r4 = requests.post(
            f"{BASE}/api/tally/partial-decrypt/{tid}?election_id={ELECTION}",
            headers=t_headers,
        )
        print(f"Trustee {i+1} decrypt: {r4.status_code}")
        if r4.status_code != 200:
            print(f"  Error: {r4.text[:200]}")

    # Trustee timeout
    r5 = requests.get(f"{BASE}/api/tally/trustee-timeout/{ELECTION}")
    ts = r5.json()
    print(f"Timeout status: {r5.status_code} — status={ts.get('status')}")

    # Finalize
    r6 = requests.post(f"{BASE}/api/tally/finalize", json={"election_id": ELECTION}, headers=headers)
    print(f"Finalize: {r6.status_code}")
    if r6.status_code != 200:
        print(f"  Error: {r6.text[:200]}")
        return

    # Transcript
    r7 = requests.get(f"{BASE}/api/tally/transcript/{ELECTION}")
    tr = r7.json()
    print(f"Transcript: {r7.status_code} — operations={tr.get('total_operations', 0)}")

    # Reproducibility
    r8 = requests.get(f"{BASE}/api/tally/reproducibility/{ELECTION}")
    rp = r8.json()
    print(f"Reproducibility: {r8.status_code} — status={rp.get('status')}")

    # Real recount
    r9 = requests.post(f"{BASE}/api/tally/recount/{ELECTION}", headers=headers)
    rc = r9.json()
    print(f"Recount: {r9.status_code} — match={rc.get('hashes_match')}")

    print("\n=== ALL EPIC 4 ENDPOINT TESTS COMPLETE ===")

if __name__ == "__main__":
    test()

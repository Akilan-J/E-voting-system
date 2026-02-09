#!/usr/bin/env python3
"""Verify the end-to-end integration workflow against a running stack."""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.getenv("EVOTING_BASE_URL", "http://localhost:8000")
HEALTH_PATH = "/health"


def request_json(method, path, *, token=None, params=None, payload=None, timeout=15):
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc

    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def wait_for_health(max_attempts=30, delay_seconds=2):
    for attempt in range(1, max_attempts + 1):
        try:
            status = request_json("GET", HEALTH_PATH)
            if status and status.get("status") == "healthy":
                print("OK: backend health check passed")
                return
        except RuntimeError as exc:
            print(f"Waiting for backend health ({attempt}/{max_attempts}) - {exc}")
        time.sleep(delay_seconds)
    raise RuntimeError("Backend did not become healthy in time")


def main():
    print("Verifying integration workflow...")
    print(f"Base URL: {BASE_URL}")

    wait_for_health()

    print("Step 1: reset database")
    request_json("POST", "/api/mock/reset-database", params={"confirm": "true"})

    print("Step 2: setup trustees")
    request_json("POST", "/api/mock/setup-trustees")

    print("Step 3: generate mock votes")
    request_json("POST", "/api/mock/generate-votes", params={"count": "5"})

    print("Step 4: fetch election stats")
    stats = request_json("GET", "/api/mock/election-stats")
    election_id = stats["election"]["id"]
    print(f"Election ID: {election_id}")

    print("Step 5: login as admin")
    admin_login = request_json("POST", "/auth/login", payload={"credential": "admin"})
    admin_token = admin_login["access_token"]

    print("Step 6: login as trustee")
    trustee_login = request_json("POST", "/auth/login", payload={"credential": "trustee"})
    trustee_token = trustee_login["access_token"]

    print("Step 7: start tallying")
    request_json(
        "POST",
        "/api/tally/start",
        token=admin_token,
        payload={"election_id": election_id},
    )

    print("Step 8: list trustees")
    trustees = request_json("GET", "/api/trustees", token=admin_token)
    trustee_ids = [t["trustee_id"] for t in trustees[:3]]
    if len(trustee_ids) < 3:
        raise RuntimeError("Need at least 3 trustees to decrypt")

    print("Step 9: partial decrypt (3 trustees)")
    for trustee_id in trustee_ids:
        request_json(
            "POST",
            f"/api/tally/partial-decrypt/{trustee_id}",
            token=trustee_token,
            params={"election_id": election_id},
        )

    print("Step 10: finalize tally")
    request_json(
        "POST",
        "/api/tally/finalize",
        token=admin_token,
        payload={"election_id": election_id},
    )

    print("Step 11: fetch results")
    result = request_json("GET", f"/api/results/{election_id}")
    print("Result summary:")
    print(json.dumps({
        "total_votes": result.get("total_votes_tallied"),
        "verification_hash": result.get("verification_hash"),
        "final_tally": result.get("final_tally"),
    }, indent=2))

    print("Integration workflow verified.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

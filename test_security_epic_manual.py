import requests
import time
import json
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_security_flow():
    print("🚀 Starting EPIC 4 Security Test Flow")
    
    # 1. Login (Simulate OIDC)
    print("\n--- 1. Authentication ---")
    login_payload = {
        "credential": "123456789012", # From init_demo_data
        "password": "password"
    }
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    if resp.status_code != 200:
        print(f"❌ Login Failed: {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login Successful")

    # 2. Check Eligibility
    print("\n--- 2. Eligibility Check ---")
    election_id = "00000000-0000-0000-0000-000000000001"
    resp = requests.get(f"{BASE_URL}/api/voter/eligibility/{election_id}", headers=headers)
    print(f"Eligibility: {resp.json()}")

    # 3. Blind Signature (Simulate Blinding)
    print("\n--- 3. Credential Issuance (Blind Sign) ---")
    # Simulate client-side blinding (simplified: just send int)
    # real: r = random, m = hash(token), blinded = m * r^e mod n
    # server signs: s' = blinded^d mod n
    # client unblinds: s = s' * r^-1 mod n
    # result: s^e = m mod n
    
    # For this test, we skip the math and test the API flow with a number
    blinded_payload = "12345" 
    issue_payload = {
        "election_id": election_id,
        "blinded_payload": blinded_payload
    }
    resp = requests.post(f"{BASE_URL}/api/voter/credential/issue", json=issue_payload, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Issuance Failed: {resp.text}")
        return
    signature = resp.json()["signature"]
    print(f"✅ Credential Issued. Signature: {signature[:20]}...")

    # 4. Cast Vote (Anonymous)
    print("\n--- 4. Cast Vote (Anonymous) ---")
    # In real flow: client unblinds signature. 
    # Here: We need a valid (token, signature) pair that verifies s^e = m.
    # Since we can't easily do RSA math in this script without crypto lib and public key from server,
    # This step might fail verification if we just pass back the blinded values using the UNBLINDED endpoints.
    # The server expects (token, signature) such that signature^e = token.
    # Our `BlindSigner` signs the input. s' = input^d.
    # So s'^e = input^(d*e) = input^1 = input.
    # So if we send token=input and signature=s', it should verify!
    # Because validation is s^e == m.
    # So we can just use the response from issuance directly for this test!
    
    vote_payload = {
        "election_id": election_id,
        "token": blinded_payload, # The message we sent to be signed
        "signature": signature,   # The signature we got back
        "vote_ciphertext": "encrypted_vote_data_simulated"
    }
    
    resp = requests.post(f"{BASE_URL}/api/voter/vote", json=vote_payload)
    if resp.status_code != 200:
        print(f"❌ Vote Cast Failed: {resp.text}")
    else:
        print(f"✅ Vote Cast Successful! Receipt: {resp.json()['receipt_hash']}")

    # 5. Verify Audit Logs
    print("\n--- 5. Verify Audit Logs ---")
    # We'll just check if logs exist in DB via API (if exposed) or assume success if no error.
    # Ideally we'd have an endpoint to inspect logs.
    
if __name__ == "__main__":
    test_security_flow()

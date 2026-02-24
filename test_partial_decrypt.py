"""Test partial decryption API endpoint"""
import requests
import json

BASE_URL = "http://localhost:3000"

# Login as trustee
login_data = {
    "credential": "trustee"
}

print("1. Logging in as trustee...")
response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
if response.status_code != 200:
    print(f"Login failed: {response.status_code}")
    print(response.json())
    exit(1)

token = response.json().get("access_token")
print(f"✓ Logged in successfully")

# Get trustees list
headers = {"Authorization": f"Bearer {token}"}
print("\n2. Getting trustees list...")
response = requests.get(f"{BASE_URL}/api/trustees", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    trustees = response.json()
    print(f"✓ Found {len(trustees)} trustees")
    if trustees:
        trustee_id = trustees[0]["trustee_id"]
        print(f"Using trustee: {trustee_id}")
    else:
        print("No trustees found")
        exit(1)
else:
    print(f"Error: {response.json()}")
    exit(1)

# Check tally status
election_id = "00000000-0000-0000-0000-000000000001"
print(f"\n3. Checking tally status for election {election_id}...")
response = requests.get(f"{BASE_URL}/api/tally/status/{election_id}", headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Attempt partial decryption
print(f"\n4. Attempting partial decryption...")
url = f"{BASE_URL}/api/tally/partial-decrypt/{trustee_id}?election_id={election_id}"
print(f"URL: {url}")
response = requests.post(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code != 200:
    print(f"\n❌ Partial decryption failed with status {response.status_code}")
else:
    print(f"\n✓ Partial decryption successful")

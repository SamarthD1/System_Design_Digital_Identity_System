import requests
import json
import time

BASE_URL = "http://127.0.0.1:5001/api"
print("=========================================")
print("  Digital Identity System API Tester  ")
print("=========================================\n")

# Helper function to print responses nicely
def print_response(action, response):
    print(f"--- {action} ---")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except:
        print(f"Response: {response.text}\n")

# 1. Register a new user
username = f"testuser_{int(time.time())}"
password = "supersecretpassword"

register_data = {
    "username": username,
    "email": f"{username}@example.com",
    "password": password
}
res = requests.post(f"{BASE_URL}/auth/register", json=register_data)
print_response("Registering User", res)

# 2. Login to get Access & Refresh Tokens
login_data = {
    "username": username,
    "password": password
}
res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
print_response("Logging In", res)

access_token = None
refresh_token = None

if res.status_code == 200:
    access_token = res.json().get("access_token")
    refresh_token = res.json().get("refresh_token")

# 3. Access Protected Route (User Profile)
if access_token:
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    res = requests.get(f"{BASE_URL}/user/profile", headers=headers)
    print_response("Fetching Protected User Profile", res)

# 4. Attempt to access Admin Route (Should Fail with 403 Forbidden)
if access_token:
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    res = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    print_response("Testing RBAC (Fetching Admin Data as Normal User)", res)

# 5. Logout User (Revoking Refresh Token)
if refresh_token:
    headers = {
        "Authorization": f"Bearer {refresh_token}"
    }
    res = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    print_response("Logging Out (Revoking Token)", res)

print("[SUCCESS] Automated API Testing Complete!")

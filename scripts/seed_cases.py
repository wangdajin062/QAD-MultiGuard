import json, os
import requests

API = "http://127.0.0.1:9000"
NO_PROXY = {"http": None, "https": None}

# Login
s = requests.Session()
resp = s.post(f"{API}/admin/api/login",
    json={"phone": "13800138000", "code": "888888"},
    proxies=NO_PROXY, timeout=15)
print(f"Login: {resp.status_code} {resp.text[:100]}")

# Load cases
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "cases_data.json"), "r", encoding="utf-8") as f:
    cases = json.load(f)
print(f"Loaded {len(cases)} cases\n")

ok = 0
for i, case in enumerate(cases):
    try:
        r = s.post(f"{API}/v1/admin/cases", json=case,
            proxies=NO_PROXY, timeout=30)
        data = r.json()
        if data.get("code") == 200:
            ok += 1
            print(f"  [{i+1:2d}/{len(cases)}] OK  {case['category']} | {case['title']}")
        else:
            print(f"  [{i+1:2d}/{len(cases)}] FAIL  {data}")
    except Exception as e:
        print(f"  [{i+1:2d}/{len(cases)}] ERR  {e}")

print(f"\nCreated: {ok}/{len(cases)}")

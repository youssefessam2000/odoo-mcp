from dotenv import load_dotenv
import xmlrpc.client
import os

load_dotenv()

base_url = os.getenv("ODOO_BASE_URL").strip().rstrip("/")
db = os.getenv("ODOO_DB").strip()
email = os.getenv("ODOO_EMAIL").strip()
api_key = os.getenv("ODOO_API_KEY").strip()

print("--- Config ---")
print(f"URL:   {base_url}")
print(f"DB:    {db}")
print(f"Email: {email}")
print(f"Key:   {api_key[:6]}...{api_key[-4:]}")
print("--------------\n")

common = xmlrpc.client.ServerProxy(f"{base_url}/xmlrpc/2/common")

# 1. Check server is reachable
print("1. Server version:", common.version())

# 2. List available databases
try:
    print("2. Available DBs:", common.list())
except Exception as e:
    print("2. Could not list DBs:", e)

# 3. Try auth with API key
print("\n3. Trying API key auth...")
uid = common.authenticate(db, email, api_key, {})
print("   Result:", uid)

if not uid:
    print("\n   API key failed.")
    # Try with exact capitalization variants
    print("\n4. Trying capitalized login variant...")
    capitalized = ".".join(p.capitalize() for p in email.split("@")[0].split(".")) + "@" + email.split("@")[1]
    print(f"   Trying: {capitalized}")
    uid2 = common.authenticate(db, capitalized, api_key, {})
    print(f"   Result: {uid2}")
    if uid2:
        print(f"\n   SUCCESS with capitalized login — update ODOO_EMAIL to: {capitalized}")
else:
    print(f"\n   SUCCESS — UID: {uid}")

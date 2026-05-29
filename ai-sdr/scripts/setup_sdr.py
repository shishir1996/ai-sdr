"""
SDR setup script - creates SDR profile, uploads CSV, configures SMTP, activates.
Usage: python scripts/setup_sdr.py <email> <password>
"""
import sys
import requests
import json

API = "https://api.outreacai.offdx.in/api/v1"

def main(email: str, password: str):
    session = requests.Session()

    # 1. Login
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        return
    token = r.json()["access_token"]
    session.headers["Authorization"] = f"Bearer {token}"
    print("Login OK")

    # 2. Check org
    me = session.get(f"{API}/auth/me").json()
    org_id = me.get("org_id")
    print(f"Org ID: {org_id}")

    # 3. List existing SDR profiles
    profiles = session.get(f"{API}/sdr/profiles").json()
    existing = [p for p in profiles if p.get("name") == "Shishir" and not p.get("deleted_at")]
    if existing:
        sdr_id = existing[0]["id"]
        print(f"Found existing SDR: {sdr_id}")
        # Delete it first
        impact = session.get(f"{API}/sdr/profiles/{sdr_id}/deletion-impact").json()
        if impact.get("total_campaigns", 0) == 0 and impact.get("total_activities", 0) == 0:
            r = session.post(f"{API}/sdr/profiles/{sdr_id}/delete", json={"confirm_text": "DELETE"})
            if r.status_code == 200:
                print("Deleted old SDR profile")
        else:
            print("SDR has data, deleting anyway")
            session.post(f"{API}/sdr/profiles/{sdr_id}/delete", json={"confirm_text": "DELETE"})

    # 4. Create SDR profile
    payload = {
        "name": "Shishir",
        "region": "India",
        "sell_type": "product",
        "product_name": "Growvix",
        "product_description": "Growvix is an AI powered social media automation too, which have the power to plan content, create content, schedule the content and post the content across multiple platform like , facebook, insta, linkedin, x, redit, google my business, etc. Also have the features to optmise the google my business profile to rank locally, sugest keywords, generates ai review replys elts.",
        "target_titles": "",
        "target_industries": "",
        "target_locations": "",
        "outreach_tone": "professional",
        "max_daily_emails": 20,
        "max_daily_linkedin": 15,
        "max_daily_calls": 10,
        "leads_target": 100,
        "lead_sources": "manual",
        "linkedin_connect_enabled": True,
        "linkedin_dm_enabled": True,
    }
    r = session.post(f"{API}/sdr/profiles", json=payload)
    if r.status_code not in (200, 201):
        print(f"Create SDR failed: {r.status_code} {r.text}")
        return
    sdr_id = r.json()["id"]
    print(f"SDR created: {sdr_id}")

    # 5. Upload CSV
    with open("ai-sdr/leads.csv", "rb") as f:
        r = session.post(f"{API}/leads/import/csv", files={"file": ("leads.csv", f, "text/csv")})
    if r.status_code not in (200, 201):
        print(f"CSV upload failed: {r.status_code} {r.text}")
    else:
        print(f"CSV upload: {r.json()}")

    # 6. Configure SMTP
    smtp_creds = {
        "provider": "smtp",
        "host": "smtp.hostinger.com",
        "port": 465,
        "username": "shishir.mandal@offdx.in",
        "password": "Newmacos143#",
        "sender_email": "shishir.mandal@offdx.in",
        "sender_name": "Shishir",
        "imap_host": "imap.hostinger.com",
        "imap_port": 993,
        "imap_username": "shishir.mandal@offdx.in",
        "imap_password": "Newmacos143#",
    }
    r = session.put(f"{API}/sdr/profiles/{sdr_id}/email-creds", json=smtp_creds)
    if r.status_code != 200:
        print(f"SMTP config failed: {r.status_code} {r.text}")
    else:
        print("SMTP configured OK")

    # 7. Activate
    r = session.post(f"{API}/sdr/profiles/{sdr_id}/activate")
    if r.status_code != 200:
        print(f"Activation failed: {r.status_code} {r.text}")
    else:
        print("SDR activated! Check agent activity page.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/setup_sdr.py <email> <password>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

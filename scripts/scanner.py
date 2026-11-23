#!/usr/bin/env python3
"""
Autonomous Web3 Bounty Hunter & CNCF Issue Radar
Scans GitHub for high-probability, actionable cash bounties and CNCF mentorship issues.
Includes multi-channel alerting for Discord and Telegram.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_github_api(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "BountyRadar-Sentinel/1.0")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error querying {url}: {e}", file=sys.stderr)
        return None

def search_issues(query, limit=10):
    encoded = urllib.parse.quote(query)
    url = f"https://api.github.com/search/issues?q={encoded}&sort=updated&order=desc&per_page={limit}"
    data = fetch_github_api(url)
    if data and "items" in data:
        return data["items"]
    return []

def send_discord_alert(bounties):
    if not DISCORD_WEBHOOK_URL or not bounties:
        return
    embeds = []
    for b in bounties[:5]:
        embeds.append({
            "title": f"💰 Bounty Alert: {b['title'][:80]}",
            "url": b["html_url"],
            "description": f"**Repo:** `{b['repo']}`\n**Category:** {b['category']}\n**Updated:** {b['updated_at']}",
            "color": 3066993
        })
    payload = json.dumps({"content": "🚨 **New Bounty Opportunities Detected!**", "embeds": embeds}).encode("utf-8")
    req = urllib.request.Request(DISCORD_WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json", "User-Agent": "BountyRadar/1.0"})
    try:
        urllib.request.urlopen(req, timeout=10)
        print("Successfully dispatched Discord alert.")
    except Exception as e:
        print(f"Discord webhook error: {e}", file=sys.stderr)

def persist_to_mongodb(web3_results, cncf_results):
    if not MONGODB_URI:
        print("MONGODB_URI not set, skipping MongoDB persistence.")
        return
    try:
        import pymongo
        client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client.bounty_radar
        
        # Ensure unique index on html_url
        db.bounties.create_index("html_url", unique=True)
        
        now = datetime.now(timezone.utc)
        upserted_count = 0
        
        all_items = []
        for item in web3_results:
            all_items.append({**item, "type": "web3_bounty", "updated_at_utc": now})
        for item in cncf_results:
            all_items.append({**item, "type": "cncf", "updated_at_utc": now})
            
        for item in all_items:
            db.bounties.update_one(
                {"html_url": item["html_url"]},
                {"$set": item, "$setOnInsert": {"discovered_at": now}},
                upsert=True
            )
            upserted_count += 1
            
        db.scan_history.insert_one({
            "timestamp": now,
            "web3_count": len(web3_results),
            "cncf_count": len(cncf_results),
            "status": "success"
        })
        print(f"MongoDB Atlas: Successfully synchronized {upserted_count} opportunities into 'bounty_radar.bounties'.")
    except Exception as e:
        print(f"MongoDB Atlas sync error (non-fatal): {e}", file=sys.stderr)

def main():
    print("Starting Bounty & CNCF Radar Scan...")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Web3 Cash Bounties ($20 - $500+)
    web3_queries = [
        ('label:bounty is:open is:issue "USDC" OR "USD"', "$20-$100+ USDC Bounties"),
        ('repo:Fractal-Neurons/pacta is:open is:issue', "Pacta Verification Bounties"),
        ('org:safetrustcr is:open is:issue', "SafeTrust Protocols"),
        ('org:Trust-Analysis is:open is:issue', "Trust-Analysis Bounties"),
    ]

    # 2. CNCF & Linux Foundation High-Impact Issues
    cncf_queries = [
        ('org:open-telemetry is:open is:issue label:"good first issue"', "OpenTelemetry (CNCF Graduated)"),
        ('org:kubernetes-sigs is:open is:issue label:"good first issue"', "Kubernetes SIGs (LFX Mentorship)"),
        ('org:jaegertracing is:open is:issue label:"good first issue"', "Jaeger Tracing (CNCF Graduated)"),
        ('org:kyverno is:open is:issue label:"good first issue"', "Kyverno Policy Engine (CNCF Graduated)"),
    ]

    web3_results = []
    for q, label in web3_queries:
        items = search_issues(q, limit=5)
        for item in items:
            web3_results.append({
                "category": label,
                "title": item.get("title", ""),
                "html_url": item.get("html_url", ""),
                "repo": item.get("repository_url", "").replace("https://api.github.com/repos/", ""),
                "comments": item.get("comments", 0),
                "updated_at": item.get("updated_at", "")[:10]
            })

    cncf_results = []
    for q, label in cncf_queries:
        items = search_issues(q, limit=5)
        for item in items:
            cncf_results.append({
                "category": label,
                "title": item.get("title", ""),
                "html_url": item.get("html_url", ""),
                "repo": item.get("repository_url", "").replace("https://api.github.com/repos/", ""),
                "comments": item.get("comments", 0),
                "updated_at": item.get("updated_at", "")[:10]
            })

    # Deduplicate by url
    def dedup(lst):
        seen = set()
        out = []
        for x in lst:
            if x["html_url"] not in seen:
                seen.add(x["html_url"])
                out.append(x)
        return out

    web3_results = dedup(web3_results)
    cncf_results = dedup(cncf_results)

    # Optional multi-channel alerts
    send_discord_alert(web3_results)

    # Persist to MongoDB Atlas cloud database
    persist_to_mongodb(web3_results, cncf_results)

    # Generate Markdown Report
    report_content = f"""# 📡 Live Bounty & Mentorship Radar Report

> **Last Updated:** `{timestamp}`  
> **Autonomous Engine:** GitHub Actions 24/7 Cloud Sentinel

---

## 💰 Active Web3 Cash Bounties ($20 – $500+ USDC)

| Project / Repo | Issue Title | Comments | Updated | Action |
|---|---|:---:|:---:|---|
"""

    if not web3_results:
        report_content += "| No active unassigned bounties detected in this cycle | - | - | - | Check again next cycle |\n"
    else:
        for b in web3_results[:12]:
            report_content += f"| `{b['repo']}` | [{b['title'][:55]}...]({b['html_url']}) | {b['comments']} | {b['updated_at']} | [Inspect Issue]({b['html_url']}) |\n"

    report_content += """
---

## 🏛️ Top CNCF & Linux Foundation Openings (LFX Mentorship Targets)

| Project | Issue Title | Comments | Updated | Action |
|---|---|:---:|:---:|---|
"""

    if not cncf_results:
        report_content += "| No fresh good-first-issues detected in this cycle | - | - | - | Check again next cycle |\n"
    else:
        for c in cncf_results[:12]:
            report_content += f"| `{c['repo']}` | [{c['title'][:55]}...]({c['html_url']}) | {c['comments']} | {c['updated_at']} | [View Issue]({c['html_url']}) |\n"

    report_content += """
---
*Automated by [givemehat/bounty-radar](https://github.com/givemehat/bounty-radar) powered by GitHub Actions.*
"""

    os.makedirs("reports", exist_ok=True)
    with open("reports/LATEST_BOUNTIES.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Successfully generated report with {len(web3_results)} bounties and {len(cncf_results)} CNCF issues.")

if __name__ == "__main__":
    main()

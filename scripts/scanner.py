#!/usr/bin/env python3
"""
Autonomous Web3 Bounty Hunter & CNCF Issue Radar
Scans GitHub for high-probability, actionable cash bounties and CNCF mentorship issues.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

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

    # Generate / Update README.md
    readme_content = f"""# 📡 Bounty Radar: Autonomous Web3 Bounty & CNCF Sentinel

[![Bounty Scan](https://github.com/givemehat/bounty-radar/actions/workflows/radar.yml/badge.svg)](https://github.com/givemehat/bounty-radar/actions/workflows/radar.yml)
[![Live Dossier](https://img.shields.io/badge/Live-Bounty%20Dossier-0052FF?style=flat)](reports/LATEST_BOUNTIES.md)
[![Status](https://img.shields.io/badge/Scan%20Frequency-Every%206%20Hours-brightgreen)](https://github.com/givemehat/bounty-radar/actions)

An automated 24/7 cloud radar running on GitHub Actions that continuously monitors, scans, and triages:
1. **Web3 Protocol Bounties ($20 – $500+ USDC)** across verified DeFi and smart contract repositories.
2. **CNCF & Linux Foundation Open Issues** across graduated projects (`open-telemetry`, `kubernetes`, `jaegertracing`, `kyverno`) for LFX Mentorship Term 1 & GSoC.

---

### 📊 Quick Radar Snapshot
- **Last Scan Completed:** `{timestamp}`
- **Active Web3 Bounties Tracked:** `{len(web3_results)}`
- **Active CNCF Openings Tracked:** `{len(cncf_results)}`
- **Full Live Dossier:** 👉 **[View Latest Bounty Report](reports/LATEST_BOUNTIES.md)**

---

### ⚙️ How It Works
```mermaid
flowchart LR
    A["⏱️ GitHub Actions Cron<br/>(Every 6 Hours)"] --> B["🔍 Python Scanner Engine"]
    B --> C["📡 Query GitHub API<br/>(Web3 & CNCF)"]
    C --> D["📊 Deduplicate & Filter<br/>High-Signal Targets"]
    D --> E["📝 Generate reports/LATEST_BOUNTIES.md"]
    E --> F["🚀 Auto-Commit & Publish Live"]
```

---

*Maintained by [@givemehat](https://github.com/givemehat) · B.Tech CSE, Gautam Buddha University.*
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"Successfully generated report with {len(web3_results)} bounties and {len(cncf_results)} CNCF issues.")

if __name__ == "__main__":
    main()

import urllib.request
import urllib.parse
import json
import os

token = os.popen("gh auth token").read().strip()
queries = [
    '"algora-pbc" is:open is:issue "$100"',
    '"algora-pbc" is:open is:issue "$200"',
    '"algora-pbc" is:open is:issue "$300"',
    '"algora-pbc" is:open is:issue "$500"',
    'label:bounty is:open is:issue "USDC"',
    'label:bounty is:open is:issue "$100"',
]

for q in queries:
    url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(q) + "&sort=updated&order=desc&per_page=5"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": "Hunter/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            count = data.get("total_count", 0)
            print(f"=== Query: {q} ({count} total) ===")
            for item in data.get("items", [])[:4]:
                comments = item.get("comments", 0)
                url_str = item.get("html_url", "")
                title = item.get("title", "")[:70]
                print(f"  [{comments} cmts] {url_str} - {title}")
    except Exception as e:
        print(f"Error {q}: {e}")

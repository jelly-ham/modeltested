"""Tell Bing (and other IndexNow engines) which pages changed today, after a deploy.

ChatGPT search and Copilot draw on Bing's index, so fresh scores reach AI answers sooner.
The key is public by design: it's served at https://modeltested.com/<key>.txt.
"""
import datetime
import json
import re
import sys
import urllib.request

HOST = "modeltested.com"
KEY = "07152c33226e13555b31ec1d9a9499c2"


def main() -> None:
    with urllib.request.urlopen(f"https://{HOST}/sitemap.xml", timeout=30) as r:
        xml = r.read().decode()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    urls = [u for u, d in re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", xml) if d == today]
    urls += [f"https://{HOST}/llms.txt", f"https://{HOST}/data/leaderboard.csv"]
    if not urls:
        print("nothing changed today")
        return
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: submitted {len(urls)} URLs, HTTP {r.status}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail a deploy over this
        print(f"IndexNow failed: {e}", file=sys.stderr)

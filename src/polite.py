"""Polite HTTP helper: robots.txt checked, one request every 3 seconds, neutral User-Agent."""
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = "measurement-case-study/1.0"
MIN_DELAY_S = 3.0
_last = 0.0
_robots = {}


def allowed(url: str) -> bool:
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(root + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=20)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[root] = rp
    return _robots[root].can_fetch(USER_AGENT, url)


def get(url: str, stream: bool = False):
    """GET url if robots.txt allows it, at most one request every MIN_DELAY_S seconds."""
    global _last
    if not allowed(url):
        print("[robots] skipped", url)
        return None
    wait = MIN_DELAY_S - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    try:
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60, stream=stream)
    except requests.RequestException as e:
        print("[error]", url, e)
        return None

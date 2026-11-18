"""Collect the public Datahash pages once (robots.txt respected, 1 request / 3 s) into data/raw/datahash/.

    python src/fetch_public.py
Pages already saved are not fetched again. Then run src/parse_public.py.
"""
import re
from pathlib import Path

import polite

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "datahash"
BASE = "https://www.datahash.com"
PAGES = ["/", "/products/", "/offerings/", "/partners/", "/glossary/", "/docs/", "/contact/", "/case-studies/"]


def slug(path: str) -> str:
    return path.strip("/").replace("/", "__") or "home"


def fetch(path: str) -> str | None:
    out = RAW / f"{slug(path)}.html"
    if out.exists():
        return out.read_text(encoding="utf-8")
    r = polite.get(BASE + path)
    if r is None or r.status_code != 200:
        print("[skip]", path, None if r is None else r.status_code)
        return None
    out.write_text(r.text, encoding="utf-8")
    print("saved", path)
    return r.text


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    html = {p: fetch(p) for p in PAGES}
    listing = html.get("/case-studies/") or ""
    cases = sorted(set(re.findall(r'href="(?:https://www\.datahash\.com)?(/case-studies/[a-z0-9\-]+/)"', listing)))
    # follow pagination of the listing if any
    for page in sorted(set(re.findall(r'href="(?:https://www\.datahash\.com)?(/case-studies/page/\d+/)"', listing))):
        cases += re.findall(r'href="(?:https://www\.datahash\.com)?(/case-studies/[a-z0-9\-]+/)"', fetch(page) or "")
    cases = sorted({c for c in cases if "/page/" not in c})
    print(len(cases), "case-study pages found")
    for c in cases:
        fetch(c)


if __name__ == "__main__":
    main()

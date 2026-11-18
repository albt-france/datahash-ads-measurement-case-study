"""Turn the saved Datahash pages (data/raw/datahash/) into two small, publishable tables:

- data/processed/datahash_facts.csv : facts as stated by Datahash, each with its page and collection date;
- data/processed/case_study_grid.csv : the evidence grid of the published case studies, ANONYMISED
  (CS01..CSnn in listing order; no brand name, no headline figure, only which evidence elements are published).

The grid is coded by transparent keyword rules on the page body (testimonial quotes removed), then checked by hand.
    python src/parse_public.py
"""
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "datahash"
OUT = ROOT / "data" / "processed"
BASE = "https://www.datahash.com"
COLLECTED = "2026-11-18"


def text_of(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    try:                                    # pages saved before the encoding fix were decoded as Latin-1
        raw = raw.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    s = BeautifulSoup(raw, "html.parser")
    for t in s(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        t.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ")).strip()


# ------------------------------------------------------------------ facts (each must be found verbatim on its page)
FACTS = [
    ("founded", "Founded in 2019", "home", "/"),
    ("brands_in_production", "used in production by over 10,000 brands", "home", "/"),
    ("countries", "customers in 50+ countries", "home", "/"),
    ("positioning", "Datahash is a first-party data activation platform", "home", "/"),
    ("native_destinations", "Meta, Google, Snap, TikTok, Pinterest, LinkedIn, X, Reddit, and Amazon Ads", "home", "/"),
    ("partner_verified", "Partner-verified on Meta, Snap, and TikTok", "home", "/"),
    ("dedup_default", "Deduped Pixel plus CAPI on Meta by default", "home", "/"),
    ("setup_time", "A standard web CAPI setup goes live in about 15 minutes", "home", "/"),
    ("crm_offline_time", "CRM and offline pipelines typically take days", "home", "/"),
    ("hashing", "Hashed with SHA-256, no PII stored on the host server", "home", "/"),
    ("products", "Signals is the base product; SingleView and Segments are optional add-ons", "products", "/products/"),
    ("offerings", "Web, app, offline, lead, CRM, WhatsApp, and Custom Audiences", "offerings", "/offerings/"),
    ("starting_point", "Web CAPI on your two biggest ad platforms, deduped with your existing pixels", "offerings", "/offerings/"),
    ("google_partnership", "one of the first partners to test, validate and scale Google's Data Manager API", "partners", "/partners/"),
    ("google_tag_gateway", "Google Tag Gateway", "partners", "/partners/"),
    ("glossary_emq", "Event Match Quality (EMQ)", "glossary", "/glossary/"),
]


def facts() -> pd.DataFrame:
    rows = []
    cache = {}
    for key, phrase, page, path in FACTS:
        cache.setdefault(page, text_of(RAW / f"{page}.html").replace("’", "'"))
        found = phrase in cache[page]
        rows.append({"fact": key, "as_stated_by_datahash": phrase, "url": BASE + path, "collected": COLLECTED,
                     "verified_on_page": found})
    df = pd.DataFrame(rows)
    assert df.verified_on_page.all(), df[~df.verified_on_page]
    return df


# ------------------------------------------------------------------ case-study evidence grid
RULES = {  # element -> regex on the case-study body (quotes removed)
    "quantified_outcome": r"\d+(\.\d+)?\s?(%|x\b)",
    "period_stated": r"\b20\d{2}\b|within \w+ weeks|first \d+ months|quarter-over-quarter|year-over-year|previous year",
    "baseline_level_shown": r"up from|before activation|from [\d.]+ the previous year",
    "concurrent_comparison": r"compared to|vs pixel alone|business-as-usual",
    "window_mentioned": r"attribution window|optimi[sz]ation window|\d+-day (click|view)",
    "ramp_up_excluded": r"learning phase|ramp-up|excluding the first",
    "interval_or_significance": r"confidence interval|statistically significant|p-value|±|credible interval",
    "other_changes_disclosed": r"split ad sets|creative|reduction in ad spend|spend increased",
    "offline_or_crm_outcome": r"offline (ROAS|purchases|sales)|in-store purchase|enrolment|point-of-sale|omnichannel ROAS",
    "signal_quality_reported": r"match quality|\bEMQ\b|\bEQS\b|email coverage",
    "labelled_measured_not_incremental": r"additional purchases measured|attributed|revenue tracked|tracked conversions",
}
METRIC_FAMILY = [("ROAS / ROI", r"ROAS|return on investment|\bROI\b"), ("Cost per result", r"cost per|CPA\b|cost-effective"),
                 ("Conversions / revenue", r"purchases|conversions|revenue|subscribers|enrolment"),
                 ("Go-live / process only", r".")]


def body(path: Path) -> tuple[str, str, str, str]:
    t = text_of(path)
    head = re.search(r"CASE STUDY / ([^\]]+?)\s*\]", t)
    plat = re.search(r"platforms\s+(.+?)\s+offering\s+(.+?)\s+metric\s+(.+?)\s+\S?\s*measured in production", t)
    main = t.split("THE NUMBER", 1)[-1].split("NEXT STEP", 1)[0]
    main = re.sub(r"“.*?”", " ", main)                      # drop testimonials (and the names in them)
    return (head.group(1).strip() if head else ""), (plat.group(1) if plat else ""), (plat.group(2) if plat else ""), \
        (plat.group(3) if plat else "") + " || " + main


def grid() -> pd.DataFrame:
    listing = (RAW / "case-studies.html").read_text(encoding="utf-8")
    order = list(dict.fromkeys(re.findall(r'href="(?:https://www\.datahash\.com)?/case-studies/([a-z0-9\-]+)/"', listing)))
    rows = []
    for i, slug in enumerate(order, 1):
        vertical, platform, offering, txt = body(RAW / f"case-studies__{slug}.html")
        metric = txt.split(" || ")[0]
        fam = next((name for name, rx in METRIC_FAMILY if re.search(rx, metric, re.I)), "?")
        row = {"case": f"CS{i:02d}", "vertical": vertical, "platform": platform, "offering": offering, "headline_metric_family": fam}
        for k, rx in RULES.items():
            row[k] = bool(re.search(rx, txt, re.I))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = facts()
    f.drop(columns="verified_on_page").to_csv(OUT / "datahash_facts.csv", index=False)
    g = grid()
    g.to_csv(OUT / "case_study_grid.csv", index=False)
    summary = g.drop(columns=["case", "vertical", "platform", "offering", "headline_metric_family"]).sum()
    print(len(f), "facts verified;", len(g), "case studies coded")
    print(summary.to_string())


if __name__ == "__main__":
    main()

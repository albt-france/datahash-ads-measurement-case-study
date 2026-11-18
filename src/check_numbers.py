"""Number checker for client deliverables (impact report, renewal one-pager, case study).

Every number in a text must be traceable to the analysis fact sheet (deliverables/<client>/facts.json): same value at
the written precision, same unit family (% vs percentage points vs x vs USD vs score), right metric (a ROAS figure
written next to "CPA" is rejected, and the reverse), right attribution window when the text names one, and right
direction. Health metrics (EMQ, match rate, event_id coverage) are rejected inside value sections.

Usage:  python src/check_numbers.py deliverables/client_a/impact_report.md      (exit code 1 if a number fails)
        python src/check_numbers.py --all
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIV = ROOT / "deliverables"

NUM = re.compile(
    r"(?P<sign>[+\-−–])?(?P<cur>\$|USD\s?)?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?P<suf>\s?(?:%|percentage points?\b|pp\b|pts?\b|x\b|×|k\b|thousand\b|million\b|m\b)|/10\b)?")
METRIC_WORDS = {
    "roas": r"\bROAS\b|return on ad spend", "cpa": r"\bCPA\b|cost per (?:acquisition|conversion|order|application|purchase)",
    "emq": r"\bEMQ\b|match quality", "match_rate": r"match rate", "event_id": r"event_id|event ID",
    "orders": r"orders?|applications?|bookings?|subscriptions?|revenue", "reported_conversions": r"reported|conversions? (?:in|on) (?:Meta|Google|TikTok|Snapchat)|platform",
}
HEALTH = {"emq", "match_rate", "event_id"}
WINDOWS = {"7d_click_1d_view": r"7-day click \+ 1-day view|7d click \+ 1d view", "7d_click": r"7-day click(?! \+)|7d click(?! \+)"}
SKIP = re.compile(r"\b(19|20)\d{2}\b|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*|"
                  r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* \d{1,2}\b|\bQ[1-4]\b|\b95%|\b90%|\bUC\d\b|"
                  r"\b\d+ (?:full )?weeks?\b|\b\d+ days?\b|\b\d+-day\b|\bpage \d+\b|\b\d+ of \d+\b|\(\d\)|^\s*\d+\.\s")


@dataclass
class Finding:
    raw: str
    ok: bool
    sentence: str
    message: str = ""


def family(suf: str, cur: str) -> str:
    s = (suf or "").strip().lower()
    if cur:
        return "usd"
    if s == "%":
        return "pct"
    if s.startswith(("percentage point", "pp", "pt")):
        return "pp"
    if s in ("x", "×"):
        return "ratio"
    if s == "/10":
        return "score"
    return "count"


def sections(text: str):
    """Yield (section_kind, sentence, offset). A '## ' heading containing 'health' marks a health section."""
    kind = "value"
    for line in text.splitlines():
        if line.startswith("#"):
            kind = "health" if re.search(r"health|signal quality", line, re.I) else "value"
            continue
        if line.startswith("[[") or line.startswith("<!--"):
            continue
        for sent in re.split(r"(?<=[.;!?])\s+|\s+\|\s+", line):
            if sent.strip():
                yield kind, sent


def candidates(value: float, decimals: int, fam: str, facts: list[dict]) -> list[dict]:
    out = []
    for f in facts:
        if f["unit"] != fam:
            continue
        v = f["value"] * (100 if fam in ("pct", "pp") else 1)
        if fam == "usd" and f.get("display") == "k":
            v = v / 1000
        if round(abs(v), decimals) == round(abs(value), decimals):
            out.append(f)
    return out


def check(text: str, sheet: dict) -> list[Finding]:
    facts = sheet["facts"]
    res = []
    for kind, sent in sections(text):
        clean = SKIP.sub(" ", sent)
        for m in NUM.finditer(clean):
            num = m.group("num").replace(",", "")
            raw = m.group(0).strip()
            value = float(num)
            dec = len(num.split(".")[1]) if "." in num else 0
            suf = (m.group("suf") or "").strip()
            fam = family(suf, m.group("cur") or "")
            in_k = fam == "usd" and suf.lower() in ("k", "thousand")
            fam_facts = [dict(f, display="k") for f in facts] if in_k else facts
            cands = candidates(value, dec, fam, fam_facts)
            if not cands:
                other = [f for f in facts if any(candidates(value, dec, u, [f]) for u in ("pct", "pp", "ratio", "usd", "count", "score"))]
                msg = "not in the fact sheet"
                if other:
                    msg = f"unit mismatch: fact {other[0]['id']} is in {other[0]['unit']}, text writes {fam}"
                res.append(Finding(raw, False, sent, msg))
                continue
            near = sent
            named = [k for k, rx in METRIC_WORDS.items() if re.search(rx, near, re.I)]
            # metric check: if the sentence names ROAS or CPA, the fact must be that metric
            ok = []
            for f in cands:
                if ("roas" in named and f["metric"] == "cpa" and "cpa" not in named) or \
                   ("cpa" in named and f["metric"] == "roas" and "roas" not in named):
                    continue
                win = [w for w, rx in WINDOWS.items() if re.search(rx, near, re.I)]
                if win and f.get("window") and f["window"] not in win:
                    continue
                if m.group("sign") and f["value"] != 0 and f["unit"] in ("pct", "pp"):
                    written = -1 if m.group("sign") in "-−–" else 1
                    if written != (1 if f["value"] > 0 else -1):
                        continue
                ok.append(f)
            if not ok:
                f = cands[0]
                reason = "metric mismatch (ROAS vs CPA)" if {"roas", "cpa"} & set(named) else "window or sign mismatch"
                res.append(Finding(raw, False, sent, f"{reason}: fact {f['id']} is {f['metric']} {f.get('window', '')}"))
                continue
            f = ok[0]
            if kind == "value" and f["metric"] in HEALTH:
                res.append(Finding(raw, False, sent, f"health metric {f['id']} used in a value section"))
                continue
            res.append(Finding(raw, True, sent, f"= {f['id']}"))
    return res


def check_file(path: Path) -> list[Finding]:
    sheet = json.loads((path.parent / "facts.json").read_text(encoding="utf-8"))
    return check(path.read_text(encoding="utf-8"), sheet)


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(DELIV.glob("*/*.md")) if "--all" in argv else [Path(a) for a in argv]
    bad = 0
    for f in files:
        r = check_file(f)
        errs = [x for x in r if not x.ok]
        print(f"{f.relative_to(ROOT) if f.is_absolute() else f}: {len(r)} numbers, {len(errs)} rejected")
        for e in errs:
            print(f"   REJECTED {e.raw!r}: {e.message} | {e.sentence[:110]}")
        bad += len(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

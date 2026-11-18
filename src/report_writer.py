"""Client deliverables (SIMULATED clients A and E): impact report, renewal one-pager, website case study.

1. Build the fact sheet of each analysis from data/output (deliverables/<client>/facts.json): every number a text may
   use, with its unit, metric, window, kind (value / health) and source.
2. Write the drafts from sentence templates (default). Optional: an LLM rewrites the draft (src/llm_client.py, only
   when .env configures one); the template version is the one kept in the repository.
3. Check every number with src/check_numbers.py: a draft with an untraceable number is not rendered.
4. Render HTML and PDF.
    python src/report_writer.py
"""
import html
import json
import re
from pathlib import Path

import pandas as pd

import charts
import check_numbers
import llm_client
from pdf_utils import print_pdf

ROOT = Path(__file__).resolve().parents[1]
OUTD, PROC, DELIV = ROOT / "data" / "output", ROOT / "data" / "processed", ROOT / "deliverables"
FOOT = "SIMULATED client and data · built from the public method in this repository · not Datahash's data or a Datahash client"


def pct(x, d=1, sign=True):
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def usd(x):
    return f"${x / 1000:,.0f}k" if abs(x) >= 10000 else f"${x:,.2f}"


# ------------------------------------------------------------------ fact sheets
def fact(fid, value, unit, metric, kind="value", window=None, source=""):
    return {"id": fid, "value": float(value), "unit": unit, "metric": metric, "kind": kind, "window": window, "source": source}


def incremental(uc, metric="business"):
    p = pd.read_csv(OUTD / "ci_paths.csv")
    p = p[(p.use_case_id == uc) & (p.metric == metric) & p.cf_lo.notna()]
    r = pd.read_csv(OUTD / "use_case_reads.csv").set_index("use_case_id").loc[uc]
    actual = p.actual.sum()
    to_inc = lambda e: actual - actual / (1 + e)
    return to_inc(r[f"{metric}_effect"]), to_inc(r[f"{metric}_lo"]), to_inc(r[f"{metric}_hi"]), actual


def platform_kpis(client, market, platform, start, end):
    a = pd.read_parquet(PROC / "ads_daily.parquet")
    a = a[(a.client == client) & (a.market == market) & (a.platform == platform) & (a.date >= start) & (a.date <= end)]
    return a.spend.sum(), a.conversions.sum(), a.conv_value.sum(), a.conv_click.sum()


def facts_for(client_key):
    r = pd.read_csv(OUTD / "use_case_reads.csv").set_index("use_case_id")
    h = charts.head()
    sig = pd.read_parquet(PROC / "signals_daily.parquet")
    biz = pd.read_parquet(PROC / "business_daily.parquet")
    uc = {"client_a": "UC1", "client_e": "UC7"}[client_key]
    x = r.loc[uc]
    go = pd.Timestamp(x.go_live)
    rs, re_ = pd.Timestamp(x.read_start), pd.Timestamp(x.read_end)
    bs, be = go - pd.Timedelta(days=7 * x.pre_weeks), go - pd.Timedelta(days=1)
    bs = max(bs, go - pd.Timedelta(days=56))
    src = "data/output/use_case_reads.csv"
    F = [fact("orders_effect", x.business_effect, "pct", "orders", source=f"{src}:{uc}.business_effect"),
         fact("orders_lo", x.business_lo, "pct", "orders", source=f"{src}:{uc}.business_lo"),
         fact("orders_hi", x.business_hi, "pct", "orders", source=f"{src}:{uc}.business_hi"),
         fact("reported_effect", x.reported_effect, "pct", "reported_conversions", window="7d_click", source=f"{src}:{uc}.reported_effect"),
         fact("reported_lo", x.reported_lo, "pct", "reported_conversions", window="7d_click", source=f"{src}:{uc}.reported_lo"),
         fact("reported_hi", x.reported_hi, "pct", "reported_conversions", window="7d_click", source=f"{src}:{uc}.reported_hi"),
         fact("naive_reported", x.reported_naive, "pct", "reported_conversions", window="7d_click", source="data/output/sql_02_pre_post.csv"),
         fact("placebo_n", x.business_placebo_n, "count", "method", source=f"{src}:{uc}.business_placebo_n")]
    inc, inc_lo, inc_hi, actual = incremental(uc)
    aov = biz[(biz.client == x.client) & (biz.market == x.market) & (biz.date >= rs) & (biz.date <= re_)]
    aov = aov.revenue.sum() / aov.orders.sum()
    F += [fact("inc_orders", round(inc), "count", "orders", source="ci_paths.csv (actual - counterfactual)"),
          fact("inc_orders_lo", round(inc_lo), "count", "orders"), fact("inc_orders_hi", round(inc_hi), "count", "orders"),
          fact("inc_revenue", round(inc * aov, -3), "usd", "orders", source="incremental orders x average order value"),
          fact("inc_revenue_lo", round(inc_lo * aov, -3), "usd", "orders"), fact("inc_revenue_hi", round(inc_hi * aov, -3), "usd", "orders"),
          fact("aov", round(aov, 2), "usd", "orders")]
    sp0, cv0, val0, ck0 = platform_kpis(x.client, x.market, x.platform, bs, be)
    sp1, cv1, val1, ck1 = platform_kpis(x.client, x.market, x.platform, rs, re_)
    setting = "7d_click_1d_view"
    if client_key == "client_e":          # the setting changed during the read: CPA on the column that did not change
        val0, val1 = val0 * ck0 / cv0, val1 * ck1 / cv1
        cv0, cv1, setting = ck0, ck1, "7d_click"
    F += [fact("spend_read", round(sp1, -3), "usd", "spend", source="ads_daily"),
          fact("cpa_before", round(sp0 / cv0, 2), "usd", "cpa", window=setting, source="ads_daily spend / conversions"),
          fact("cpa_after", round(sp1 / cv1, 2), "usd", "cpa", window=setting),
          fact("cpa_change", round(sp1 / cv1 / (sp0 / cv0) - 1, 3), "pct", "cpa", window=setting),
          fact("roas_before", round(val0 / sp0, 1), "ratio", "roas", window=setting, source="ads_daily conv_value / spend"),
          fact("roas_after", round(val1 / sp1, 1), "ratio", "roas", window=setting)]
    s = sig[(sig.client == x.client) & (sig.market == x.market) & (sig.platform == x.platform)].set_index("date")
    F += [fact("emq_before", round(s.loc[bs:be, "emq"].mean(), 1), "score", "emq", "health"),
          fact("emq_after", round(s.loc[rs:re_, "emq"].mean(), 1), "score", "emq", "health"),
          fact("event_id_cov", s.loc[rs:re_, "server_events_with_event_id"].sum() / s.loc[rs:re_, "server_events"].sum(), "pct", "event_id", "health"),
          fact("match_before", s.loc[bs:be, "match_rate"].mean(), "pct", "match_rate", "health"),
          fact("match_after", s.loc[rs:re_, "match_rate"].mean(), "pct", "match_rate", "health")]
    if client_key == "client_e":
        w = h["traps"]["window"]
        F += [fact("window_reported_change", w["reported_active_setting_change"], "pct", "reported_conversions", window="7d_click"),
              fact("window_consistent_change", w["consistent_7d_click_change"], "pct", "reported_conversions", window="7d_click"),
              fact("window_business_change", w["business_change"], "pct", "orders"),
              fact("view_share", w["view_share_before"], "pct", "reported_conversions", window="7d_click_1d_view")]
    sheet = {"client": client_key, "use_case_id": uc, "client_label": x.client_label, "use_case": x.use_case,
             "platform": x.platform, "market": x.market, "control_market": x.control_market, "go_live": str(go.date()),
             "ramp_up_days": int(x.ramp_up_days), "read_start": str(rs.date()), "read_end": str(re_.date()),
             "read_weeks": int(x.read_weeks), "pre_weeks": int(x.pre_weeks), "facts": F}
    return sheet


# ------------------------------------------------------------------ drafts (sentence templates)
def d(date):
    return pd.Timestamp(date).strftime("%d %b %Y").lstrip("0")


def draft_impact(S):
    f = {x["id"]: x["value"] for x in S["facts"]}
    a = S["client"] == "client_a"
    noun = "orders" if a else "approved applications"
    t = [f"# Impact report · {S['client_label']} · {S['use_case']} on {S['platform']}",
         f"<!-- SIMULATED -->",
         "## Question",
         f"Did {S['use_case']} on {S['platform']} in {S['market']} bring more {noun}, or only more conversions visible to the platform?",
         "## Answer",
         f"Yes, a modest incremental effect: {noun} rose {pct(f['orders_effect'])} against the {S['control_market']} control "
         f"(95% interval {pct(f['orders_lo'])} to {pct(f['orders_hi'])}), about {f['inc_orders']:,.0f} extra {noun} "
         f"and {usd(f['inc_revenue'])} of revenue over the read. "
         f"{S['platform']}-reported conversions rose much more, {pct(f['reported_effect'])}: most of that is signal recovered, "
         f"which helps bidding but is not extra business on its own.",
         "## Baseline",
         f"{S['pre_weeks']} weeks of weekly {noun} in {S['market']} and {S['control_market']} before go-live on {d(S['go_live'])}, from the client's own system. "
         f"Reported CPA was {usd(f['cpa_before'])} on the {'7-day click + 1-day view' if a else '7-day click'} setting.",
         "## Intervention",
         f"{S['use_case']} on {S['platform']} in {S['market']} only, deduplicated with the pixel on event_id. "
         f"The {S['ramp_up_days']}-day ramp-up (learning phase) is excluded from every comparison. "
         f"{S['control_market']} was not migrated during the read and serves as the control.",
         "## Result",
         f"Read window: {S['read_weeks']} full weeks, {d(S['read_start'])} to {d(S['read_end'])}, fixed before the read.",
         f"- Client {noun}: {pct(f['orders_effect'])} (95% interval {pct(f['orders_lo'])} to {pct(f['orders_hi'])}), "
         f"between {f['inc_orders_lo']:,.0f} and {f['inc_orders_hi']:,.0f} extra {noun}.",
         f"- {S['platform']}-reported conversions, 7-day click: {pct(f['reported_effect'])} (95% interval {pct(f['reported_lo'])} to {pct(f['reported_hi'])}).",
         (f"- Reported CPA moved from {usd(f['cpa_before'])} to {usd(f['cpa_after'])} and reported ROAS from {f['roas_before']:.1f}x to {f['roas_after']:.1f}x: "
          f"platform metrics, they move mostly because more conversions became visible." if a else
          f"- Reported CPA on 7-day click moved from {usd(f['cpa_before'])} to {usd(f['cpa_after'])}: a diagnostic only; "
          f"the success metric for a CRM signal is approved applications."),
         f"[[chart:{S['client']}_ci]]",
         "## Attribution logic",
         f"The model follows the ratio between {S['market']} and {S['control_market']}, which share the calendar, so Ramadan, Eid and sale "
         f"periods cancel out; holidays that hit only one market are modelled. 0 of {f['placebo_n']:.0f} in-time placebos "
         f"(fake go-live dates before the real one) produced an effect this large. Platform conversions are read on 7-day click, "
         f"by click date, on complete weeks only.",
    ]
    if not a:
        t += [f"The attribution setting changed during the read (7-day click + 1-day view to 7-day click, account-wide). "
              f"As reported, conversions dropped {pct(-f['window_reported_change'], 0, False)}; on the unchanged 7-day click column they moved "
              f"{pct(f['window_consistent_change'], 0)}, in line with {noun} ({pct(f['window_business_change'], 0)}) over the same weeks. "
              f"The drop is the window (view-through conversions were {pct(f['view_share'], 0, False)} of the total), not performance."]
    t += ["## Signal health (not business value)",
          f"EMQ {f['emq_before']:.1f}/10 before, {f['emq_after']:.1f}/10 after; match rate {pct(f['match_before'], 0, False)} to {pct(f['match_after'], 0, False)}; "
          f"event_id on {pct(f['event_id_cov'], 0, False)} of server events, so deduplication works.",
          "## Limits",
          f"One market, {S['read_weeks']} weeks: the interval is wide relative to the effect. The control market can drift for reasons of its own. "
          f"The effect is measured on {noun}, not on margin.",
          "## Next step",
          f"Roll out to {S['control_market']} with a staggered start by region and read it as a geo test; keep the attribution setting fixed for the quarter."]
    return "\n\n".join(t)


def draft_onepager(S):
    f = {x["id"]: x["value"] for x in S["facts"]}
    a = S["client"] == "client_a"
    noun = "orders" if a else "approved applications"
    return "\n\n".join([
        f"# Renewal one-pager · {S['client_label']}",
        "<!-- SIMULATED -->",
        f"## What {S['use_case']} on {S['platform']} delivered ({d(S['read_start'])} to {d(S['read_end'])})",
        f"**{pct(f['orders_effect'])} {noun}** against an untouched control market (95% interval {pct(f['orders_lo'])} to {pct(f['orders_hi'])}): "
        f"about {f['inc_orders']:,.0f} extra {noun} in {S['read_weeks']} weeks.",
        f"**{usd(f['inc_revenue'])} of incremental revenue** over the same weeks (between {usd(f['inc_revenue_lo'])} and {usd(f['inc_revenue_hi'])}), "
        "measured in the client's own system.",
        f"**{pct(f['reported_effect'])} {S['platform']}-reported conversions** (7-day click): signal recovered, which the bidding algorithm now learns from. "
        "It is not counted as value above.",
        "## How we know",
        f"Control market {S['control_market']}, ramp-up excluded, read window fixed before go-live, 95% interval, in-time placebos; every number above "
        "is traced to the analysis fact sheet.",
        "## Signal health (not business value)",
        f"EMQ {f['emq_before']:.1f}/10 → {f['emq_after']:.1f}/10; event_id on {pct(f['event_id_cov'], 0, False)} of server events.",
        "## Next quarter we measure",
        f"Roll-out to {S['control_market']} as a geo test (pre-registered before launch: seven test weeks, effect on {noun}, synthetic control); "
        "CRM outcomes sent back to the platform; attribution setting frozen.",
    ])


def draft_case_study(S):
    f = {x["id"]: x["value"] for x in S["facts"]}
    a = S["client"] == "client_a"
    noun = "orders" if a else "approved applications"
    vertical = "retailer" if a else "bank and insurer"
    return "\n\n".join([
        f"# A {vertical} in the Gulf: {pct(f['orders_effect'])} incremental {noun} with {S['use_case']} on {S['platform']}",
        "<!-- SIMULATED -->",
        "## The challenge",
        f"Browser tracking was losing conversions, so {S['platform']} optimised on a partial signal. The team wanted to know what a server-side "
        "signal would change in the business, not only in the platform dashboard.",
        "## What changed",
        f"{S['use_case']} went live in {S['market']} on {d(S['go_live'])}, deduplicated with the pixel on event_id. {S['control_market']} stayed on the pixel.",
        "## Results",
        f"{S['platform']}-reported conversions rose {pct(f['reported_effect'])}. The business result is smaller and is the one that matters: "
        f"{pct(f['orders_effect'])} {noun} against the control market, about {usd(f['inc_revenue'])} of revenue in {S['read_weeks']} weeks.",
        "## How we measured it",
        f"> Baseline: {S['pre_weeks']} weeks of {noun} in both markets. Intervention: {S['market']} only, {S['ramp_up_days']}-day ramp-up excluded. "
        f"Result: {pct(f['orders_effect'])} (95% interval {pct(f['orders_lo'])} to {pct(f['orders_hi'])}) over {S['read_weeks']} weeks fixed in advance. "
        f"Attribution logic: ratio to the control market (shared calendar), in-time placebos, platform figures on 7-day click by click date.",
    ])


# ------------------------------------------------------------------ rendering
CSS = """
@page { size: A4; margin: 14mm 14mm 12mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #0B0B0B; font-size: 10.5pt; line-height: 1.45; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 4px; } h2 { font-size: 12pt; margin: 14px 0 4px; color: #1C5CAB; }
.tag { display: inline-block; background: #FBE9E0; color: #9A3B12; font-weight: 700; font-size: 8pt; letter-spacing: .08em; padding: 2px 8px; border-radius: 4px; margin-bottom: 8px; }
p, li { margin: 3px 0; } ul { padding-left: 18px; margin: 4px 0; }
blockquote { background: #F4F4F2; border-left: 4px solid #2A78D6; margin: 8px 0; padding: 8px 12px; }
blockquote::before { content: "How we measured it"; display: block; font-weight: 700; margin-bottom: 4px; }
img { width: 100%; max-height: 74mm; object-fit: contain; margin: 6px 0; }
.foot { font-size: 7.5pt; color: #898781; border-top: 1px solid #E1E0D9; margin-top: 14px; padding-top: 4px; }
.big { font-size: 11.5pt; }
"""


def md_to_html(md: str, title: str, imgdir: str) -> str:
    out, ul = [], False
    for block in md.split("\n\n"):
        b = block.strip()
        if not b or b.startswith("<!--"):
            continue
        b_html = html.escape(b, quote=False)
        b_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", b_html)
        if b.startswith("[[chart:"):
            out.append(f'<img src="{imgdir}/{b[8:-2]}.png"/>')
        elif b.startswith("# "):
            out.append(f"<h1>{b_html[2:]}</h1><div class='tag'>SIMULATED</div>")
        elif b.startswith("## "):
            out.append(f"<h2>{b_html[3:]}</h2>")
        elif b.startswith("&gt; "):
            out.append(f"<blockquote>{b_html[5:]}</blockquote>")
        elif b.startswith("- "):
            items = "".join(f"<li>{i[2:]}</li>" for i in b_html.split("\n"))
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p class='{'big' if '<b>' in b_html else ''}'>{b_html}</p>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
            f"<style>{CSS}</style></head><body>{''.join(out)}<div class='foot'>{FOOT}</div></body></html>")


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for key in ("client_a", "client_e"):
        folder = DELIV / key
        folder.mkdir(parents=True, exist_ok=True)
        S = facts_for(key)
        (folder / "facts.json").write_text(json.dumps(S, indent=1, default=str), encoding="utf-8")
        uc = S["use_case_id"]
        charts.ci_chart(uc, "business", f"{key}_ci",
                        title=f"{'Orders' if key == 'client_a' else 'Approved applications'}, {S['market']}: actual vs counterfactual",
                        figsize=(6.4, 2.8))
        for name, fn in (("impact_report", draft_impact), ("renewal_onepager", draft_onepager), ("case_study", draft_case_study)):
            text = llm_client.rewrite(fn(S))
            (folder / f"{name}.md").write_text(text, encoding="utf-8")
            res = check_numbers.check(text, S)
            bad = [r for r in res if not r.ok]
            print(f"{key}/{name}: {len(res)} numbers checked, {len(bad)} rejected")
            for b in bad:
                print("   REJECTED", b.raw, b.message, "|", b.sentence[:100])
            if bad:
                continue                                  # not rendered: an untraceable number blocks the deliverable
            page = folder / f"{name}.html"
            page.write_text(md_to_html(text, f"{S['client_label']} {name.replace('_', ' ')}", "../../docs/img"), encoding="utf-8")
            print_pdf(page, folder / f"{name}.pdf", f"{S['client_label']} - {name.replace('_', ' ')} (simulated)")


if __name__ == "__main__":
    main()

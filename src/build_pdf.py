"""Build the 8-page PDF report: charts (src/charts.py) -> HTML pages (16:9) -> PDF with headless Edge.

Every number on the pages is read from data/output, data/processed or the deliverables' fact sheets.
    python src/build_pdf.py
Outputs: docs/report.html, docs/Datahash_Measurement_CaseStudy.pdf
"""
import json
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

import charts
from pdf_utils import print_pdf

ROOT = Path(__file__).resolve().parents[1]
DOCS, OUTD, PROC = ROOT / "docs", ROOT / "data" / "output", ROOT / "data" / "processed"
COLLECTED = "18 Nov 2026"
PDF_NAME = "Datahash_Measurement_CaseStudy.pdf"
DISCLAIMER = "Independent case study based on public data · not affiliated with or endorsed by Datahash"
# The AI-use note is written once, in README.md (Methods), and reused here verbatim.
AI_NOTE = next(l[2:].strip() for l in (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
               if l.startswith("- AI-assisted workflow:"))


def p(x, d=0, sign=True):
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def load():
    f = {"h": charts.head(), "reads": pd.read_csv(OUTD / "use_case_reads.csv").set_index("use_case_id"),
         "det": pd.read_csv(OUTD / "detection.csv"), "facts": pd.read_csv(PROC / "datahash_facts.csv").set_index("fact"),
         "grid": pd.read_csv(PROC / "case_study_grid.csv"), "power": pd.read_csv(OUTD / "criteo_power.csv"),
         "a": {x["id"]: x["value"] for x in json.loads((ROOT / "deliverables" / "client_a" / "facts.json").read_text(encoding="utf-8"))["facts"]},
         "e": {x["id"]: x["value"] for x in json.loads((ROOT / "deliverables" / "client_e" / "facts.json").read_text(encoding="utf-8"))["facts"]}}
    return f


# ------------------------------------------------------------------ layout helpers
def page(n, title, subtitle, tag, body, sources):
    tag_html = f'<div class="tag tag-{tag.lower().split()[0]}">{tag}</div>'
    return f"""
<section class="page">
  <header><div><h1>{title}</h1><p class="sub">{subtitle}</p></div>{tag_html}</header>
  <main>{body}</main>
  <footer><span>{sources} · collected {COLLECTED}</span><span>{DISCLAIMER}</span><span>{n}</span></footer>
</section>"""


def card(inner, cls=""):
    return f'<div class="card {cls}">{inner}</div>'


def img(src, cap=""):
    return f'<figure><img src="{src}"/>{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'


def tile(label, value, text):
    return card(f'<div class="label">{label}</div><div class="big">{value}</div><p>{text}</p>', "tile")


# ------------------------------------------------------------------ pages
def p0(f, ch):
    h, R, c, a = f["h"], f["reads"], f["h"]["criteo"], f["a"]
    g = h["grid"]
    tiles = "".join([
        tile("PUBLIC DATA · PAGE 2", f"×{c['naive_ratio']:.0f}",
             f"what 'exposed vs unexposed' shows in Criteo's randomised test. The randomised effect on exposed users is "
             f"{p(c['cace_rel'])}, and {p(c['itt_rel'])} for the whole eligible group."),
        tile("SIMULATED · PAGE 5", f"{p(R.loc['UC1', 'reported_effect'])} → {p(R.loc['UC1', 'business_effect'], 1)}",
             f"Web CAPI on Meta: platform-reported conversions vs client orders against a control market "
             f"(95% {p(R.loc['UC1', 'business_lo'], 1)} to {p(R.loc['UC1', 'business_hi'], 1)})."),
        tile("SIMULATED · PAGE 4", f"{h['detected']} / {h['events']}",
             f"planted traps caught with one set of rules: broken dedup ({p(R.loc['UC2', 'reported_effect'])} of duplicates), "
             f"Ramadan, a window change, the click-date lag, an EMQ jump with no value."),
        tile("PUBLIC DATA · PAGE 1", f"{g['quantified_outcome']} / {f['h']['grid_n']}",
             f"Datahash case studies with a quantified outcome. A shared template would add the baseline "
             f"(in {g['baseline_level_shown']}), the window (0) and an interval (0)."),
    ])
    q = card(f"""<h2>Business questions</h2><ol class="qs">
      <li><b>Proof</b> What does Datahash publish, and what would a shared evidence template add? <span class="pg">p.1</span></li>
      <li><b>Incrementality</b> How far is "exposed" from "incremental" in a real randomised test? <span class="pg">p.2</span></li>
      <li><b>Playbook</b> What should each use case move, on which platform, and how do we prove it? <span class="pg">p.3</span></li>
      <li><b>Skepticism</b> Which great-looking uplifts break under a proper read? <span class="pg">p.4</span></li>
      <li><b>Value</b> How big is the real effect, how sure are we, and how does it reach a renewal? <span class="pg">p.5–6</span></li></ol>
      <p class="reco"><b>Recommendations:</b> (1) one evidence template for every analysis and story: baseline, intervention,
      result with an interval, attribution logic, scored by a 14-point checklist; (2) freeze the read plan before go-live:
      ramp-up excluded, attribution setting fixed, read on complete lag weeks; (3) report <i>signal recovered</i> and
      <i>incremental value</i> separately, never EMQ as value; (4) make staggered roll-outs and geo tests the default design,
      platform lift studies when they have the power; (5) automate the repetitive 80%: SQL checks for dedup, settings and lag,
      a causal-impact runner, and report drafts whose every number is checked against the analysis.</p>""", "wide")
    m = card("""<h2>Data &amp; methods</h2>
      <p><b class="k">PUBLIC</b> Datahash's site and its 16 published case studies (coded, not named); the Criteo Uplift
      dataset v2.1: a real randomised ad-incrementality test of ~14 million users (CC BY-NC-SA 4.0, aggregates only);
      platform documentation.</p>
      <p><b class="k">SIMULATED</b> six fictional clients in KSA, UAE and India, four platforms, 22 months, with eight
      measurement traps planted and a hidden truth. Realistic patterns, <u>not</u> Datahash's or any client's data.</p>
      <p><b class="k">METHODS</b> SQL (DuckDB), intention-to-treat and Wald estimators, power, causal impact (structural
      time series) with in-time placebos, synthetic control with placebo groups, a number checker for client texts.</p>""", "wide")
    work = card("""<h2>The job posting, page by page</h2><ul class="small">
      <li><b>Measure each first-party use case per platform</b> → p.3 playbook; p.5 reads with intervals.</li>
      <li><b>Baselines, control metrics, ramp-up exclusion, seasonality, causal impact, geo tests, lift studies</b> → p.2, p.4, p.5.</li>
      <li><b>Attribution settings, conversion vs click date, dedup, EMQ</b> → p.4 (each one breaks an uplift).</li>
      <li><b>Impact reports, renewal one-pagers, case studies, partner proof</b> → p.6 and <i>deliverables/</i>.</li>
      <li><b>Tracker, templates, checklist; automate the 80%</b> → workbook, <i>docs/</i>, <i>src/check_numbers.py</i>.</li></ul>""")
    how = card("""<h3>How to read this report</h3><p><b>Titles</b> state the conclusion. &nbsp; <b>Tags</b> PUBLIC DATA / SIMULATED
      mark where the data come from. &nbsp; <b>Whiskers and bands</b> are 95% intervals. &nbsp; <b>Grey</b> = what the platform
      reports or the control; <b>blue</b> = what the business gets; <b>red</b> = a trap. &nbsp; Code, SQL, the notebook, the
      workbook, an interactive dashboard and the client deliverables are in the repository.</p>""", "how")
    body = f'<div class="grid4">{tiles}</div><div class="g0">{q}<div class="stack">{m}{work}</div></div>{how}'
    return page(0, "Datahash: proving what first-party signals are worth, without fooling ourselves",
                "Public data on Datahash and a real randomised ad-incrementality test (Criteo), plus a simulated, calibrated multi-client "
                "panel, turned into a measurement playbook per use case, causal-impact and geo-experiment reads, client-ready impact "
                "reports and a shared evidence standard.", "OVERVIEW", body, "Sources: data/SOURCES.md")


def p1(f, ch):
    F, g, n = f["facts"].as_stated_by_datahash, f["h"]["grid"], f["h"]["grid_n"]
    facts = card(f"""<h2>What Datahash states (datahash.com, read {COLLECTED})</h2><ul class="facts">
      <li>"{F['positioning']}". "{F['founded']}", "{F['brands_in_production']}", "{F['countries']}".</li>
      <li>Products: "{F['products']}".</li>
      <li>Offerings: "{F['offerings']}"; recommended start: "{F['starting_point']}".</li>
      <li>Destinations: "{F['native_destinations']}"; "{F['partner_verified']}"; Google: "{F['google_partnership']}"; Google Tag Gateway listed.</li>
      <li>Defaults that matter for measurement: "{F['dedup_default']}"; "{F['hashing']}"; "{F['setup_time']}", while "{F['crm_offline_time']}".</li>
      </ul><p class="note">All quotes as stated by Datahash on its public pages; figures not verified independently.</p>""")
    read = card(f"""<h2>What a shared evidence template would let each story show</h2>
      <p>The {n} published case studies all name the use case and the platform, and {g['quantified_outcome']} give a figure.
      Several already go further than most of the industry: {g['other_changes_disclosed']} disclose other changes made at the same
      time, {g['offline_or_crm_outcome']} report offline or CRM outcomes, {g['labelled_measured_not_incremental']} label the figure as
      <i>measured</i> or <i>attributed</i>.</p>
      <p>The same template, applied to every story, would add what turns a strong number into a proof a CMO can reuse and a
      partner programme can audit: the <b>baseline level</b> ({g['baseline_level_shown']} of {n} today), the <b>before/after window</b>
      ({g['period_stated']}), a <b>comparison group</b> ({g['concurrent_comparison']}), the <b>attribution setting</b> (0; one names an
      optimisation window), the <b>ramp-up treatment</b> ({g['ramp_up_excluded']}) and an <b>interval</b> ({g['interval_or_significance']}).</p>
      <p>That template is exactly the job's "tracker, templates and quality checklist": <i>docs/EVIDENCE_STANDARD.md</i> and the
      <i>Evidence checklist</i> tab of the workbook.</p>""")
    body = f"""<div class="grid-2-1"><div class="stack">{facts}{read}</div><div class="stack">
      {card(img(ch['evidence_grid'], 'Coded by keyword rules on each page body (testimonials removed), checked by hand. Brands and headline figures are not reproduced.'), 'tall')}
      {card(img(ch['grid_mix']), 'auto')}</div></div>"""
    return page(1, f"Datahash and the evidence its stories need: {g['quantified_outcome']} of {n} case studies give a number, a template would add how it was measured",
                "Facts as stated by Datahash and an anonymised grid of what each of its 16 published case studies shows: use case, platform, outcome, window, baseline, comparison, interval.",
                "PUBLIC DATA", body, "datahash.com (home, products, offerings, partners, glossary, docs, contact, 16 case studies)")


def p2(f, ch):
    c, pw = f["h"]["criteo"], f["power"].set_index("relative_lift")
    txt = card(f"""<h2>What the randomised test says</h2><ul class="facts">
      <li><b>{c['users'] / 1e6:.1f} million users</b>, {c['treated_share']:.0%} eligible to see ads, the rest held out at random.</li>
      <li><b>Intention to treat:</b> conversion rate {c['cr_control'] * 100:.3f}% → {c['cr_treated'] * 100:.3f}%, a lift of
      <b>{p(c['itt_rel'])}</b> (95% {p(c['itt_rel_lo'])} to {p(c['itt_rel_hi'])}). Visits {p(c['visit_rel'])}.</li>
      <li><b>Only {c['exposure_rate']:.1%} of eligible users were reached.</b> Wald estimator: each reached user gained
      {c['cace'] * 100:.1f} points of conversion probability ({c['counterfactual_exposed']:.1%} → {c['cr_exposed']:.1%}), {p(c['cace_rel'])}.</li>
      <li><b>The trap:</b> exposed vs unexposed users convert {c['naive_ratio']:.0f} times as much: about
      {c['naive_rel'] / c['cace_rel']:.0f} times the real effect. About {c['incremental_share_exposed']:.0%} of exposed users' conversions
      ({c['incremental_conversions']:,.0f} of {c['exposed_conversions']:,}) were caused by the ads.</li>
      <li><b>Why:</b> in the two top deciles of a pre-treatment feature, {c['exposure_top20']:.0%} are exposed vs
      {c['exposure_rest']:.0%} elsewhere, and their conversion rate <i>without ads</i> is {c['control_cr_top20'] / c['control_cr_rest']:.0f} times higher.</li>
      </ul>""")
    lesson = card(f"""<h2>What it means for a CAPI renewal</h2><p>Platform-credited conversions mix what ads caused with
      what would have happened anyway, and a server-side signal raises <i>both</i>. Only a randomised or controlled comparison
      separates them. Power matters: at this {c['cr_control'] * 100:.2f}% base rate an 85/15 test needs about
      {pw.loc[0.10, 'control_users_85_15_split'] / 1e3:,.0f}k control users for a 10% lift and
      {pw.loc[0.05, 'control_users_85_15_split'] / 1e6:.1f} million for 5%: most single-client CAPI effects (2–6%) need a geo test
      or a staggered roll-out instead.</p>""")
    body = f"""<div class="grid3">{card(img(ch['criteo_rates']))}{card(img(ch['criteo_naive']))}{card(img(ch['criteo_selection']))}</div>
      <div class="grid-2-1 low">{txt}{lesson}</div>"""
    return page(2, f"Exposed is not incremental: in a real randomised test, 'exposed vs unexposed' overstates the effect about {c['naive_rel'] / c['cace_rel']:.0f}-fold",
                "Criteo Uplift Prediction Dataset v2.1: intention-to-treat lift with an interval, the effect on exposed users, the selection behind the naive comparison, and the power a lift test needs.",
                "PUBLIC DATA", body, "Criteo Uplift v2.1, huggingface.co/datasets/criteo/criteo-uplift, CC BY-NC-SA 4.0, aggregates only")


def p3(f, ch):
    rows = [
        ("Web CAPI<br><span class='pl'>Meta · Snapchat · TikTok</span>", "Reported conversions, then client orders", "Orders in control market; platforms without CAPI",
         "event_id coverage, dedup rate, EMQ / EQS", "Market split + causal impact; Conversion Lift", "7–10 days", "Missing event_id: +25–40% of duplicates"),
        ("App CAPI<br><span class='pl'>Meta · Snapchat · TikTok</span>", "App events received, then subscriptions", "Web orders; un-migrated app platform",
         "Dedup vs SDK, EMQ, match rate", "Android vs iOS split; SKAN read apart", "7 days", "EMQ jump sold as value"),
        ("CRM Conversions API<br><span class='pl'>Meta · Google · Snapchat</span>", "Qualified outcomes, cost per qualified outcome", "Raw lead volume may fall (expected)",
         "Upload freshness, match rate", "Market split, 8+ weeks (CRM lag)", "14 days", "Window change or Ramadan in the read"),
        ("Google Tag Gateway<br><span class='pl'>Google Ads (+ enhanced conv.)</span>", "Tag hits, observed conversions, then bookings", "Other platforms; control regions",
         "First-party tag share, EC match rate", "Geo test + synthetic control, power planned", "7 days", "Reading by click date at the end"),
        ("GA4 server-side<br><span class='pl'>GA4</span>", "Sessions, returning-user share, unassigned share", "Client orders (must not move)",
         "GA4 purchases per client order", "Before/after on ratios to orders", "7 days", "'New users fell': it is the fix"),
    ]
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    table = card(f"""<table class="pb"><tr><th>Use case</th><th>Should move</th><th>Should not move (controls)</th><th>Signal health, kept apart</th>
      <th>Method</th><th>Ramp-up</th><th>Main trap</th></tr>{trs}</table>""", "auto")
    steps = ["<b>1 Plan</b>KPI, baseline, ramp-up, read window, control and minimum effect, frozen before go-live",
             "<b>2 Check the signal</b>event_id coverage, dedup, setting changes, lag completeness (SQL 03–04)",
             "<b>3 Read</b>causal impact vs control market, or geo test, or platform lift; 95% interval",
             "<b>4 Try to break it</b>placebos, season, window, date basis, persistence",
             "<b>5 Report</b>signal recovered vs incremental value; every number checked; renewal one-pager"]
    flow = card('<div class="flow">' + "".join(f"<div>{s}</div>" for s in steps) + "</div>", "auto")
    G, gen = f["h"]["traps"]["ga4"], f["h"]["traps"]
    ga = card(f"""<h3>GA4 server-side, read the right way (SIMULATED client A)</h3><p>Raw GA4 counts move with the season; read them per
      client order. After the switch: sessions per order {p(G['sessions_per_order_change'])}, GA4 purchases per order
      {p(G['ga4_purchases_per_order_change'])}, share of new users {G['new_share_before']:.0%} → {G['new_share_after']:.0%} (server-set cookies last longer),
      unassigned sessions {G['unassigned_before']:.1%} → {G['unassigned_after']:.1%}. Client orders: no change attributable to it.
      All of this is measurement, not marketing performance.</p>""")
    when = card("""<h3>Which method when</h3><table class="small"><tr><th>Situation</th><th>Method</th></tr>
      <tr><td>Live in one market, another not yet</td><td>Causal impact on the treated/control ratio + in-time placebos</td></tr>
      <tr><td>Roll-out can be planned by region</td><td>Geo test, synthetic control, placebo groups, power first</td></tr>
      <tr><td>Enough volume for a holdout</td><td>Platform Conversion Lift (user-level randomisation)</td></tr>
      <tr><td>None of the above</td><td>Pre/post + control metric + last year, labelled "not causal"</td></tr></table>""")
    body = flow + table + f'<div class="grid2 full">{when}{ga}</div>'
    return page(3, "What each use case should move: one playbook, five use cases, four platforms, and the controls that keep it honest",
                "For each first-party use case: the metrics that should move, the ones that must not, the signal-health metrics kept out of value, the method, the ramp-up to exclude and the trap to check first.",
                "PLAYBOOK", body, "docs/MEASUREMENT_PLAYBOOK.md; platform documentation (links in docs/PLATFORM_LIFT_GUIDE.md)")


def p4(f, ch):
    R, t = f["reads"], f["h"]["traps"]
    w, lag, d = t["window"], t["lag"], t["dedup"]
    s = R.loc["UC4"]
    cal = pd.read_parquet(PROC / "calendar.parquet")
    ram = cal[(cal.event == "Ramadan") & (cal.date >= pd.Timestamp(s.go_live))].date.min()
    days_before = (ram - pd.Timestamp(s.go_live)).days
    cap = [
        f"<b>Broken dedup.</b> Server events carried no event_id: TikTok conversions {p(R.loc['UC2', 'reported_effect'])} vs the KSA control "
        f"(per client order {p(d['inflation_vs_before'])}), client orders {p(R.loc['UC2', 'business_effect'], 1)}. Flagged by SQL in week one; normal again after the fix.",
        f"<b>Season.</b> CRM API went live {days_before} days before Ramadan: naive {p(s.business_naive)}. Against the UAE control {p(s.business_effect, 1)}; "
        f"in the 8 weeks after Eid {p(s.persistence_effect, 1)} (95% {p(s.persistence_lo, 1)} to {p(s.persistence_hi, 1)}). Not retained.",
        f"<b>Window change.</b> 7-day click + 1-day view → 7-day click: reported {p(w['reported_active_setting_change'])}; same-setting column "
        f"{p(w['consistent_7d_click_change'])}, client applications {p(w['business_change'])}. The drop is the {w['view_share_before']:.0%} of view-through.",
        f"<b>Click date.</b> By click date the last 3 weeks fall {p(lag['click_date_change_last3w'], 1)}, by conversion date {p(lag['conv_date_change_last3w'], 1)}. "
        f"Travel on Google Ads: the last 7 days show {p(lag['travel_google_click_vs_conv_last7d'])} by click date.",
    ]
    body = f"""<div class="grid2x2 full">
      {card(img(ch['trap_dedup'], cap[0]))}{card(img(ch['trap_season'], cap[1]))}
      {card(img(ch['trap_window'], cap[2]))}{card(img(ch['trap_lag'], cap[3]))}</div>
      {card(f'''<p class="small"><b>Ramp-up</b> (client A): the first week after go-live reads {p(t['ramp']['ramp_days_effect']['effect'])} on Meta conversions,
      the steady weeks {p(t['ramp']['without_ramp_4w']['effect'])}; a 4-week read that keeps the learning weeks gives {p(t['ramp']['with_ramp_4w']['effect'])}.
      <b>EMQ</b> (client D): {t['emq']['emq_before']:.1f} → {t['emq']['emq_after']:.1f}, match rate {t['emq']['match_before']:.0%} → {t['emq']['match_after']:.0%},
      subscriptions {p(t['emq']['business_effect'], 1)} (95% {p(t['emq']['business_lo'], 1)} to {p(t['emq']['business_hi'], 1)}): a better signal, not yet value.</p>''', 'auto')}"""
    return page(4, "Breaking a great-looking uplift: duplicates, Ramadan, a window change and an unfinished month each fake a result",
                "Four traps planted in the simulated panel, each caught by a rule written before the read: event_id coverage, a control market plus a persistence read, a fixed attribution setting, complete lag weeks.",
                "SIMULATED", body, "sql/03_dedup_check.sql, sql/04_attribution_changes.sql, src/analysis.py")


def p5(f, ch):
    R, g = f["reads"], f["h"]["geo"]
    a = R.loc["UC1"]
    txt = card(f"""<h2>Causal impact, in plain words</h2><p>KSA and UAE share Ramadan, Eid and sale periods, so the model follows the
      <b>ratio</b> of weekly orders between them (national days, which hit only one market, are a regressor). Fitted on
      {a.pre_weeks:.0f} weeks before go-live, it projects 1,000 "no change" paths; the ramp-up weeks are skipped.</p>
      <p><b>Client A, Web CAPI on Meta:</b> orders {p(a.business_effect, 1)} (95% {p(a.business_lo, 1)} to {p(a.business_hi, 1)}),
      platform-reported conversions {p(a.reported_effect, 1)}. {a.business_placebo_n:.0f} in-time placebos (fake go-live dates): none as large.
      Most of the reported rise is <b>signal recovered</b>, worth having because bidding learns from it, but not extra business.</p>""")
    geo = card(f"""<h2>Geo test, planned before launch</h2><p>Client F: 6 treated regions bid on the Google Tag Gateway conversion
      action, 18 controls keep the old one. Power from the pre-period noise: a 7-week test detects {g['mde_by_weeks']['7']:.1%}
      (4 weeks: {g['mde_by_weeks']['4']:.1%}).</p><p><b>Result:</b> bookings {p(g['effect'], 1)} (95% {p(g['lo'], 1)} to {p(g['hi'], 1)}),
      no placebo group as large; in-time placebo {p(g['placebo_in_time'], 1)}. A naive pre/post would claim {p(g['naive_prepost'])} (summer travel),
      a simple difference-in-differences {p(g['did'], 1)}: the weighted control matters.</p>""")
    body = f"""<div class="grid2 full">{card(img(ch['ci_chart']))}{card(img(ch['geo_chart']))}</div>
      <div class="grid3 short">{txt}{geo}{card(img(ch['placebo_chart']))}</div>"""
    return page(5, f"Causal impact and geo tests: Web CAPI added {p(a.business_effect, 1)} orders, not {p(a.reported_effect)}; the tag gateway added {p(g['effect'], 1)} bookings",
                "Structural time-series reads against a control market with in-time placebos, and a synthetic-control geo test with 300 placebo groups, all with 95% intervals.",
                "SIMULATED", body, "src/analysis.py (statsmodels UnobservedComponents, scipy SLSQP), sql/05_geo.sql")


def p6(f, ch):
    a, e = f["a"], f["e"]
    one = card(f"""<h2>Renewal one-pager, client A (excerpt)</h2>
      <p class="kpi"><b>{p(a['orders_effect'], 1)} orders</b> vs an untouched control (95% {p(a['orders_lo'], 1)} to {p(a['orders_hi'], 1)})</p>
      <p class="kpi"><b>${a['inc_revenue'] / 1e3:,.0f}k incremental revenue</b> in 7 weeks, from the client's order system</p>
      <p class="kpi"><b>{p(a['reported_effect'], 1)} Meta-reported conversions</b>: signal recovered, not counted as value</p>
      <p class="note">Signal health, in its own box: EMQ {a['emq_before']:.1f} → {a['emq_after']:.1f}; event_id on {a['event_id_cov']:.0%} of server events.
      Next quarter: UAE roll-out as a geo test. Each number is checked by <i>src/check_numbers.py</i> against the fact sheet.</p>""")
    auto = card(f"""<h2>What is automated (the repetitive 80%)</h2><ul class="small">
      <li><b>SQL checks</b>: dedup health, setting changes, click vs conversion date, pre/post with control (DuckDB).</li>
      <li><b>One function per read</b>: causal impact with placebos; synthetic control with placebo groups.</li>
      <li><b>Report drafts</b> from a fact sheet (sentence templates; an optional LLM may rephrase), then the
      <b>number checker</b> rejects any figure it cannot trace: 8 trap tests (ROAS/CPA swapped, % vs points, wrong window,
      health metric as value, wrong sign).</li>
      <li><b>Client E</b>: the account changed its attribution setting mid-read; the report reads CPA on 7-day click
      (${e['cpa_before']:,.0f} → ${e['cpa_after']:,.0f}) and approved applications {p(e['orders_effect'], 1)}.</li></ul>""")
    ck = card("""<h2>Quality checklist (14 points, scored in the workbook)</h2><p class="small">Read plan frozen · ramp-up excluded ·
      control · control metric · same attribution setting · date basis · event_id coverage · seasonality · interval + placebo ·
      business outcome · health kept apart · every number traced · other changes disclosed · limits and next step.
      In the tracker, the broken-dedup read and the GA4 read (no control, no interval) are the two that are not publishable.</p>""")
    body = f"""<div class="g6 full">{card(img(ch['portfolio']))}{card(img(ch['emq_chart']))}</div>
      <div class="grid3 low">{one}{auto}{ck}</div>"""
    return page(6, "From analysis to renewal: report the value with its interval, the signal on its own, and let no unchecked number out",
                "Portfolio of the eight reads with the same rules, an EMQ gain that is not value, and the client deliverables: impact report, renewal one-pager and case study with 'How we measured it'.",
                "SIMULATED", body, "deliverables/, excel/analysis_tracker.xlsx, src/report_writer.py, src/check_numbers.py")


def p7(f, ch):
    det = f["det"]
    trs = "".join(f"<tr><td>{r.event}</td><td>{r.trap}</td><td>{r.check}</td><td>{'yes' if r.detected else 'no'}</td>"
                  f"<td>{'' if pd.isna(r.interval_covers_truth) else ('yes' if r.interval_covers_truth in (True, 'True') else 'no')}</td></tr>"
                  for r in det.itertuples())
    src = card(f"""<h2>Sources, licences, dates</h2><table class="small">
      <tr><th>Data</th><th>Source</th><th>Licence / terms</th></tr>
      <tr><td>Datahash pages and 16 case studies</td><td>datahash.com, read {COLLECTED}, robots.txt respected, 1 request / 3 s</td><td>Public pages; quotes as stated by Datahash; brands not named</td></tr>
      <tr><td>Criteo Uplift v2.1 (~14M rows)</td><td>huggingface.co/datasets/criteo/criteo-uplift</td><td>CC BY-NC-SA 4.0: non-commercial, attribution; aggregates only</td></tr>
      <tr><td>Platform documentation</td><td>Meta, Google, Snapchat, TikTok developer and help pages</td><td>Cited and summarised</td></tr>
      <tr><td>Simulated panel</td><td>src/simulate.py, seed 42, 1 Jan 2025 – 31 Oct 2026</td><td>Fictional; assumptions in data/ASSUMPTIONS.md</td></tr></table>""")
    dt = card(f"""<h2>Detection of the planted traps</h2><table class="small"><tr><th>#</th><th>Trap</th><th>Rule-based check</th><th>Caught</th>
      <th>Interval covers truth</th></tr>{trs}</table><p class="note">The one interval that misses (client C, Ramadan read, true effect 0)
      is why the persistence rule exists; a 95% interval should miss about one time in twenty.</p>""")
    lim = card("""<h2>Limits</h2><ul class="small">
      <li>The panel is simulated: it shows the method and the traps, not Datahash's results or any client's.</li>
      <li>The case-study grid codes what is <i>published</i>, not what was measured: the underlying analyses may hold more.</li>
      <li>Criteo is display retargeting in one period; its lift size does not transfer to CAPI, only the logic does.</li>
      <li>Causal impact assumes the control market is untouched and follows the same calendar; geo tests assume no spill-over
      between regions. Both are checked with placebos, not proven.</li>
      <li>No access to Ads Manager, Google Ads or GA4 accounts: platform behaviour comes from public documentation.</li></ul>""")
    ai = card(f"""<h2>Methods note</h2><p class="small">Reproduce: <code>python src/fetch_public.py</code>, <code>parse_public.py</code>,
      <code>extract_criteo.py</code>, <code>simulate.py</code>, <code>run_sql.py</code>, <code>analysis.py</code>, <code>report_writer.py</code>,
      <code>pytest</code>, <code>build_notebook.py</code>, <code>build_excel.py</code>, <code>build_dashboard.py</code>, <code>build_pdf.py</code>.
      Everything runs without any API key.</p><p class="small"><b>{AI_NOTE}</b></p>""")
    nxt = card("""<h2>With real accounts, the next steps</h2><ul class="small">
      <li>Pull Ads Manager, Google Ads, Snapchat and TikTok reports by API with both date bases and the attribution-setting columns.</li>
      <li>Land the GA4 BigQuery export next to the client's orders; run the same SQL checks every week.</li>
      <li>Pre-register each read in the tracker at go-live; publish only what passes the checklist.</li>
      <li>Plan the first real geo test with the power table; propose a platform lift study where volume allows.</li></ul>""")
    body = f'<div class="grid2 full"><div class="stack">{src}{lim}{nxt}</div><div class="stack">{dt}{ai}</div></div>'
    return page(7, "Methods, limits and sources: what is public, what is simulated, and what each number rests on",
                "Data sources and licences, the detection score of the eight planted traps, the limits of the study and how to reproduce it.",
                "METHODS", body, "data/SOURCES.md, data/ASSUMPTIONS.md")


CSS = """
@page { size: 1600px 900px; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #0B0B0B; background: #F4F4F2; }
.page { width: 1600px; height: 900px; padding: 30px 44px 22px; display: flex; flex-direction: column; page-break-after: always; overflow: hidden; background: #F4F4F2; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 30px; }
h1 { font-size: 26px; margin: 0 0 6px; font-weight: 700; line-height: 1.15; max-width: 1330px; }
.sub { margin: 0; color: #52514E; font-size: 14.5px; max-width: 1330px; }
.tag { font-size: 12px; font-weight: 700; letter-spacing: .08em; padding: 5px 10px; border-radius: 4px; white-space: nowrap; color: #52514E; }
.tag-public { background: #E3EEFB; color: #1C5CAB; } .tag-simulated { background: #FBE9E0; color: #9A3B12; }
.tag-overview, .tag-playbook, .tag-methods { background: #E9E8E2; color: #52514E; }
main { flex: 1; display: flex; flex-direction: column; gap: 12px; margin-top: 14px; min-height: 0; }
footer { display: flex; justify-content: space-between; gap: 20px; font-size: 11px; color: #898781; margin-top: 10px; }
.card { background: #FCFCFB; border: 1px solid #E1E0D9; border-radius: 8px; padding: 12px 16px; min-height: 0; overflow: hidden; }
.card h2 { font-size: 16px; margin: 0 0 6px; } .card h3 { font-size: 14px; margin: 0 0 4px; }
.card p, .card li { font-size: 13.5px; line-height: 1.4; margin: 3px 0; color: #2B2A27; }
.card ul, .card ol { padding-left: 18px; margin: 4px 0; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.grid2x2 { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 12px; min-height: 0; }
.full { flex: 1 !important; } .short { flex: 0.75 !important; } .low { flex: 0.62 !important; }
.g6 { display: grid; grid-template-columns: 1.35fr 1fr; gap: 12px; min-height: 0; }
.g0 { display: grid; grid-template-columns: 1.25fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid-2-1 { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; flex: 1.25; min-height: 0; }
figure { margin: 0; height: 100%; display: flex; flex-direction: column; }
figure img { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
figcaption { font-size: 12px; color: #2B2A27; margin-top: 3px; line-height: 1.35; }
.tile .label { font-size: 12px; font-weight: 700; color: #52514E; letter-spacing: .04em; }
.tile .big { font-size: 42px; font-weight: 700; margin: 2px 0; color: #0B0B0B; }
.tile p { font-size: 13.5px; color: #52514E; }
.stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; } .stack .card { flex: 1; }
.auto { flex: 0 0 auto !important; } .tall { flex: 1.6 !important; }
.qs li { font-size: 15px !important; margin: 5px 0; } .qs b { color: #2A78D6; margin-right: 6px; }
.pg { color: #898781; font-size: 12px; } .reco { font-size: 14px !important; }
.k { color: #52514E; font-size: 12.5px; letter-spacing: .05em; margin-right: 4px; }
.how p { font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; color: #52514E; font-weight: 600; border-bottom: 1px solid #E1E0D9; padding: 4px 6px; }
td { border-bottom: 1px solid #EFEEE9; padding: 4px 6px; vertical-align: top; }
table.pb td { font-size: 14px; padding: 9px 8px; } table.pb td:first-child { font-weight: 600; width: 15%; }
.pl { font-weight: 400; color: #52514E; font-size: 12px; }
table.small, .small, .small li, .small td, .small th { font-size: 12.5px !important; }
.note { font-size: 11.5px !important; color: #6B6A65 !important; }
.facts li { font-size: 13.5px !important; margin: 5px 0; }
.kpi { font-size: 15px !important; margin: 6px 0 !important; } .kpi b { color: #1C5CAB; }
.flow { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.flow div { background: #E3EEFB; border-radius: 6px; padding: 8px 10px; font-size: 12.5px; color: #2B2A27; position: relative; }
.flow b { display: block; color: #1C5CAB; font-size: 14px; margin-bottom: 2px; }
code { font-size: 12px; background: #F4F4F2; padding: 0 3px; border-radius: 3px; }
"""


def build_html() -> Path:
    ch = charts.build_all()
    f = load()
    pages = [p0, p1, p2, p3, p4, p5, p6, p7]
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Datahash measurement case study</title><style>{CSS}</style></head><body>
{''.join(pg(f, ch) for pg in pages)}
</body></html>"""
    out = DOCS / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def main():
    html = build_html()
    pdf = print_pdf(html, DOCS / PDF_NAME, "Datahash - measurement case study")
    print("written", html.relative_to(ROOT), pdf.relative_to(ROOT), len(PdfReader(str(pdf)).pages), "pages")


if __name__ == "__main__":
    main()

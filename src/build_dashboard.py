"""Self-contained HTML dashboard (Plotly, no server): dashboard/measurement_dashboard.html

Tabs: Portfolio (reported vs incremental, all use cases) · Use case read (weekly actual vs counterfactual, ramp-up,
interval) · Geo test (synthetic control, placebos) · Real lift: Criteo (PUBLIC DATA).
    python src/build_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
OUTD, PROC = ROOT / "data" / "output", ROOT / "data" / "processed"
OUT = ROOT / "dashboard" / "measurement_dashboard.html"
BLUE, GREY, RED, GREEN, INK = "#2A78D6", "#A3A19A", "#D03B3B", "#1BAF7A", "#0B0B0B"
LABEL = {"UC1": "A · Web CAPI · Meta", "UC2": "B · Web CAPI · TikTok", "UC3": "B · Web CAPI · Snapchat",
         "UC4": "C · CRM API · Meta", "UC5": "D · App CAPI · Meta", "UC7": "E · CRM API · Meta", "UC8": "F · Tag Gateway · Google Ads"}
LAYOUT = dict(template="simple_white", font=dict(family="Segoe UI, Arial", size=12, color=INK), margin=dict(l=60, r=20, t=50, b=50),
              legend=dict(orientation="h", y=-0.18), paper_bgcolor="white", plot_bgcolor="white")


def div(fig, first=False):
    fig.update_layout(**LAYOUT)
    return pio.to_html(fig, include_plotlyjs=first, full_html=False, config={"displaylogo": False, "responsive": True})


def portfolio(reads, geo):
    d = reads.set_index("use_case_id")
    ids = list(d.index) + ["UC8"]
    fig = go.Figure()
    rep = [d.reported_effect.get(u) for u in ids[:-1]] + [None]
    fig.add_trace(go.Scatter(x=rep, y=[LABEL[u] for u in ids], mode="markers", name="Platform-reported conversions",
                             marker=dict(color=GREY, size=12),
                             error_x=dict(type="data", symmetric=False,
                                          array=[d.reported_hi.get(u) - d.reported_effect.get(u) for u in ids[:-1]] + [0],
                                          arrayminus=[d.reported_effect.get(u) - d.reported_lo.get(u) for u in ids[:-1]] + [0])))
    biz = [d.business_effect.get(u) for u in ids[:-1]] + [geo["effect"]]
    hi = [d.business_hi.get(u) for u in ids[:-1]] + [geo["hi"]]
    lo = [d.business_lo.get(u) for u in ids[:-1]] + [geo["lo"]]
    verdict = list(d.verdict) + ["Incremental business effect"]
    fig.add_trace(go.Scatter(x=biz, y=[LABEL[u] for u in ids], mode="markers", name="Client orders (incremental)",
                             marker=dict(color=BLUE, size=12, symbol="square"),
                             error_x=dict(type="data", symmetric=False, array=[h - b for h, b in zip(hi, biz)],
                                          arrayminus=[b - l for b, l in zip(biz, lo)]),
                             customdata=verdict, hovertemplate="%{y}<br>%{x:+.1%}<br>%{customdata}<extra></extra>"))
    fig.add_vline(x=0, line_color=INK, line_width=1)
    fig.update_layout(title="Reported uplift vs incremental uplift (95% intervals) · SIMULATED", xaxis_tickformat="+.0%", height=480,
                      yaxis=dict(autorange="reversed"))
    tbl = "".join(f"<tr><td>{LABEL[u]}</td><td>{v}</td></tr>" for u, v in zip(ids, verdict))
    return div(fig, first=True) + f"<table class='t'><tr><th>Use case</th><th>Verdict (same rules for all)</th></tr>{tbl}</table>"


def use_case_tab(paths, reads):
    figs = []
    for i, (u, r) in enumerate(reads.set_index("use_case_id").iterrows()):
        fig = go.Figure()
        for metric, color in (("business", BLUE), ("reported", GREY)):
            p = paths[(paths.use_case_id == u) & (paths.metric == metric)].copy()
            p["date"] = pd.Timestamp(r.go_live) + pd.to_timedelta(p.block * 7, unit="D")
            p = p[p.block >= -26]
            base = p[p.block < 0].actual.mean()
            vis = metric == "business"
            post = p.dropna(subset=["cf_lo"])
            fig.add_trace(go.Scatter(x=list(post.date) + list(post.date[::-1]), y=list(post.cf_hi / base) + list(post.cf_lo[::-1] / base),
                                     fill="toself", fillcolor="rgba(163,161,154,0.25)", line=dict(width=0), name=f"95% band ({metric})",
                                     visible=vis, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=p.date, y=p.counterfactual / base, name=f"counterfactual ({metric})", visible=vis,
                                     line=dict(color=GREY, dash="dash")))
            fig.add_trace(go.Scatter(x=p.date, y=p.actual / base, name=f"actual ({metric})", visible=vis, line=dict(color=color, width=3)))
        go_live = pd.Timestamp(r.go_live)
        fig.add_vrect(x0=go_live, x1=go_live + pd.Timedelta(days=r.ramp_up_days), fillcolor="#FBE9E0", line_width=0,
                      annotation_text="ramp-up excluded", annotation_position="top left")
        fig.update_layout(title=f"{LABEL[u]} · orders {r.business_effect:+.1%} ({r.business_lo:+.1%} to {r.business_hi:+.1%}) · "
                                f"reported {r.reported_effect:+.1%} · {r.verdict}",
                          yaxis_title="index (pre-period = 1)", height=430,
                          updatemenus=[dict(type="buttons", direction="right", x=0, y=1.13, showactive=True, buttons=[
                              dict(label="Client orders", method="update", args=[{"visible": [True] * 3 + [False] * 3}]),
                              dict(label="Platform conversions", method="update", args=[{"visible": [False] * 3 + [True] * 3}])])])
        figs.append(f"<div class='uc' id='uc-{u}' style='display:{'block' if i == 0 else 'none'}'>{div(fig)}</div>")
    opts = "".join(f"<option value='{u}'>{LABEL[u]}</option>" for u in reads.use_case_id)
    return (f"<label>Use case: <select onchange=\"document.querySelectorAll('.uc').forEach(e=>e.style.display='none');"
            f"document.getElementById('uc-'+this.value).style.display='block';window.dispatchEvent(new Event('resize'));\">{opts}</select></label>"
            + "".join(figs))


def geo_tab(geo):
    w = pd.read_csv(OUTD / "geo_weekly.csv")
    w = w[w.block >= -40]
    f1 = go.Figure()
    f1.add_trace(go.Scatter(x=w.block, y=w.treated_index, name="6 treated regions", line=dict(color=BLUE, width=3)))
    f1.add_trace(go.Scatter(x=w.block, y=w.synthetic_index, name="synthetic control", line=dict(color=GREY, dash="dash")))
    f1.add_vrect(x0=0.5, x1=7.5, fillcolor="#E3EEFB", line_width=0, annotation_text="test (7 weeks)")
    f1.add_vrect(x0=-0.5, x1=0.5, fillcolor="#FBE9E0", line_width=0)
    f1.update_layout(title=f"Geo test · bookings {geo['effect']:+.1%} (95% {geo['lo']:+.1%} to {geo['hi']:+.1%}) · SIMULATED",
                     xaxis_title="weeks from go-live (5 Jul 2026)", yaxis_title="index (pre-period = 1)", height=420)
    pl = pd.read_csv(OUTD / "geo_placebos.csv").placebo_effect
    f2 = go.Figure(go.Histogram(x=pl, marker_color=GREY, name="placebo groups", nbinsx=30))
    f2.add_vline(x=geo["effect"], line_color=BLUE, line_width=3, annotation_text="treated")
    f2.add_vline(x=geo["naive_prepost"], line_color=RED, line_dash="dash", annotation_text="naive pre/post")
    f2.update_layout(title=f"{len(pl)} placebo groups of 6 control regions: none reaches the treated effect", xaxis_tickformat="+.0%", height=380)
    wts = pd.read_csv(OUTD / "geo_weights.csv")
    tbl = "".join(f"<tr><td>{r.iloc[0]}</td><td>{r.weight:.1%}</td></tr>" for _, r in wts.iterrows())
    return div(f1) + div(f2) + f"<table class='t'><tr><th>Control region</th><th>Weight</th></tr>{tbl}</table>"


def criteo_tab(c):
    f1 = go.Figure(go.Bar(x=["Control (held out)", "Treatment (eligible)"], y=[c["cr_control"], c["cr_treated"]],
                          marker_color=[GREY, BLUE], text=[f"{c['cr_control']:.3%}", f"{c['cr_treated']:.3%}"], textposition="outside"))
    f1.update_layout(title=f"Randomised: +{c['itt_rel']:.0%} conversions (95% {c['itt_rel_lo']:.0%} to {c['itt_rel_hi']:.0%}) · PUBLIC DATA",
                     yaxis_tickformat=".2%", height=380)
    f2 = go.Figure(go.Bar(y=["Exposed vs unexposed (naive)", "Effect on exposed (Wald)", "Intention to treat"],
                          x=[c["naive_rel"], c["cace_rel"], c["itt_rel"]], orientation="h", marker_color=[RED, BLUE, BLUE],
                          text=[f"+{c['naive_rel']:.0%}", f"+{c['cace_rel']:.0%}", f"+{c['itt_rel']:.0%}"], textposition="outside"))
    f2.update_layout(title="Same campaign, three 'lifts' (log scale)", xaxis_type="log", height=340)
    d = pd.read_parquet(PROC / "criteo_by_propensity.parquet")
    t, k = d[d.treatment == 1], d[d.treatment == 0]
    f3 = go.Figure()
    f3.add_trace(go.Bar(x=t.decile, y=t.exposure_rate, name="share exposed (treatment)", marker_color="#C9DDF5"))
    f3.add_trace(go.Scatter(x=k.decile, y=k.conversion_rate, name="conversion rate without ads (control)", yaxis="y2",
                            line=dict(color=RED, width=3)))
    f3.update_layout(title="Ads reach users who would convert anyway (deciles of feature f9)", yaxis_tickformat=".0%",
                     yaxis2=dict(overlaying="y", side="right", tickformat=".1%"), height=380)
    return div(f1) + div(f2) + div(f3)


CSS = """
body{font-family:'Segoe UI',Arial,sans-serif;background:#F4F4F2;color:#0B0B0B;margin:0;padding:16px}
h1{font-size:22px;margin:0 0 4px} p.sub{color:#52514E;margin:0 0 12px}
.tabs button{border:0;background:#E1E0D9;padding:8px 14px;margin-right:4px;border-radius:6px 6px 0 0;cursor:pointer;font:inherit}
.tabs button.on{background:#FCFCFB;font-weight:600}
.tab{display:none;background:#FCFCFB;border:1px solid #E1E0D9;border-radius:0 8px 8px 8px;padding:12px}
.tab.on{display:block} table.t{border-collapse:collapse;margin:10px 0;font-size:13px} .t td,.t th{border-bottom:1px solid #E1E0D9;padding:4px 10px;text-align:left}
select{font:inherit;padding:4px} footer{font-size:11px;color:#898781;margin-top:10px}
"""


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    reads = pd.read_csv(OUTD / "use_case_reads.csv")
    paths = pd.read_csv(OUTD / "ci_paths.csv")
    h = json.loads((OUTD / "headline.json").read_text(encoding="utf-8"))
    tabs = [("Portfolio", portfolio(reads, h["geo"])), ("Use case read", use_case_tab(paths, reads)),
            ("Geo test", geo_tab(h["geo"])), ("Real lift: Criteo", criteo_tab(h["criteo"]))]
    buttons = "".join(f"<button class='{'on' if i == 0 else ''}' onclick=\"show({i})\">{n}</button>" for i, (n, _) in enumerate(tabs))
    body = "".join(f"<div class='tab {'on' if i == 0 else ''}'>{c}</div>" for i, (_, c) in enumerate(tabs))
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Datahash measurement dashboard</title><style>{CSS}</style></head><body>
<h1>Proving what first-party signals are worth</h1>
<p class="sub">Portfolio, use case reads and geo test: SIMULATED clients (not Datahash's data). Criteo tab: PUBLIC DATA (CC BY-NC-SA 4.0, aggregates only).</p>
<div class="tabs">{buttons}</div>{body}
<footer>Independent case study based on public data · not affiliated with or endorsed by Datahash</footer>
<script>function show(i){{document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('on',i===j));
document.querySelectorAll('.tabs button').forEach((b,j)=>b.classList.toggle('on',i===j));window.dispatchEvent(new Event('resize'));}}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print("written", OUT.relative_to(ROOT), f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

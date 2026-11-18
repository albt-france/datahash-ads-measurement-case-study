"""Matplotlib charts for the PDF report and the client deliverables. One function per chart; every number is read
from data/output or data/processed (nothing typed by hand).

Style: light grey-beige page, white cards, blue for the data, grey for comparison/control, red for alerts and
thresholds, dashed lines for thresholds, Segoe UI. Platforms keep one colour everywhere.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTD, PROC = ROOT / "data" / "output", ROOT / "data" / "processed"
IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

BLUE, GREY, RED, GREEN, INK, MUTED, GRID = "#2A78D6", "#A3A19A", "#D03B3B", "#1BAF7A", "#0B0B0B", "#52514E", "#E1E0D9"
LIGHT = "#C9DDF5"
PLAT = {"Meta": "#2A78D6", "Google Ads": "#EB6834", "Snapchat": "#EDA100", "TikTok": "#1BAF7A", "GA4": "#8A6FD1"}

plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})
PCT = mtick.PercentFormatter(1.0, decimals=0)


def head():
    return json.loads((OUTD / "headline.json").read_text(encoding="utf-8"))


def csv(name, folder=OUTD, **kw):
    return pd.read_csv(folder / f"{name}.csv", **kw)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / f"{name}.png", dpi=200)
    plt.close(fig)
    return f"img/{name}.png"


LABEL = {"UC1": "A · Web CAPI · Meta", "UC2": "B · Web CAPI · TikTok", "UC3": "B · Web CAPI · Snapchat",
         "UC4": "C · CRM API · Meta", "UC5": "D · App CAPI · Meta", "UC7": "E · CRM API · Meta", "UC8": "F · Tag Gateway · Google"}


# ------------------------------------------------------------------ page 1: Datahash evidence grid (PUBLIC DATA)
def evidence_grid():
    g = csv("case_study_grid", PROC)
    names = {"quantified_outcome": "Quantified outcome", "period_stated": "Before/after period stated",
             "offline_or_crm_outcome": "Offline or CRM outcome", "other_changes_disclosed": "Other changes disclosed",
             "labelled_measured_not_incremental": "Labelled as measured / attributed", "baseline_level_shown": "Baseline level shown",
             "concurrent_comparison": "Comparison group (e.g. pixel only)", "window_mentioned": "Optimisation window named",
             "signal_quality_reported": "Signal quality (EMQ) reported", "ramp_up_excluded": "Ramp-up excluded",
             "interval_or_significance": "Interval or significance"}
    s = g[list(names)].sum().rename(names).sort_values()
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    cols = [RED if v == 0 else (GREY if v < len(g) / 2 else BLUE) for v in s.values]
    ax.barh(s.index, s.values, color=cols, height=0.62)
    for i, v in enumerate(s.values):
        ax.text(v + 0.2, i, f"{int(v)}/{len(g)}", va="center", fontsize=9, color=INK)
    ax.set_xlim(0, len(g) + 2)
    ax.set_title(f"Evidence elements published in the {len(g)} case studies")
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("case studies")
    return save(fig, "p1_evidence_grid")


def grid_mix():
    g = csv("case_study_grid", PROC)
    plat = g.platform.str.split(", ").explode().value_counts()
    off = g.offering.str.split(", ").explode().value_counts()
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.5))
    for ax, s, t in ((axes[0], plat, "Platform"), (axes[1], off, "Offering")):
        ax.barh(s.index[::-1], s.values[::-1], color=BLUE, height=0.6)
        ax.set_title(t)
        ax.grid(axis="y", visible=False)
        for i, v in enumerate(s.values[::-1]):
            ax.text(v + 0.1, i, str(v), va="center", fontsize=8.5)
        ax.set_xlim(0, s.max() + 2)
    return save(fig, "p1_mix")


# ------------------------------------------------------------------ page 2: Criteo (PUBLIC DATA)
def criteo_rates():
    c = head()["criteo"]
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    vals = [c["cr_control"], c["cr_treated"]]
    ax.bar(["Control (held out)\n15% of users", "Treatment (eligible)\n85% of users"], vals, color=[GREY, BLUE], width=0.55)
    se = [(c["itt_abs_hi"] - c["itt_abs"]) / 1.96] * 2
    for i, v in enumerate(vals):
        ax.text(i, v * 1.03, f"{v * 100:.3f}%", ha="center", fontsize=10, color=INK)
    ax.set_ylim(0, max(vals) * 1.25)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=2))
    ax.set_title(f"Randomised: +{c['itt_rel'] * 100:.0f}% conversions (95% CI {c['itt_rel_lo'] * 100:.0f}–{c['itt_rel_hi'] * 100:.0f}%)")
    ax.grid(axis="x", visible=False)
    return save(fig, "p2_rates")


def criteo_naive():
    c = head()["criteo"]
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    labels = ["Exposed vs unexposed\n(naive dashboard)", "Effect on exposed users\n(Wald / CACE)", "Whole eligible group\n(intention to treat)"]
    vals = [c["naive_rel"], c["cace_rel"], c["itt_rel"]]
    cols = [RED, BLUE, BLUE]
    ax.barh(labels[::-1], vals[::-1], color=cols[::-1], height=0.55)
    ax.set_xscale("log")
    for i, v in enumerate(vals[::-1]):
        ax.text(v * 1.12, i, f"+{v * 100:,.0f}%", va="center", fontsize=10, color=INK)
    ax.set_xlim(0.3, 300)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"+{x * 100:,.0f}%"))
    ax.set_title("Same campaign, three 'lifts' (log scale)")
    ax.grid(axis="y", visible=False)
    return save(fig, "p2_naive")


def criteo_selection():
    d = pd.read_parquet(PROC / "criteo_by_propensity.parquet")
    t, c = d[d.treatment == 1].set_index("decile"), d[d.treatment == 0].set_index("decile")
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    ax.bar(t.index, t.exposure_rate, color=LIGHT, label="share exposed (treatment group)")
    ax.set_ylabel("share exposed")
    ax.yaxis.set_major_formatter(PCT)
    ax2 = ax.twinx()
    ax2.plot(c.index, c.conversion_rate, color=RED, marker="o", lw=2, label="conversion rate WITHOUT ads (control)")
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=1))
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    ax.set_xlabel("decile of a pre-treatment feature (f9)")
    ax.set_xticks(range(1, 11))
    ax.set_title("Ads go to users who would convert anyway")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    return save(fig, "p2_selection")


# ------------------------------------------------------------------ page 4: traps (SIMULATED)
def trap_dedup():
    d = csv("sql_03_dedup_check", parse_dates=["week"])
    t = d[(d.client == "C2") & (d.market == "UAE") & (d.platform == "TikTok")].set_index("week").loc["2025-06-01":"2026-01-31"]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.plot(t.index, t.reported_per_order, color=BLUE, lw=2, label="TikTok conversions per client order")
    ax.axvspan(pd.Timestamp("2025-09-07"), pd.Timestamp("2025-10-26"), color="#FBE9E0", label="server events without event_id")
    ax.set_ylim(0, t.reported_per_order.max() * 1.3)
    ax2 = ax.twinx()
    ax2.plot(t.index, t.event_id_coverage, color=RED, lw=1.4, ls="--", label="event_id coverage (server)")
    ax2.set_ylim(0, 1.15)
    ax2.yaxis.set_major_formatter(PCT)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    r = csv("use_case_reads").set_index("use_case_id").loc["UC2"]
    ax.set_title(f"Client B: {r.reported_effect * 100:+.0f}% conversions that are duplicates")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=7.5)
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))
    return save(fig, "p4_dedup")


def trap_season():
    b = pd.read_parquet(PROC / "business_daily.parquet")
    p = b[b.client == "C3"].pivot(index="date", columns="market", values="orders").resample("W-SAT").sum()
    p = p.loc["2025-12-01":"2026-05-31"]
    base = p.loc["2025-12-07":"2026-01-31"].mean()
    idx = p / base
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.plot(idx.index, idx.KSA, color=BLUE, lw=2, label="KSA (CRM API live 1 Feb)")
    ax.plot(idx.index, idx.UAE, color=GREY, lw=2, label="UAE (control, not migrated)")
    ax.axvspan(pd.Timestamp("2026-02-18"), pd.Timestamp("2026-03-19"), color="#FFF3D6", label="Ramadan 2026")
    ax.axvline(pd.Timestamp("2026-02-01"), color=RED, ls="--", lw=1)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.2f}"))
    ax.set_ylabel("orders, index (Dec–Jan = 1)")
    h = head()
    r = csv("use_case_reads").set_index("use_case_id").loc["UC4"]
    ax.set_title(f"Client C: naive +{r.business_naive * 100:.0f}% → +{r.business_effect * 100:.1f}% vs control → "
                 f"not confirmed after Eid", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
    return save(fig, "p4_season")


def trap_window():
    a = pd.read_parquet(PROC / "ads_daily.parquet")
    a = a[(a.client == "C5") & (a.market == "UAE") & (a.platform == "Meta")].groupby("date")[["conversions", "conv_click"]].sum()
    a = a.rolling(7).mean().loc["2026-04-20":"2026-08-10"]
    w = head()["traps"]["window"]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.plot(a.index, a.conversions, color=RED, lw=2, label="as reported (active setting)")
    ax.plot(a.index, a.conv_click, color=BLUE, lw=2, label="7-day click, same setting all along")
    ax.axvline(pd.Timestamp(w["changed_on"]), color=INK, ls="--", lw=1)
    ax.text(pd.Timestamp(w["changed_on"]), ax.get_ylim()[1] * 0.98, " 7d click + 1d view → 7d click", fontsize=8, va="top")
    ax.set_title(f"Client E: reported {w['reported_active_setting_change'] * 100:.0f}% is mostly the window")
    ax.set_ylabel("Meta conversions / day (7-day avg)")
    ax.legend(fontsize=7.5, loc="upper left")
    ax.set_ylim(top=ax.get_ylim()[1] * 1.12)
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
    return save(fig, "p4_window")


def trap_lag():
    t = csv("lag_daily", parse_dates=["date"]).set_index("date").loc["2026-08-15":]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.plot(t.index, t.conv_by_conv_date.rolling(7).mean(), color=BLUE, lw=2, label="by conversion date")
    ax.plot(t.index, t.conv_by_click_date.rolling(7).mean(), color=RED, lw=2, label="by click date (as the platform credits)")
    ax.axvspan(pd.Timestamp("2026-10-11"), pd.Timestamp("2026-10-31"), color="#FBE9E0")
    ax.set_title("All clients: the last 3 weeks are not finished yet")
    ax.set_ylabel("conversions / day, all platforms (7-day avg)")
    ax.legend(fontsize=7.5, loc="lower left")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    return save(fig, "p4_lag")


# ------------------------------------------------------------------ page 5: causal impact + geo (SIMULATED)
def ci_chart(uc="UC1", metric="business", name="p5_ci", title=None, figsize=(5.2, 3.1)):
    p = csv("ci_paths")
    p = p[(p.use_case_id == uc) & (p.metric == metric)].copy()
    go = pd.Timestamp(p.go_live.iloc[0])
    p["date"] = go + pd.to_timedelta(p.block * 7, unit="D")
    p = p[p.block >= -20]
    r = csv("use_case_reads").set_index("use_case_id").loc[uc]
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(p.date, p.actual, color=BLUE, lw=2, label="actual")
    ax.plot(p.date, p.counterfactual, color=GREY, lw=1.6, ls="--", label="counterfactual (from control market)")
    post = p.dropna(subset=["cf_lo"])
    ax.fill_between(post.date, post.cf_lo, post.cf_hi, color=GREY, alpha=0.25, label="95% band")
    ax.axvspan(go, go + pd.Timedelta(days=7 * int(np.ceil(r.ramp_up_days / 7))), color="#FBE9E0", label="ramp-up (excluded)")
    e, lo, hi = r[f"{metric}_effect"], r[f"{metric}_lo"], r[f"{metric}_hi"]
    ax.set_title(title or f"{'Client orders' if metric == 'business' else 'Platform conversions'}: "
                          f"{e * 100:+.1f}% (95% {lo * 100:+.1f} to {hi * 100:+.1f}%)")
    ax.legend(fontsize=7.5, loc="upper right", ncol=2)
    ax.set_ylim(top=ax.get_ylim()[1] * 1.04)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))
    ax.set_ylabel("per week")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    return save(fig, name)


def geo_chart():
    w = csv("geo_weekly")
    w = w[w.block >= -30]
    g = head()["geo"]
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    ax.plot(w.block, w.treated_index, color=BLUE, lw=2, label="6 treated regions")
    ax.plot(w.block, w.synthetic_index, color=GREY, lw=1.8, ls="--", label="synthetic control (weighted controls)")
    ax.axvspan(-0.5, 0.5, color="#FBE9E0", label="ramp-up week")
    ax.axvspan(0.5, 7.5, color="#E3EEFB", label="test: 7 weeks")
    ax.set_xlabel("weeks from go-live (5 Jul 2026)")
    ax.set_ylabel("bookings, index (pre-period = 1)")
    ax.set_title(f"Client F geo test: {g['effect'] * 100:+.1f}% bookings (95% {g['lo'] * 100:+.1f} to {g['hi'] * 100:+.1f}%)")
    ax.legend(fontsize=7.5, loc="upper left")
    return save(fig, "p5_geo")


def placebo_chart():
    pl = csv("geo_placebos").placebo_effect
    g = head()["geo"]
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    ax.hist(pl, bins=30, color=GREY, alpha=0.8, label=f"{len(pl)} placebo groups of 6 control regions")
    ax.axvline(g["effect"], color=BLUE, lw=2.5, label=f"real treated group: {g['effect'] * 100:+.1f}%")
    ax.axvline(g["naive_prepost"], color=RED, lw=1.5, ls="--", label=f"naive pre/post: {g['naive_prepost'] * 100:+.1f}%")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_title(f"No placebo comes close (p = {max(g['p_value'], 1 / len(pl)):.3f}" + (" or less)" if g["p_value"] == 0 else ")"))
    ax.set_xlabel("estimated effect")
    ax.legend(fontsize=7.5, loc="upper right")
    return save(fig, "p5_placebo")


# ------------------------------------------------------------------ page 6: portfolio + EMQ (SIMULATED)
def portfolio():
    r = csv("use_case_reads")
    g = head()["geo"]
    rows = [(LABEL[u], x.reported_effect, x.reported_lo, x.reported_hi, x.business_effect, x.business_lo, x.business_hi, x.verdict)
            for u, x in r.set_index("use_case_id").iterrows()]
    rows.append((LABEL["UC8"], np.nan, np.nan, np.nan, g["effect"], g["lo"], g["hi"], "Incremental business effect"))
    d = pd.DataFrame(rows, columns=["label", "rep", "rlo", "rhi", "biz", "blo", "bhi", "verdict"])
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    y = np.arange(len(d))[::-1]
    ax.errorbar(d.rep, y + 0.15, xerr=[d.rep - d.rlo, d.rhi - d.rep], fmt="o", color=GREY, ms=6, capsize=2, label="platform-reported conversions")
    ax.errorbar(d.biz, y - 0.15, xerr=[d.biz - d.blo, d.bhi - d.biz], fmt="s", color=BLUE, ms=6, capsize=2, label="client orders (incremental)")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(d.label, fontsize=8.5)
    for yi, v in zip(y, d.verdict):
        ax.text(0.47, yi, v.split(":")[0].replace("Incremental business effect", "Incremental").replace(
            "Signal recovered, no business effect shown", "Signal only"), fontsize=7.5, va="center",
            color=GREEN if v.startswith("Incremental") else (RED if v.startswith("Not") else MUTED))
    ax.set_xlim(-0.1, 0.62)
    ax.xaxis.set_major_formatter(PCT)
    ax.grid(axis="y", visible=False)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.4, -0.08), ncol=2)
    ax.set_title("Reported uplift vs incremental uplift, 95% intervals")
    return save(fig, "p6_portfolio")


def emq_chart():
    s = pd.read_parquet(PROC / "signals_daily.parquet")
    s = s[(s.client == "C4") & (s.market == "India-Android") & (s.platform == "Meta")].set_index("date").loc["2026-04-01":"2026-08-31"]
    b = pd.read_parquet(PROC / "business_daily.parquet")
    b = b[b.client == "C4"].pivot(index="date", columns="market", values="orders").loc["2026-04-01":"2026-08-31"]
    ratio = (b["India-Android"] / b["India-iOS"]).rolling(7).mean()
    ratio = ratio / ratio.loc[:"2026-06-06"].mean()
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    ax.plot(s.index, s.emq.rolling(7).mean(), color=PLAT["Meta"], lw=2, label="Event Match Quality (0–10)")
    ax.set_ylim(0, 10)
    ax2 = ax.twinx()
    ax2.plot(ratio.index, ratio, color=INK, lw=1.6, label="subscriptions, Android vs iOS (index)")
    ax2.set_ylim(0.8, 1.2)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    e = head()["traps"]["emq"]
    ax.set_title(f"Client D: EMQ {e['emq_before']:.1f} → {e['emq_after']:.1f}, subscriptions flat")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="lower right")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
    return save(fig, "p6_emq")


def build_all():
    return {f.__name__: f() for f in (evidence_grid, grid_mix, criteo_rates, criteo_naive, criteo_selection, trap_dedup,
                                      trap_season, trap_window, trap_lag, ci_chart, geo_chart, placebo_chart, portfolio, emq_chart)}


if __name__ == "__main__":
    print(build_all())

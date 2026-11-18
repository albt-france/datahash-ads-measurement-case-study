"""All the numbers of the study, computed once and saved to data/output/ (CSV + headline.json).

The notebook, the dashboard, the Excel workbook, the client deliverables and the PDF all read these files,
so every figure is traceable to one line of code.
    python src/analysis.py
Sections: 1. Criteo (PUBLIC DATA)  2. use-case reads (SIMULATED)  3. geo test  4. traps  5. detection score
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats
from statsmodels.tsa.statespace.structural import UnobservedComponents

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "data" / "output"
SEED = 7
MAJOR_EVENTS = ["Ramadan", "Eid al-Fitr", "Eid al-Adha", "White Friday", "11.11", "Diwali season", "Year-end sales"]
Z95 = stats.norm.ppf(0.975)


def rd(name):
    return pd.read_parquet(PROC / f"{name}.parquet")


# ============================================================== 1. Criteo: exposed is not incremental
def criteo():
    g = rd("criteo_by_group").set_index("treatment")
    e = rd("criteo_by_exposure")
    n0, n1 = g.loc[0, "users"], g.loc[1, "users"]
    p0, p1 = g.loc[0, "conversion_rate"], g.loc[1, "conversion_rate"]
    v0, v1 = g.loc[0, "visit_rate"], g.loc[1, "visit_rate"]
    se = np.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
    itt = p1 - p0
    # relative lift CI by the delta method on log(p1/p0)
    se_log = np.sqrt((1 - p0) / (n0 * p0) + (1 - p1) / (n1 * p1))
    rel = p1 / p0 - 1
    rel_lo, rel_hi = np.exp(np.log(p1 / p0) - Z95 * se_log) - 1, np.exp(np.log(p1 / p0) + Z95 * se_log) - 1
    expo = g.loc[1, "exposure_rate"]                          # nobody is exposed in control: one-sided non-compliance
    cace = itt / expo                                         # Wald estimator: effect on the users actually exposed
    cace_lo, cace_hi = (itt - Z95 * se) / expo, (itt + Z95 * se) / expo
    ex = e[(e.treatment == 1) & (e.exposure == 1)].iloc[0]
    un = e[(e.treatment == 1) & (e.exposure == 0)].iloc[0]
    p_exp = ex.conversion_rate
    counterfactual_exposed = p_exp - cace                    # what exposed users would have done without ads
    naive_ratio = p_exp / un.conversion_rate                 # "exposed vs unexposed" (what a dashboard shows)
    incr_share = cace / p_exp                                # share of exposed users' conversions caused by ads
    # power: users per arm to detect a relative lift on this base rate (two-sided z test, 80% power)
    def n_per_arm(base, lift, alpha=0.05, power=0.8, ratio=1.0):
        p_t = base * (1 + lift)
        za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
        var = base * (1 - base) / ratio + p_t * (1 - p_t)
        return int(np.ceil((za + zb) ** 2 * var / (p_t - base) ** 2))
    power = pd.DataFrame([{"relative_lift": l, "control_users_85_15_split": n_per_arm(p0, l, ratio=0.15 / 0.85) * 0.15 / 0.85,
                           "users_per_arm_50_50": n_per_arm(p0, l)} for l in (0.02, 0.05, 0.10, 0.20, 0.59)])
    power["control_users_85_15_split"] = power.control_users_85_15_split.round().astype(int)
    # selection: in the 2 top deciles of a pre-treatment feature exposure is far higher, and so is the baseline
    prop = rd("criteo_by_propensity")
    top = prop[prop.decile >= 9]
    rest = prop[prop.decile < 9]
    sel = {"exposure_top20": float(top[top.treatment == 1].exposure_rate.mean()),
           "exposure_rest": float(rest[rest.treatment == 1].exposure_rate.mean()),
           "control_cr_top20": float(top[top.treatment == 0].conversion_rate.mean()),
           "control_cr_rest": float(rest[rest.treatment == 0].conversion_rate.mean())}
    res = {"users": int(n0 + n1), "control_users": int(n0), "treated_users": int(n1), "treated_share": n1 / (n0 + n1),
           "cr_control": p0, "cr_treated": p1, "visit_control": v0, "visit_treated": v1,
           "itt_abs": itt, "itt_abs_lo": itt - Z95 * se, "itt_abs_hi": itt + Z95 * se,
           "itt_rel": rel, "itt_rel_lo": rel_lo, "itt_rel_hi": rel_hi,
           "visit_rel": v1 / v0 - 1, "exposure_rate": expo,
           "cace": cace, "cace_lo": cace_lo, "cace_hi": cace_hi,
           "cr_exposed": p_exp, "cr_unexposed_treated": un.conversion_rate,
           "counterfactual_exposed": counterfactual_exposed, "cace_rel": cace / counterfactual_exposed,
           "naive_ratio": naive_ratio, "naive_rel": naive_ratio - 1, "incremental_share_exposed": incr_share,
           "exposed_conversions": int(ex.conversions), "incremental_conversions": float(cace * ex.users),
           **sel}
    power.to_csv(OUT / "criteo_power.csv", index=False)
    pd.Series(res).to_csv(OUT / "criteo_results.csv", header=["value"])
    return res


# ============================================================== 2. causal impact (structural time series)
def weekly(s: pd.Series, go_live) -> pd.Series:
    """7-day blocks aligned on go-live (block 0 = go-live day + 6 days); incomplete blocks dropped."""
    k = np.floor((s.index - pd.Timestamp(go_live)).days / 7).astype(int)
    g = s.groupby(k)
    return g.sum()[g.count() == 7]


def _ci_fit(ratio_pre, steps, reps, seed, X_pre=None, X_fut=None):
    fit = UnobservedComponents(ratio_pre, level="llevel", exog=X_pre).fit(disp=False, maxiter=200)
    sims = fit.simulate(steps, repetitions=reps, anchor="end", exog=X_fut, rng=seed).reshape(steps, reps)
    return fit, sims


def calendar_exog(market, control_market, go_live) -> pd.DataFrame | None:
    """Weekly share of days with an event that hits only ONE of the two markets (e.g. Saudi vs UAE National Day).
    Shared events (Ramadan, Eid, White Friday) cancel out in the ratio and need no regressor."""
    cal = rd("calendar")
    reg = lambda m: {"India-Android": "India", "India-iOS": "India"}.get(m, m)
    t, c = reg(market), reg(control_market)
    if t == c:
        return None
    days = pd.date_range("2025-01-01", "2026-10-31")
    cols = {}
    for name, region in cal[cal.region.isin([t, c])][["event", "region"]].drop_duplicates().itertuples(index=False):
        hit = pd.Series(days.isin(cal[(cal.event == name) & (cal.region == region)].date), index=days).astype(float)
        cols[f"{name} ({region})"] = hit * (1 if region == t else -1)
    X = pd.DataFrame(cols, index=days)
    return weekly(X.sum(axis=1).rename("own_holidays").to_frame().iloc[:, 0], go_live).to_frame() / 7


def causal_impact(y: pd.Series, x: pd.Series, pre_blocks, post_blocks, reps=1000, seed=SEED, placebo=True, X=None):
    """Counterfactual of a treated weekly series from a control series (CausalImpact-style, local level).

    Plain words: treated and control markets share the calendar (Ramadan, sales, payday), so we model the RATIO
    treated / control. Before go-live that ratio drifts slowly (local level); holidays that hit only one of the two
    markets enter as a regressor (X). We project the ratio after go-live 1,000 times with its uncertainty and multiply
    by the control: that is what the treated market would have done without the change.
    Effect = actual / counterfactual - 1 over the read window, 95% interval = 2.5-97.5 percentiles.
    Ramp-up weeks sit between pre_blocks and post_blocks and are never used.
    In-time placebos: the same read at fake go-live dates inside the pre-period, where the true effect is zero,
    tell how big an "effect" pure noise produces (empirical p-value).
    """
    ratio = np.log(y.clip(lower=1)) - np.log(x.clip(lower=1))
    xa = lambda blocks: None if X is None else X.reindex(blocks).fillna(0).to_numpy()
    first, last = min(post_blocks), max(post_blocks)
    fut = list(range(max(pre_blocks) + 1, last + 1))
    fit, sims = _ci_fit(ratio.loc[pre_blocks].to_numpy(), len(fut), reps, seed, xa(pre_blocks), xa(fut))
    keep = [b - max(pre_blocks) - 1 for b in post_blocks]
    cf = np.exp(sims[keep]) * x.loc[post_blocks].to_numpy()[:, None]
    rel = y.loc[post_blocks].sum() / cf.sum(axis=0) - 1
    out = {"effect": float(np.median(rel)), "lo": float(np.percentile(rel, 2.5)), "hi": float(np.percentile(rel, 97.5)),
           "p_positive": float((rel > 0).mean())}
    if placebo:
        n, gapw = len(post_blocks), first - max(pre_blocks) - 1
        fakes = []
        for fake_end in range(min(pre_blocks) + 20, max(pre_blocks) - gapw - n + 1):
            pre_f = [b for b in pre_blocks if b <= fake_end]
            post_f = [fake_end + 1 + gapw + i for i in range(n)]
            fut_f = list(range(fake_end + 1, post_f[-1] + 1))
            _, sm = _ci_fit(ratio.loc[pre_f].to_numpy(), len(fut_f), 200, seed, xa(pre_f), xa(fut_f))
            cf_f = np.exp(sm[[b - fake_end - 1 for b in post_f]]) * x.loc[post_f].to_numpy()[:, None]
            fakes.append(float(np.median(y.loc[post_f].sum() / cf_f.sum(axis=0) - 1)))
        fakes = np.array(fakes)
        out.update({"placebo_n": len(fakes), "placebo_sd": float(fakes.std()),
                    "placebo_p": float((np.abs(fakes) >= abs(out["effect"])).mean()) if len(fakes) else np.nan})
    fitted = np.exp(ratio.loc[pre_blocks] - fit.resid) * x.loc[pre_blocks]          # one-step-ahead fit
    path = pd.DataFrame({"block": list(pre_blocks) + list(post_blocks),
                         "actual": list(y.loc[pre_blocks]) + list(y.loc[post_blocks]),
                         "counterfactual": list(fitted) + list(np.median(cf, axis=1)),
                         "cf_lo": [np.nan] * len(pre_blocks) + list(np.percentile(cf, 2.5, axis=1)),
                         "cf_hi": [np.nan] * len(pre_blocks) + list(np.percentile(cf, 97.5, axis=1))}).iloc[4:]
    return out, path


def series(df, client, market, platform=None, col="orders"):
    d = df[(df.client == client) & (df.market == market)]
    if platform:
        d = d[d.platform == platform]
    return d.groupby("date")[col].sum().asfreq("D")


def windows(r):
    """Pre-registered blocks for a use case: up to 52 pre weeks, ramp-up weeks skipped, read weeks inside read_end."""
    first = int(np.ceil(r.ramp_up_days / 7))
    last = int(np.floor(((r.read_end - r.go_live).days + 1) / 7)) - 1
    pre_n = min(52, (r.go_live - pd.Timestamp("2025-01-01")).days // 7)
    return list(range(-pre_n, 0)), list(range(first, last + 1))


def use_case_reads():
    uc, ads, biz = rd("use_cases"), rd("ads_daily"), rd("business_daily")
    naive = pd.read_csv(OUT / "sql_02_pre_post.csv").set_index("use_case_id")
    rows, paths = [], []
    for r in uc.itertuples():
        if r.use_case_id in ("UC6", "UC8"):
            continue
        pre_b, post_b = windows(r)
        out = {"use_case_id": r.use_case_id, "client": r.client, "client_label": r.client_label, "market": r.market,
               "control_market": r.control_market, "use_case": r.use_case, "platform": r.platform,
               "go_live": r.go_live.date(), "ramp_up_days": r.ramp_up_days, "read_weeks": len(post_b),
               "read_start": (r.go_live + pd.Timedelta(days=7 * post_b[0])).date(),
               "read_end": (r.go_live + pd.Timedelta(days=7 * post_b[-1] + 6)).date(), "pre_weeks": len(pre_b)}
        X = calendar_exog(r.market, r.control_market, r.go_live)
        for metric, df, col, plat in (("reported", ads, "conv_click", r.platform), ("business", biz, "orders", None)):
            y = weekly(series(df, r.client, r.market, plat, col), r.go_live)
            x = weekly(series(df, r.client, r.control_market, plat, col), r.go_live)
            ci, path = causal_impact(y, x, pre_b, post_b, X=X)
            out.update({f"{metric}_{k}": v for k, v in ci.items()})
            paths.append(path.assign(use_case_id=r.use_case_id, metric=metric, go_live=r.go_live))
        # seasonal overlap: share of read days inside a major shared event (pre-registered rule: > 25% -> persistence read)
        cal = rd("calendar")
        region = "India" if r.market.startswith("India") else "GCC"
        peak = cal[cal.event.isin(MAJOR_EVENTS) & cal.region.isin([region, r.market, "All"])].date.unique()
        read_days = pd.date_range(out["read_start"], out["read_end"])
        out["season_overlap"] = float(read_days.isin(peak).mean())
        if out["season_overlap"] > 0.25:
            pers = list(range(post_b[-1] + 1, post_b[-1] + 1 + len(post_b)))
            y = weekly(series(biz, r.client, r.market, None, "orders"), r.go_live)
            x = weekly(series(biz, r.client, r.control_market, None, "orders"), r.go_live)
            ci, _ = causal_impact(y, x, pre_b, pers, X=X, placebo=False)
            out.update({"persistence_start": (r.go_live + pd.Timedelta(days=7 * pers[0])).date(),
                        "persistence_end": (r.go_live + pd.Timedelta(days=7 * pers[-1] + 6)).date(),
                        "persistence_effect": ci["effect"], "persistence_lo": ci["lo"], "persistence_hi": ci["hi"]})
        out.update({"reported_naive": naive.loc[r.use_case_id, "reported_naive"],
                    "business_naive": naive.loc[r.use_case_id, "business_naive"],
                    "business_vs_control": naive.loc[r.use_case_id, "business_vs_control"]})
        rows.append(out)
    res = pd.DataFrame(rows)
    # retained as a business effect only if the interval excludes 0 AND noise rarely produces as much (placebo p < 0.05)
    res["business_retained"] = ((res.business_lo > 0) | (res.business_hi < 0)) & (res.business_placebo_p < 0.05)
    # a read dominated by a seasonal peak must hold in the following weeks too
    seasonal = res.season_overlap > 0.25
    res.loc[seasonal, "business_retained"] &= (res.loc[seasonal, "persistence_lo"] > 0) | (res.loc[seasonal, "persistence_hi"] < 0)
    res["signal_recovered_not_value"] = res.reported_effect - res.business_effect
    pd.concat(paths, ignore_index=True).to_csv(OUT / "ci_paths.csv", index=False)
    return res


# ============================================================== 3. geo test: synthetic control + placebos
def synth_weights(Y_pre_treated, Y_pre_donors):
    """Non-negative weights summing to 1 that make the donors' pre-period best match the treated series."""
    k = Y_pre_donors.shape[1]
    obj = lambda w: np.sum((Y_pre_treated - Y_pre_donors @ w) ** 2)
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    r = optimize.minimize(obj, np.full(k, 1 / k), bounds=[(0, 1)] * k, constraints=cons, method="SLSQP",
                          options={"maxiter": 500, "ftol": 1e-12})
    return r.x


def sc_effect(panel, treated, donors, pre_blocks, test_blocks):
    """Index each region on its pre-period mean, fit weights, return relative effect and the weekly gap."""
    idx = panel / panel.loc[pre_blocks].mean()
    yt = idx[treated].mul(panel.loc[pre_blocks, treated].mean()).sum(axis=1)
    yt = yt / yt.loc[pre_blocks].mean()
    w = synth_weights(yt.loc[pre_blocks].to_numpy(), idx.loc[pre_blocks, donors].to_numpy())
    synth = idx[donors].to_numpy() @ w
    synth = pd.Series(synth, index=idx.index)
    eff = yt.loc[test_blocks].sum() / synth.loc[test_blocks].sum() - 1
    rmspe_pre = np.sqrt(((yt.loc[pre_blocks] - synth.loc[pre_blocks]) ** 2).mean())
    return eff, yt, synth, pd.Series(w, index=donors), rmspe_pre


def geo_test():
    g = pd.read_csv(OUT / "sql_05_geo.csv")
    panel = g.pivot(index="block", columns="region", values="bookings")
    groups = g.drop_duplicates("region").set_index("region").geo_group
    treated = groups[groups == "treated"].index.tolist()
    controls = groups[groups == "control"].index.tolist()
    pre_blocks = [b for b in panel.index if b <= -1 and b >= -78]
    test_blocks = list(range(1, 8))
    eff, yt, synth, w, rmspe = sc_effect(panel, treated, controls, pre_blocks, test_blocks)
    # in-space placebos: 300 fake "treated" groups of 6 control regions, donors = the 12 other controls
    rng = np.random.default_rng(SEED)
    plac = []
    for _ in range(300):
        fake = list(rng.choice(controls, size=len(treated), replace=False))
        donors = [c for c in controls if c not in fake]
        plac.append(sc_effect(panel, fake, donors, pre_blocks, test_blocks)[0])
    plac = np.array(plac)
    lo, hi = eff - np.percentile(plac, 97.5), eff - np.percentile(plac, 2.5)
    p_value = float((np.abs(plac) >= abs(eff)).mean())
    # in-time placebo: pretend go-live 20 weeks earlier, using only pre-period data
    fake_test = list(range(-20, -13))
    fake_pre = [b for b in pre_blocks if b < -20]
    eff_time = sc_effect(panel, treated, controls, fake_pre, fake_test)[0]
    # naive comparisons
    pre_mean_t = panel.loc[pre_blocks[-8:], treated].sum(axis=1).mean()
    naive_prepost = panel.loc[test_blocks, treated].sum(axis=1).mean() / pre_mean_t - 1
    did = naive_prepost + 1
    did = did / (panel.loc[test_blocks, controls].sum(axis=1).mean() / panel.loc[pre_blocks[-8:], controls].sum(axis=1).mean()) - 1
    # power planning (done before the test): MDE of 7 test weeks from the pre-period noise of the treated/synth gap
    gap = np.log(yt.loc[pre_blocks] / synth.loc[pre_blocks])
    sd = gap.std()
    rho = float(np.corrcoef(gap[1:], gap[:-1])[0, 1])
    infl = np.sqrt((1 + max(rho, 0)) / (1 - max(rho, 0)))
    mde = {n: float((stats.norm.ppf(0.975) + stats.norm.ppf(0.8)) * sd * infl / np.sqrt(n)) for n in (4, 7, 10, 13)}
    weekly = pd.DataFrame({"block": yt.index, "treated_index": yt.values, "synthetic_index": synth.values})
    weekly.to_csv(OUT / "geo_weekly.csv", index=False)
    w[w > 0.001].sort_values(ascending=False).rename("weight").to_csv(OUT / "geo_weights.csv")
    pd.Series(plac, name="placebo_effect").to_csv(OUT / "geo_placebos.csv", index=False)
    res = {"effect": float(eff), "lo": float(lo), "hi": float(hi), "p_value": p_value, "placebo_in_time": float(eff_time),
           "rmspe_pre": float(rmspe), "naive_prepost": float(naive_prepost), "did": float(did),
           "n_treated": len(treated), "n_controls": len(controls), "pre_weeks": len(pre_blocks), "test_weeks": len(test_blocks),
           "mde_by_weeks": mde, "gap_sd": float(sd), "gap_rho": rho,
           "top_donors": w.sort_values(ascending=False).head(3).round(3).to_dict()}
    return res


# ============================================================== 4. traps
def traps(reads: pd.DataFrame):
    out = {}
    ads, sig = rd("ads_daily"), rd("signals_daily")
    uc = rd("use_cases").set_index("use_case_id")
    # 3. ramp-up: UC1 read with and without the learning weeks (go-live 12 Apr 2026, 10-day ramp-up = weeks 0-1)
    r = uc.loc["UC1"]
    y = weekly(series(ads, "C1", "KSA", "Meta", "conv_click"), r.go_live)
    x = weekly(series(ads, "C1", "UAE", "Meta", "conv_click"), r.go_live)
    pre_b, X = list(range(-52, 0)), calendar_exog("KSA", "UAE", r.go_live)
    incl, _ = causal_impact(y, x, pre_b, [0, 1, 2, 3], placebo=False, X=X)
    excl, _ = causal_impact(y, x, pre_b, [2, 3, 4, 5], placebo=False, X=X)
    first, _ = causal_impact(y, x, pre_b, [0], placebo=False, X=X)
    out["ramp"] = {"with_ramp_4w": incl, "without_ramp_4w": excl, "ramp_days_effect": first, "ramp_days": int(r.ramp_up_days)}
    # 2. dedup: event_id coverage on the server stream, reported per order before / during / after the fix
    d = pd.read_csv(OUT / "sql_03_dedup_check.csv", parse_dates=["week"])
    t = d[(d.client == "C2") & (d.market == "UAE") & (d.platform == "TikTok")].set_index("week")
    before = t.loc["2025-07-07":"2025-08-31", "reported_per_order"].mean()
    during = t.loc["2025-09-15":"2025-10-19", "reported_per_order"].mean()
    after = t.loc["2025-11-03":"2025-12-28", "reported_per_order"].mean()
    out["dedup"] = {"flag_weeks": int(t.flag_dedup_broken.sum()), "first_flag": str(t[t.flag_dedup_broken].index.min().date()),
                    "event_id_coverage_broken": float(t.loc["2025-09-15":"2025-10-19", "event_id_coverage"].mean()),
                    "event_id_coverage_fixed": float(t.loc["2025-11-03":"2025-12-28", "event_id_coverage"].mean()),
                    "reported_per_order_before": float(before), "reported_per_order_broken": float(during),
                    "reported_per_order_after_fix": float(after), "inflation_vs_before": float(during / before - 1)}
    # 5. attribution window change (client E, Meta): active-setting conversions vs consistent 7-day click
    ch = pd.read_csv(OUT / "sql_04_attribution_changes__setting_changes.csv")
    a = ads[(ads.client == "C5") & (ads.market == "UAE") & (ads.platform == "Meta")].groupby("date")[["conversions", "conv_click"]].sum()
    pre_w, post_w = a.loc["2026-05-17":"2026-06-13"], a.loc["2026-06-14":"2026-07-11"]
    bz = series(rd("business_daily"), "C5", "UAE")
    out["window"] = {"changed_on": ch.changed_on.iloc[0], "from": ch.previous_setting.iloc[0], "to": ch.new_setting.iloc[0],
                     "business_change": float(bz.loc["2026-06-14":"2026-07-11"].mean() / bz.loc["2026-05-17":"2026-06-13"].mean() - 1),
                     "reported_active_setting_change": float(post_w.conversions.mean() / pre_w.conversions.mean() - 1),
                     "consistent_7d_click_change": float(post_w.conv_click.mean() / pre_w.conv_click.mean() - 1),
                     "view_share_before": float(1 - pre_w.conv_click.sum() / pre_w.conversions.sum())}
    # 6. EMQ: client D App CAPI
    s = sig[(sig.client == "C4") & (sig.market == "India-Android") & (sig.platform == "Meta")].set_index("date")
    rr = uc.loc["UC5"]
    rd5 = reads.set_index("use_case_id").loc["UC5"]
    out["emq"] = {"emq_before": float(s.loc[rr.go_live - pd.Timedelta(days=56): rr.go_live - pd.Timedelta(days=1), "emq"].mean()),
                  "emq_after": float(s.loc[rr.read_start: rr.read_end, "emq"].mean()),
                  "match_before": float(s.loc[rr.go_live - pd.Timedelta(days=56): rr.go_live - pd.Timedelta(days=1), "match_rate"].mean()),
                  "match_after": float(s.loc[rr.read_start: rr.read_end, "match_rate"].mean()),
                  "business_effect": float(rd5.business_effect), "business_lo": float(rd5.business_lo), "business_hi": float(rd5.business_hi)}
    # 4. seasonal false signal: UC4, read window on Ramadan 2026
    rd4 = reads.set_index("use_case_id").loc["UC4"]
    cal = rd("calendar")
    ram = cal[(cal.event == "Ramadan") & (cal.date >= rr.go_live - pd.Timedelta(days=365))]
    out["season"] = {"business_naive": float(rd4.business_naive), "business_effect": float(rd4.business_effect),
                     "business_lo": float(rd4.business_lo), "business_hi": float(rd4.business_hi),
                     "reported_effect": float(rd4.reported_effect),
                     "ramadan_days_in_read": int(((cal.event == "Ramadan") & (cal.date >= uc.loc["UC4"].read_start)
                                                  & (cal.date <= uc.loc["UC4"].read_end) & (cal.region == "GCC")).sum())}
    # 8. click date vs conversion date: last 3 weeks before the extract
    c = pd.read_csv(OUT / "sql_04_attribution_changes__click_vs_conversion_date.csv", parse_dates=["date"])
    tot = c.groupby("date")[["conv_by_click_date", "conv_by_conv_date"]].sum()
    last3, prev3 = tot.loc["2026-10-11":"2026-10-31"], tot.loc["2026-09-20":"2026-10-10"]
    c6 = c[(c.client == "C6") & (c.platform == "Google Ads")].groupby("date")[["conv_by_click_date", "conv_by_conv_date"]].sum()
    out["lag"] = {"click_date_change_last3w": float(last3.conv_by_click_date.mean() / prev3.conv_by_click_date.mean() - 1),
                  "conv_date_change_last3w": float(last3.conv_by_conv_date.mean() / prev3.conv_by_conv_date.mean() - 1),
                  "travel_google_click_vs_conv_last7d": float(c6.loc["2026-10-25":"2026-10-31"].conv_by_click_date.sum()
                                                              / c6.loc["2026-10-25":"2026-10-31"].conv_by_conv_date.sum() - 1)}
    tot.to_csv(OUT / "lag_daily.csv")
    # GA4 server-side (client A): new vs returning users, sessions, unassigned
    ga = rd("ga4_daily").groupby("date").sum(numeric_only=True)
    b, a2 = ga.loc["2025-04-20":"2025-06-14"], ga.loc["2025-06-22":"2025-08-16"]
    biz = rd("business_daily")
    bb = biz[biz.client == "C1"].groupby("date").orders.sum()
    out["ga4"] = {"sessions_change": float(a2.sessions.mean() / b.sessions.mean() - 1),
                  "new_users_change": float(a2.new_users.mean() / b.new_users.mean() - 1),
                  "returning_users_change": float(a2.returning_users.mean() / b.returning_users.mean() - 1),
                  "new_share_before": float(b.new_users.sum() / (b.new_users.sum() + b.returning_users.sum())),
                  "new_share_after": float(a2.new_users.sum() / (a2.new_users.sum() + a2.returning_users.sum())),
                  "unassigned_before": float(b.unassigned_sessions.sum() / b.sessions.sum()),
                  "unassigned_after": float(a2.unassigned_sessions.sum() / a2.sessions.sum()),
                  "ga4_purchases_change": float(a2.ga4_purchases.mean() / b.ga4_purchases.mean() - 1),
                  "business_orders_change": float(bb.loc["2025-06-22":"2025-08-16"].mean() / bb.loc["2025-04-20":"2025-06-14"].mean() - 1)}
    g = out["ga4"]
    for k in ("sessions", "new_users", "returning_users", "ga4_purchases"):
        g[f"{k}_per_order_change"] = (1 + g[f"{k}_change"]) / (1 + g["business_orders_change"]) - 1
    return out


# ============================================================== 5. verdicts + detection score
def verdicts(reads, geo, tr):
    """Same rules for every use case, applied in this order (docs/EVIDENCE_STANDARD.md)."""
    d = pd.read_csv(OUT / "sql_03_dedup_check.csv")
    flagged = set(map(tuple, d[d.flag_dedup_broken == True][["client", "market", "platform"]].drop_duplicates().to_numpy()))
    v = []
    for _, r in reads.iterrows():
        if (r.client, r.market, r.platform) in flagged:
            verdict = "Not real: duplicates (event_id missing)"
        elif r.business_retained:
            verdict = "Incremental business effect"
        elif r.season_overlap > 0.25:
            verdict = "Seasonal: naive uplift not retained"
        else:
            verdict = "Signal recovered, no business effect shown"
        v.append({"use_case_id": r.use_case_id, "verdict": verdict})
    v.append({"use_case_id": "UC8", "verdict": "Incremental business effect" if geo["lo"] > 0 and geo["p_value"] < 0.05
              else "Inconclusive"})
    v.append({"use_case_id": "UC6", "verdict": "Measurement change (GA4), not business"})
    return pd.DataFrame(v)


def detection(reads, geo, tr, ver):
    """Score the reads against the hidden truth (only available before publication)."""
    truth_file = ROOT / "data" / "_hidden_truth.csv"
    R, V = reads.set_index("use_case_id"), ver.set_index("use_case_id").verdict
    checks = [
        (1, "True uplift kept, sized on business not on platform",
         bool(R.loc["UC1", "business_retained"]) and R.loc["UC1", "reported_effect"] > 2 * R.loc["UC1", "business_effect"]),
        (2, "Broken dedup flagged, uplift rejected", tr["dedup"]["flag_weeks"] > 0 and V["UC2"].startswith("Not real")),
        (3, "Ramp-up excluded (learning dip visible)", tr["ramp"]["ramp_days_effect"]["effect"] < tr["ramp"]["without_ramp_4w"]["effect"]),
        (4, "Seasonal false signal not retained", V["UC4"].startswith("Seasonal")),
        (5, "Window change found, consistent read used",
         tr["window"]["reported_active_setting_change"] - tr["window"]["consistent_7d_click_change"] < -0.10
         and abs(tr["window"]["consistent_7d_click_change"] - tr["window"]["business_change"]) < 0.05),
        (6, "EMQ gain not sold as value", tr["emq"]["emq_after"] - tr["emq"]["emq_before"] > 2 and not R.loc["UC5", "business_retained"]),
        (7, "Geo effect found with interval", V["UC8"].startswith("Incremental")),
        (8, "Click-date dip not read as a drop", tr["lag"]["click_date_change_last3w"] < -0.05 and abs(tr["lag"]["conv_date_change_last3w"]) < 0.10),
    ]
    df = pd.DataFrame(checks, columns=["event", "check", "detected"])
    if truth_file.exists():
        t = pd.read_csv(truth_file)
        df = df.merge(t[["event", "trap", "truth", "true_reported_change", "true_business_change"]], on="event")
        # does the interval contain the programmed business effect?
        cover = []
        for row in df.itertuples():
            u = t.set_index("event").loc[row.event, "use_case_id"]
            tb = row.true_business_change
            if u == "UC8":
                cover.append(geo["lo"] <= tb <= geo["hi"])
            elif u in R.index and pd.notna(tb):
                cover.append(R.loc[u, "business_lo"] <= tb <= R.loc[u, "business_hi"])
            else:
                cover.append(None)
        df["interval_covers_truth"] = cover
    elif (OUT / "detection.csv").exists():
        # published copy: the truth file was deleted after scoring, keep the scoring columns it produced
        old = pd.read_csv(OUT / "detection.csv")
        if "trap" in old.columns:
            df = df.merge(old.drop(columns=["check", "detected"]), on="event", how="left")
    df.to_csv(OUT / "detection.csv", index=False)
    return df


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cr = criteo()
    reads = use_case_reads()
    geo = geo_test()
    tr = traps(reads)
    ver = verdicts(reads, geo, tr)
    reads = reads.merge(ver, on="use_case_id", how="left")
    reads.to_csv(OUT / "use_case_reads.csv", index=False)
    ver.to_csv(OUT / "verdicts.csv", index=False)
    det = detection(reads, geo, tr, ver)
    grid = pd.read_csv(PROC / "case_study_grid.csv")
    head = {"criteo": cr, "geo": geo, "traps": tr, "detected": int(det.detected.sum()), "events": len(det),
            "grid": {k: int(v) for k, v in grid.drop(columns=["case", "vertical", "platform", "offering",
                                                               "headline_metric_family"]).sum().items()},
            "grid_n": len(grid)}
    (OUT / "headline.json").write_text(json.dumps(head, indent=1, default=str), encoding="utf-8")
    print(reads[["use_case_id", "reported_naive", "reported_effect", "business_naive", "business_effect",
                 "business_lo", "business_hi", "business_placebo_p", "verdict"]].round(3).to_string(index=False))
    print("geo", {k: round(v, 3) for k, v in geo.items() if isinstance(v, float)})
    print(det.to_string(index=False))


if __name__ == "__main__":
    main()

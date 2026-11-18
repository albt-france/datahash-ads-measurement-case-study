"""SIMULATED multi-client panel: 6 fictional Datahash-like clients, 4 ad platforms, 2025-01-01 to 2026-10-31, daily.

Nothing here is Datahash's or any real client's data. Orders of magnitude are calibrated on public ranges
(see data/ASSUMPTIONS.md). Eight measurement traps are planted; their truth goes to data/_hidden_truth.csv,
which is used once at the end (notebook) to score the detection, then deleted before publication.

    python src/simulate.py
Outputs (data/processed/*.parquet): ads_daily, signals_daily, business_daily, geo_daily, ga4_daily, use_cases, calendar
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
SEED = 42
START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-10-31")
EXTRACT = END                                   # reports pulled at the end of 31 Oct 2026
DATES = pd.date_range(START, END, freq="D")
N = len(DATES)
rng = np.random.default_rng(SEED)

# ------------------------------------------------------------------ calendar (public holiday dates)
EVENTS = [  # name, region, start, end
    ("Ramadan", "GCC", "2025-03-01", "2025-03-29"), ("Eid al-Fitr", "GCC", "2025-03-30", "2025-04-02"),
    ("Eid al-Adha", "GCC", "2025-06-06", "2025-06-09"), ("Saudi National Day", "KSA", "2025-09-21", "2025-09-23"),
    ("Diwali season", "India", "2025-10-10", "2025-10-22"), ("11.11", "GCC", "2025-11-11", "2025-11-11"),
    ("White Friday", "GCC", "2025-11-24", "2025-11-30"), ("UAE National Day", "UAE", "2025-12-01", "2025-12-03"),
    ("Year-end sales", "All", "2025-12-26", "2025-12-31"),
    ("Ramadan", "GCC", "2026-02-18", "2026-03-19"), ("Eid al-Fitr", "GCC", "2026-03-20", "2026-03-23"),
    ("Eid al-Adha", "GCC", "2026-05-27", "2026-05-30"), ("Saudi National Day", "KSA", "2026-09-21", "2026-09-23"),
    ("Diwali season", "India", "2026-10-29", "2026-11-08"),
]
SUMMER = {"GCC": [("2025-07-01", "2025-08-31"), ("2026-07-01", "2026-08-31")]}

# multiplicative calendar effects by vertical (share of extra demand)
LIFT = {
    "retail":    {"Ramadan": .15, "Eid al-Fitr": .30, "Eid al-Adha": .15, "White Friday": .45, "11.11": .30,
                  "Diwali season": .40, "Saudi National Day": .15, "UAE National Day": .12, "Year-end sales": .20, "summer": -.10},
    "qsr":       {"Ramadan": .25, "Eid al-Fitr": .15, "Eid al-Adha": .10, "White Friday": .05, "11.11": .05,
                  "Diwali season": .10, "Saudi National Day": .10, "UAE National Day": .08, "Year-end sales": .08, "summer": -.05},
    "telecom":   {"Ramadan": .24, "Eid al-Fitr": .20, "Eid al-Adha": .08, "White Friday": .20, "11.11": .10,
                  "Diwali season": .15, "Saudi National Day": .12, "UAE National Day": .10, "Year-end sales": .05, "summer": -.04},
    "streaming": {"Ramadan": .10, "Eid al-Fitr": .05, "Eid al-Adha": .03, "White Friday": .06, "11.11": .02,
                  "Diwali season": .08, "Saudi National Day": .02, "UAE National Day": .02, "Year-end sales": .06, "summer": .00},
    "bank":      {"Ramadan": .05, "Eid al-Fitr": -.10, "Eid al-Adha": -.08, "White Friday": .03, "11.11": .00,
                  "Diwali season": .10, "Saudi National Day": .00, "UAE National Day": .00, "Year-end sales": -.10, "summer": -.08},
    "travel":    {"Ramadan": -.12, "Eid al-Fitr": .30, "Eid al-Adha": .25, "White Friday": .10, "11.11": .03,
                  "Diwali season": .25, "Saudi National Day": .10, "UAE National Day": .12, "Year-end sales": .15, "summer": .20},
}

# weekend days (Mon=0): KSA Fri-Sat, UAE Sat-Sun (since 2022), India Sun
WEEKEND = {"KSA": (4, 5), "UAE": (5, 6), "India": (6,)}

# ------------------------------------------------------------------ clients (fictional)
# share = fraction of business orders a platform claims under its default window (overlaps allowed, as in real reports)
CLIENTS = {
    "C1": dict(label="Client A · Retail", vertical="retail", aov=85, lag=1.5,
               markets={"KSA": 1800, "UAE": 1150},
               platforms={"Meta": (.22, 9000), "Google Ads": (.26, 8000), "Snapchat": (.10, 3500), "TikTok": (.07, 2500)}),
    "C2": dict(label="Client B · Quick-service restaurant", vertical="qsr", aov=14, lag=0.3,
               markets={"UAE": 5200, "KSA": 6100},
               platforms={"Meta": (.12, 2600), "Google Ads": (.10, 2200), "Snapchat": (.16, 3200), "TikTok": (.14, 2800)}),
    "C3": dict(label="Client C · Telecom", vertical="telecom", aov=160, lag=2.0,
               markets={"KSA": 950, "UAE": 620},
               platforms={"Meta": (.15, 7000), "Google Ads": (.22, 9000), "Snapchat": (.10, 3500), "TikTok": (.05, 1800)}),
    "C4": dict(label="Client D · Streaming", vertical="streaming", aov=6, lag=1.0,
               markets={"India-Android": 7400, "India-iOS": 2300},
               platforms={"Meta": (.20, 4200), "Google Ads": (.25, 5200)}),        # TikTok is not available in India
    "C5": dict(label="Client E · Bank & insurance", vertical="bank", aov=420, lag=4.0,
               markets={"UAE": 310, "KSA": 380},
               platforms={"Meta": (.14, 6500), "Google Ads": (.30, 11000), "Snapchat": (.06, 2000)}),
    "C6": dict(label="Client F · Travel", vertical="travel", aov=640, lag=8.0,
               markets={"KSA": 0, "UAE": 0, "India": 0},                      # filled from the regions below
               platforms={"Google Ads": (.35, 21000), "Meta": (.12, 8000), "Snapchat": (.07, 2600)}),
}
WINDOW = {"Meta": (7, "7d_click_1d_view"), "Google Ads": (30, "30d_click"), "Snapchat": (28, "28d_click_1d_view"),
          "TikTok": (7, "7d_click_1d_view")}
VIEW_SHARE = {"Meta": .18, "Google Ads": 0.0, "Snapchat": .22, "TikTok": .20}   # share of default-window conversions that are view-through

# use cases: reported = true change in platform-reported conversions (consistent window, complete lag);
# business = true change in client-side orders. Ramp-up days are excluded from any read.
USE_CASES = [
    # id, client, market, use case, platform, go-live, ramp days, reported, business, emq before -> after
    ("UC1", "C1", "KSA", "Web CAPI", "Meta", "2026-04-12", 10, .18, .04, (5.9, 7.6)),
    ("UC2", "C2", "UAE", "Web CAPI", "TikTok", "2025-09-07", 7, .35, .00, (4.9, 5.3)),
    ("UC3", "C2", "UAE", "Web CAPI", "Snapchat", "2025-09-07", 7, .09, .00, (5.2, 6.9)),
    ("UC4", "C3", "KSA", "CRM Conversions API", "Meta", "2026-02-01", 14, .06, .00, (5.5, 7.0)),
    ("UC5", "C4", "India-Android", "App CAPI", "Meta", "2026-06-07", 7, .05, .00, (4.6, 8.3)),
    ("UC6", "C1", "KSA+UAE", "GA4 server-side", "GA4", "2025-06-15", 7, .07, .00, (None, None)),
    ("UC7", "C5", "UAE", "CRM Conversions API", "Meta", "2026-05-03", 14, .10, .06, (5.8, 7.8)),
    ("UC8", "C6", "Treated regions", "Google Tag Gateway", "Google Ads", "2026-07-05", 7, .11, .05, (None, None)),
]
DEDUP_FIX = pd.Timestamp("2025-10-26")          # UC2: event_id added server-side on this date
WINDOW_CHANGE = ("C5", "Meta", pd.Timestamp("2026-06-14"), "7d_click")   # trap 5
GEO_END = pd.Timestamp("2026-08-29")            # end of the geo test; GTG rolled out everywhere after

REGIONS = {  # region: (country, bookings/day)
    "Riyadh": ("KSA", 210), "Jeddah": ("KSA", 170), "Dammam": ("KSA", 80), "Makkah": ("KSA", 60), "Madinah": ("KSA", 45),
    "Khobar": ("KSA", 50), "Taif": ("KSA", 25), "Abha": ("KSA", 22),
    "Dubai": ("UAE", 240), "Abu Dhabi": ("UAE", 130), "Sharjah": ("UAE", 70), "Ajman": ("UAE", 25), "Al Ain": ("UAE", 30),
    "Ras Al Khaimah": ("UAE", 18), "Fujairah": ("UAE", 12),
    "Mumbai": ("India", 190), "Delhi NCR": ("India", 220), "Bengaluru": ("India", 160), "Hyderabad": ("India", 95),
    "Chennai": ("India", 80), "Kolkata": ("India", 60), "Pune": ("India", 70), "Ahmedabad": ("India", 45), "Jaipur": ("India", 30),
}
TREATED = ["Jeddah", "Dammam", "Abu Dhabi", "Sharjah", "Bengaluru", "Hyderabad"]


# ------------------------------------------------------------------ helpers
def region_of(market: str) -> str:
    return "India" if market.startswith("India") else "GCC"


def country_of(market: str) -> str:
    return "India" if market.startswith("India") else market


def ar1(n, sd, phi=0.6):
    e = rng.normal(0, sd * np.sqrt(1 - phi ** 2), n)
    x = np.zeros(n)
    x[0] = rng.normal(0, sd)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def calendar_table() -> pd.DataFrame:
    rows = []
    for name, reg, a, b in EVENTS:
        for d in pd.date_range(a, b):
            if START <= d <= END:
                rows.append((d, name, reg))
    for reg, spans in SUMMER.items():
        for a, b in spans:
            for d in pd.date_range(a, b):
                rows.append((d, "summer", reg))
    return pd.DataFrame(rows, columns=["date", "event", "region"])


CAL = calendar_table()


def seasonal_factor(vertical: str, market: str) -> np.ndarray:
    """Calendar x weekly x yearly trend multiplier for one market."""
    country, reg = country_of(market), region_of(market)
    f = np.ones(N)
    sub = CAL[(CAL.region == reg) | (CAL.region == country) | (CAL.region == "All")]
    idx = (sub.date - START).dt.days.to_numpy()
    for i, ev in zip(idx, sub.event):
        f[i] *= 1 + LIFT[vertical].get(ev, 0)
    dow = DATES.day_of_week.to_numpy()
    wk = np.isin(dow, WEEKEND[country])
    f *= np.where(wk, 1.10 if vertical in ("retail", "qsr", "streaming") else 0.92, 1.0)
    f *= 1 + 0.10 * np.arange(N) / 365            # +10% a year organic growth
    return f


def lag_pmf(mean: float, window: int) -> np.ndarray:
    """Click-to-conversion lag (days), geometric, truncated at the attribution window."""
    p = 1 / (1 + mean)
    k = np.arange(window + 1)
    pmf = p * (1 - p) ** k
    return pmf / pmf.sum()


def ramp(go: pd.Timestamp, days: int) -> np.ndarray:
    """0 before go-live, linear 0->1 over the ramp-up days, 1 after."""
    t = (DATES - go).days.to_numpy().astype(float)
    return np.clip((t + 1) / days, 0, 1) * (t >= 0)


def learning_dip(go: pd.Timestamp, days: int, depth=.15) -> np.ndarray:
    """Learning phase: delivery is less efficient right after the change, fading over the ramp-up."""
    t = (DATES - go).days.to_numpy()
    on = (t >= 0) & (t < days)
    return np.where(on, 1 - depth * (1 - (t + 1) / days), 1.0)


# ------------------------------------------------------------------ business truth
def business_and_geo():
    biz, geo = [], []
    effects = {}   # (client, market) -> business multiplier series
    for uc in USE_CASES:
        uid, c, m, _, _, go, rd, _, b, _ = uc
        if b and c != "C6":
            effects[(c, m)] = 1 + b * ramp(pd.Timestamp(go), rd)
    for c, spec in CLIENTS.items():
        common = ar1(N, .035)                                      # shocks shared by all markets of a client
        if c == "C6":
            continue
        for m, base in spec["markets"].items():
            mult = seasonal_factor(spec["vertical"], m) * np.exp(common + ar1(N, .018, .3))
            mult *= effects.get((c, m), 1.0)
            orders = rng.poisson(base * mult)
            rev = orders * spec["aov"] * np.exp(rng.normal(0, .02, N))
            biz.append(pd.DataFrame({"date": DATES, "client": c, "market": m, "orders": orders, "revenue": rev.round(2)}))
    # C6 travel: region level, the geo test lives here
    spec = CLIENTS["C6"]
    common = {k: ar1(N, .04) for k in ("KSA", "UAE", "India")}
    eff = 1 + .05 * ramp(pd.Timestamp("2026-07-05"), 7) * (DATES <= GEO_END) \
        + .05 * ramp(GEO_END + pd.Timedelta(days=1), 7) * (DATES > GEO_END)       # after the test: everyone gets GTG
    eff_ctrl = 1 + .05 * ramp(GEO_END + pd.Timedelta(days=1), 7) * (DATES > GEO_END)
    for r, (country, base) in REGIONS.items():
        mult = seasonal_factor("travel", country) * np.exp(common[country] + ar1(N, .035, .3))
        mult *= eff if r in TREATED else eff_ctrl
        bookings = rng.poisson(base * mult)
        rev = bookings * spec["aov"] * np.exp(rng.normal(0, .03, N))
        geo.append(pd.DataFrame({"date": DATES, "client": "C6", "region": r, "country": country,
                                 "geo_group": "treated" if r in TREATED else "control",
                                 "bookings": bookings, "revenue": rev.round(2)}))
    geo = pd.concat(geo, ignore_index=True)
    c6 = geo.groupby(["date", "country"], as_index=False)[["bookings", "revenue"]].sum() \
        .rename(columns={"country": "market", "bookings": "orders"}).assign(client="C6")
    biz = pd.concat(biz + [c6[["date", "client", "market", "orders", "revenue"]]], ignore_index=True)
    return biz, geo


# ------------------------------------------------------------------ ads + signals
def platform_multipliers(c, m, p):
    """Return (reported multiplier on conversions, dedup duplication factor, emq series, use-case row or None)."""
    rep, dup, emq = np.ones(N), np.ones(N), None
    hit = None
    for uc in USE_CASES:
        uid, cc, mm, case, pp, go, rd, r, b, (e0, e1) = uc
        go = pd.Timestamp(go)
        if cc != c or pp != p:
            continue
        if uid == "UC8":     # geo: treated share of the country, approximated on country totals
            share = sum(REGIONS[x][1] for x in TREATED if REGIONS[x][0] == m) / sum(v[1] for v in REGIONS.values() if v[0] == m)
            k = ramp(go, rd) * (DATES <= GEO_END) * share + ramp(GEO_END + pd.Timedelta(days=1), 7) * (DATES > GEO_END)
            # reported change = signal recovery on top of the business change already in the orders
            rep *= 1 + ((1 + r) / (1 + b) - 1) * k
            hit = uc
            continue
        if mm != m:
            continue
        hit = uc
        k = ramp(go, rd)
        if uid == "UC2":                                    # broken dedup: duplicates, no signal recovered
            broken = (DATES >= go) & (DATES < DEDUP_FIX)
            dup = np.where(broken, 1 + r * k, 1.0)
        else:
            rep *= 1 + ((1 + r) / (1 + b) - 1) * k             # signal recovered beyond the business change
        rep *= learning_dip(go, rd)
        if e0 is not None:
            emq = e0 + (e1 - e0) * k
    return rep, dup, emq, hit


def ads_and_signals(biz: pd.DataFrame):
    ads, sig = [], []
    for c, spec in CLIENTS.items():
        for m in spec["markets"]:
            orders = biz[(biz.client == c) & (biz.market == m)].sort_values("date").orders.to_numpy().astype(float)
            vol = orders.mean()
            season = seasonal_factor(spec["vertical"], m)
            for p, (share, spend0) in spec["platforms"].items():
                if m.startswith("India") and p == "TikTok":
                    continue
                window, setting0 = WINDOW[p]
                rep, dup, emq, hit = platform_multipliers(c, m, p)
                mscale = (vol / sum(spec["markets"].values())) if c != "C6" else 1 / 3
                spend_day = spend0 * mscale * 2 * (0.6 + 0.4 * season / season.mean()) * np.exp(ar1(N, .06, .5))
                setting = np.full(N, setting0, dtype=object)
                if (c, p) == WINDOW_CHANGE[:2]:
                    setting[DATES >= WINDOW_CHANGE[2]] = WINDOW_CHANGE[3]
                pmf = lag_pmf(spec["lag"], window)
                cdf = np.cumsum(pmf)
                for camp, w, eff in (("Prospecting", .65, .8), ("Retargeting", .35, 1.37)):
                    spend = spend_day * w
                    cpm = {"Meta": 6.5, "Google Ads": 9.0, "Snapchat": 4.0, "TikTok": 5.0}[p] * np.exp(rng.normal(0, .05, N))
                    imps = spend / cpm * 1000
                    ctr = {"Meta": .011, "Google Ads": .035, "Snapchat": .006, "TikTok": .009}[p] * (1.6 if camp == "Retargeting" else 1)
                    clicks = rng.binomial(imps.astype(np.int64), ctr)
                    # cohort conversions by click/impression date (complete), default window
                    lam = orders * share * w * eff * rep * dup * np.exp(rng.normal(0, .05, N))
                    view = lam * VIEW_SHARE[p]
                    click = lam - view
                    click_full = rng.poisson(click).astype(float)
                    view_full = rng.poisson(view).astype(float)
                    # what the platform shows on 31 Oct 2026 by click date: recent cohorts are still incomplete
                    age = (EXTRACT - DATES).days.to_numpy()
                    seen = cdf[np.minimum(age, window)]
                    click_seen = np.round(click_full * seen)
                    # by conversion date: spread each cohort over its lag
                    click_conv_date = np.convolve(click_full, pmf)[:N].round()
                    use_view = np.array([s.endswith("1d_view") for s in setting])
                    conv = click_seen + np.where(use_view, view_full, 0)
                    conv_cd = click_conv_date + np.where(use_view, view_full, 0)
                    aov = spec["aov"] * np.exp(rng.normal(0, .03, N))
                    ads.append(pd.DataFrame({
                        "date": DATES, "client": c, "market": m, "platform": p, "campaign": camp,
                        "spend": spend.round(2), "impressions": imps.round().astype(np.int64), "clicks": clicks,
                        "attribution_setting": setting, "conv_click": click_seen, "conv_view": view_full,
                        "conversions": conv, "conversions_by_conv_date": conv_cd,
                        "conv_value": (conv * aov).round(2), "conv_value_by_conv_date": (conv_cd * aov).round(2)}))
                # signals: events sent to the platform (all purchases the tag sees, not only attributed ones)
                cov_b = {"Meta": .68, "Google Ads": .74, "Snapchat": .66, "TikTok": .67}[p] * np.exp(rng.normal(0, .02, N))
                srv_on = np.zeros(N)
                id_share = np.full(N, .97)
                if hit is not None and hit[0] != "UC8":
                    srv_on = ramp(pd.Timestamp(hit[5]), hit[6])
                    if hit[0] == "UC2":
                        id_share = np.where(DATES < DEDUP_FIX, 0.0, .97)
                if hit is not None and hit[0] == "UC8":
                    srv_on = np.zeros(N)                          # GTG serves the same tag first-party: no server stream
                    cov_b = cov_b * rep                          # more browser hits survive blockers
                browser = rng.poisson(orders * cov_b)
                server = rng.poisson(orders * .90 * srv_on)
                overlap = np.minimum(browser, server) * .97        # same purchase seen by both streams
                removed = np.round(overlap * id_share)
                if emq is None:
                    base = {"Meta": 5.6, "Google Ads": np.nan, "Snapchat": 5.0, "TikTok": 4.8}[p]
                    emq = np.full(N, base)
                emq_obs = np.clip(emq + rng.normal(0, .12, N), 0, 10).round(1) if p != "Google Ads" else np.full(N, np.nan)
                match = np.clip(.30 + .055 * np.nan_to_num(emq_obs, nan=6.2) + rng.normal(0, .01, N), 0, 1)
                sig.append(pd.DataFrame({
                    "date": DATES, "client": c, "market": m, "platform": p,
                    "browser_events": browser, "server_events": server,
                    "server_events_with_event_id": np.round(server * id_share).astype(np.int64),
                    "duplicates_removed": removed.astype(np.int64),
                    "events_after_dedup": (browser + server - removed).astype(np.int64),
                    "emq": emq_obs, "match_rate": match.round(3)}))
    return pd.concat(ads, ignore_index=True), pd.concat(sig, ignore_index=True)


# ------------------------------------------------------------------ GA4 (client A, server-side tagging)
def ga4(biz: pd.DataFrame) -> pd.DataFrame:
    rows = []
    k = ramp(pd.Timestamp("2025-06-15"), 7)
    for m in CLIENTS["C1"]["markets"]:
        orders = biz[(biz.client == "C1") & (biz.market == m)].sort_values("date").orders.to_numpy()
        visitors = orders / .021                                  # ~2.1% conversion rate
        sessions = rng.poisson(visitors * 1.45 * .80 * (1 + .09 * k))   # 20% of sessions lost to blockers before; +9% back
        # cookie life: before server-side cookies, part of returning users look new (ITP caps cookies at 7 days)
        true_new = .42
        misread = .16 * (1 - k)                                   # share of returning users counted as new
        users = visitors * .80 * (1 + .09 * k) / (1 + .25 * k * 0)  # users seen by GA4
        new = rng.poisson(users * (true_new + (1 - true_new) * misread))
        ret = rng.poisson(users * (1 - true_new) * (1 - misread))
        unassigned = rng.binomial(sessions, .085 - .045 * k)       # sessions with no source (lost click IDs)
        purchases = rng.poisson(orders * .80 * (1 + .07 * k))
        rows.append(pd.DataFrame({"date": DATES, "client": "C1", "market": m, "sessions": sessions, "new_users": new,
                                  "returning_users": ret, "unassigned_sessions": unassigned, "ga4_purchases": purchases}))
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------ use cases + hidden truth
def use_case_table() -> pd.DataFrame:
    rows = []
    for uid, c, m, case, p, go, rd, r, b, _ in USE_CASES:
        go = pd.Timestamp(go)
        rows.append({"use_case_id": uid, "client": c, "client_label": CLIENTS[c]["label"], "market": m,
                     "control_market": {"C1": "UAE", "C2": "KSA", "C3": "UAE", "C4": "India-iOS", "C5": "KSA"}.get(c, "Control regions")
                     if uid != "UC6" else "none (site-wide)",
                     "use_case": case, "platform": p, "go_live": go, "ramp_up_days": rd,
                     "ramp_up_end": go + pd.Timedelta(days=rd - 1),
                     "read_start": go + pd.Timedelta(days=rd),
                     "read_end": min(go + pd.Timedelta(days=rd + 55),
                                     {"UC8": GEO_END, "UC2": DEDUP_FIX - pd.Timedelta(days=1)}.get(uid, END))})
    return pd.DataFrame(rows)


def hidden_truth() -> pd.DataFrame:
    t = [
        (1, "UC1", "True uplift", "Meta-reported conversions +18%, client revenue only +4% (signal recovered vs value)", .18, .04),
        (2, "UC2", "Broken deduplication", "Server events sent without event_id until 26 Oct 2025: reported +35%, all duplicates", .35, .0),
        (3, "UC1", "Ramp-up", "10-day learning phase after go-live (dip then recovery) must be excluded", None, None),
        (4, "UC4", "Seasonal false signal", "Read window falls on Ramadan 2026: naive pre/post up, no business effect", .06, .0),
        (5, "UC7", "Attribution window change", "Meta setting 7d click + 1d view -> 7d click on 14 Jun 2026: reported drop, not real", .10, .06),
        (6, "UC5", "EMQ up, no value", "EMQ 4.6 -> 8.3 on App CAPI with no business effect", .05, .0),
        (7, "UC8", "Geo test", "Google Tag Gateway as bidding signal in 6 treated regions: bookings +5%", .11, .05),
        (8, "ALL", "Click-date lag", "Conversions by click date incomplete for the last weeks before 31 Oct 2026", None, None),
    ]
    return pd.DataFrame(t, columns=["event", "use_case_id", "trap", "truth", "true_reported_change", "true_business_change"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    biz, geo = business_and_geo()
    ads, sig = ads_and_signals(biz)
    tables = {"business_daily": biz, "geo_daily": geo, "ads_daily": ads, "signals_daily": sig, "ga4_daily": ga4(biz),
              "use_cases": use_case_table(), "calendar": CAL,
              "clients": pd.DataFrame([{"client": c, "client_label": s["label"], "vertical": s["vertical"], "aov_usd": s["aov"]}
                                       for c, s in CLIENTS.items()])}
    for name, df in tables.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name:15s} {df.shape}")
    hidden_truth().to_csv(ROOT / "data" / "_hidden_truth.csv", index=False)


if __name__ == "__main__":
    main()

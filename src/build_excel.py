"""Build excel/analysis_tracker.xlsx: Tracker, Pre/post calculator, Lift power, Evidence checklist.

All results are live Excel formulas on input cells (blue); the inputs come from data/output. The same cells are
recomputed in Python at the end (fallback when Excel is not at hand) and printed. Workbook metadata is left empty.
    python src/build_excel.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUTD, PROC = ROOT / "data" / "output", ROOT / "data" / "processed"
XL = ROOT / "excel" / "analysis_tracker.xlsx"

HEAD = PatternFill("solid", fgColor="2A78D6")
INPUT = Font(color="1C5CAB")
BOLD = Font(bold=True)
WHITE = Font(bold=True, color="FFFFFF")
THIN = Border(bottom=Side(style="thin", color="E1E0D9"))
GOOD = PatternFill("solid", fgColor="DDF3EA")
BAD = PatternFill("solid", fgColor="FBE9E0")


def header(ws, row, cols):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=j, value=c)
        cell.fill, cell.font = HEAD, WHITE
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def widths(ws, w):
    for col, v in w.items():
        ws.column_dimensions[col].width = v


CHECKS = [
    ("Read plan written before go-live (baseline, ramp-up, window, KPI, minimum effect)", "must"),
    ("Ramp-up / learning phase excluded", "must"),
    ("Control market, region or group (or platform lift study)", "must"),
    ("Control metric checked flat", "should"),
    ("Same attribution setting before/after; changes logged", "must"),
    ("Date basis stated; no read ending in an incomplete lag period", "must"),
    ("event_id coverage > 90% on server events; conversions per order stable", "must"),
    ("Seasonality: last year or persistence read when > 25% of window is a peak", "must"),
    ("95% interval plus placebo or power check", "must"),
    ("Business outcome from the client system reported", "must"),
    ("Health metrics (EMQ, match rate) kept out of value", "must"),
    ("Every number traced (check_numbers.py)", "must"),
    ("Other changes in the period disclosed", "should"),
    ("Limits and next step written", "should"),
]


def tracker(wb, reads, geo, ver):
    ws = wb.active
    ws.title = "Tracker"
    ws["A1"] = "Analysis tracker · SIMULATED clients · one row per use case read"
    ws["A1"].font = Font(bold=True, size=13)
    cols = ["ID", "Client", "Use case", "Platform", "Market", "Control", "Go-live", "Ramp-up (days)", "Read start", "Read end",
            "Method", "Status", "Reported effect", "Business effect", "Business 95% low", "Business 95% high",
            "Interval excludes 0", "Verdict", "Checklist score", "Evidence complete"]
    header(ws, 3, cols)
    rows = []
    for _, r in reads.iterrows():
        rows.append([r.use_case_id, r.client_label, r.use_case, r.platform, r.market, r.control_market, r.go_live,
                     int(r.ramp_up_days), r.read_start, r.read_end, "Causal impact on ratio to control + in-time placebos",
                     "Closed", r.reported_effect, r.business_effect, r.business_lo, r.business_hi])
    rows.append(["UC8", "Client F · Travel", "Google Tag Gateway", "Google Ads", "6 treated regions", "18 control regions",
                 "2026-07-05", 7, "2026-07-12", "2026-08-29", "Geo test, synthetic control + 300 placebo groups", "Closed",
                 None, geo["effect"], geo["lo"], geo["hi"]])
    rows.append(["UC6", "Client A · Retail", "GA4 server-side", "GA4", "KSA+UAE", "none (site-wide)", "2025-06-15", 7,
                 "2025-06-22", "2025-08-16", "Before/after on ratios to client orders", "Closed", None, None, None, None])
    vmap = ver.set_index("use_case_id").verdict
    order = {u: i for i, u in enumerate(["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"])}
    rows.sort(key=lambda x: order[x[0]])
    for i, row in enumerate(rows):
        rr = 4 + i
        for j, v in enumerate(row, 1):
            c = ws.cell(row=rr, column=j, value=v)
            if j in (13, 14, 15, 16) and v is not None:
                c.number_format = "+0.0%;-0.0%;0.0%"
                c.font = INPUT
        ws.cell(row=rr, column=17, value=f'=IF(OR(O{rr}="",P{rr}=""),"n/a",IF(OR(O{rr}>0,P{rr}<0),"Yes","No"))')
        ws.cell(row=rr, column=18, value=vmap.get(row[0], ""))
        letter = "CDEFGHIJ"[order[row[0]]]          # column of this use case in the checklist
        ws.cell(row=rr, column=19, value=f"='Evidence checklist'!{letter}20")
        ws.cell(row=rr, column=20, value=f"='Evidence checklist'!{letter}21")
    n = 4 + len(rows) - 1
    ws.conditional_formatting.add(f"T4:T{n}", CellIsRule(operator="equal", formula=['"Yes"'], fill=GOOD))
    ws.conditional_formatting.add(f"T4:T{n}", CellIsRule(operator="equal", formula=['"No"'], fill=BAD))
    ws[f"A{n + 2}"] = "Summary"
    ws[f"A{n + 2}"].font = BOLD
    ws[f"A{n + 3}"], ws[f"C{n + 3}"] = "Reads with an interval excluding 0", f'=COUNTIF(Q4:Q{n},"Yes")'
    ws[f"A{n + 4}"], ws[f"C{n + 4}"] = "Reads with complete evidence", f'=COUNTIF(T4:T{n},"Yes")'
    ws[f"A{n + 5}"], ws[f"C{n + 5}"] = "Average reported effect (reads with both)", f"=AVERAGEIFS(M4:M{n},M4:M{n},\"<>\",N4:N{n},\"<>\")"
    ws[f"A{n + 6}"], ws[f"C{n + 6}"] = "Average business effect (same reads)", f"=AVERAGEIFS(N4:N{n},M4:M{n},\"<>\",N4:N{n},\"<>\")"
    for c in (f"C{n + 5}", f"C{n + 6}"):
        ws[c].number_format = "+0.0%"
    widths(ws, {"A": 6, "B": 26, "C": 22, "D": 12, "E": 16, "F": 18, "G": 11, "H": 9, "I": 11, "J": 11, "K": 34, "L": 8,
                "M": 10, "N": 10, "O": 10, "P": 10, "Q": 10, "R": 40, "S": 10, "T": 10})
    ws.freeze_panes = "C4"
    return rows


def prepost(wb):
    ws = wb.create_sheet("Pre-post calculator")
    ws["A1"] = "Pre/post calculator · daily means from sql/02_pre_post.sql · SIMULATED"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = "Blue cells are inputs. Ramp-up days are already excluded from both windows. The interval uses the weekly noise of the treated/control log-ratio before go-live."
    q = pd.read_csv(OUTD / "sql_02_pre_post.csv")
    biz = pd.read_parquet(PROC / "business_daily.parquet")
    uc = pd.read_parquet(PROC / "use_cases.parquet").set_index("use_case_id")
    cols = ["ID", "Treated baseline (orders/day)", "Treated read", "Control baseline", "Control read", "Ramp-up days excluded",
            "Weekly sd of log ratio (pre)", "Lag-1 autocorrelation", "Baseline weeks", "Read weeks",
            "Naive change", "Change vs control", "Std error", "95% low", "95% high", "Significant"]
    header(ws, 4, cols)
    out = []
    for i, r in enumerate(q.itertuples()):
        u = uc.loc[r.use_case_id]
        t = biz[(biz.client == u.client) & (biz.market == u.market)].set_index("date").orders
        c = biz[(biz.client == u.client) & (biz.market == u.control_market)].set_index("date").orders
        bs, be = u.go_live - pd.Timedelta(days=56), u.go_live - pd.Timedelta(days=1)
        vals = [t.loc[bs:be].mean(), t.loc[u.read_start:u.read_end].mean(), c.loc[bs:be].mean(), c.loc[u.read_start:u.read_end].mean()]
        pre = np.log(t.loc[:be] / c.loc[:be]).iloc[-364:]
        wk = pre.groupby(np.arange(len(pre)) // 7).mean()
        sd, rho = float(wk.std()), float(np.corrcoef(wk[1:], wk[:-1])[0, 1])
        nb, nr = 8, round(((u.read_end - u.read_start).days + 1) / 7, 1)
        rr = 5 + i
        row = [r.use_case_id, *[round(v, 1) for v in vals], int(u.ramp_up_days), round(sd, 4), round(rho, 3), nb, nr]
        for j, v in enumerate(row, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j > 1:
                cell.font = INPUT
        ws.cell(row=rr, column=11, value=f"=C{rr}/B{rr}-1")
        ws.cell(row=rr, column=12, value=f"=(C{rr}/B{rr})/(E{rr}/D{rr})-1")
        ws.cell(row=rr, column=13, value=f"=G{rr}*SQRT(1/I{rr}+1/J{rr})*SQRT((1+MAX(H{rr},0))/(1-MAX(H{rr},0)))")
        ws.cell(row=rr, column=14, value=f"=(1+L{rr})*EXP(-1.96*M{rr})-1")
        ws.cell(row=rr, column=15, value=f"=(1+L{rr})*EXP(1.96*M{rr})-1")
        ws.cell(row=rr, column=16, value=f'=IF(OR(N{rr}>0,O{rr}<0),"Yes","No")')
        for col in (11, 12, 14, 15):
            ws.cell(row=rr, column=col).number_format = "+0.0%;-0.0%"
        ws.cell(row=rr, column=13).number_format = "0.000"
        # python recomputation of the same cells
        ctrl = (vals[1] / vals[0]) / (vals[3] / vals[2]) - 1
        se = sd * np.sqrt(1 / nb + 1 / nr) * np.sqrt((1 + max(rho, 0)) / (1 - max(rho, 0)))
        out.append((r.use_case_id, vals[1] / vals[0] - 1, ctrl, (1 + ctrl) * np.exp(-1.96 * se) - 1, (1 + ctrl) * np.exp(1.96 * se) - 1))
    n = 5 + len(q)
    ws[f"A{n + 1}"] = ("Reading: 'Naive change' compares the treated market with itself; 'Change vs control' divides by what the control "
                       "market did over the same weeks (difference-in-differences on ratios). Season, sales and market trends cancel out.")
    widths(ws, {c: 13 for c in "ABCDEFGHIJKLMNOP"})
    return out


def power(wb, c):
    ws = wb.create_sheet("Lift power")
    ws["A1"] = "Lift study and geo test sizing"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A3"], ws["B3"] = "Baseline conversion rate (Criteo control, PUBLIC DATA)", round(c["cr_control"], 6)
    ws["A4"], ws["B4"] = "Significance (two-sided)", 0.05
    ws["A5"], ws["B5"] = "Power", 0.8
    ws["A6"], ws["B6"] = "Control share of users", 0.15
    for a in ("B3", "B4", "B5", "B6"):
        ws[a].font = INPUT
    ws["B3"].number_format = "0.000%"
    header(ws, 8, ["Relative lift to detect", "Test rate", "Control users needed", "Test users needed", "Total users"])
    lifts = [0.02, 0.05, 0.10, 0.20, round(c["itt_rel"], 2)]
    for i, l in enumerate(lifts):
        r = 9 + i
        ws.cell(row=r, column=1, value=l).number_format = "0%"
        ws.cell(row=r, column=1).font = INPUT
        ws.cell(row=r, column=2, value=f"=$B$3*(1+A{r})").number_format = "0.000%"
        # n_test with k = control/test ratio: n_test = (za+zb)^2 * (p0(1-p0)/k + p1(1-p1)) / (p1-p0)^2
        k = "($B$6/(1-$B$6))"
        ws.cell(row=r, column=4, value=f"=ROUNDUP((NORM.S.INV(1-$B$4/2)+NORM.S.INV($B$5))^2*($B$3*(1-$B$3)/{k}+B{r}*(1-B{r}))/(B{r}-$B$3)^2,0)")
        ws.cell(row=r, column=3, value=f"=ROUND(D{r}*{k},0)")
        ws.cell(row=r, column=5, value=f"=C{r}+D{r}")
        for col in (3, 4, 5):
            ws.cell(row=r, column=col).number_format = "#,##0"
    ws["A15"] = "Geo test minimum detectable effect (synthetic control gap, SIMULATED client F)"
    ws["A15"].font = BOLD
    g = json.loads((OUTD / "headline.json").read_text(encoding="utf-8"))["geo"]
    ws["A16"], ws["B16"] = "Weekly sd of log gap (pre-period)", round(g["gap_sd"], 4)
    ws["A17"], ws["B17"] = "Lag-1 autocorrelation", round(g["gap_rho"], 3)
    for a in ("B16", "B17"):
        ws[a].font = INPUT
    header(ws, 19, ["Test weeks", "Minimum detectable effect"])
    for i, w in enumerate([4, 7, 10, 13]):
        r = 20 + i
        ws.cell(row=r, column=1, value=w).font = INPUT
        ws.cell(row=r, column=2, value=f"=(NORM.S.INV(1-$B$4/2)+NORM.S.INV($B$5))*$B$16*SQRT((1+MAX($B$17,0))/(1-MAX($B$17,0)))/SQRT(A{r})").number_format = "0.0%"
    widths(ws, {"A": 52, "B": 16, "C": 20, "D": 20, "E": 16})
    # python recomputation
    za, zb = stats.norm.ppf(0.975), stats.norm.ppf(0.8)
    p0, kk = c["cr_control"], 0.15 / 0.85
    rec = []
    for l in lifts:
        p1 = p0 * (1 + l)
        nt = np.ceil((za + zb) ** 2 * (p0 * (1 - p0) / kk + p1 * (1 - p1)) / (p1 - p0) ** 2)
        rec.append((l, round(nt * kk), int(nt)))
    infl = np.sqrt((1 + max(g["gap_rho"], 0)) / (1 - max(g["gap_rho"], 0)))
    rec_geo = [(w, (za + zb) * g["gap_sd"] * infl / np.sqrt(w)) for w in (4, 7, 10, 13)]
    return rec, rec_geo


def checklist(wb, rows):
    ws = wb.create_sheet("Evidence checklist")
    ws["A1"] = "Evidence checklist · Y / N per analysis (docs/EVIDENCE_STANDARD.md)"
    ws["A1"].font = Font(bold=True, size=13)
    ids = ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]
    header(ws, 3, ["Check", "Level"] + ids)
    # answers per analysis (UC6 = GA4: no control market and no interval; UC2 fails dedup until fixed)
    ans = {u: ["Y"] * len(CHECKS) for u in ids}
    ans["UC2"][6] = "N"
    ans["UC6"][2] = "N"
    ans["UC6"][8] = "N"
    ans["UC4"][7] = "Y"
    dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=False)
    ws.add_data_validation(dv)
    for i, (check, level) in enumerate(CHECKS):
        r = 4 + i
        ws.cell(row=r, column=1, value=check).alignment = Alignment(wrap_text=True)
        ws.cell(row=r, column=2, value=level)
        for j, u in enumerate(ids):
            cell = ws.cell(row=r, column=3 + j, value=ans[u][i])
            cell.font = INPUT
            dv.add(cell)
    last = 4 + len(CHECKS) - 1
    ws.cell(row=19, column=1, value="Weights: must = 2, should = 1").font = BOLD
    ws.cell(row=20, column=1, value="Score (weighted share of checks passed)").font = BOLD
    ws.cell(row=21, column=1, value="Publishable (every 'must' passed)").font = BOLD
    for j in range(len(ids)):
        col = "CDEFGHIJ"[j]
        ws[f"{col}20"] = (f'=(2*COUNTIFS($B$4:$B${last},"must",{col}4:{col}{last},"Y")+COUNTIFS($B$4:$B${last},"should",{col}4:{col}{last},"Y"))'
                          f'/(2*COUNTIF($B$4:$B${last},"must")+COUNTIF($B$4:$B${last},"should"))')
        ws[f"{col}20"].number_format = "0%"
        ws[f"{col}21"] = f'=IF(COUNTIFS($B$4:$B${last},"must",{col}4:{col}{last},"N")=0,"Yes","No")'
    ws.conditional_formatting.add("C21:J21", CellIsRule(operator="equal", formula=['"Yes"'], fill=GOOD))
    ws.conditional_formatting.add("C21:J21", CellIsRule(operator="equal", formula=['"No"'], fill=BAD))
    ws.conditional_formatting.add(f"C4:J{last}", CellIsRule(operator="equal", formula=['"N"'], fill=BAD))
    widths(ws, {"A": 70, "B": 8, **{c: 7 for c in "CDEFGHIJ"}})
    must = [l == "must" for _, l in CHECKS]
    rec = {}
    for u in ids:
        y = [a == "Y" for a in ans[u]]
        score = sum((2 if m else 1) for m, ok in zip(must, y) if ok) / sum(2 if m else 1 for m in must)
        rec[u] = (round(score, 3), "Yes" if all(ok for m, ok in zip(must, y) if m) else "No")
    return rec


def main():
    XL.parent.mkdir(parents=True, exist_ok=True)
    reads = pd.read_csv(OUTD / "use_case_reads.csv")
    ver = pd.read_csv(OUTD / "verdicts.csv")
    h = json.loads((OUTD / "headline.json").read_text(encoding="utf-8"))
    wb = Workbook()
    rows = tracker(wb, reads, h["geo"], ver)
    pp = prepost(wb)
    pw, pg = power(wb, h["criteo"])
    ck = checklist(wb, rows)
    for k in ("creator", "lastModifiedBy", "title", "subject", "description", "keywords", "category"):
        setattr(wb.properties, k, "")
    wb.save(XL)
    print("written", XL.relative_to(ROOT))
    print("Python recomputation of the formula cells:")
    for u, n, c, lo, hi in pp:
        print(f"  {u}: naive {n:+.1%}, vs control {c:+.1%} (95% {lo:+.1%} to {hi:+.1%})")
    for l, nc, nt in pw:
        print(f"  lift {l:.0%}: control {nc:,}, test {nt:,}")
    for w, m in pg:
        print(f"  geo {w} weeks: MDE {m:.1%}")
    print("  checklist:", ck)


if __name__ == "__main__":
    main()

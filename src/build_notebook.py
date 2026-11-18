"""Build and execute notebooks/measurement.ipynb (the single notebook of the study).

    python src/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "measurement.ipynb"

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Proving what first-party signals are worth, without fooling ourselves

One notebook, two kinds of data:

* **PUBLIC DATA**: the Criteo Uplift Prediction Dataset v2.1, a real randomised ad-incrementality test
  (~14 million users, CC BY-NC-SA 4.0). Only aggregates are used here (`sql/01_criteo_lift.sql`).
* **SIMULATED**: six fictional clients of a first-party signal platform (`src/simulate.py`, seed 42), with eight
  measurement traps planted. Not Datahash's data, not any client's data.

Every number of the report, the dashboard, the workbook and the client deliverables comes from `src/analysis.py`,
which this notebook calls and explains.
""")
code("""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import analysis as A
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")
OUT, PROC = ROOT / "data" / "output", ROOT / "data" / "processed"
H = json.loads((OUT / "headline.json").read_text(encoding="utf-8"))
""")

md("""
## 1. Exposed is not incremental (Criteo, PUBLIC DATA)

Users were randomly split: 85% *eligible* to see the ads (treatment), 15% held out (control). Only a small share of
the eligible users were actually reached (`exposure`).

**Intention to treat (ITT)**: compare the two randomised groups as a whole. Randomisation makes them identical except
for the ads, so the difference is caused by the ads. Interval: normal approximation for two proportions; relative
lift interval by the delta method on log(p1/p0).
""")
code("""
g = pd.read_parquet(PROC / "criteo_by_group.parquet").set_index("treatment")
n0, n1 = g.loc[0, "users"], g.loc[1, "users"]
p0, p1 = g.loc[0, "conversion_rate"], g.loc[1, "conversion_rate"]
se = np.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
se_log = np.sqrt((1 - p0) / (n0 * p0) + (1 - p1) / (n1 * p1))
print(f"control {p0:.4%} vs treatment {p1:.4%}  ->  ITT +{p1 - p0:.4%} points")
print(f"relative lift {p1 / p0 - 1:+.1%}  (95% {np.exp(np.log(p1 / p0) - 1.96 * se_log) - 1:+.1%} to {np.exp(np.log(p1 / p0) + 1.96 * se_log) - 1:+.1%})")
""")
md("""
**Effect on the exposed (Wald estimator / CACE).** Nobody in the control group can be exposed, so the whole ITT effect
comes from the reached users: effect per reached user = ITT / exposure rate. This is still a randomised estimate.

**The trap**: comparing exposed with unexposed users inside the treatment group. The ad system chose whom to reach,
and it reached users who were already likely to convert.
""")
code("""
c = H["criteo"]
print(f"exposure rate in treatment: {c['exposure_rate']:.2%}")
print(f"effect per exposed user: +{c['cace']:.2%} points (95% {c['cace_lo']:.2%} to {c['cace_hi']:.2%})")
print(f"exposed users convert at {c['cr_exposed']:.2%}; without ads they would have converted at {c['counterfactual_exposed']:.2%}"
      f" -> +{c['cace_rel']:.0%} relative")
print(f"naive exposed vs unexposed ratio: x{c['naive_ratio']:.0f} (+{c['naive_rel']:.0%}), i.e. ~{c['naive_rel'] / c['cace_rel']:.0f} times the true effect")
print(f"share of exposed users' conversions caused by the ads: {c['incremental_share_exposed']:.0%}")
pd.read_parquet(PROC / "criteo_by_propensity.parquet").pivot(index="decile", columns="treatment", values=["exposure_rate", "conversion_rate"])
""")
md("""
Selection is visible in the deciles of a pre-treatment feature: the top two deciles hold most of the exposure **and**
the highest conversion rates *in the control group*, where nobody saw an ad.

**Power.** How many users does a lift study need? Two-proportion z-test, 5% two-sided, 80% power, 85/15 split.
""")
code("""pd.read_csv(OUT / "criteo_power.csv")""")

md("""
## 2. The simulated panel: naive reads vs controlled reads (SIMULATED)

`sql/02_pre_post.sql` computes, for each use case: the naive before/after change in the treated market, the change
relative to the control market (difference-in-differences on ratios), and the same weeks last year. Baseline = 8
weeks before go-live; ramp-up excluded; read window fixed in `use_cases`.
""")
code("""pd.read_csv(OUT / "sql_02_pre_post.csv")""")

md("""
## 3. Causal impact (structural time series), explained simply

1. Treated and control markets share the calendar (Ramadan, Eid, sales), so we model the **ratio** treated / control,
   by week, in logs. Holidays that hit only one of the two markets (national days) enter as a regressor.
2. Before go-live the ratio follows a slowly drifting **local level** (`statsmodels` `UnobservedComponents`).
3. We project the ratio over the read window 1,000 times with its uncertainty and multiply by the control: 1,000
   plausible "no change" paths. Effect = actual / counterfactual - 1; 95% interval = 2.5-97.5 percentiles.
4. **In-time placebos**: the same read at fake go-live dates in the pre-period (true effect = 0) shows how large an
   effect noise alone produces. Rule: retained only if the interval excludes 0 **and** placebo p < 0.05.
5. If more than 25% of the read window is a seasonal peak, the effect must also hold in the 8 following weeks.
""")
code("""
uc = pd.read_parquet(PROC / "use_cases.parquet").set_index("use_case_id")
r = uc.loc["UC1"]
biz = pd.read_parquet(PROC / "business_daily.parquet")
y = A.weekly(A.series(biz, "C1", "KSA"), r.go_live)
x = A.weekly(A.series(biz, "C1", "UAE"), r.go_live)
pre_b, post_b = A.windows(r)
ci, path = A.causal_impact(y, x, pre_b, post_b, X=A.calendar_exog("KSA", "UAE", r.go_live))
print({k: round(v, 4) for k, v in ci.items()})
path.tail(8)
""")
code("""
reads = pd.read_csv(OUT / "use_case_reads.csv")
reads[["use_case_id", "client_label", "use_case", "platform", "reported_naive", "reported_effect", "reported_lo", "reported_hi",
       "business_naive", "business_effect", "business_lo", "business_hi", "business_placebo_p", "season_overlap", "verdict"]]
""")

md("""
## 4. Breaking a great-looking uplift (SIMULATED)

**Broken deduplication** (`sql/03_dedup_check.sql`): server events without `event_id` cannot be matched to the pixel
copy, so each purchase counts twice.
""")
code("""
t = H["traps"]
pd.DataFrame({"dedup": t["dedup"]}).T
""")
md("""
**Ramp-up**: the first week after go-live (learning phase) vs the steady weeks. Including it dilutes the read.
""")
code("""
{k: (round(v["effect"], 4) if isinstance(v, dict) else v) for k, v in t["ramp"].items()}
""")
md("""
**Attribution window change** (`sql/04_attribution_changes.sql`): the account moved from 7-day click + 1-day view to
7-day click. The reported series breaks; the 7-day click column (unchanged) and client outcomes do not.

**Click date vs conversion date**: by click date, recent days are still filling up.

**EMQ**: signal health improved sharply with no effect on subscriptions. **GA4 server-side**: changes in GA4 counts,
read relative to client orders.
""")
code("""
pd.DataFrame({k: pd.Series(t[k]) for k in ("window", "lag", "emq", "season")})
""")
code("""pd.Series(t["ga4"])""")

md("""
## 5. Geo test: synthetic control and placebos (SIMULATED client F)

Six treated regions bid on the Google tag gateway conversion action; 18 control regions keep the old one.

* **Synthetic control**: non-negative weights summing to 1 on the control regions, chosen so the weighted mix tracks
  the treated regions over 78 pre-weeks (`scipy.optimize`, SLSQP). Effect = treated / synthetic - 1 over 7 test weeks.
* **Placebo groups**: 300 fake treated groups of 6 control regions, each with its own synthetic control from the other
  12. Their effects show the noise; the 95% interval is the estimate minus the placebo quantiles.
* **In-time placebo**: the same method on a fake go-live 20 weeks earlier.
* **Power, planned before the test**: minimum detectable effect from the pre-period noise of the gap.
""")
code("""
geo = H["geo"]
{k: geo[k] for k in ("effect", "lo", "hi", "p_value", "placebo_in_time", "naive_prepost", "did", "rmspe_pre", "mde_by_weeks", "top_donors")}
""")
code("""pd.read_csv(OUT / "geo_weights.csv")""")

md("""
## 6. Detection score

Each planted trap is checked by a rule that does not look at the truth; the hidden truth file (used once, deleted
before publication) then says whether the read was right and whether the 95% interval covered the programmed effect.
""")
code("""pd.read_csv(OUT / "detection.csv")""")
md("""
Reading: all eight traps are caught. One interval misses its truth: the CRM read of client C during Ramadan
(a small positive residual, true effect 0), which is why the seasonal persistence rule exists. Its persistence read did not hold, so the
uplift was not retained. A 95% interval is expected to miss about one time in twenty.
""")


def main():
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}
    ExecutePreprocessor(timeout=900, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(NB.parent)}})
    NB.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NB)
    print("written", NB.relative_to(ROOT))


if __name__ == "__main__":
    main()

# Evidence standard and quality checklist

Every impact analysis, renewal one-pager and published case study follows the same four-part structure and passes
the same checklist. The checklist is also a tab of `excel/analysis_tracker.xlsx`, where it is scored by formula.

## The four parts every claim needs

| Part | What it must say | Example (simulated client A) |
|---|---|---|
| **Baseline** | The metric, its level, the window, the source system. | Client orders in KSA, 8 weeks before 12 Apr 2026, from the order system. |
| **Intervention** | What changed, where, when, ramp-up excluded, what else changed at the same time. | Meta Web CAPI with `event_id` dedup, KSA only, live 12 Apr 2026, 10-day ramp-up excluded; no budget change. |
| **Result** | Effect with a 95% interval, against a control, over a window fixed before looking. | Orders +3.2% (95% +1.7% to +4.6%) vs the UAE control, 7 weeks. |
| **Attribution logic** | Why the change explains the result and what else could; which platform setting and which date basis. | Ratio to UAE removes the shared calendar; in-time placebos rarely reach 3%; Meta read on 7-day click, by click date, complete. |

## Checklist (a claim is publishable only when every "must" is ticked)

| # | Check | Level |
|---|---|---|
| 1 | Read plan (baseline, ramp-up, read window, KPI, minimum effect) written **before** go-live | must |
| 2 | Ramp-up / learning phase excluded from both windows | must |
| 3 | A control market, region or group, or a platform lift study | must |
| 4 | A control metric that the use case cannot move, checked flat | should |
| 5 | Same attribution setting before and after; any setting change logged | must |
| 6 | Date basis stated (click date vs conversion date); no read window ending in an incomplete lag period | must |
| 7 | `event_id` coverage above 90% on the server stream; conversions per order stable | must |
| 8 | Seasonality: same weeks last year, or a persistence read if > 25% of the window is a seasonal peak | must |
| 9 | 95% interval on the effect, plus placebo or power check | must |
| 10 | Business outcome (client system) reported, not only platform conversions | must |
| 11 | Signal-health metrics (EMQ, match rate, coverage) in their own section, never as value | must |
| 12 | Every number traceable to a query or a cell (checked by `src/check_numbers.py`) | must |
| 13 | Other changes in the period (budget, creative, pricing, promotions) disclosed | should |
| 14 | Limits and next measurement step written | should |

## Decision rules used in this study

1. **Retained as an incremental business effect** only if the 95% interval excludes zero **and** fewer than 5% of
   in-time placebos (fake go-live dates in the pre-period) produce an effect as large.
2. If more than 25% of the read window is a seasonal peak, the effect must also hold in the 8 following weeks.
3. Any week with server events but `event_id` coverage under 90% → the reported uplift is rejected until fixed.
4. A change of attribution setting inside the read → the read is redone on the setting that did not change.
5. Health metrics (EMQ, match rate) never enter the "value" section of a report.

## What we refuse to publish

- An uplift read on a window chosen after looking at the data.
- "Exposed vs unexposed" or "CAPI users vs pixel users" comparisons presented as incremental.
- A percentage-point change written as a percent change, or a ROAS figure presented as a CPA (or the reverse).
- An EMQ or match-rate gain presented as business value.
- Any number that `src/check_numbers.py` cannot trace to the fact sheet of the analysis.

## What a shared evidence template would let each published story show

The 16 case studies on datahash.com (read on 18 Nov 2026, coded in `data/processed/case_study_grid.csv`, brands
not named) already state the use case, the platform and, in 13 of 16, a quantified outcome. A shared template
would let each story also show the elements that turn a strong number into a proof a CMO can reuse:
the baseline level (shown in 2 of 16), the before/after window (6 of 16), a comparison group (2 of 16),
the attribution setting (0 of 16; one mentions an optimisation window), the ramp-up treatment (0 of 16) and an interval (0 of 16). Several stories
already go further than most of the industry: they disclose concurrent changes (4 of 16), report offline or CRM
outcomes (4 of 16) and label the figure as measured or attributed rather than incremental (4 of 16).

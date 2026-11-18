# Measurement playbook: one page per first-party use case

How to prove what a first-party signal use case is worth, platform by platform. Every read in this repository
follows this playbook; the evidence rules themselves are in [EVIDENCE_STANDARD.md](EVIDENCE_STANDARD.md).

**The one idea.** A server-side signal changes two different things:

1. **What the platform can see** (signal recovered): more conversions reported, better match keys, higher EMQ.
   This shows up within days, it is real, and it is *measurement*, not value.
2. **What the business gets** (incremental value): more orders or revenue in the client's own systems, because
   the bidding algorithm now learns from a fuller signal. This is smaller, slower, and needs a control.

A renewal story needs both, labelled separately. In the simulated panel of this study, Web CAPI raised
Meta-reported conversions by about 18% while client orders rose by about 3% (page 5 of the report).

---

## Common rules (all use cases)

| Step | Rule |
|---|---|
| Before go-live | Write the read plan: KPI, baseline window, ramp-up length, read window, control, minimum effect worth detecting. Freeze it in the tracker (`excel/analysis_tracker.xlsx`). |
| Baseline | 8 weeks before go-live; flag any campaign, budget, creative, pricing or site change in that window. |
| Ramp-up | Excluded from every comparison (lengths below). The learning phase depresses delivery and volatility is high. |
| Read window | 6 to 8 full weeks after the ramp-up, fixed in advance. Never end it in the last 3 weeks before the data pull when reading by click date. |
| Control | First choice: a market, app platform or region not yet migrated (staggered roll-out). Otherwise a geo test or a platform lift study. A control *metric* that the use case cannot move is always added. |
| Settings | Same attribution setting before and after (use the "compare attribution settings" columns or the 7-day click column). Note any change of setting. |
| Season | If more than 25% of the read window falls in Ramadan, Eid, White Friday, 11.11, Diwali or year-end sales, the effect must also hold in the 8 weeks after. |
| Dedup | Check `event_id` coverage on the server stream (target above 90%) and the conversions-per-order ratio before any uplift claim. |
| Business truth | Orders and revenue from the client's own systems (OMS, CRM, POS) are the outcome. Platform conversions are a diagnostic. |

---

## Web CAPI (Meta, Snapchat, TikTok)

| | |
|---|---|
| **Should move** | Platform-reported conversions and conversion value (signal recovered); then CPA and reported ROAS; then client orders and revenue (incremental). |
| **Should not move (controls)** | Client orders in the control market; conversions on platforms without CAPI; sessions and traffic. If orders move everywhere, it is not CAPI. |
| **Signal health** | `event_id` coverage on server events, dedup rate, EMQ (Meta, TikTok) or Event Quality Score (Snapchat), match rate. Health metrics are reported in their own box, never as value. |
| **Method** | Staggered roll-out read (treated vs control market, causal impact on the ratio) for business; reported conversions read the same way; platform Conversion Lift when volume allows. |
| **Ramp-up** | 7 to 10 days (learning phase restarts when the optimisation event changes). |
| **Traps** | Missing `event_id` (double counting: +25% to +40% "uplift" that is pure duplication); reading the whole lift as value; comparing a period that includes a sale event. |

## App CAPI (Meta, Snapchat, TikTok; with or without an MMP)

| | |
|---|---|
| **Should move** | App events received server-side, match rate, reported installs and purchases; then client subscriptions or orders from the app. |
| **Should not move** | Web orders; the other app platform (Android vs iOS) if only one is migrated; organic installs. |
| **Signal health** | Dedup against SDK events, EMQ/EQS, share of events with advertiser ID or hashed keys. |
| **Method** | Platform split (Android vs iOS) or market split read with causal impact; SKAdNetwork postbacks read separately (they are delayed and aggregated). |
| **Ramp-up** | 7 days. |
| **Traps** | EMQ jumps (for example 4.6 to 8.3) with no change in subscriptions: a better *signal*, not a better *business*. TikTok is not available in India. |

## CRM Conversions API (lead and offline outcomes)

| | |
|---|---|
| **Should move** | Down-funnel events visible to the platform (qualified lead, approved application, activation, store sale); then cost per *qualified* outcome; then business outcomes. |
| **Should not move** | Raw lead volume may *fall* when the platform optimises for quality: that is expected, not a failure. Control market outcomes. |
| **Signal health** | Upload freshness (hours), match rate of hashed email/phone, share of CRM events matched to a lead. |
| **Method** | Market split with causal impact on qualified outcomes; Conversion Lift on the lead-quality objective when possible. Longer read (8+ weeks) because CRM lag is days to weeks. |
| **Ramp-up** | 14 days (offline/CRM pipelines and lead-quality optimisation take longer to learn). |
| **Traps** | Changing the attribution setting in the same month (a 7-day click + 1-day view → 7-day click switch removed about 19% of reported conversions in the simulated panel); a read window on Ramadan. |

## Google Tag Gateway (+ enhanced conversions)

| | |
|---|---|
| **Should move** | Tag hits that survive blockers and browser limits (first-party serving), observed conversions in Google Ads; then, through Smart Bidding, client bookings or orders. |
| **Should not move** | Platforms not served through the gateway; client orders in control regions. |
| **Signal health** | Share of tags served first-party, enhanced-conversions match rate, diagnostics in the Google tag. |
| **Method** | Geo test: campaigns in treated regions bid on the improved conversion action, control regions keep the old one; synthetic control with placebo tests; power planned before launch. Google Conversion Lift (geo-based) when the account is eligible. |
| **Ramp-up** | 7 days (Smart Bidding re-learns after a conversion-action change). |
| **Traps** | Reading Google Ads by click date at the end of the period (travel lags of 1 to 4 weeks); comparing regions with different seasonality without a weighted control. |

## GA4 server-side (server-side tagging)

| | |
|---|---|
| **Should move** | Sessions recorded (hits that blockers dropped), the split of new vs returning users (server-set first-party cookies live longer, so fewer returning users are counted as new), share of "Unassigned" sessions. |
| **Should not move** | Client orders. GA4 purchases per client order should rise towards 1 (better coverage), not orders themselves. |
| **Signal health** | GA4 purchases / client orders, unassigned share, cookie lifetime. |
| **Method** | Before/after on ratios to client orders (sessions per order, GA4 purchases per order), never on raw GA4 counts. Annotate the change in GA4 so year-on-year reports are read correctly. |
| **Ramp-up** | 7 days. |
| **Traps** | "New users fell 17%": that is the measurement improving, not a marketing problem. Year-on-year comparisons across the switch need a note. |

---

## Which method when

| Situation | Method | Why |
|---|---|---|
| Use case live in one market, another not yet | Causal impact on treated/control ratio + in-time placebos | Shares the calendar; cheap; uses data already there. |
| Roll-out can be planned by region | Geo test + synthetic control + placebo groups | Randomisation-like control; no user-level data needed. |
| Enough conversions for a holdout (see power table) | Platform Conversion Lift | User-level randomisation: the only direct read of incrementality. |
| Nothing above possible | Pre/post with control metric, same weeks last year, and an explicit "not causal" label | Better than nothing; never sold as incremental. |

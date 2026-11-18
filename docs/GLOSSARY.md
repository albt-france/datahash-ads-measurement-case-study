# Glossary

| Term | Plain definition | Why it matters for measurement |
|---|---|---|
| **Conversions API (CAPI)** | Sending conversion events from the advertiser's server to the ad platform, next to (not instead of) the browser pixel or app SDK. | Recovers events lost to blockers, browser limits and app privacy changes. More *observed* conversions; incremental value must be shown separately. |
| **Deduplication** | When the pixel and the server send the same purchase, the platform keeps one. | Without it, every purchase seen by both streams counts twice: a fake uplift. |
| **`event_id`** | The shared identifier both copies of an event carry so the platform can deduplicate them (with the event name, within a time window). | The first check of any CAPI read: coverage on server events should be above 90%. |
| **Match keys** | Customer identifiers sent with an event (hashed email, phone, name, address, click ID, IP, user agent). | More keys → more events matched to platform users → better optimisation. |
| **Event Match Quality (EMQ)** | Meta's 0–10 score of how well server events can be matched to its users (TikTok has an equivalent; Snapchat uses an Event Quality Score). | A *health* metric. A higher EMQ makes value possible, it is not value. |
| **Enhanced conversions** | Google's way of adding hashed first-party data (email, phone, address) to conversion tags. | Same logic as match keys for Google Ads; the match rate is a health metric. |
| **Google tag gateway** | Serving Google tags from the advertiser's own domain (through a CDN or load balancer) instead of a Google domain. | More tag hits survive blockers; observed conversions rise; Smart Bidding learns from a fuller signal. |
| **Server-side tagging (GA4)** | Sending analytics hits through the advertiser's own tagging server. | Changes GA4 counts (sessions, new vs returning users, unassigned traffic) without changing the business. |
| **Consent-related signal loss** | Events that cannot be used because the user did not consent, or that are sent without identifiers. | Part of the gap between platform and business numbers that no tool should "recover" without consent. |
| **Attribution window / setting** | How long after a click or view a conversion is credited (for example 7-day click + 1-day view). | Changing it breaks the series: a move from 7-day click + 1-day view to 7-day click alone removes view-through conversions overnight. |
| **Click date vs conversion date** | Platforms usually credit a conversion to the day of the click or impression; some columns report by the day the conversion happened. | By click date, recent days are still filling up: the last weeks always look like a drop. |
| **Ramp-up / learning phase** | The days after a change when delivery systems re-learn and results are volatile. | Excluded from any before/after comparison. |
| **Baseline** | The level of the metric before the change, over a window fixed in advance. | Without it a percentage has no meaning. |
| **Control metric / control market** | A metric or market that the change cannot affect, read over the same weeks. | Separates the effect from season, promotions and market trends. |
| **Intention to treat (ITT)** | The effect of being *assigned* to see ads, comparing the randomised groups as a whole. | The clean, randomised number of a lift study. |
| **Effect on the exposed (CACE, Wald estimator)** | ITT divided by the share of the test group that was actually reached. | The effect per reached user; still randomised, unlike "exposed vs unexposed". |
| **Causal impact** | A time-series model that predicts what the treated series would have done without the change, from series the change did not touch, with an interval. | Turns a staggered roll-out into a causal read. |
| **Synthetic control** | A weighted mix of control regions (weights ≥ 0, summing to 1) that tracks the treated regions before the test. | The comparison series for a geo test. |
| **Placebo test** | The same estimate on fake treated groups or fake dates where nothing happened. | Shows how big an "effect" pure noise produces. |
| **Minimum detectable effect (MDE)** | The smallest effect a test of a given size and length can reliably detect. | Decides whether to run a test, and how long. |
| **Smart Bidding** | Google's automated bidding that predicts conversion likelihood per auction. | Feeds on the conversion signal: a fuller signal can change who is bought, which is where business value comes from. |
| **ROAS / CPA** | Revenue per unit of ad spend / ad spend per conversion. ROAS up and CPA down are the same direction. | Reported ROAS rises mechanically when more conversions become visible; incremental ROAS uses incremental revenue. |

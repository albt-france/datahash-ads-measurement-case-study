# Reading a platform lift study (Meta, Google, Snapchat, TikTok)

A lift study randomly holds out part of the audience (or of the regions) from the ads and compares conversions
between the two groups. It is the closest thing to a controlled experiment that an advertiser can run inside a
platform. This guide says how to read one and what it does and does not prove. The real randomised test in this
repository (Criteo, page 2 of the report) is used as the worked example.

## What a lift study reports

| Number | What it means | Criteo example (PUBLIC DATA) |
|---|---|---|
| Conversion rate, test vs control | Outcome in each randomised group | 0.309% vs 0.194% |
| Incremental conversions | Test conversions minus what the control rate predicts | ≈ 13,700 of 23,031 conversions by exposed users |
| Lift (relative) | Incremental / baseline | +59% for the whole eligible group (95% CI +54% to +65%) |
| Effect on the exposed | Lift among users who actually saw an ad (only part of the test group is reached) | +146%: exposure 3.6%, Wald estimator |
| Confidence / probability | How likely the lift is not noise | 95% intervals here; platforms often show a probability of a positive effect |

**Intention-to-treat vs exposed.** The randomised comparison is between *groups* (eligible vs held out). Reached
users are a self-selected subset: comparing them with unreached users gave a ratio of 45 (+4,403%) in Criteo, about
30 times the true effect on the exposed. Any "exposed vs not exposed" chart is a targeting chart, not a lift.

## What a lift study proves

- That the campaign *caused* extra conversions on the platform's conversion definition, during the test, for that
  audience and budget.
- The size of that effect, with an interval, if the test had enough power (see the power table).

## What it does not prove

- That the conversions are incremental for the **business**: the platform conversion definition, window and
  deduplication still apply. Check client orders as well.
- That the effect holds at a different budget, season or audience.
- Anything about a first-party signal use case **unless** the test is designed around it (for example, test cell
  bidding on the CAPI-enriched conversion action vs control cell on the old one).
- Cross-platform incrementality: each platform's lift is measured on its own conversions.

## Platform notes (from public documentation; check the current version before a study)

| Platform | Study type | Notes for a CAPI / first-party read |
|---|---|---|
| Meta | Conversion Lift (user-level holdout, in Experiments); GeoLift (open-source geo method) | Event Match Quality and dedup (`event_id` + event name) must be healthy before the test; keep the attribution setting fixed. |
| Google Ads | Conversion Lift, user-based or geography-based, for eligible accounts | Enhanced conversions and Google tag gateway change what is observed: start the study after the ramp-up. |
| Snapchat | Lift studies through Snap measurement | Pixel + CAPI dedup and Event Quality Score first; 28-day click default window is long, read by conversion date. |
| TikTok | Conversion Lift Study | Pixel + Events API dedup on `event_id`; not available in India. |

## Power: is the test big enough?

With a 0.194% baseline conversion rate (Criteo control), an 85/15 split needs about 14,900 control users to detect
a 59% lift, about 483,000 for a 10% lift and about 1.9 million for a 5% lift (80% power, 5% two-sided), see
`data/output/criteo_power.csv`. Most single-client CAPI effects on business outcomes are in the 2% to 6% range: a
user-level lift study will often be under-powered, and a geo test or a staggered market roll-out is the realistic
design (`notebooks/measurement.ipynb`, geo power section).

## Sources

- Criteo Uplift Prediction Dataset v2.1, https://huggingface.co/datasets/criteo/criteo-uplift (CC BY-NC-SA 4.0).
- Meta, Conversions API: https://developers.facebook.com/docs/marketing-api/conversions-api ; deduplication:
  https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events ;
  Event Match Quality: https://www.facebook.com/business/help/765081237991954 ; GeoLift: https://facebookincubator.github.io/GeoLift/
- Google Ads, About Conversion Lift: https://support.google.com/google-ads/answer/12003020 ; enhanced conversions:
  https://support.google.com/google-ads/answer/9888656 ; Google tag gateway: https://developers.google.com/tag-platform/tag-manager/gateway
- Snapchat Conversions API: https://developers.snap.com/api/marketing-api/Conversions-API
- TikTok event deduplication: https://ads.tiktok.com/help/article/event-deduplication
- CausalImpact (method used on page 5): https://google.github.io/CausalImpact/CausalImpact.html

# Simulation assumptions (SIMULATED data)

`src/simulate.py`, seed 42, daily from 1 Jan 2025 to 31 Oct 2026, reports "pulled" at the end of 31 Oct 2026.
Six fictional clients; none is Datahash's client and no number is Datahash's.

## Clients

| Client | Vertical | Markets (treated / control) | Platforms | Orders a day | Average value (USD) |
|---|---|---|---|---|---|
| A | Retail | KSA / UAE | Meta, Google Ads, Snapchat, TikTok | 1,800 / 1,150 | 85 |
| B | Quick-service restaurant | UAE / KSA | Meta, Google Ads, Snapchat, TikTok | 5,200 / 6,100 | 14 |
| C | Telecom | KSA / UAE | Meta, Google Ads, Snapchat, TikTok | 950 / 620 activations | 160 |
| D | Streaming | India Android / India iOS | Meta, Google Ads (TikTok is not available in India) | 7,400 / 2,300 subscriptions | 6 |
| E | Bank & insurance | UAE / KSA | Meta, Google Ads, Snapchat | 310 / 380 approved applications | 420 |
| F | Travel | 24 regions in KSA, UAE, India (6 treated) | Google Ads, Meta, Snapchat | 1,900 bookings | 640 |

## Demand

- Calendar multipliers by vertical (Ramadan, Eid, White Friday, 11.11, Diwali, national days, year-end, Gulf summer),
  weekends by country (KSA Fri–Sat, UAE Sat–Sun, India Sun), +10% organic growth a year.
- Noise: a shock shared by all markets of a client (AR(1), sd 3.5%), a market-specific shock (AR(1), sd 1.8%),
  Poisson counts. Regions of client F: country shock sd 4%, region shock sd 3.5%.

## Platforms

- Each platform claims a share of client orders under its default window (shares overlap, as in real reports:
  7% to 35%). View-through share of default-window conversions: Meta 18%, Snapchat 22%, TikTok 20%, Google 0%.
- Default windows: Meta and TikTok 7-day click + 1-day view, Snapchat 28-day click + 1-day view, Google Ads 30-day click.
- Click-to-conversion lag: geometric, mean 0.3 days (QSR) to 8 days (travel), cut at the window.
- Browser coverage of purchases before CAPI: 66% to 74%. EMQ before CAPI: 4.6 to 5.9.
- Learning phase: delivery up to 15% lower on the first day of the ramp-up, back to normal at its end.

## Use cases and the effects programmed (the "truth")

| ID | Client | Use case | Go-live | Ramp-up | Reported conversions | Client orders |
|---|---|---|---|---|---|---|
| UC1 | A | Web CAPI, Meta, KSA | 12 Apr 2026 | 10 days | +18% | +4% |
| UC2 | B | Web CAPI, TikTok, UAE (no `event_id` until 26 Oct 2025) | 7 Sep 2025 | 7 days | +35% duplicates | 0% |
| UC3 | B | Web CAPI, Snapchat, UAE | 7 Sep 2025 | 7 days | +9% | 0% |
| UC4 | C | CRM Conversions API, Meta, KSA (read window on Ramadan 2026) | 1 Feb 2026 | 14 days | +6% | 0% |
| UC5 | D | App CAPI, Meta, India Android (EMQ 4.6 → 8.3) | 7 Jun 2026 | 7 days | +5% | 0% |
| UC6 | A | GA4 server-side, KSA + UAE | 15 Jun 2025 | 7 days | sessions +9%, fewer users misread as new | 0% |
| UC7 | E | CRM Conversions API, Meta, UAE (window change 14 Jun 2026, both markets) | 3 May 2026 | 14 days | +10% | +6% |
| UC8 | F | Google tag gateway as bidding signal, 6 treated regions, test to 29 Aug 2026 | 5 Jul 2026 | 7 days | +11% | +5% |

Ranges were chosen to sit inside the public orders of magnitude: CAPI case studies report recovered or additional
conversions from a few percent to a few tens of percent (Datahash's 16 published stories, as stated by Datahash, range from
single-digit gains in measured conversions to several-fold ROAS changes), and the Criteo randomised test shows that the incremental part of
platform-credited conversions can be much smaller than the credited total. The truth table
(`data/_hidden_truth.csv`) was used once to score the detection and is not published.

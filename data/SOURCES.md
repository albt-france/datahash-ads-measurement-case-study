# Sources

| Data | Source | Collected | Licence / terms | Used for |
|---|---|---|---|---|
| Datahash public pages: home, products, offerings, partners, glossary, docs, contact | https://www.datahash.com (pages `/`, `/products/`, `/offerings/`, `/partners/`, `/glossary/`, `/docs/`, `/contact/`) | 18 Nov 2026 | Public web pages; `robots.txt` respected (only `/wp-admin/` and `/wp-login.php` disallowed); 1 request every 3 s, fetched once | Facts "as stated by Datahash" (`data/processed/datahash_facts.csv`), page 1 |
| Datahash case studies (16) | https://www.datahash.com/case-studies/ and the 16 linked pages | 18 Nov 2026 | Same | Anonymised evidence grid (`data/processed/case_study_grid.csv`): which evidence elements each story publishes. Brands, people and headline figures are not reproduced. |
| Criteo Uplift Prediction Dataset v2.1 | https://huggingface.co/datasets/criteo/criteo-uplift, file `criteo-research-uplift-v2.1.csv.gz` (311 MB, ~14 million rows) | 18 Nov 2026 | **CC BY-NC-SA 4.0** (non-commercial, attribution, share-alike). Only aggregates are published (`data/processed/criteo_*.parquet`); the raw file is not in the repository. Reference: Criteo AI Lab, "A Large Scale Benchmark for Individual Treatment Effect Prediction and Uplift Modeling" (2021). | Page 2: randomised lift, effect on the exposed, selection bias, power |
| Platform documentation | Meta (Conversions API, deduplication, Event Match Quality, GeoLift), Google (enhanced conversions, Google tag gateway, Conversion Lift), Snapchat (Conversions API), TikTok (event deduplication) | Links checked 18 Nov 2026 | Cited and summarised, not copied | `docs/MEASUREMENT_PLAYBOOK.md`, `docs/PLATFORM_LIFT_GUIDE.md`, `docs/GLOSSARY.md` (links in the lift guide) |
| Public holiday calendar | Ramadan, Eid al-Fitr, Eid al-Adha, Saudi and UAE National Days, Diwali, White Friday, 11.11 (2025–2026 dates) | 18 Nov 2026 | Public dates | `calendar` table of the simulation |
| Job posting | Datahash, "Marketing Data Analyst - Ads Measurement & Value Realization", posted 17 Nov 2026 | 18 Nov 2026 | Public posting | Scope of the study |

**Everything else is SIMULATED** (`src/simulate.py`, seed 42): six fictional clients, their ad, signal, GA4 and
business data. It is not Datahash's data and not any client's data. Assumptions: [ASSUMPTIONS.md](ASSUMPTIONS.md).

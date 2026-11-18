# Impact report · Client E · Bank & insurance · CRM Conversions API on Meta

<!-- SIMULATED -->

## Question

Did CRM Conversions API on Meta in UAE bring more approved applications, or only more conversions visible to the platform?

## Answer

Yes, a modest incremental effect: approved applications rose +5.4% against the KSA control (95% interval +3.4% to +7.4%), about 1,031 extra approved applications and $433k of revenue over the read. Meta-reported conversions rose much more, +7.4%: most of that is signal recovered, which helps bidding but is not extra business on its own.

## Baseline

52 weeks of weekly approved applications in UAE and KSA before go-live on 3 May 2026, from the client's own system. Reported CPA was $159.81 on the 7-day click setting.

## Intervention

CRM Conversions API on Meta in UAE only, deduplicated with the pixel on event_id. The 14-day ramp-up (learning phase) is excluded from every comparison. KSA was not migrated during the read and serves as the control.

## Result

Read window: 8 full weeks, 17 May 2026 to 11 Jul 2026, fixed before the read.

- Client approved applications: +5.4% (95% interval +3.4% to +7.4%), between 669 and 1,384 extra approved applications.

- Meta-reported conversions, 7-day click: +7.4% (95% interval +1.1% to +13.9%).

- Reported CPA on 7-day click moved from $159.81 to $149.44: a diagnostic only; the success metric for a CRM signal is approved applications.

[[chart:client_e_ci]]

## Attribution logic

The model follows the ratio between UAE and KSA, which share the calendar, so Ramadan, Eid and sale periods cancel out; holidays that hit only one market are modelled. 0 of 22 in-time placebos (fake go-live dates before the real one) produced an effect this large. Platform conversions are read on 7-day click, by click date, on complete weeks only.

The attribution setting changed during the read (7-day click + 1-day view to 7-day click, account-wide). As reported, conversions dropped 26%; on the unchanged 7-day click column they moved -9%, in line with approved applications (-7%) over the same weeks. The drop is the window (view-through conversions were 19% of the total), not performance.

## Signal health (not business value)

EMQ 5.8/10 before, 7.8/10 after; match rate 62% to 73%; event_id on 97% of server events, so deduplication works.

## Limits

One market, 8 weeks: the interval is wide relative to the effect. The control market can drift for reasons of its own. The effect is measured on approved applications, not on margin.

## Next step

Roll out to KSA with a staggered start by region and read it as a geo test; keep the attribution setting fixed for the quarter.
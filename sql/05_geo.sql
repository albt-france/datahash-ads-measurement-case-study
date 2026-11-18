-- Geo test preparation (SIMULATED, client F: Google Tag Gateway as the bidding signal in 6 treated regions).
-- Weekly blocks aligned on go-live (2026-07-05): block 0 = ramp-up week (excluded), blocks 1-7 = test,
-- negative blocks = pre-period used to fit the synthetic control. After the test every region is treated.
SELECT region, country, geo_group,
       CAST(floor(date_diff('day', DATE '2026-07-05', date) / 7) AS INTEGER) AS block,
       min(date)      AS block_start,
       sum(bookings)  AS bookings,
       sum(revenue)   AS revenue,
       count(*)       AS days
FROM geo_daily
WHERE date <= DATE '2026-08-29'
GROUP BY ALL
HAVING count(*) = 7                                   -- complete blocks only
ORDER BY region, block;

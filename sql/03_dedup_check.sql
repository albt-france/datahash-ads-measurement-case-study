-- Deduplication health, weekly, per client x market x platform (SIMULATED).
-- When a server stream (CAPI) runs next to the pixel, each purchase arrives twice; the platform keeps one copy
-- only if both copies carry the same event_id. No event_id -> no dedup -> conversions inflated.
WITH w AS (
    SELECT client, market, platform, date_trunc('week', date) AS week,
           sum(browser_events)                AS browser,
           sum(server_events)                 AS server,
           sum(server_events_with_event_id)   AS server_with_id,
           sum(duplicates_removed)            AS removed,
           avg(emq)                           AS emq
    FROM signals_daily GROUP BY ALL
),
conv AS (
    SELECT client, market, platform, date_trunc('week', date) AS week, sum(conv_click) AS reported
    FROM ads_daily GROUP BY ALL
),
biz AS (
    SELECT client, market, date_trunc('week', date) AS week, sum(orders) AS orders
    FROM business_daily GROUP BY ALL
)
SELECT w.*,
       c.reported,
       b.orders,
       server_with_id / nullif(server, 0)                       AS event_id_coverage,
       removed / nullif(least(browser, server), 0)              AS dedup_rate,          -- ~0.97 when healthy
       c.reported / b.orders                                    AS reported_per_order,
       (server > 0 AND server_with_id / nullif(server, 0) < 0.9) AS flag_dedup_broken
FROM w
JOIN conv c USING (client, market, platform, week)
JOIN biz  b USING (client, market, week)
ORDER BY client, market, platform, week;

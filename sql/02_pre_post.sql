-- Pre/post read for every use case (SIMULATED panel), the way it should be done:
--   * baseline  = the 56 days before go-live (fixed BEFORE looking at the results: see docs/EVIDENCE_STANDARD.md)
--   * ramp-up   = go-live .. go-live + ramp_up_days - 1, EXCLUDED from both windows
--   * read      = read_start .. read_end (fixed in use_cases, max 8 weeks)
--   * control   = the same metric in the control market (not yet migrated), same windows
--   * last year = the same weekdays 364 days earlier, as a seasonality check
-- Reported conversions use conv_click (7-day click, identical setting before and after), so a window change cannot leak in.
WITH uc AS (
    SELECT *, go_live - INTERVAL 56 DAY AS base_start, go_live - INTERVAL 1 DAY AS base_end
    FROM use_cases
    WHERE platform <> 'GA4' AND use_case_id <> 'UC8'          -- GA4 is read in ga4_daily, UC8 in the geo test
),
reported AS (
    SELECT client, market, platform, date, sum(conv_click) AS conv
    FROM ads_daily GROUP BY ALL
),
roles AS (SELECT * FROM (VALUES ('treated'), ('control')) t(role)),
wins  AS (SELECT * FROM (VALUES ('baseline', 0), ('read', 0), ('baseline_ly', 364), ('read_ly', 364)) t(win, shift)),
windows AS (   -- one row per use case x market role x window, with the daily means
    SELECT uc.use_case_id, roles.role, wins.win,
           avg(r.conv)   AS reported_per_day,
           avg(b.orders) AS orders_per_day,
           count(*)      AS days
    FROM uc
    CROSS JOIN roles
    CROSS JOIN wins
    JOIN business_daily b
      ON b.client = uc.client
     AND b.market = CASE roles.role WHEN 'treated' THEN uc.market ELSE uc.control_market END
     AND b.date BETWEEN (CASE WHEN wins.win LIKE 'baseline%' THEN uc.base_start ELSE uc.read_start END) - to_days(wins.shift)
                    AND (CASE WHEN wins.win LIKE 'baseline%' THEN uc.base_end   ELSE uc.read_end   END) - to_days(wins.shift)
    LEFT JOIN reported r
      ON r.client = b.client AND r.market = b.market AND r.platform = uc.platform AND r.date = b.date
    GROUP BY ALL
),
wide AS (
    SELECT use_case_id,
           max(CASE WHEN role = 'treated' AND win = 'baseline'    THEN reported_per_day END) AS t_base_rep,
           max(CASE WHEN role = 'treated' AND win = 'read'        THEN reported_per_day END) AS t_read_rep,
           max(CASE WHEN role = 'control' AND win = 'baseline'    THEN reported_per_day END) AS c_base_rep,
           max(CASE WHEN role = 'control' AND win = 'read'        THEN reported_per_day END) AS c_read_rep,
           max(CASE WHEN role = 'treated' AND win = 'baseline'    THEN orders_per_day END)   AS t_base_ord,
           max(CASE WHEN role = 'treated' AND win = 'read'        THEN orders_per_day END)   AS t_read_ord,
           max(CASE WHEN role = 'control' AND win = 'baseline'    THEN orders_per_day END)   AS c_base_ord,
           max(CASE WHEN role = 'control' AND win = 'read'        THEN orders_per_day END)   AS c_read_ord,
           max(CASE WHEN role = 'treated' AND win = 'baseline_ly' AND days >= 50 THEN orders_per_day END) AS t_base_ly_ord,
           max(CASE WHEN role = 'treated' AND win = 'read_ly'     AND days >= 20 THEN orders_per_day END) AS t_read_ly_ord
    FROM windows GROUP BY use_case_id
)
SELECT use_case_id,
       -- naive: treated market, after vs before
       t_read_rep / t_base_rep - 1                                   AS reported_naive,
       t_read_ord / t_base_ord - 1                                   AS business_naive,
       -- controlled: change in treated divided by change in control (difference-in-differences on ratios)
       (t_read_rep / t_base_rep) / (c_read_rep / c_base_rep) - 1     AS reported_vs_control,
       (t_read_ord / t_base_ord) / (c_read_ord / c_base_ord) - 1     AS business_vs_control,
       -- seasonality check: what the same weeks did last year (NULL when last year is outside the data)
       t_read_ly_ord / t_base_ly_ord - 1                             AS business_same_weeks_last_year,
       (t_read_ord / t_base_ord) / (t_read_ly_ord / t_base_ly_ord) - 1 AS business_vs_last_year
FROM wide
ORDER BY use_case_id;

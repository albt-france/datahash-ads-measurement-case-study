-- @setting_changes
-- 1) Attribution-setting changes: a new window is a break in the reported series, not a change in performance.
WITH s AS (
    SELECT DISTINCT client, market, platform, date, attribution_setting FROM ads_daily
),
l AS (
    SELECT *, lag(attribution_setting) OVER (PARTITION BY client, market, platform ORDER BY date) AS previous_setting
    FROM s
)
SELECT client, market, platform, date AS changed_on, previous_setting, attribution_setting AS new_setting
FROM l
WHERE previous_setting IS NOT NULL AND previous_setting <> attribution_setting
ORDER BY changed_on;

-- @click_vs_conversion_date
-- 2) Click date vs conversion date: platforms credit a conversion to the day of the click. Recent click days are
--    still filling up (the conversions have not happened yet), so the last weeks look like a drop that is not real.
SELECT client, platform, date,
       date_diff('day', date, DATE '2026-10-31')        AS days_before_extract,
       sum(conversions)                                AS conv_by_click_date,
       sum(conversions_by_conv_date)                   AS conv_by_conv_date
FROM ads_daily
WHERE date >= DATE '2026-08-01'
GROUP BY ALL
ORDER BY client, platform, date;

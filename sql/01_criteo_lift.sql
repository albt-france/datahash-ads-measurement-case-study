-- Criteo Uplift v2.1 (PUBLIC DATA, CC BY-NC-SA 4.0): a randomised ad-incrementality test.
-- treatment = 1 -> user eligible to see the ads (85% of users); treatment = 0 -> held out (control).
-- exposure  = 1 -> the user was actually shown an ad (only possible in the treatment group).
-- Only aggregates leave this file. Each block below is written to data/processed/criteo_<name>.parquet.

-- @by_group
-- Intention-to-treat (ITT): compare the whole randomised groups, exposed or not.
SELECT treatment,
       count(*)                      AS users,
       sum(exposure)                 AS exposed,
       sum(visit)                    AS visits,
       sum(conversion)               AS conversions,
       avg(exposure)                 AS exposure_rate,
       avg(visit)                    AS visit_rate,
       avg(conversion)               AS conversion_rate
FROM criteo
GROUP BY treatment
ORDER BY treatment;

-- @by_exposure
-- The trap: inside the treatment group, exposed vs unexposed users are NOT comparable
-- (the ad system chooses whom to show ads to). This is what "platform-reported" comparisons look like.
SELECT treatment, exposure,
       count(*)          AS users,
       sum(visit)        AS visits,
       sum(conversion)   AS conversions,
       avg(visit)        AS visit_rate,
       avg(conversion)   AS conversion_rate
FROM criteo
GROUP BY treatment, exposure
ORDER BY treatment, exposure;

-- @by_propensity
-- Selection check: deciles of a pre-treatment feature (f9, anonymised). If exposure rises with the decile and so
-- does the baseline conversion rate in the CONTROL group, exposed users were already more likely to convert.
WITH d AS (
    SELECT *, ntile(10) OVER (ORDER BY f9) AS decile FROM criteo
)
SELECT decile, treatment,
       count(*)          AS users,
       avg(exposure)     AS exposure_rate,
       avg(visit)        AS visit_rate,
       avg(conversion)   AS conversion_rate,
       sum(conversion)   AS conversions
FROM d
GROUP BY decile, treatment
ORDER BY decile, treatment;

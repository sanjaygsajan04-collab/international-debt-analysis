-- Views used by the 30 analytical queries (MySQL 8).
-- A view is a saved SELECT. It lets every query reuse the same "debt" definition.
-- Debt measure: External debt stocks, total (DT.DOD.DECT.CD), in current US$.
-- Regional groups (is_aggregate = 1) are left out so no debt is counted twice.

USE international_debt;

-- Total external debt for every real country and year
DROP VIEW IF EXISTS v_total_debt;
CREATE VIEW v_total_debt AS
SELECT d.country_code, c.country_name, c.region, c.income_group, d.year, d.value AS total_debt
FROM debt_data d
JOIN countries c ON d.country_code = c.country_code
WHERE d.indicator_code = 'DT.DOD.DECT.CD'
  AND c.is_aggregate = 0;

-- Same, for the latest year only (2024)
DROP VIEW IF EXISTS v_total_debt_latest;
CREATE VIEW v_total_debt_latest AS
SELECT * FROM v_total_debt
WHERE year = (SELECT MAX(year) FROM v_total_debt);

-- All external debt stock indicators in US$ (DT.DOD.*), latest year, real countries.
-- The indicators overlap (for example long-term includes public debt), and the total is excluded.
DROP VIEW IF EXISTS v_debt_indicators;
CREATE VIEW v_debt_indicators AS
SELECT d.country_code, c.country_name, d.indicator_code, i.indicator_name, d.value
FROM debt_data d
JOIN countries c  ON d.country_code = c.country_code
JOIN indicators i ON d.indicator_code = i.indicator_code
WHERE c.is_aggregate = 0
  AND i.unit = 'US$'
  AND d.indicator_code LIKE 'DT.DOD.%'
  AND d.indicator_code <> 'DT.DOD.DECT.CD'
  AND d.year = (SELECT MAX(year) FROM debt_data);

-- The four debt types that do NOT overlap and add up to total debt, latest year
DROP VIEW IF EXISTS v_debt_components;
CREATE VIEW v_debt_components AS
SELECT * FROM v_debt_indicators
WHERE indicator_code IN ('DT.DOD.DPPG.CD', 'DT.DOD.DPNG.CD', 'DT.DOD.DSTC.CD', 'DT.DOD.DIMF.CD');

-- Advanced query A5: the 10 countries with the highest debt
DROP VIEW IF EXISTS v_top10_debt_countries;
CREATE VIEW v_top10_debt_countries AS
SELECT country_code, country_name, total_debt
FROM v_total_debt_latest
ORDER BY total_debt DESC
LIMIT 10;

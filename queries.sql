-- International Debt Analysis: 30 SQL analytical queries (MySQL 8)
-- Run views.sql first (python create_views.py).
-- "Debt" = total external debt stocks (US$), real countries only, latest year (2024) unless stated.
-- Each query starts with a header line of the form: -- <ID>. <question>

USE international_debt;

-- ==================== BASIC ====================

-- B1. Retrieve all distinct country names from the dataset.
SELECT DISTINCT country_name
FROM countries
WHERE is_aggregate = 0
ORDER BY country_name;

-- B2. Count the total number of countries available.
SELECT COUNT(*) AS total_countries
FROM countries
WHERE is_aggregate = 0;

-- B3. Find the total number of indicators present.
SELECT COUNT(*) AS total_indicators
FROM indicators;

-- B4. Display the first 10 records of the dataset.
SELECT d.country_code, c.country_name, i.indicator_name, d.year, d.value
FROM debt_data d
JOIN countries c  ON d.country_code = c.country_code
JOIN indicators i ON d.indicator_code = i.indicator_code
ORDER BY d.country_code, d.indicator_code, d.year
LIMIT 10;

-- B5. Calculate the total global debt (latest year).
SELECT SUM(total_debt) AS total_global_debt
FROM v_total_debt_latest;

-- B6. List all unique indicator names.
SELECT DISTINCT indicator_name
FROM indicators
ORDER BY indicator_name;

-- B7. Find the number of records for each country.
SELECT c.country_name, COUNT(*) AS number_of_records
FROM debt_data d
JOIN countries c ON d.country_code = c.country_code
WHERE c.is_aggregate = 0
GROUP BY c.country_name
ORDER BY number_of_records DESC;

-- B8. Display all records where debt is greater than 1 billion USD (all years).
SELECT country_name, year, total_debt
FROM v_total_debt
WHERE total_debt > 1000000000
ORDER BY total_debt DESC;

-- B9. Find the minimum, maximum, and average debt values (latest year).
SELECT MIN(total_debt) AS minimum_debt,
       MAX(total_debt) AS maximum_debt,
       ROUND(AVG(total_debt), 2) AS average_debt
FROM v_total_debt_latest;

-- B10. Count total number of records in the dataset.
SELECT COUNT(*) AS total_records
FROM debt_data;

-- ==================== INTERMEDIATE ====================

-- I1. Find the total debt for each country (latest year).
SELECT country_name, total_debt
FROM v_total_debt_latest
ORDER BY total_debt DESC;

-- I2. Display the top 10 countries with the highest total debt.
SELECT country_name, total_debt
FROM v_total_debt_latest
ORDER BY total_debt DESC
LIMIT 10;

-- I3. Find the average debt per country (average of its yearly totals, 2000 to 2024).
SELECT country_name, ROUND(AVG(total_debt), 2) AS average_debt
FROM v_total_debt
GROUP BY country_name
ORDER BY average_debt DESC;

-- I4. Calculate total debt for each indicator (latest year, all countries).
SELECT indicator_name, SUM(value) AS total_debt
FROM v_debt_indicators
GROUP BY indicator_code, indicator_name
ORDER BY total_debt DESC;

-- I5. Identify the indicator contributing the highest total debt.
SELECT indicator_name, SUM(value) AS total_debt
FROM v_debt_indicators
GROUP BY indicator_code, indicator_name
ORDER BY total_debt DESC
LIMIT 1;

-- I6. Find the country with the lowest total debt.
SELECT country_name, total_debt
FROM v_total_debt_latest
ORDER BY total_debt ASC
LIMIT 1;

-- I7. Calculate total debt for each country and indicator combination (latest year).
SELECT country_name, indicator_name, SUM(value) AS total_debt
FROM v_debt_indicators
GROUP BY country_name, indicator_code, indicator_name
ORDER BY country_name, total_debt DESC;

-- I8. Count how many indicators each country has.
SELECT c.country_name, COUNT(DISTINCT d.indicator_code) AS number_of_indicators
FROM debt_data d
JOIN countries c ON d.country_code = c.country_code
WHERE c.is_aggregate = 0
GROUP BY c.country_name
ORDER BY number_of_indicators DESC, c.country_name;

-- I9. Display countries whose total debt is above the global average.
SELECT country_name, total_debt
FROM v_total_debt_latest
WHERE total_debt > (SELECT AVG(total_debt) FROM v_total_debt_latest)
ORDER BY total_debt DESC;

-- I10. Rank countries based on total debt (highest to lowest).
SELECT RANK() OVER (ORDER BY total_debt DESC) AS debt_rank,
       country_name, total_debt
FROM v_total_debt_latest
ORDER BY debt_rank;

-- ==================== ADVANCED ====================

-- A1. Find the top 5 indicators contributing most to global debt (share of total external debt).
SELECT indicator_name,
       SUM(value) AS total_debt,
       ROUND(SUM(value) * 100 / (SELECT SUM(total_debt) FROM v_total_debt_latest), 2) AS percent_of_global_debt
FROM v_debt_indicators
GROUP BY indicator_code, indicator_name
ORDER BY total_debt DESC
LIMIT 5;

-- A2. Calculate percentage contribution of each country to total global debt.
SELECT country_name, total_debt,
       ROUND(total_debt * 100 / SUM(total_debt) OVER (), 2) AS percent_of_global_debt
FROM v_total_debt_latest
ORDER BY total_debt DESC;

-- A3. Identify the top 3 countries for each indicator based on debt.
WITH ranked AS (
    SELECT indicator_name, country_name, value,
           ROW_NUMBER() OVER (PARTITION BY indicator_code ORDER BY value DESC) AS position_in_indicator
    FROM v_debt_indicators
)
SELECT indicator_name, position_in_indicator, country_name, value
FROM ranked
WHERE position_in_indicator <= 3
ORDER BY indicator_name, position_in_indicator;

-- A4. Find the difference between maximum and minimum debt for each country (2000 to 2024).
SELECT country_name,
       MAX(total_debt) AS maximum_debt,
       MIN(total_debt) AS minimum_debt,
       MAX(total_debt) - MIN(total_debt) AS difference
FROM v_total_debt
GROUP BY country_name
ORDER BY difference DESC;

-- A5. Create a view for the top 10 countries with highest debt, then read from it.
DROP VIEW IF EXISTS v_top10_debt_countries;
CREATE VIEW v_top10_debt_countries AS
SELECT country_code, country_name, total_debt
FROM v_total_debt_latest
ORDER BY total_debt DESC
LIMIT 10;

SELECT country_name, total_debt
FROM v_top10_debt_countries
ORDER BY total_debt DESC;

-- A6. Categorize countries into High, Medium and Low Debt (thresholds: 100 billion and 10 billion US$).
SELECT country_name, total_debt,
       CASE
           WHEN total_debt >= 100000000000 THEN 'High Debt'
           WHEN total_debt >= 10000000000  THEN 'Medium Debt'
           ELSE 'Low Debt'
       END AS debt_category
FROM v_total_debt_latest
ORDER BY total_debt DESC;

-- A7. Use a window function to calculate cumulative debt per country (running total over the years).
SELECT country_name, year, total_debt,
       SUM(total_debt) OVER (PARTITION BY country_code ORDER BY year) AS cumulative_debt
FROM v_total_debt
ORDER BY country_name, year;

-- A8. Find indicators where average debt is higher than the overall average debt.
SELECT indicator_name, ROUND(AVG(value), 2) AS average_debt
FROM v_debt_indicators
GROUP BY indicator_code, indicator_name
HAVING AVG(value) > (SELECT AVG(value) FROM v_debt_indicators)
ORDER BY average_debt DESC;

-- A9. Identify countries contributing more than 5% of global debt.
SELECT country_name, total_debt, percent_of_global_debt
FROM (
    SELECT country_name, total_debt,
           ROUND(total_debt * 100 / SUM(total_debt) OVER (), 2) AS percent_of_global_debt
    FROM v_total_debt_latest
) AS shares
WHERE percent_of_global_debt > 5
ORDER BY total_debt DESC;

-- A10. Find the most dominant debt type (highest value) for each country.
--      Uses the four debt types that do not overlap: PPG, private non-guaranteed, short-term, IMF.
WITH ranked AS (
    SELECT country_name, indicator_name, value,
           ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY value DESC) AS rn
    FROM v_debt_components
)
SELECT country_name, indicator_name AS dominant_debt_type, value
FROM ranked
WHERE rn = 1
ORDER BY country_name;

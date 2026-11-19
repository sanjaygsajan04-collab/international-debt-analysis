-- International Debt Analysis: database design (MySQL 8)
-- 3 tables: countries and indicators (lookup tables) and debt_data (the facts).
-- WARNING: running this file deletes and recreates the tables.

CREATE DATABASE IF NOT EXISTS international_debt
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE international_debt;

DROP TABLE IF EXISTS debt_data;
DROP TABLE IF EXISTS indicators;
DROP TABLE IF EXISTS countries;

-- One row per country or regional group
CREATE TABLE countries (
    country_code  VARCHAR(3)   NOT NULL,
    country_name  VARCHAR(100) NOT NULL,
    region        VARCHAR(50)  NOT NULL,
    income_group  VARCHAR(30)  NOT NULL,
    is_aggregate  TINYINT(1)   NOT NULL DEFAULT 0,   -- 1 = regional group, not a real country
    PRIMARY KEY (country_code),
    UNIQUE KEY uq_country_name (country_name),
    CONSTRAINT chk_is_aggregate CHECK (is_aggregate IN (0, 1))
);

-- One row per indicator (what is being measured)
CREATE TABLE indicators (
    indicator_code VARCHAR(30)  NOT NULL,
    indicator_name VARCHAR(255) NOT NULL,
    topic          VARCHAR(255) NOT NULL,
    unit           VARCHAR(20)  NOT NULL,            -- US$, Percent, Years or Other
    PRIMARY KEY (indicator_code)
);

-- One row per country, indicator and year: the actual numbers
CREATE TABLE debt_data (
    country_code   VARCHAR(3)    NOT NULL,
    indicator_code VARCHAR(30)   NOT NULL,
    year           SMALLINT      NOT NULL,
    value          DECIMAL(24,4) NOT NULL,           -- negative values are valid (net flows)
    PRIMARY KEY (country_code, indicator_code, year),
    CONSTRAINT fk_debt_country   FOREIGN KEY (country_code)   REFERENCES countries (country_code),
    CONSTRAINT fk_debt_indicator FOREIGN KEY (indicator_code) REFERENCES indicators (indicator_code),
    CONSTRAINT chk_year CHECK (year BETWEEN 1990 AND 2100),
    INDEX idx_indicator_year (indicator_code, year),
    INDEX idx_year (year)
);

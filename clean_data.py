"""Step 3: clean the International Debt Statistics files and save tidy CSVs.

Input : IDS_ALLCountries_Data.csv, IDS_CountryMetaData.csv, IDS_SeriesMetaData.csv
Output: countries_clean.csv, indicators_clean.csv, debt_data_clean.csv
"""
import pandas as pd

LAST_ACTUAL_YEAR = 2024  # later years in the file are projections


def load_raw():
    """Read the three source files (they are not UTF-8, so use latin-1)."""
    data = pd.read_csv("IDS_ALLCountries_Data.csv", encoding="latin-1", low_memory=False)
    countries = pd.read_csv("IDS_CountryMetaData.csv", encoding="latin-1")
    series = pd.read_csv("IDS_SeriesMetaData.csv", encoding="latin-1")
    return data, countries, series


def clean_main(data):
    """Remove junk rows, strip spaces and duplicates, keep needed columns."""
    data = data.dropna(subset=["Series Code"]).copy()      # footer / blank rows
    for col in ["Country Name", "Country Code", "Series Name", "Series Code"]:
        # 'AFG   ' -> 'AFG'; also turn hidden non-breaking spaces into normal spaces
        data[col] = data[col].str.replace("\xa0", " ", regex=False).str.strip()
    data = data.drop(columns=["Counterpart-Area Name", "Counterpart-Area Code"])  # always 'World'
    data = data.drop_duplicates()
    return data


def build_countries(data, meta):
    """One row per country with region and income group. Flags regional groups."""
    meta = meta.copy()
    meta["Code"] = meta["Code"].str.strip()
    names = data[["Country Code", "Country Name"]].drop_duplicates()
    out = names.merge(
        meta[["Code", "Region", "Income Group"]],
        left_on="Country Code", right_on="Code", how="left",
    ).drop(columns="Code")
    out.columns = ["country_code", "country_name", "region", "income_group"]
    # Regional totals (e.g. 'IDA total') have no Region: they are not real countries
    out["is_aggregate"] = out["region"].isna().astype(int)
    out["region"] = out["region"].fillna("Aggregate group")
    out["income_group"] = out["income_group"].fillna("Not classified")
    return out.sort_values("country_code").reset_index(drop=True)


def unit_of(name):
    """Work out the unit from the indicator name."""
    n = name.lower()
    if "current us$" in n:
        return "US$"
    if "%" in n:
        return "Percent"
    if "(years)" in n:
        return "Years"
    return "Other"


def build_indicators(data, meta):
    """One row per indicator. Names come from the data file, topic from the metadata."""
    meta = meta.copy()
    meta["Code"] = meta["Code"].str.strip()
    names = data[["Series Code", "Series Name"]].drop_duplicates()
    out = names.merge(meta[["Code", "Topic"]], left_on="Series Code", right_on="Code", how="left")
    out = out.drop(columns="Code")
    out.columns = ["indicator_code", "indicator_name", "topic"]
    out["topic"] = out["topic"].fillna("Unclassified")
    out["unit"] = out["indicator_name"].map(unit_of)
    return out.sort_values("indicator_code").reset_index(drop=True)


def build_debt_data(data):
    """Wide years -> long rows. Keep actual years only and drop empty cells."""
    years = [c for c in data.columns if c.isdigit() and int(c) <= LAST_ACTUAL_YEAR]
    long = data.melt(
        id_vars=["Country Code", "Series Code"], value_vars=years,
        var_name="year", value_name="value",
    )
    long = long.dropna(subset=["value"])
    long["year"] = long["year"].astype(int)
    long.columns = ["country_code", "indicator_code", "year", "value"]
    return long.sort_values(["country_code", "indicator_code", "year"]).reset_index(drop=True)


def main():
    data, countries_meta, series_meta = load_raw()
    print("Raw rows:", len(data))

    data = clean_main(data)
    print("Rows after cleaning:", len(data))

    countries = build_countries(data, countries_meta)
    indicators = build_indicators(data, series_meta)
    debt = build_debt_data(data)

    countries.to_csv("countries_clean.csv", index=False)
    indicators.to_csv("indicators_clean.csv", index=False)
    debt.to_csv("debt_data_clean.csv", index=False)

    print("\ncountries_clean.csv  :", len(countries), "rows",
          f"({int((countries.is_aggregate == 0).sum())} real countries,",
          f"{int(countries.is_aggregate.sum())} regional groups)")
    print("indicators_clean.csv :", len(indicators), "rows;", indicators["unit"].value_counts().to_dict())
    print("debt_data_clean.csv  :", len(debt), "rows; years", debt.year.min(), "to", debt.year.max())
    print("\nChecks:")
    print("  every debt country in countries :", set(debt.country_code) <= set(countries.country_code))
    print("  every debt indicator in indicators:", set(debt.indicator_code) <= set(indicators.indicator_code))
    print("  duplicate keys in debt_data     :", int(debt.duplicated(["country_code", "indicator_code", "year"]).sum()))
    print("  null values left                :", int(debt.isna().sum().sum()))


if __name__ == "__main__":
    main()

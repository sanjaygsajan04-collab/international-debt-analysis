"""Step 4: Exploratory Data Analysis. Prints findings and saves charts to eda_charts/."""
import os
import matplotlib
matplotlib.use("Agg")  # save charts to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

TOTAL_DEBT = "DT.DOD.DECT.CD"   # External debt stocks, total (current US$)
os.makedirs("eda_charts", exist_ok=True)
sns.set_theme(style="whitegrid")

debt = pd.read_csv("debt_data_clean.csv")
countries = pd.read_csv("countries_clean.csv")
indicators = pd.read_csv("indicators_clean.csv")

real = countries[countries.is_aggregate == 0]          # leave out regional groups
total = debt[(debt.indicator_code == TOTAL_DEBT) & debt.country_code.isin(real.country_code)]
total = total.merge(real, on="country_code")
latest_year = int(total.year.max())
latest = total[total.year == latest_year].sort_values("value", ascending=False)


def billions(x):
    return x / 1e9


def save(name):
    plt.tight_layout()
    plt.savefig(f"eda_charts/{name}.png", dpi=120)
    plt.close()


print("1. DATA OVERVIEW")
print("   Real countries:", len(real), "| indicators:", len(indicators), "| rows:", len(debt))
print("   Years:", debt.year.min(), "to", debt.year.max(), "| latest year used:", latest_year)
print("   Indicators by unit:", indicators.unit.value_counts().to_dict())

print("\n2. STATISTICAL SUMMARY of total external debt, %d (US$ billion)" % latest_year)
print(billions(latest.value).describe().round(2).to_string())
print("   Median vs mean: debt is very skewed, a few countries owe most of the total.")

print("\n3. TOP AND LOWEST DEBT COUNTRIES, %d" % latest_year)
top10 = latest.head(10)
low10 = latest.tail(10)
print("   Highest:", ", ".join(f"{r.country_name} ({billions(r.value):,.0f}B)" for r in top10.itertuples()))
print("   Lowest :", ", ".join(f"{r.country_name} ({billions(r.value):,.2f}B)" for r in low10.itertuples()))
share = latest.value.head(10).sum() / latest.value.sum() * 100
print(f"   Top 10 countries hold {share:.1f}% of all external debt in the file.")

plt.figure(figsize=(9, 5))
sns.barplot(x=billions(top10.value), y=top10.country_name, color="#4f46e5")
plt.xlabel("Total external debt (US$ billion)"); plt.ylabel("")
plt.title(f"Top 10 countries by external debt, {latest_year}")
save("top10_countries")

print("\n4. GLOBAL TREND (all real countries)")
trend = total.groupby("year").value.sum() / 1e12
print("   2000: %.2f trillion -> %d: %.2f trillion (x%.1f)" % (trend.iloc[0], latest_year, trend.iloc[-1], trend.iloc[-1] / trend.iloc[0]))
growth = trend.pct_change() * 100
print("   Fastest growth year: %d (+%.1f%%) | only falls: %s" % (growth.idxmax(), growth.max(), ", ".join(str(y) for y in growth[growth < 0].index)))
plt.figure(figsize=(9, 4.5))
sns.lineplot(x=trend.index, y=trend.values, marker="o", color="#0ea5e9")
plt.ylabel("US$ trillion"); plt.xlabel("Year"); plt.title("Total external debt of all countries")
save("global_trend")

print("\n5. BY REGION AND INCOME GROUP, %d (US$ billion)" % latest_year)
region = (latest.groupby("region").value.sum() / 1e9).sort_values(ascending=False)
income = (latest.groupby("income_group").value.sum() / 1e9).sort_values(ascending=False)
print(region.round(0).to_string()); print(income.round(0).to_string())
plt.figure(figsize=(9, 4.5))
sns.barplot(x=region.values, y=region.index, color="#4f46e5")
plt.xlabel("US$ billion"); plt.ylabel(""); plt.title(f"External debt by region, {latest_year}")
save("by_region")

print("\n6. DEBT TYPES, %d (US$ billion) - parts of total external debt" % latest_year)
parts = {"DT.DOD.DPPG.CD": "Public & publicly guaranteed", "DT.DOD.DPNG.CD": "Private non-guaranteed",
         "DT.DOD.DSTC.CD": "Short-term", "DT.DOD.DIMF.CD": "IMF credit"}
sel = debt[debt.indicator_code.isin(parts) & (debt.year == latest_year) & debt.country_code.isin(real.country_code)]
by_type = (sel.groupby("indicator_code").value.sum() / 1e9).rename(index=parts).sort_values(ascending=False)
print(by_type.round(0).to_string())
print("   These four types do not overlap: together they add up to the total external debt.")
plt.figure(figsize=(8, 4))
sns.barplot(x=by_type.values, y=by_type.index, color="#10b981")
plt.xlabel("US$ billion"); plt.ylabel(""); plt.title(f"Debt by type, {latest_year}")
save("by_type")

print("\n7. DISTRIBUTION (log scale)")
plt.figure(figsize=(8, 4))
sns.histplot(billions(latest.value), log_scale=True, bins=25, color="#4f46e5")
plt.xlabel("Total external debt, US$ billion (log scale)"); plt.title("How debt is spread across countries")
save("distribution")

print("\n8. RELATIONSHIP: debt vs debt service (%d)" % latest_year)
service = debt[(debt.indicator_code == "DT.TDS.DECT.CD") & (debt.year == latest_year)]
both = latest.merge(service[["country_code", "value"]], on="country_code", suffixes=("_debt", "_service"))
corr = both[["value_debt", "value_service"]].corr().iloc[0, 1]
print("   Correlation between total debt and debt service: %.2f" % corr)
plt.figure(figsize=(7, 5))
sns.scatterplot(x=billions(both.value_debt), y=billions(both.value_service), color="#4f46e5")
plt.xscale("log"); plt.yscale("log")
plt.xlabel("Total external debt (US$ billion)"); plt.ylabel("Debt service (US$ billion)")
plt.title("Bigger debt, bigger repayments")
save("debt_vs_service")

print("\nCharts saved in the eda_charts folder.")

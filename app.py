import math
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from db import run_query
from sql_utils import read_statements, read_titles

APP_NAME = "Debt Compass"   # change the dashboard name here

st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="collapsed")

HERE = os.path.dirname(os.path.abspath(__file__))
DEBT_TYPES = {
    "DT.DOD.DPPG.CD": "Public & publicly guaranteed",
    "DT.DOD.DPNG.CD": "Private non-guaranteed",
    "DT.DOD.DSTC.CD": "Short-term",
    "DT.DOD.DIMF.CD": "IMF credit",
}

# Palette: paper, ink and forest green with amber and terracotta accents
PAPER, INK, FOREST, AMBER, TERRACOTTA = "#f5f0e6", "#1f2a24", "#1f5f4a", "#d98e04", "#b5532f"
COLORWAY = ["#1f5f4a", "#d98e04", "#b5532f", "#4a5d6a", "#7a9e7e", "#8c5a7c"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=DM+Sans:wght@400;500;700&display=swap');
.stApp { background: #f5f0e6; }
html, body, p, label, li, button, input, textarea, [data-testid="stMarkdownContainer"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3, h4, .serif { font-family: 'Fraunces', serif !important; color: #1f2a24; letter-spacing: -0.01em; }
.block-container { max-width: 1250px; padding-top: 1.5rem; }
.masthead { display: flex; justify-content: space-between; align-items: flex-end;
            border-bottom: 3px double #1f2a24; padding-bottom: 10px; margin-bottom: 14px; }
.masthead .title { font-family: 'Fraunces', serif; font-size: 2.6rem; font-weight: 700; color: #1f2a24; line-height: 1; }
.masthead .tag { font-size: 0.85rem; letter-spacing: 0.14em; text-transform: uppercase; color: #1f5f4a; margin-top: 6px; }
.masthead .source { font-size: 0.8rem; color: #4a5d6a; text-align: right; }
.section { margin: 26px 0 6px 0; }
.section .kicker { font-size: 0.75rem; letter-spacing: 0.16em; text-transform: uppercase; color: #b5532f; font-weight: 700; }
.section .head { font-family: 'Fraunces', serif; font-size: 1.55rem; font-weight: 700; color: #1f2a24; }
.stat { background: #fffdf8; border: 1px solid #d9d0bb; border-left: 6px solid #1f5f4a; border-radius: 6px; padding: 12px 16px; }
.stat .label { font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; color: #4a5d6a; }
.stat .value { font-family: 'Fraunces', serif; font-size: 2rem; font-weight: 700; color: #1f2a24; line-height: 1.15; }
.stat .note { font-size: 0.82rem; color: #b5532f; }
.story-number { font-family: 'Fraunces', serif; font-size: 3.4rem; font-weight: 700; color: #1f5f4a; line-height: 1; }
.story-title { font-family: 'Fraunces', serif; font-size: 1.35rem; font-weight: 700; color: #1f2a24; margin: 6px 0; }
.story-text { font-size: 1rem; color: #33403a; line-height: 1.55; }
.chapter { font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; color: #d98e04; font-weight: 700; }
</style>
"""


# ---------- Look and feel helpers ----------
def masthead(year_text):
    st.markdown(
        f"<div class='masthead'><div><div class='title'>{APP_NAME}</div>"
        "<div class='tag'>External debt of developing countries, 2000 to 2024</div></div>"
        f"<div class='source'>Source: World Bank International Debt Statistics<br>{year_text}</div></div>",
        unsafe_allow_html=True,
    )


def section(kicker, head):
    st.markdown(
        f"<div class='section'><div class='kicker'>{kicker}</div><div class='head'>{head}</div></div>",
        unsafe_allow_html=True,
    )


def stat_card(label, value, note=""):
    st.markdown(
        f"<div class='stat'><div class='label'>{label}</div><div class='value'>{value}</div>"
        f"<div class='note'>{note}&nbsp;</div></div>",
        unsafe_allow_html=True,
    )


def money(value):
    """Short US$ text: $8.94T, $716.0B or $320.4M."""
    value = float(value)
    if abs(value) >= 1e12:
        return f"${value / 1e12:,.2f}T"
    if abs(value) >= 1e9:
        return f"${value / 1e9:,.1f}B"
    return f"${value / 1e6:,.1f}M"


def style(fig, height=380, card=False):
    """Give every Plotly chart the same look. card=True puts the chart on a light card."""
    ink = INK
    fig.update_layout(
        height=height,
        font=dict(family="DM Sans, sans-serif", color=ink),
        paper_bgcolor="#fffdf8" if card else "rgba(0,0,0,0)",
        plot_bgcolor="#fffdf8" if card else "rgba(0,0,0,0)",
        colorway=COLORWAY,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(title=None),
    )
    grid = "#e0d8c4"
    fig.update_xaxes(gridcolor=grid, zeroline=False)
    fig.update_yaxes(gridcolor=grid, zeroline=False)
    return fig


def show(fig, key, select=False):
    """Draw a chart. With select=True the chart reports clicks back to Python."""
    if select:
        return st.plotly_chart(fig, key=key, width="stretch", on_select="rerun", selection_mode="points")
    st.plotly_chart(fig, key=key, width="stretch")
    return None


def picked_country(event, code_to_name=None):
    """Name of the country the user clicked in a chart, or None."""
    try:
        points = event.selection.points
        for p in points:
            custom = p.get("customdata")
            if custom:
                return custom[0] if isinstance(custom, (list, tuple)) else custom
            for axis in ("y", "x"):
                if isinstance(p.get(axis), str):
                    return p[axis]
            if code_to_name and p.get("location") in code_to_name:
                return code_to_name[p["location"]]
    except Exception:
        pass
    return None


def csv_button(df, filename):
    st.download_button(
        "Download CSV", df.to_csv(index=False).encode("utf-8"),
        file_name=filename, mime="text/csv", key=f"dl_{filename}",
    )


# ---------- Data loading (cached, so the database is only asked once) ----------
@st.cache_data(show_spinner="Loading debt data...")
def load_total_debt():
    """Total external debt for every real country and year (from the v_total_debt view)."""
    df = run_query(
        "SELECT country_code, country_name, region, income_group, year, total_debt FROM v_total_debt"
    )
    df["total_debt"] = df["total_debt"].astype(float)
    df["year"] = df["year"].astype(int)
    return df


@st.cache_data(show_spinner="Loading debt types...")
def load_debt_types():
    """The four debt types that add up to total debt, for every country and year."""
    codes = ", ".join(f"'{code}'" for code in DEBT_TYPES)
    df = run_query(
        "SELECT d.country_code, c.country_name, c.region, d.indicator_code, d.year, d.value "
        "FROM debt_data d JOIN countries c ON d.country_code = c.country_code "
        f"WHERE c.is_aggregate = 0 AND d.indicator_code IN ({codes})"
    )
    df["value"] = df["value"].astype(float)
    df["year"] = df["year"].astype(int)
    df["debt_type"] = df["indicator_code"].map(DEBT_TYPES)
    return df


@st.cache_data(show_spinner="Loading debt burden...")
def load_burden(total):
    """Debt size, debt as % of national income (GNI) and yearly repayments, per country and year."""
    raw = run_query(
        "SELECT d.country_code, d.indicator_code, d.year, d.value "
        "FROM debt_data d JOIN countries c ON d.country_code = c.country_code "
        "WHERE c.is_aggregate = 0 AND d.indicator_code IN ('DT.DOD.DECT.GN.ZS', 'DT.TDS.DECT.CD')"
    )
    raw["value"] = raw["value"].astype(float)
    raw["year"] = raw["year"].astype(int)
    wide = raw.pivot_table(index=["country_code", "year"], columns="indicator_code", values="value").reset_index()
    wide = wide.rename(columns={"DT.DOD.DECT.GN.ZS": "debt_pct_gni", "DT.TDS.DECT.CD": "debt_service"})
    for col in ("debt_pct_gni", "debt_service"):
        if col not in wide.columns:
            wide[col] = float("nan")
    return total.merge(wide, on=["country_code", "year"], how="left")


@st.cache_data(show_spinner="Loading indicators...")
def load_indicators_for_year(year):
    """Every US$ external debt stock indicator (except the total) for one year."""
    df = run_query(
        "SELECT d.country_code, d.indicator_code, i.indicator_name, d.value "
        "FROM debt_data d "
        "JOIN indicators i ON d.indicator_code = i.indicator_code "
        "JOIN countries c ON d.country_code = c.country_code "
        "WHERE c.is_aggregate = 0 AND i.unit = 'US$' "
        "AND SUBSTR(d.indicator_code, 1, 7) = 'DT.DOD.' AND d.indicator_code <> 'DT.DOD.DECT.CD' "
        "AND d.year = %s",
        params=(int(year),),
    )
    df["value"] = df["value"].astype(float)
    return df


@st.cache_data
def load_indicator_list():
    return run_query(
        "SELECT indicator_code, indicator_name, topic FROM indicators "
        "WHERE unit = 'US$' ORDER BY indicator_name"
    )


@st.cache_data(show_spinner="Loading indicator...")
def load_indicator_values(code, year):
    """One indicator for one year, every real country (parameterised query)."""
    df = run_query(
        "SELECT c.country_name, c.region, d.value FROM debt_data d "
        "JOIN countries c ON d.country_code = c.country_code "
        "WHERE c.is_aggregate = 0 AND d.indicator_code = %s AND d.year = %s "
        "ORDER BY d.value DESC",
        params=(code, int(year)),
    )
    df["value"] = df["value"].astype(float)
    return df


# ---------- Atlas: the one-page picture ----------
def atlas_controls(total):
    """The only filters in the app: a year and (optionally) some regions."""
    first, last = int(total["year"].min()), int(total["year"].max())
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        year = c1.slider("Year", first, last, last, key="atlas_year")
        regions = sorted(total["region"].unique())
        chosen = c2.pills("Regions (leave empty for all)", regions, selection_mode="multi", key="atlas_regions")
    return year, (chosen or regions)


def atlas_summary(scope, year):
    current = scope[scope["year"] == year]
    total_now = current["total_debt"].sum()
    previous = scope[scope["year"] == year - 1]["total_debt"].sum()
    change = f"{(total_now / previous - 1) * 100:+.1f}% vs {year - 1}" if previous else "first year in the data"
    ranked = current.sort_values("total_debt", ascending=False)
    top10_share = ranked["total_debt"].head(10).sum() / total_now * 100 if total_now else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Total external debt", money(total_now), change)
    with c2:
        stat_card("Countries", f"{len(current)}", "with data this year")
    with c3:
        stat_card("Top 10 hold", f"{top10_share:.0f}%", "of all the debt")
    with c4:
        biggest = ranked.iloc[0] if len(ranked) else None
        stat_card("Largest debtor", biggest["country_name"] if biggest is not None else "-",
                  money(biggest["total_debt"]) if biggest is not None else "")
    return current


def map_and_treemap(current, code_to_name):
    section("Chapter 1", "Where the debt sits")
    left, right = st.columns([3, 2])
    df = current.assign(debt_b=current["total_debt"] / 1e9)
    df["log_debt"] = df["debt_b"].clip(lower=0.01).apply(math.log10)
    with left:
        fig = px.choropleth(
            df, locations="country_code", color="log_debt", hover_name="country_name",
            custom_data=["country_name"], hover_data={"debt_b": ":,.1f", "log_debt": False, "country_code": False},
            color_continuous_scale=["#e9efe3", "#9cc3a5", "#3f8a6b", "#1f5f4a", "#10342a"],
        )
        fig.update_coloraxes(colorbar=dict(
            title="US$ bn", tickvals=[-1, 0, 1, 2, 3], ticktext=["0.1", "1", "10", "100", "1,000"]))
        fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth",
                        bgcolor="rgba(0,0,0,0)", landcolor="#e8e2d2", showcountries=True, countrycolor="#f5f0e6")
        style(fig, 420)
        fig.update_layout(title="Debt by country (click a country)")
        event = show(fig, "atlas_map", select=True)
    with right:
        tree = px.treemap(
            df, path=[px.Constant("All countries"), "region", "country_name"], values="debt_b",
            color="region", color_discrete_sequence=COLORWAY,
        )
        style(tree, 420)
        tree.update_layout(title="Share of debt: region, then country")
        tree.update_traces(root_color="#f5f0e6")
        show(tree, "atlas_treemap")
    return picked_country(event, code_to_name)


def highest_lowest(current):
    section("Chapter 2", "The heaviest and the lightest debtors")
    ranked = current.sort_values("total_debt", ascending=False).assign(debt_b=lambda d: d["total_debt"] / 1e9)
    top = ranked.head(10)
    bottom = ranked.tail(10)
    left, right = st.columns(2)
    picks = []
    for column, data, title, color, key in [
        (left, top, "Ten highest (US$ billion)", FOREST, "atlas_top"),
        (right, bottom, "Ten lowest (US$ billion)", AMBER, "atlas_bottom"),
    ]:
        with column:
            fig = px.bar(data, x="debt_b", y="country_name", orientation="h", custom_data=["country_name"],
                         color_discrete_sequence=[color], labels={"debt_b": "US$ billion", "country_name": ""})
            fig.update_yaxes(categoryorder="total ascending")
            style(fig, 380)
            fig.update_layout(title=title)
            picks.append(picked_country(show(fig, key, select=True)))
    return next((p for p in picks if p), None)


def spotlight(country, scope, debt_types, year):
    section("Spotlight", f"{country}")
    history = scope[scope["country_name"] == country].sort_values("year")
    if history.empty:
        st.info("No data for this country with the current regions.")
        return
    now = history[history["year"] == year]
    left, right = st.columns(2)
    with left:
        history = history.assign(debt_b=history["total_debt"] / 1e9)
        fig = px.area(history, x="year", y="debt_b", labels={"debt_b": "US$ billion", "year": ""},
                      color_discrete_sequence=[FOREST])
        style(fig, 320)
        fig.update_layout(title="Debt over time (US$ billion)")
        show(fig, "spot_history")
    with right:
        types = debt_types[(debt_types["country_name"] == country) & (debt_types["year"] == year)]
        if types.empty:
            st.info("No debt-type data for this year.")
        else:
            fig = px.pie(types, names="debt_type", values="value", hole=0.55, color_discrete_sequence=COLORWAY)
            style(fig, 320)
            fig.update_layout(title=f"What the debt is made of, {year}")
            show(fig, "spot_types")
    if not now.empty:
        st.caption(f"{country} owed {money(now['total_debt'].iloc[0])} in {year}.")


def indicators_section(scope, debt_types, year):
    section("Chapter 3", "Debt across the indicators")
    codes = set(scope["country_code"])
    left, right = st.columns(2)
    with left:
        types = debt_types[(debt_types["year"] == year) & debt_types["country_code"].isin(codes)]
        by_type = types.groupby("debt_type")["value"].sum().reset_index()
        by_type["debt_b"] = by_type["value"] / 1e9
        fig = px.pie(by_type, names="debt_type", values="debt_b", hole=0.55, color_discrete_sequence=COLORWAY)
        style(fig, 380)
        fig.update_layout(title="Four types of debt that add up to the total")
        show(fig, "atlas_types")
    with right:
        raw = load_indicators_for_year(year)
        raw = raw[raw["country_code"].isin(codes)]
        by_indicator = raw.groupby("indicator_name")["value"].sum().sort_values(ascending=False).head(8)
        data = (by_indicator / 1e9).rename("debt_b").reset_index()
        data["indicator_name"] = data["indicator_name"].str.replace("External debt stocks, ", "", regex=False) \
            .str.replace(" (DOD, current US$)", "", regex=False)
        fig = px.bar(data, x="debt_b", y="indicator_name", orientation="h",
                     color_discrete_sequence=[TERRACOTTA], labels={"debt_b": "US$ billion", "indicator_name": ""})
        fig.update_yaxes(categoryorder="total ascending")
        style(fig, 380)
        fig.update_layout(title="Eight biggest debt indicators (they overlap)")
        show(fig, "atlas_indicators")


def trends_section(scope):
    section("Chapter 4", "Trends and patterns")
    left, right = st.columns(2)
    by_region = scope.groupby(["year", "region"])["total_debt"].sum().reset_index()
    by_region["debt_t"] = by_region["total_debt"] / 1e12
    with left:
        share = st.toggle("Show as share of the total (%)", key="atlas_share")
        fig = px.area(by_region, x="year", y="debt_t", color="region", color_discrete_sequence=COLORWAY,
                      groupnorm="percent" if share else None,
                      labels={"debt_t": "Percent" if share else "US$ trillion", "year": ""})
        style(fig, 380)
        fig.update_layout(title="Debt by region over time")
        show(fig, "atlas_regions_trend")
    with right:
        yearly = scope.groupby("year")["total_debt"].sum()
        growth = (yearly.pct_change() * 100).dropna().rename("growth").reset_index()
        growth["direction"] = growth["growth"].apply(lambda g: "Growth" if g >= 0 else "Fall")
        fig = px.bar(growth, x="year", y="growth", color="direction",
                     color_discrete_map={"Growth": FOREST, "Fall": TERRACOTTA},
                     labels={"growth": "% change on previous year", "year": ""})
        style(fig, 380)
        fig.update_layout(title="Year-on-year growth of total debt", showlegend=False)
        show(fig, "atlas_growth")


def atlas_page(total, debt_types):
    year, regions = atlas_controls(total)
    scope = total[total["region"].isin(regions)]
    if scope[scope["year"] == year].empty:
        st.warning("No data for this choice.")
        return
    current = atlas_summary(scope, year)
    code_to_name = dict(zip(current["country_code"], current["country_name"]))

    from_map = map_and_treemap(current, code_to_name)
    from_bars = highest_lowest(current)
    chosen = from_bars or from_map
    if chosen:
        spotlight(chosen, scope, debt_types, year)
    indicators_section(scope, debt_types, year)
    trends_section(scope)

    with st.expander("How is debt defined here?"):
        st.write(
            "Debt means **total external debt stocks** (World Bank code DT.DOD.DECT.CD) in current US$, "
            "the amount owed to foreign lenders at the end of the year. Regional groups such as "
            "'IDA total' are left out so no debt is counted twice."
        )


# ---------- Stories: a short read, one idea per chapter ----------
def story(number, chapter, title, text, fig, key, flip=False):
    with st.container(border=True):
        if flip:
            chart, words = st.columns([3, 2])
        else:
            words, chart = st.columns([2, 3])
        with words:
            st.markdown(f"<div class='chapter'>{chapter}</div><div class='story-number'>{number}</div>"
                        f"<div class='story-title'>{title}</div><div class='story-text'>{text}</div>",
                        unsafe_allow_html=True)
        with chart:
            show(fig, key)


def stories_page(total, burden):
    last = int(total["year"].max())
    first = int(total["year"].min())
    now = total[total["year"] == last].sort_values("total_debt", ascending=False)
    grand = now["total_debt"].sum()

    # 1 concentration
    shares = (now["total_debt"].cumsum() / grand * 100).reset_index(drop=True)
    top10 = shares.iloc[9] if len(shares) >= 10 else shares.iloc[-1]
    reach80 = int((shares < 80).sum() + 1)
    df = pd.DataFrame({"rank": range(1, len(shares) + 1), "share": shares})
    fig = px.line(df, x="rank", y="share", color_discrete_sequence=[FOREST],
                  labels={"rank": "Countries, biggest first", "share": "Cumulative % of all debt"})
    fig.add_vline(x=10, line_dash="dot", line_color=TERRACOTTA)
    style(fig, 340)
    story(f"{top10:.0f}%", "Chapter 1: concentration", "A handful of borrowers carry most of the debt",
          f"The ten biggest debtors hold {top10:.0f}% of all external debt in {last}. "
          f"Just {reach80} of {len(now)} countries account for 80%.", fig, "story_1")

    # 2 growth
    yearly = total.groupby("year")["total_debt"].sum().reset_index()
    yearly["debt_t"] = yearly["total_debt"] / 1e12
    multiple = yearly["total_debt"].iloc[-1] / yearly["total_debt"].iloc[0]
    fig = px.area(yearly, x="year", y="debt_t", color_discrete_sequence=[AMBER],
                  labels={"debt_t": "US$ trillion", "year": ""})
    style(fig, 340)
    story(f"x{multiple:.1f}", "Chapter 2: growth", "Debt grew almost fivefold in a generation",
          f"Total external debt rose from {money(yearly['total_debt'].iloc[0])} in {first} to "
          f"{money(yearly['total_debt'].iloc[-1])} in {last}.", fig, "story_2", flip=True)

    # 3 regions
    start = total[total["year"] == first].groupby("region")["total_debt"].sum()
    end = total[total["year"] == last].groupby("region")["total_debt"].sum()
    change = ((end - start.reindex(end.index).fillna(0)) / 1e9).sort_values(ascending=False).rename("rise").reset_index()
    leader = change.iloc[0]
    fig = px.bar(change, x="region", y="rise", color_discrete_sequence=[TERRACOTTA],
                 labels={"rise": f"Increase since {first} (US$ billion)", "region": ""})
    style(fig, 340)
    story(money(leader["rise"] * 1e9), "Chapter 3: regions", "One region drove most of the rise",
          f"{leader['region']} added {money(leader['rise'] * 1e9)} of debt since {first}, "
          "more than any other region.", fig, "story_3")

    # 4 income groups
    income = now.groupby("income_group")["total_debt"].sum().reset_index()
    top_income = income.sort_values("total_debt", ascending=False).iloc[0]
    fig = px.pie(income, names="income_group", values="total_debt", hole=0.55, color_discrete_sequence=COLORWAY)
    style(fig, 340)
    story(f"{top_income['total_debt'] / grand * 100:.0f}%", "Chapter 4: income",
          f"{top_income['income_group']} countries owe the most",
          f"Countries in the '{top_income['income_group']}' group hold "
          f"{top_income['total_debt'] / grand * 100:.0f}% of the total, far more than low-income countries.",
          fig, "story_4", flip=True)

    # 5 burden
    latest = burden[(burden["year"] == last)].dropna(subset=["debt_pct_gni"])
    heavy = latest.sort_values("debt_pct_gni", ascending=False)
    biggest = now.iloc[0]["country_name"]
    rank_text = ""
    row = heavy.reset_index(drop=True)
    match = row.index[row["country_name"] == biggest]
    if len(match):
        rank_text = f" The biggest debtor, {biggest}, ranks only {int(match[0]) + 1} of {len(row)} on this measure."
    fig = px.bar(heavy.head(10), x="debt_pct_gni", y="country_name", orientation="h",
                 color_discrete_sequence=[FOREST], labels={"debt_pct_gni": "Debt as % of national income", "country_name": ""})
    fig.update_yaxes(categoryorder="total ascending")
    style(fig, 340)
    top_burden = heavy.iloc[0]
    story(f"{top_burden['debt_pct_gni']:.0f}%", "Chapter 5: burden", "Big debt is not the same as heavy debt",
          f"Measured against national income, {top_burden['country_name']} is the most indebted "
          f"at {top_burden['debt_pct_gni']:.0f}% of GNI.{rank_text}", fig, "story_5")


# ---------- Country lab ----------
def country_lab(total, burden):
    section("Country", "Watch countries move")
    data = burden.dropna(subset=["debt_pct_gni"]).copy()
    data["debt_service"] = data["debt_service"].fillna(0).clip(lower=0)
    data["debt_b"] = data["total_debt"] / 1e9
    data["service_b"] = data["debt_service"] / 1e9
    data = data.sort_values("year")
    fig = px.scatter(
        data, x="debt_b", y="debt_pct_gni", size="service_b", color="region", hover_name="country_name",
        animation_frame="year", animation_group="country_name", log_x=True, size_max=50,
        range_x=[0.1, 5000], range_y=[0, max(20.0, float(data["debt_pct_gni"].quantile(0.99)) * 1.1)],
        labels={"debt_b": "Total debt (US$ billion, log scale)", "debt_pct_gni": "Debt as % of national income",
                "service_b": "Yearly repayments (US$ billion)"},
        color_discrete_sequence=COLORWAY,
    )
    style(fig, 520, card=True)
    fig.update_xaxes(tickvals=[0.1, 1, 10, 100, 1000], ticktext=["0.1", "1", "10", "100", "1,000"])
    fig.update_layout(title="Press play: size = yearly repayments, height = debt burden")
    try:
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 600
    except Exception:
        pass
    show(fig, "lab_bubbles")

    section("Country", "Compare countries")
    names = sorted(total["country_name"].unique())
    defaults = [n for n in ["China", "India", "Brazil"] if n in names]
    c1, c2 = st.columns([3, 2])
    chosen = c1.multiselect("Countries (up to 8)", names, default=defaults, max_selections=8, key="lab_countries")
    first, last = int(total["year"].min()), int(total["year"].max())
    start, end = c2.slider("Years", first, last, (first, last), key="lab_years")
    growth = st.toggle("Show growth since the first year (%)", key="lab_growth")
    if not chosen:
        st.info("Choose at least one country.")
        return
    rows = total[total["country_name"].isin(chosen) & total["year"].between(start, end)]
    wide = rows.pivot_table(index="year", columns="country_name", values="total_debt") / 1e9
    if growth:
        base = wide.apply(lambda col: col.dropna().iloc[0] if col.notna().any() else float("nan"))
        wide = (wide / base - 1) * 100
    long = wide.reset_index().melt(id_vars="year", var_name="country_name", value_name="value").dropna()
    fig = px.line(long, x="year", y="value", color="country_name", color_discrete_sequence=COLORWAY,
                  labels={"value": "% growth" if growth else "US$ billion", "year": "", "country_name": ""})
    style(fig, 400)
    show(fig, "lab_compare")

    summary = rows.sort_values("year").groupby("country_name").agg(
        first_year=("year", "min"), last_year=("year", "max"),
        first_debt=("total_debt", "first"), last_debt=("total_debt", "last"),
    )
    summary["change_pct"] = ((summary["last_debt"] / summary["first_debt"] - 1) * 100).round(1)
    table = summary.reset_index()
    table["first_debt"] = (table["first_debt"] / 1e9).round(2)
    table["last_debt"] = (table["last_debt"] / 1e9).round(2)
    table = table.rename(columns={"first_debt": "first_debt_billion", "last_debt": "last_debt_billion"})
    st.dataframe(table, width="stretch", hide_index=True)
    csv_button(table, "country_comparison.csv")


# ---------- Indicator lab ----------
def indicator_chart(shown, key):
    fig = px.bar(shown, x="value_b", y="country_name", orientation="h", color="region",
                 color_discrete_sequence=COLORWAY, labels={"value_b": "US$ billion", "country_name": ""})
    fig.update_yaxes(categoryorder="total ascending")
    style(fig, max(380, 24 * len(shown) + 120))
    show(fig, key)


def indicator_table(values, key_suffix=""):
    table = values.rename(columns={"country_name": "Country", "region": "Region", "value": "Value (US$)"})
    st.dataframe(table, width="stretch", hide_index=True)
    csv_button(table, "indicator_values.csv")


def debt_types_sunburst(debt_types, year, key):
    types = debt_types[debt_types["year"] == year]
    if types.empty:
        st.info("No debt-type data for this year.")
        return
    fig = px.sunburst(types.assign(debt_b=types["value"] / 1e9), path=["region", "debt_type"], values="debt_b",
                      color_discrete_sequence=COLORWAY)
    style(fig, 460)
    fig.update_layout(title=f"Debt types inside each region, {year} (click a region to zoom)")
    show(fig, key)


def indicator_lab(total, debt_types):
    section("Indicator", "Look at any indicator")
    indicators = load_indicator_list()
    label = dict(zip(indicators["indicator_code"], indicators["indicator_name"]))
    topic = dict(zip(indicators["indicator_code"], indicators["topic"]))
    default = list(label).index("DT.DOD.DECT.CD") if "DT.DOD.DECT.CD" in label else 0
    code = st.selectbox("Indicator (type to search 538 US$ indicators)", list(label), index=default,
                        format_func=lambda c: label[c], key="ind_code")
    st.caption(topic[code])
    c1, c2, c3 = st.columns(3)
    last = int(total["year"].max())
    year = c1.slider("Year", int(total["year"].min()), last, last, key="ind_year")
    top_n = c2.slider("Show top", 5, 40, 15, step=5, key="ind_top")
    layout = c3.radio("Layout", ["Side by side", "Tabs", "Stacked"], key="ind_layout")

    values = load_indicator_values(code, year)
    if values.empty:
        st.warning("This indicator has no data for the chosen year.")
        return
    shown = values.head(top_n).assign(value_b=lambda d: d["value"] / 1e9)

    if layout == "Tabs":
        tab_chart, tab_table, tab_types = st.tabs(["Chart", "Table", "Debt types"])
        with tab_chart:
            indicator_chart(shown, "ind_bar")
        with tab_table:
            indicator_table(values)
        with tab_types:
            debt_types_sunburst(debt_types, year, "ind_sunburst")
    elif layout == "Stacked":
        indicator_chart(shown, "ind_bar")
        indicator_table(values)
        section("Indicator", "What the debt is made of")
        debt_types_sunburst(debt_types, year, "ind_sunburst")
    else:
        left, right = st.columns([3, 2])
        with left:
            indicator_chart(shown, "ind_bar")
        with right:
            indicator_table(values)
        section("Indicator", "What the debt is made of")
        debt_types_sunburst(debt_types, year, "ind_sunburst")


# ---------- SQL desk ----------
def load_queries():
    """The 30 analytical queries from queries.sql (only the SELECT ones are runnable)."""
    path = os.path.join(HERE, "queries.sql")
    titles = read_titles(path)
    queries = {}
    for query_id, sql in read_statements(path):
        if sql.upper().startswith(("SELECT", "WITH")):
            queries[query_id] = sql
    return {f"{qid}. {titles.get(qid, '')}": sql for qid, sql in queries.items()}


def sql_desk():
    section("SQL", "The 30 analytical queries")
    queries = load_queries()
    choice = st.selectbox("Choose a query", list(queries.keys()), key="sql_choice")
    sql = queries[choice]
    st.code(sql, language="sql")
    if st.button("Run query", key="sql_run"):
        result = run_query(sql)
        st.write(f"{len(result):,} rows")
        st.dataframe(result, width="stretch", hide_index=True)
        csv_button(result, "query_result.csv")


# ---------- App ----------
def main():
    st.markdown(CSS, unsafe_allow_html=True)
    total = load_total_debt()
    masthead(f"Data up to {int(total['year'].max())}")
    atlas, stories, country, indicator, sql = st.tabs(["Atlas", "Stories", "Country", "Indicator", "SQL"])
    debt_types = load_debt_types()
    with atlas:
        atlas_page(total, debt_types)
    with stories:
        stories_page(total, load_burden(total))
    with country:
        country_lab(total, load_burden(total))
    with indicator:
        indicator_lab(total, debt_types)
    with sql:
        sql_desk()


main()

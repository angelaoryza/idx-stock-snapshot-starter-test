"""A simple calculator showing how monthly savings may grow over time."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from sectors import (
    SectorsError,
    get_company_financials,
    get_company_overview,
    get_daily_prices,
)


@st.cache_data(ttl=3600)
def get_cached_daily_prices(ticker, start, end):
    return get_daily_prices(ticker, start=start, end=end)


@st.cache_data(ttl=3600)
def get_cached_company_financials(ticker):
    return get_company_financials(ticker)


def format_rupiah(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")


st.set_page_config(page_title="Investment Goal Calculator", layout="centered")
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0C0A09;
        background-image: radial-gradient(
            ellipse 80% 40% at 50% 0%,
            rgba(229, 51, 126, 0.12),
            transparent 70%
        );
    }

    [data-testid="stMetric"] {
        min-height: 112px;
        padding: 16px;
        background: rgba(28, 23, 20, 0.72);
        border: 1px solid rgba(246, 241, 238, 0.14);
        border-radius: 14px;
        box-shadow: 0 12px 38px -16px rgba(0, 0, 0, 0.6),
            inset 0 1px 0 rgba(246, 241, 238, 0.08);
    }

    [data-testid="stMetricLabel"] p {
        color: #A99F99;
        font-family: "JetBrains Mono", monospace;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    [data-testid="stMetricValue"] {
        color: #F6F1EE;
        font-family: "JetBrains Mono", monospace;
        font-weight: 700;
    }

    .st-key-daily-change-positive [data-testid="stMetricValue"] {
        color: #1FB36A;
    }

    .st-key-daily-change-negative [data-testid="stMetricValue"] {
        color: #E0003B;
    }

    .st-key-company-facts {
        padding: 16px 18px 8px;
        background: rgba(28, 23, 20, 0.5);
        border: 1px solid rgba(246, 241, 238, 0.14);
        border-radius: 14px;
        box-shadow: 0 12px 38px -16px rgba(0, 0, 0, 0.6),
            inset 0 1px 0 rgba(246, 241, 238, 0.08);
    }

    .st-key-company-facts h2 {
        margin-top: 0;
        font-family: "Plus Jakarta Sans", sans-serif;
    }

    .st-key-company-facts [data-testid="stHorizontalBlock"] {
        padding: 7px 0;
        border-bottom: 1px solid rgba(246, 241, 238, 0.07);
    }

    .st-key-company-facts [data-testid="stHorizontalBlock"]:last-child {
        border-bottom: 0;
    }

    .st-key-company-facts [data-testid="stCaptionContainer"] p {
        color: #A99F99;
        font-size: 0.8rem;
    }

    .st-key-company-facts [data-testid="stMarkdownContainer"] p {
        margin: 0;
        color: #F6F1EE;
        font-family: "JetBrains Mono", monospace;
        font-size: 0.82rem;
        font-weight: 700;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Investment Goal Calculator")
st.write("See how your monthly savings could grow over time.")

today = date.today()
default_date_range = (today - timedelta(days=30), today)
start_date, end_date = st.session_state.get(
    "closing_price_date_range",
    default_date_range,
)
effective_start_date = start_date
date_range_exceeds_limit = end_date - start_date > timedelta(days=90)
if date_range_exceeds_limit:
    effective_start_date = end_date - timedelta(days=90)

ticker = st.text_input("IDX ticker", value="BBCA")
company = None
company_error = None
try:
    company = get_company_overview(ticker)
except SectorsError as error:
    company_error = error
    st.warning(str(error))

personal_tab, price_tab, financials_tab = st.tabs(["Personal", "Price", "Financials"])

with price_tab:
    if company:
        with st.container(key="company-facts"):
            st.header(company.get("company_name", "Company name unavailable"))
            for label, value in (
                ("Sector", company.get("sector", "Not available")),
                ("Sub-sector", company.get("sub_sector", "Not available")),
            ):
                label_column, value_column = st.columns([1, 2])
                label_column.caption(label)
                value_column.write(value)

        last_close_price = company.get("last_close_price")
        daily_close_change = company.get("daily_close_change")
        market_cap = company.get("market_cap")
        last_close, daily_change, market_value = st.columns(3)
        last_close.metric(
            "Last close",
            format_rupiah(last_close_price) if last_close_price is not None else "Not available",
        )
        daily_change_tone = (
            "positive"
            if daily_close_change is not None and daily_close_change > 0
            else "negative"
            if daily_close_change is not None and daily_close_change < 0
            else "neutral"
        )
        with daily_change.container(key=f"daily-change-{daily_change_tone}"):
            st.metric(
                "Daily change",
                f"{daily_close_change:.2%}"
                if daily_close_change is not None
                else "Not available",
            )
        market_value.metric(
            "Market cap (Rp trillion)",
            f"{market_cap / 1_000_000_000_000:.1f}" if market_cap is not None else "Not available",
        )

        if last_close_price is not None and last_close_price > 0:
            lot_price = last_close_price * 100
            monthly_saving_for_lots = st.session_state.get("monthly_saving", 1_000_000)
            lots = monthly_saving_for_lots // lot_price
            leftover = monthly_saving_for_lots - lots * lot_price
            with st.container(border=True):
                st.caption("Based on your personal monthly saving (not Sectors market data)")
                st.write(f"Your monthly saving buys {lots} lots of this stock")
                st.write(f"Left over: {format_rupiah(leftover)}")

        if start_date > end_date:
            st.warning("The start date must be on or before the end date.")
        else:
            if date_range_exceeds_limit:
                st.warning("Sectors allows up to 90 days per request; showing the most recent 90 days.")

            try:
                daily_prices = get_cached_daily_prices(
                    ticker,
                    effective_start_date,
                    end_date,
                )
            except SectorsError as error:
                st.warning(str(error))
            else:
                st.subheader(
                    "Closing price, last 90 days"
                    if effective_start_date != start_date
                    else "Closing price, selected date range"
                )
                st.line_chart(
                    daily_prices,
                    x="date",
                    y="close",
                    x_label="Date",
                    y_label="Price (Rp)",
                )

        st.slider(
            "Closing price date range",
            min_value=today - timedelta(days=365),
            max_value=today,
            value=default_date_range,
            format="YYYY-MM-DD",
            key="closing_price_date_range",
        )

    st.subheader("Compare: every line starts at 100")
    comparison_tickers_text = st.text_input(
        "Compare 2 to 4 IDX tickers (comma-separated)",
        value="BBCA, TLKM",
    )
    comparison_tickers = list(
        dict.fromkeys(
            symbol.strip().upper()
            for symbol in comparison_tickers_text.split(",")
            if symbol.strip()
        )
    )

    if len(comparison_tickers) < 2:
        st.write("Choose at least two tickers to compare.")
    elif len(comparison_tickers) > 4:
        st.warning("Choose no more than four tickers to compare.")
    elif start_date > end_date:
        st.warning("The start date must be on or before the end date.")
    else:
        if date_range_exceeds_limit and not company:
            st.warning("Sectors allows up to 90 days per request; showing the most recent 90 days.")

        normalized_series = {}
        comparison_has_error = False
        for symbol in comparison_tickers:
            try:
                prices = get_cached_daily_prices(
                    symbol,
                    effective_start_date,
                    end_date,
                )
            except SectorsError as error:
                st.warning(f"{symbol}: {error}")
                comparison_has_error = True
                break

            if prices.empty or "close" not in prices.columns or prices["close"].iloc[0] == 0:
                st.warning(f"{symbol}: no usable closing prices were returned for these dates.")
                comparison_has_error = True
                break

            normalized_series[symbol] = (
                prices.set_index("date")["close"] / prices["close"].iloc[0] * 100
            )

        if not comparison_has_error:
            comparison_data = pd.DataFrame(normalized_series)
            st.line_chart(
                comparison_data,
                x_label="Date",
                y_label="Indexed closing price (first close = 100)",
            )

with personal_tab:
    starting_amount = st.number_input(
        "Starting amount (Rp)",
        min_value=0,
        value=0,
        step=1_000_000,
    )
    monthly_saving = st.number_input(
        "Monthly saving (Rp)",
        min_value=0,
        value=1_000_000,
        step=100_000,
        key="monthly_saving",
    )
    years = st.number_input(
        "Number of years",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
    )
    yearly_return_percent = st.number_input(
        "Expected yearly return (%)",
        min_value=0.0,
        max_value=30.0,
        value=8.0,
        step=0.5,
    )

    monthly_return = (1 + yearly_return_percent / 100) ** (1 / 12) - 1
    balance = float(starting_amount)
    yearly_totals = [balance]

    for month in range(1, int(years) * 12 + 1):
        balance *= 1 + monthly_return
        balance += monthly_saving

        if month % 12 == 0:
            yearly_totals.append(balance)

    st.subheader("Estimated amount at the end")
    st.metric("Final amount", format_rupiah(balance))

    chart_data = pd.DataFrame(
        {"Total savings": yearly_totals},
        index=pd.Index(range(int(years) + 1), name="Year"),
    )
    st.line_chart(chart_data)
    st.caption(
        "Monthly savings are added at the end of each month. Actual returns can vary."
    )
    st.warning("This calculator is for learning only and is not investment advice.")

with financials_tab:
    if company_error:
        st.warning(str(company_error))
    else:
        try:
            financials = get_cached_company_financials(ticker)
        except SectorsError as error:
            st.warning(str(error))
        else:
            historical_financials = financials.get("historical_financials", [])
            financial_rows = []
            for item in historical_financials:
                year = item.get("year")
                revenue = item.get("revenue")
                earnings = item.get("earnings")
                if any(value is None or value == "" for value in (year, revenue, earnings)):
                    continue
                financial_rows.append(
                    {
                        "Year": year,
                        "Revenue (Rp trillion)": revenue / 1_000_000_000_000,
                        "Earnings (Rp trillion)": earnings / 1_000_000_000_000,
                    }
                )

            if not financial_rows:
                st.write("No complete yearly financial data is available for this ticker.")
            else:
                financial_data = pd.DataFrame(financial_rows).sort_values("Year")
                st.subheader("Revenue and earnings by year (Rp trillion)")
                st.bar_chart(
                    financial_data.set_index("Year")[
                        ["Revenue (Rp trillion)", "Earnings (Rp trillion)"]
                    ]
                )
                st.dataframe(financial_data, hide_index=True)

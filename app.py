"""A simple calculator showing how monthly savings may grow over time."""

import pandas as pd
import streamlit as st

from sectors import SectorsError, get_company_overview


def format_rupiah(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")


st.set_page_config(page_title="Investment Goal Calculator", layout="centered")
st.title("Investment Goal Calculator")
st.write("See how your monthly savings could grow over time.")

ticker = st.text_input("IDX ticker", value="BBCA")
company = None
try:
    company = get_company_overview(ticker)
except SectorsError as error:
    st.warning(str(error))

if company:
    st.header(company.get("company_name", "Company name unavailable"))
    st.write(f"Sector: {company.get('sector', 'Not available')}")
    st.write(f"Sub-sector: {company.get('sub_sector', 'Not available')}")
    last_close_price = company.get("last_close_price")
    if last_close_price is not None:
        st.write(f"Last close price: {format_rupiah(last_close_price)}")

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

if company and last_close_price is not None and last_close_price > 0:
    lot_price = last_close_price * 100
    lots = monthly_saving // lot_price
    leftover = monthly_saving - lots * lot_price
    st.write(f"Your monthly saving buys {lots} lots of this stock")
    st.write(f"Left over: {format_rupiah(leftover)}")

chart_data = pd.DataFrame(
    {"Total savings": yearly_totals},
    index=pd.Index(range(int(years) + 1), name="Year"),
)
st.line_chart(chart_data)
st.caption(
    "Monthly savings are added at the end of each month. Actual returns can vary."
)
st.warning("This calculator is for learning only and is not investment advice.")

if company:
    with st.expander("Raw company data"):
        st.json(company)

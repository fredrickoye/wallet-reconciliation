"""
Wallet Reconciliation & Discrepancy Dashboard
Streamlit interactive dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Wallet Reconciliation Dashboard",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    path = Path(__file__).parent / "data" / "wallet_discrepancies.csv"
    df = pd.read_csv(path, parse_dates=["bank_debit_time", "wallet_credit_time"])
    df["discrepancy_flag"] = df["discrepancy_flag"].astype(bool)
    return df

df = load_data()

# Sidebar
st.sidebar.title("Filters")
providers = st.sidebar.multiselect(
    "Provider",
    options=sorted(df["provider"].unique()),
    default=sorted(df["provider"].unique())
)
filtered = df[df["provider"].isin(providers)]

# Header
st.title("🔄 Wallet Reconciliation & Discrepancy Dashboard")
st.markdown("""
**Problem:** Customers get debited by their bank but the wallet is not credited (or credited late / with the wrong amount).  
Support teams currently investigate these cases one ticket at a time. This dashboard automates the detection and shows which providers and reasons drive the bulk of the problem.

*Synthetic data only. Figures illustrate methodology — they do **not** represent real-world performance of any payment provider. Provider names are fictional (A / B / C).*
""")

# KPIs
total = len(filtered)
disc = filtered["discrepancy_flag"].sum()
disc_rate = disc / total * 100 if total else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Transactions", f"{total:,}")
col2.metric("Discrepancies", f"{disc:,}")
col3.metric("Discrepancy Rate", f"{disc_rate:.1f}%")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Discrepancy Rate by Provider")
    by_prov = filtered.groupby("provider")["discrepancy_flag"].mean().reset_index()
    by_prov["rate_pct"] = by_prov["discrepancy_flag"] * 100
    fig = px.bar(
        by_prov.sort_values("rate_pct", ascending=False),
        x="provider", y="rate_pct",
        text=by_prov.sort_values("rate_pct", ascending=False)["rate_pct"].round(1).astype(str) + "%",
        color="rate_pct", color_continuous_scale="Reds",
        labels={"provider": "Provider", "rate_pct": "Discrepancy Rate (%)"}
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, height=380, margin=dict(t=30))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Discrepancy Reasons")
    reasons = filtered[filtered["discrepancy_flag"]]["discrepancy_reason"].value_counts().reset_index()
    reasons.columns = ["reason", "count"]
    fig = px.bar(
        reasons, y="reason", x="count", orientation="h",
        color="count", color_continuous_scale="Oranges",
        labels={"reason": "Reason", "count": "Count"}
    )
    fig.update_layout(showlegend=False, height=380, margin=dict(t=30), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

# Credit lag
credited = filtered[filtered["wallet_credit_time"].notna()].copy()
if len(credited) > 0:
    credited["lag_seconds"] = (credited["wallet_credit_time"] - credited["bank_debit_time"]).dt.total_seconds()
    st.subheader("Credit Lag Distribution (seconds)")
    fig = px.histogram(
        credited, x="lag_seconds", nbins=40,
        labels={"lag_seconds": "Credit Lag (seconds)"},
        color_discrete_sequence=["#4c72b0"]
    )
    fig.update_layout(height=360, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

# Amount mismatch scatter
mismatch = filtered[filtered["discrepancy_reason"] == "Amount mismatch"]
if len(mismatch) > 0:
    st.subheader("Amount Mismatch Cases (Bank vs Wallet)")
    fig = px.scatter(
        mismatch, x="bank_amount", y="wallet_amount",
        labels={"bank_amount": "Bank Debit (NGN)", "wallet_amount": "Wallet Credit (NGN)"},
        opacity=0.7
    )
    max_val = max(mismatch["bank_amount"].max(), mismatch["wallet_amount"].max())
    fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                  line=dict(color="red", dash="dash"))
    fig.update_layout(height=400, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Business Value")
st.markdown("""
This dashboard essentially automates the manual reconciliation work support agents currently do ticket-by-ticket:
- Instantly surface mismatches
- Show which provider / reason is driving volume
- Give ops a daily discrepancy view instead of reactive digging
""")

st.caption("Built by [Omololu Oyewumi](https://www.linkedin.com/in/omololu-oyewumi-4aa682331) · Synthetic data only")

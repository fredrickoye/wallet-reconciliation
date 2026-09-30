"""
Wallet Reconciliation & Discrepancy Analysis
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "wallet_discrepancies.csv"
OUT = Path(__file__).parent.parent / "outputs"
OUT.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (10, 5)

df = pd.read_csv(DATA, parse_dates=["bank_debit_time", "wallet_credit_time"])
df["discrepancy_flag"] = df["discrepancy_flag"].astype(bool)

print("=" * 60)
print("WALLET RECONCILIATION / DISCREPANCY ANALYSIS")
print("=" * 60)
print(f"\nTotal transactions : {len(df):,}")
print(f"Discrepancies      : {df['discrepancy_flag'].sum():,} ({df['discrepancy_flag'].mean()*100:.1f}%)")

# Reason breakdown
print("\n--- Discrepancy Reasons ---")
reasons = df[df["discrepancy_flag"]]["discrepancy_reason"].value_counts()
print(reasons)

# By provider
print("\n--- Discrepancy Rate by Provider ---")
by_prov = df.groupby("provider").agg(
    total=("transaction_id", "count"),
    discrepancies=("discrepancy_flag", "sum"),
    rate=("discrepancy_flag", "mean")
).round(3)
print(by_prov.sort_values("rate", ascending=False))

# Lag analysis (for credited ones)
credited = df[df["wallet_credit_time"].notna()].copy()
credited["lag_seconds"] = (credited["wallet_credit_time"] - credited["bank_debit_time"]).dt.total_seconds()
print("\n--- Credit Lag (seconds) for successfully credited txns ---")
print(credited["lag_seconds"].describe().round(1))

# ---- Charts ----

# 1. Discrepancy rate by provider
fig, ax = plt.subplots()
order = by_prov.sort_values("rate", ascending=False).index
sns.barplot(data=df, x="provider", y="discrepancy_flag", order=order, ax=ax, errorbar=None)
ax.set_ylabel("Discrepancy Rate")
ax.set_title("Wallet Discrepancy Rate by Payment Provider")
ax.set_ylim(0, 0.25)
plt.tight_layout()
plt.savefig(OUT / "discrepancy_by_provider.png", dpi=150)
plt.close()

# 2. Reason distribution
fig, ax = plt.subplots(figsize=(9, 5))
reasons.plot.barh(ax=ax, color="#c44e52")
ax.set_xlabel("Count")
ax.set_title("Discrepancy Reasons")
plt.tight_layout()
plt.savefig(OUT / "discrepancy_reasons.png", dpi=150)
plt.close()

# 3. Lag distribution (log scale-ish)
fig, ax = plt.subplots()
sns.histplot(credited["lag_seconds"].clip(upper=1800), bins=40, ax=ax, color="#4c72b0")
ax.set_xlabel("Credit Lag (seconds)")
ax.set_title("Distribution of Wallet Credit Lag (capped at 30 min)")
plt.tight_layout()
plt.savefig(OUT / "credit_lag_distribution.png", dpi=150)
plt.close()

# 4. Amount comparison for mismatches
mismatch = df[df["discrepancy_reason"] == "Amount mismatch"].copy()
if len(mismatch) > 0:
    fig, ax = plt.subplots()
    ax.scatter(mismatch["bank_amount"], mismatch["wallet_amount"], alpha=0.6, s=30)
    max_val = max(mismatch["bank_amount"].max(), mismatch["wallet_amount"].max())
    ax.plot([0, max_val], [0, max_val], "r--", label="Perfect match")
    ax.set_xlabel("Bank Debit Amount (NGN)")
    ax.set_ylabel("Wallet Credit Amount (NGN)")
    ax.set_title("Amount Mismatch Cases (Bank vs Wallet)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "amount_mismatch_scatter.png", dpi=150)
    plt.close()

insights = f"""
WALLET RECONCILIATION & DISCREPANCY ANALYSIS – KEY FINDINGS
============================================================

Dataset: {len(df):,} synthetic bank-debit / wallet-credit pairs
Overall discrepancy rate: {df['discrepancy_flag'].mean()*100:.1f}%

1. DISCREPANCY REASONS
{reasons.to_string()}

   Dominant issues:
   - Provider lag / delayed credit
   - Amount mismatches
   - Webhook failures (never credited)

2. PROVIDER COMPARISON
{by_prov.to_string()}

3. CREDIT LAG
   Median lag for credited transactions is low, but a long tail exists.
   Transactions that take > 5 minutes are flagged as discrepancies.

BUSINESS VALUE
--------------
This pipeline essentially automates the manual reconciliation work that
support teams currently do by hand:
- Flag mismatches automatically
- Surface which provider / reason is driving the volume
- Give ops a daily "discrepancy dashboard" instead of ticket-by-ticket digging

All data is synthetic. No real customer or company data was used.
"""
with open(OUT / "insights_summary.txt", "w") as f:
    f.write(insights)

print("\nOutputs saved.")
print(insights)

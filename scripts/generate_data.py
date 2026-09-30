"""
Generate synthetic wallet reconciliation / discrepancy data
modelled on common bank-debit vs wallet-credit mismatches.
"""
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
from pathlib import Path

fake = Faker()
np.random.seed(123)
Faker.seed(123)

n = 6000
providers = ['Provider A', 'Provider B', 'Provider C']

start = datetime.now() - timedelta(days=60)
bank_times = [start + timedelta(seconds=np.random.randint(0, 60*24*3600)) for _ in range(n)]

data = {
    'transaction_id': [fake.uuid4() for _ in range(n)],
    'user_id': [f"USR{fake.random_int(10000,99999)}" for _ in range(n)],
    'bank_debit_time': bank_times,
    'bank_amount': np.round(np.random.exponential(scale=5000, size=n) + 200, 2),
    'provider': np.random.choice(providers, n, p=[0.5, 0.3, 0.2]),
}

df = pd.DataFrame(data)

# Wallet credit time = bank time + lag (seconds)
# Most are near-instant, some have significant lag, a few never credit
lags = np.random.choice(
    [0, 5, 15, 30, 60, 120, 300, 900, 3600, None],
    size=n,
    p=[0.55, 0.15, 0.08, 0.05, 0.04, 0.03, 0.03, 0.02, 0.02, 0.03]
)

df['wallet_credit_time'] = None
df['wallet_amount'] = None
df['discrepancy_flag'] = False
df['discrepancy_reason'] = None

for i, lag in enumerate(lags):
    if lag is None:
        # Never credited
        df.at[i, 'discrepancy_flag'] = True
        df.at[i, 'discrepancy_reason'] = 'Webhook failure / never credited'
        df.at[i, 'wallet_amount'] = 0.0
    else:
        credit_time = df.at[i, 'bank_debit_time'] + timedelta(seconds=int(lag))
        df.at[i, 'wallet_credit_time'] = credit_time
        # Amount mismatch in a small % of cases
        if np.random.rand() < 0.04:
            # Partial or wrong amount
            factor = np.random.choice([0.5, 0.0, 1.5, 0.8])
            df.at[i, 'wallet_amount'] = round(df.at[i, 'bank_amount'] * factor, 2)
            df.at[i, 'discrepancy_flag'] = True
            if factor == 0:
                df.at[i, 'discrepancy_reason'] = 'Zero credit'
            else:
                df.at[i, 'discrepancy_reason'] = 'Amount mismatch'
        else:
            df.at[i, 'wallet_amount'] = df.at[i, 'bank_amount']
            # Late credit still flagged if lag > 5 min
            if lag > 300:
                df.at[i, 'discrepancy_flag'] = True
                df.at[i, 'discrepancy_reason'] = 'Provider lag / delayed credit'

# Also add pure provider-side failures
extra_fail = df.sample(frac=0.02, random_state=42).index
df.loc[extra_fail, 'discrepancy_flag'] = True
df.loc[extra_fail, 'discrepancy_reason'] = 'Provider error'
df.loc[extra_fail, 'wallet_amount'] = 0.0
df.loc[extra_fail, 'wallet_credit_time'] = None

df = df.sort_values('bank_debit_time').reset_index(drop=True)

out = Path(__file__).parent.parent / "data" / "wallet_discrepancies.csv"
df.to_csv(out, index=False)
print(f"Generated {len(df)} rows → {out}")
print(df['discrepancy_flag'].value_counts(normalize=True).round(3))
print(df['discrepancy_reason'].value_counts(dropna=False))

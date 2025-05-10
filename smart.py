# ai01.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# ------------------------------------------------------------
# 💼 Professional Daily Cash Flow Monitor (with Edit/Delete)
# ------------------------------------------------------------

st.set_page_config(page_title="Cash Flow Monitor", layout="wide")
st.title("💼 Daily Cash Flow Monitor")

# --- Account Management ---
ACCOUNTS_PATH = "accounts.csv"
if os.path.exists(ACCOUNTS_PATH):
    accounts = pd.read_csv(ACCOUNTS_PATH)["Account"].dropna().tolist()
else:
    accounts = ["Cash"]

st.sidebar.title("SMART ACCOUNTABILITY")
st.sidebar.header("⚙️ Manage Accounts")
new_acc = st.sidebar.text_input("New Account Name")
if st.sidebar.button("Add Account"):
    name = new_acc.strip()
    if not name:
        st.sidebar.error("Enter a valid account name.")
    elif name in accounts:
        st.sidebar.warning(f"'{name}' already exists.")
    else:
        accounts.append(name)
        pd.DataFrame({"Account": accounts}).to_csv(ACCOUNTS_PATH, index=False)
        st.sidebar.success(f"Added '{name}'")

# --- Load & Prepare Data ---
DATA_PATH = "cash_flow.csv"
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
else:
    df = pd.DataFrame(columns=["S.No", "Date", "Description", "Account", "Amount"])

# enforce types and compute running balance
df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
if not df.empty:
    df = df.sort_values(["Account", "Date"]).reset_index(drop=True)
    df["S.No"]    = df.index + 1
    df["Balance"] = df.groupby("Account")["Amount"].cumsum()
else:
    df["Balance"] = []

# --- Add Transaction ---
st.sidebar.header("➕ Add Transaction")
with st.sidebar.form("add_tx", clear_on_submit=True):
    d       = st.date_input("Date", datetime.today().date())
    desc    = st.text_input("Description")
    acct    = st.selectbox("Account", options=accounts)
    ttype   = st.radio("Type", ["Credit", "Debit"])
    amt     = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
    signed  = amt if ttype == "Credit" else -amt
    do_add  = st.form_submit_button("Add")

if do_add:
    if not desc.strip():
        st.sidebar.error("Description required.")
    else:
        new_row = {
            "S.No":        len(df) + 1,
            "Date":        pd.to_datetime(d),
            "Description": desc,
            "Account":     acct,
            "Amount":      signed
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df = df.sort_values(["Account", "Date"]).reset_index(drop=True)
        df["S.No"]    = df.index + 1
        df["Balance"] = df.groupby("Account")["Amount"].cumsum()
        df.to_csv(DATA_PATH, index=False)
        st.sidebar.success("✅ Transaction added.")

# --- Manage Transactions: Delete & Modify ---
st.sidebar.header("✏️ Manage Transactions")
if not df.empty:
    # Delete
    to_delete = st.sidebar.multiselect("Select S.No to delete", df["S.No"].tolist())
    if st.sidebar.button("Delete Selected"):
        if to_delete:
            df = df[~df["S.No"].isin(to_delete)].copy()
            df = df.sort_values(["Account", "Date"]).reset_index(drop=True)
            df["S.No"]    = df.index + 1
            df["Balance"] = df.groupby("Account")["Amount"].cumsum()
            df.to_csv(DATA_PATH, index=False)
            st.sidebar.success(f"Deleted S.No {to_delete}")
        else:
            st.sidebar.warning("No rows selected for deletion.")

    # Modify
    mod_sno = st.sidebar.selectbox("Select S.No to modify", [None] + df["S.No"].tolist())
    if mod_sno:
        row = df.loc[df["S.No"] == mod_sno].iloc[0]
        with st.sidebar.form(f"mod_tx_{mod_sno}", clear_on_submit=True):
            new_date  = st.date_input("Date", row.Date.date())
            new_desc  = st.text_input("Description", row.Description)
            new_acct  = st.selectbox("Account", options=accounts, index=accounts.index(row.Account))
            new_type  = st.radio("Type", ["Credit", "Debit"], index=0 if row.Amount > 0 else 1)
            new_amt   = st.number_input("Amount", min_value=0.0, value=abs(row.Amount), step=0.01, format="%.2f")
            do_mod    = st.form_submit_button("Update")
        if do_mod:
            signed_amt = new_amt if new_type == "Credit" else -new_amt
            df.loc[df["S.No"] == mod_sno, ["Date", "Description", "Account", "Amount"]] = [
                pd.to_datetime(new_date), new_desc, new_acct, signed_amt
            ]
            df = df.sort_values(["Account", "Date"]).reset_index(drop=True)
            df["S.No"]    = df.index + 1
            df["Balance"] = df.groupby("Account")["Amount"].cumsum()
            df.to_csv(DATA_PATH, index=False)
            st.sidebar.success(f"Updated S.No {mod_sno}")

# --- Pie Chart: Credit / Debit / Balance ---
st.subheader("📊 Pie Chart: Credit / Debit / Balance")
if df.empty:
    st.info("No transactions to display.")
    st.stop()

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

# handle widget returning either a single date or a tuple/list
date_range = st.date_input("Pie-Chart Date Range", value=(min_date, max_date))
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_pie, end_pie = date_range
else:
    # if user picks a single date, treat as both start and end
    start_pie = end_pie = date_range

# ensure pure date objects
start_pie = pd.to_datetime(start_pie).date()
end_pie   = pd.to_datetime(end_pie).date()

sel_accts = st.multiselect("Select Account(s)", options=accounts, default=accounts)

mask = (
    (df["Date"].dt.date >= start_pie) &
    (df["Date"].dt.date <= end_pie) &
    (df["Account"].isin(sel_accts))
)
df_pie = df.loc[mask]

total_credit = df_pie.loc[df_pie["Amount"] > 0, "Amount"].sum()
total_debit  = df_pie.loc[df_pie["Amount"] < 0, "Amount"].abs().sum()
bal_series   = df_pie.groupby("Account")["Balance"].last()
total_balance= bal_series.sum() if not bal_series.empty else 0.0

pie_df = pd.DataFrame({
    "Category": ["Credit", "Debit", "Balance"],
    "Value":    [total_credit, total_debit, total_balance]
})

fig = px.pie(pie_df, names="Category", values="Value",
             hole=0.4,
             title=f"Distribution {start_pie} → {end_pie}")
fig.update_traces(textinfo="label+percent+value")
st.plotly_chart(fig, use_container_width=True)

# --- Display Filtered Transactions ---
st.subheader("📥 Updated Data (All Accounts)")
st.dataframe(df.loc[mask], use_container_width=True)

# --- Download Detailed Transactions Excel ---
st.subheader("📥 Download Detailed Transactions (Excel)")
df_exp = df.loc[mask].copy()
df_exp["Credit"] = df_exp["Amount"].apply(lambda x: x if x > 0 else 0)
df_exp["Debit"]  = df_exp["Amount"].apply(lambda x: -x if x < 0 else 0)
df_exp = df_exp[["S.No", "Date", "Description", "Account", "Amount", "Credit", "Debit", "Balance"]]

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    df_exp.to_excel(writer, index=False, sheet_name="Transactions")
buf.seek(0)
data = buf.getvalue()

st.download_button(
    "⬇️ Download Detailed Transactions",
    data=data,
    file_name="transactions_detailed.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

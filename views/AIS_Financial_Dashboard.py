import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title

# Initialize UI
apply_nav_title()
animated_typing_title("UF AIS Financial Management Application")
st.divider()

# 1. Load raw data
df_committees   = load_committees_df()
df_budgets      = load_committee_budgets_df()
df_transactions = load_transactions_df()
df_terms        = load_terms_df()

# 2. Inspect and clean df_terms columns
# Ensure no surrounding quotes or whitespace in column names
def clean_name(c):
    name = str(c).strip()
    # strip surrounding single/double quotes
    if (name.startswith("'") and name.endswith("'")) or (name.startswith('"') and name.endswith('"')):
        name = name[1:-1]
    return name
# Clean column names in place
df_terms.columns = [clean_name(c) for c in df_terms.columns]

# 3. Ensure required term columns exist
required_cols = ["TermID", "Semester", "Start_Date", "End_Date"]
for col in required_cols:
    if col not in df_terms.columns:
        st.error(f"Missing required column in terms table: {col}")
        st.stop()

# 4. Parse date columns in df_terms and df_transactions
df_terms["Start_Date"] = pd.to_datetime(df_terms["Start_Date"], errors="raise")
df_terms["End_Date"]   = pd.to_datetime(df_terms["End_Date"], errors="raise")
df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"], errors="coerce")

# 5. Build a clean budgets table
df_budgets_clean = (
    df_budgets
    # join term info
    .merge(
        df_terms[["TermID","Semester"]],
        left_on="termid", right_on="TermID", how="left"
    )
    # join committee metadata
    .merge(
        df_committees[["CommitteeID","Committee_Name","Committee_Type"]],
        left_on="committeeid", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee'")
    .loc[:, ["Semester","committeebudgetid","budget_amount","Committee_Name"]]
)

# 6. Helper to get semester from a date
def get_semester(dt: pd.Timestamp) -> str | None:
    if pd.isna(dt): return None
    mask = (df_terms["Start_Date"] <= dt) & (df_terms["End_Date"] >= dt)
    sems = df_terms.loc[mask, "Semester"]
    return sems.iloc[0] if not sems.empty else None

# 7. Prepare committee transactions
df_txn = (
    df_transactions
    .assign(Semester=lambda df: df["transaction_date"].apply(get_semester))
    .merge(
        df_committees[["CommitteeID","Committee_Name","Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee' and amount < 0")
    .assign(amount=lambda df: df["amount"].abs())
    .loc[:, ["Semester","Committee_Name","amount"]]
)

# 8. Display Spending vs. Budget
sem = st.selectbox("Which semester to view?", df_terms["Semester"].dropna().unique())
col1, col2 = st.columns([3,4], border=True)

with col1:
    spend = (
        df_txn.query("Semester == @sem")
        .groupby("Committee_Name", as_index=False)["amount"].sum()
        .rename(columns={"amount": "Spent"})
    )
    summary = (
        df_budgets_clean.query("Semester == @sem")
        .merge(spend, on="Committee_Name", how="left")
        .fillna({"Spent": 0})
        .assign(**{"% Spent": lambda df: df["Spent"] / df["budget_amount"] * 100})
    )
    summary["% Spent"].fillna(0, inplace=True)
    df_disp = (
        summary
        .rename(columns={"budget_amount": "Budget"})
        .loc[:, ["Committee_Name","Budget","Spent","% Spent"]]
        .sort_values("% Spent", ascending=False)
    )
    st.write(f"#### Spending vs Budget ({sem})")
    st.dataframe(df_disp.style.format({"Budget":"{:.2f}","Spent":"{:.2f}","% Spent":"{:.2f}%"}),
                 use_container_width=True, hide_index=True)

with col2:
    chart_df = summary.sort_values("% Spent", ascending=True)
    fig = px.bar(
        chart_df,
        x="% Spent",
        y="Committee_Name",
        orientation="h",
        text=chart_df["% Spent"].round(1).astype(str) + "%",
        labels={"% Spent":"% of Budget Spent","Committee_Name":"Committee"},
        color="% Spent", color_continuous_scale="Blues",
        custom_data=["Committee_Name","% Spent","Spent"]
    )
    fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>% Spent: %{customdata[1]:.1f}%<br>Spent: $%{customdata[2]:,.2f}<extra></extra>")
    max_val = max(100, chart_df["% Spent"].max() * 1.05)
    fig.update_layout(xaxis=dict(range=[0, max_val]), margin=dict(l=150,r=20,t=20,b=20),
                      coloraxis_colorbar=dict(title="% Spent"))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 9. Previous semester helper
def previous_semester(current: str) -> str | None:
    terms_sorted = (
        df_terms[["Semester","Start_Date"]]
        .drop_duplicates()
        .sort_values("Start_Date")
        ["Semester"].tolist()
    )
    if current in terms_sorted:
        idx = terms_sorted.index(current)
        return terms_sorted[idx-1] if idx>0 else None
    return None

# 10. Income Overview
income_df = df_transactions[df_transactions["amount"] > 0].copy()
income_df["Income_Type"] = "Other"
inc_map = {
    "Dues": ["Dues"],
    "Merchandise": ["Merch","Head Shot"],
    "Sponsorship/Donation": ["Sponsorship / Donation"],
    "Events": ["Social Events","Formal","Professional Events","Fundraiser","ISOM Passport"],
    "Refunds": ["Reimbursement","Refunded"],
    "Transfers": ["Transfers"]
}
for cat, kws in inc_map.items():
    for kw in kws:
        income_df.loc[income_df["purpose"].str.contains(kw, case=False, na=False), "Income_Type"] = cat
income_df["Semester"] = income_df["transaction_date"].apply(get_semester)
sem_inc = income_df[income_df["Semester"] == sem]

inc_col1, inc_col2 = st.columns([1,1], border=True)

with inc_col1:
    total_inc = sem_inc["amount"].sum()
    prev_sem = previous_semester(sem)
    prev_amt = income_df[income_df["Semester"] == prev_sem]["amount"].sum() if prev_sem else 0
    delta = total_inc - prev_amt
    st.write("### Income Overview")
    st.metric(label=f"Total Income ({sem})", value=f"${total_inc:,.2f}", border=True)
    st.metric(label=f"Change vs {prev_sem}", value="", delta=f"${delta:+,.2f}", border=True)
    inc_by_type = sem_inc.groupby("Income_Type", as_index=False)["amount"].sum()
    fig_inc = px.pie(
        inc_by_type, values="amount", names="Income_Type", hole=0.4,
        title=f"{sem} Income Distribution By Type", color_discrete_sequence=px.colors.qualitative.G10
    )
    fig_inc.update_traces(textinfo="percent+label",
                          hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>")
    fig_inc.update_layout(margin=dict(t=35,b=20), title_font_size=20)
    st.plotly_chart(fig_inc, use_container_width=True)

with inc_col2:
    st.write("### Non-Committee Expenses")
    tmp = df_transactions.copy()
    tmp["Semester"] = tmp["transaction_date"].apply(get_semester)
    noncom = tmp[(tmp["amount"] < 0) & (tmp["Semester"] == sem)].copy()
    noncom = noncom.merge(df_committees[["CommitteeID","Committee_Type"]],
                          left_on="budget_category", right_on="CommitteeID", how="left")
    noncom = noncom[(noncom["Committee_Type"] != "committee") | noncom["Committee_Type"].isna()]
    noncom["amount"] = noncom["amount"].abs()
    if noncom.empty:
        st.info(f"No non-committee expenses found for {sem}")
    else:
        exp_map = {
            "Merchandise": ["Merch","Head Shot"],
            "Events": ["Social Events","GBM Catering","Formal","Professional Events","Fundraiser","Road Trip","ISOM Passport"],
            "Food & Drink": ["Food & Drink"],
            "Travel": ["Travel"],
            "Reimbursements": ["Reimbursement","Refunded"],
            "Transfers": ["Transfers"],
            "Tax & Fees": ["Tax"],
            "Miscellaneous": ["Misc."]
        }
        noncom["Expense_Category"] = "Other"
        for cat, kws in exp_map.items():
            for kw in kws:
                noncom.loc[noncom["purpose"].str.contains(kw, case=False, na=False), "Expense_Category"] = cat
        total_non = noncom["amount"].sum()
        st.metric(label=f"Total Non-Committee Expenses ({sem})", value=f"${total_non:,.2f}", border=True)
        by_cat = noncom.groupby("Expense_Category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        fig_non = px.pie(
            by_cat, values="amount", names="Expense_Category", hole=0.4,
            title=f"{sem} Non-Committee Expense Distribution", color_discrete_sequence=px.colors.qualitative.G10
        )
        fig_non.update_traces(textinfo="percent+label",
                              hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>")
        fig_non.update_layout(margin=dict(t=35,b=20), title_font_size=20)
        st.plotly_chart(fig_non, use_container_width=True)

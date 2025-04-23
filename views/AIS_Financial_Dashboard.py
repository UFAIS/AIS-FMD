import streamlit as st
import pandas as pd
import os
import plotly.express as px
from utils import load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title

apply_nav_title()
animated_typing_title("UF AIS Financial Management Application")
st.divider()

# 1. Load raw data
df_committees   = load_committees_df()
df_budgets      = load_committee_budgets_df()
df_transactions = load_transactions_df()
df_terms        = load_terms_df()

# 2. Normalize and parse all date columns
df_terms.columns = (
    df_terms.columns
       .str.strip()
       .str.replace(" ", "_")
       .str.lower()
)
# Now columns are: ['termid','semester','start_date','end_date',...]
df_terms["start_date"] = pd.to_datetime(df_terms["start_date"])
df_terms["end_date"]   = pd.to_datetime(df_terms["end_date"])
df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"])

# 3. Build a “clean” budgets table
df_budgets_clean = (
    df_budgets
    # Attach semester name
    .merge(df_terms[["termid","semester"]], left_on="termid", right_on="termid", how="left")
    # Attach committee metadata
    .merge(
        df_committees[["CommitteeID","Committee_Name","Committee_Type"]],
        left_on="committeeid", right_on="CommitteeID", how="left"
    )
    # Keep only real committees
    .query("Committee_Type == 'committee'")
    # Keep only the columns we need
    .loc[:, ["semester","committeebudgetid","budget_amount","Committee_Name"]]
)

# 4. Helper to assign a semester to each date
def get_semester(dt: pd.Timestamp):
    hits = df_terms[
        (df_terms["start_date"] <= dt) &
        (df_terms["end_date"]   >= dt)
    ]["semester"]
    return hits.iloc[0] if not hits.empty else None

# 5. Prepare transactions: semester‐tag, join committee info, filter & abs
df_txn = (
    df_transactions
    .assign(semester=df_transactions["transaction_date"].apply(get_semester))
    .merge(
        df_committees[["CommitteeID","Committee_Name","Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee' and amount < 0")
    .assign(amount=lambda d: d["amount"].abs())
    .loc[:, ["semester","Committee_Name","amount"]]
)

# 6. Two‐column layout
sem = st.selectbox("Which semester would you like to view?", df_terms["semester"].unique())
col1, col2 = st.columns([3, 4], border=True)

with col1:
    # 1) Aggregate spend for that semester
    spend_sem = (
        df_txn
        .query("semester == @sem")
        .groupby("Committee_Name", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount":"Spent"})
    )

    # 2) Merge budgets + spend & compute %
    summary = (
        df_budgets_clean.query("semester == @sem")
        .merge(spend_sem, on="Committee_Name", how="left")
        .fillna({"Spent": 0})
        .assign(**{"% Spent": lambda d: d["Spent"] / d["budget_amount"] * 100})
    )
    summary["% Spent"].fillna(0, inplace=True)

    # 3) Select & rename columns
    display_df = (
        summary[["Committee_Name","budget_amount","Spent","% Spent"]]
        .rename(columns={"budget_amount":"Budget"})
        .reset_index(drop=True)
        .sort_values("% Spent", ascending=False)
    )

    # 4) Build a Styler that forces two decimals
    styled = (
        display_df
        .style
        .format({
            "Budget":    "{:.2f}",
            "Spent":     "{:.2f}",
            "% Spent":   "{:.2f}%"
        })
    )

    # 5) Display it
    st.write(f"#### Spending vs. Budget ({sem})")
    st.dataframe(styled, use_container_width=True, hide_index=True)

with col2:
    st.write(f"#### % of Budget Spent by Committee ({sem})")
    # Sort the dataframe by "% Spent" in ascending order for horizontal bar
    summary = summary.sort_values(by="% Spent", ascending=True)

    fig = px.bar(
        summary,
        x="% Spent",
        y="Committee_Name",
        orientation="h",
        text=summary["% Spent"].round(1).astype(str) + "%",
        labels={"% Spent":"% of Budget Spent", "Committee_Name":"Committee"},
        color="% Spent",
        color_continuous_scale="Blues",
        custom_data=["Committee_Name", "% Spent", "Spent"]
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Percentage Spent: %{customdata[1]:.1f}%<br>Amount Spent: $%{customdata[2]:,.2f}<extra></extra>"
    )
    max_pct = max(100, summary["% Spent"].max() * 1.05)
    fig.update_layout(
        xaxis=dict(range=[0, max_pct]),
        margin=dict(l=150, r=20, t=20, b=20),
        coloraxis_colorbar=dict(title="% Spent")
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 7. Previous semester helper
def get_previous_semester_name(current_semester: str) -> str | None:
    ordered = (
        df_terms
        .drop_duplicates(subset=["semester","start_date"])
        .sort_values("start_date")["semester"]
        .tolist()
    )
    try:
        idx = ordered.index(current_semester)
        if idx > 0:
            return ordered[idx - 1]
    except ValueError:
        pass
    return None

# 8. Income calculations
income_df = df_transactions.copy()
income_df = income_df[income_df["amount"] > 0]
income_df["Income_Type"] = "Other"
for category, purposes in {
    "Dues": ["Dues"],
    "Merchandise": ["Merch", "Head Shot"],
    "Sponsorship/Donation": ["Sponsorship / Donation"],
    "Events": ["Social Events", "Formal", "Professional Events", "Fundraiser", "ISOM Passport"],
    "Refunds": ["Reimbursement", "Refunded"],
    "Transfers": ["Transfers"]
}.items():
    for purpose in purposes:
        income_df.loc[
            income_df["purpose"].str.contains(purpose, case=False, na=False),
            "Income_Type"
        ] = category
income_df["semester"] = income_df["transaction_date"].apply(get_semester)
semester_income = income_df[income_df["semester"] == sem]

inc_col1, inc_col2 = st.columns([1, 1], border=True)
with inc_col1:
    current_total = semester_income["amount"].sum()
    prev_sem = get_previous_semester_name(sem)
    prev_total = income_df[income_df["semester"] == prev_sem]["amount"].sum()
    diff = current_total - prev_total

    st.write("### Income Overview")
    st.metric(label=f"Total Income ({sem})", value=f"${current_total:,.2f}" , border=True)
    st.metric(label=f"Change vs {prev_sem}", value="", delta=f"${diff:+,.2f}" , border=True)

    income_by_type = semester_income.groupby("Income_Type", as_index=False)["amount"].sum()
    fig_pie = px.pie(
        income_by_type,
        values="amount",
        names="Income_Type",
        hole=0.4,
        title=f"{sem} Income Distribution By Type",
        color_discrete_sequence=px.colors.qualitative.G10
    )
    fig_pie.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>"
    )
    fig_pie.update_layout(margin=dict(t=35, b=20), title_font_size=20)
    st.plotly_chart(fig_pie, use_container_width=True)

with inc_col2:
    st.write("### Non-Committee Expenses")
    temp = df_transactions.copy()
    temp["semester"] = temp["transaction_date"].apply(get_semester)
    noncommittee = temp[(temp["amount"] < 0) & (temp["semester"] == sem)].copy()
    noncommittee = noncommittee.merge(
        df_committees[["CommitteeID","Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    noncommittee = noncommittee[(noncommittee["Committee_Type"] != "committee") | noncommittee["Committee_Type"].isna()]
    noncommittee["amount"] = noncommittee["amount"].abs()
    if noncommittee.empty:
        st.info(f"No non-committee expenses found for {sem}")
    else:
        mapping = {
            "Merchandise": ["Merch", "Head Shot"],
            "Events": ["Social Events", "GBM Catering", "Formal", "Professional Events", "Fundraiser", "Road Trip", "ISOM Passport"],
            "Food & Drink": ["Food & Drink"],
            "Travel": ["Travel"],
            "Reimbursements": ["Reimbursement", "Refunded"],
            "Transfers": ["Transfers"],
            "Tax & Fees": ["Tax"],
            "Miscellaneous": ["Misc."]
        }
        noncommittee["Expense_Category"] = "Other"
        for category, keywords in mapping.items():
            for kw in keywords:
                noncommittee.loc[
                    noncommittee["purpose"].str.contains(kw, case=False, na=False),
                    "Expense_Category"
                ] = category
        non_total = noncommittee["amount"].sum()
        st.metric(label=f"Total Non-Committee Expenses ({sem})", value=f"${non_total:,.2f}", border=True)
        expense_by_cat = noncommittee.groupby("Expense_Category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        fig_ec = px.pie(
            expense_by_cat,
            values="amount",
            names="Expense_Category",
            hole=0.4,
            title=f"{sem} Non-Committee Expense Distribution",
            color_discrete_sequence=px.colors.qualitative.G10
        )
        fig_ec.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>"
        )
        fig_ec.update_layout(margin=dict(t=35, b=20), title_font_size=20)
        st.plotly_chart(fig_ec, use_container_width=True)

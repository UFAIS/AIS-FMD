import streamlit as st
import pandas as pd
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

# 2. Parse all date columns in df_terms to datetime
# Using the exact column names as provided: 'Start_Date', 'End_Date'
df_terms["Start_Date"] = pd.to_datetime(df_terms["Start_Date"])
df_terms["End_Date"]   = pd.to_datetime(df_terms["End_Date"])
# Parse transaction dates as well
df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"])

# 3. Build a “clean” budgets table
df_budgets_clean = (
    df_budgets
    # Attach Semester name from df_terms
    .merge(
        df_terms[["TermID", "Semester"]],
        left_on="termid", right_on="TermID", how="left"
    )
    # Attach committee metadata
    .merge(
        df_committees[["CommitteeID", "Committee_Name", "Committee_Type"]],
        left_on="committeeid", right_on="CommitteeID", how="left"
    )
    # Filter only real committees
    .query("Committee_Type == 'committee'")
    # Keep only needed columns
    .loc[:, ["Semester", "committeebudgetid", "budget_amount", "Committee_Name"]]
)

# 4. Helper to assign a semester to each date
def get_semester(dt: pd.Timestamp) -> str | None:
    if pd.isna(dt):
        return None
    mask = (df_terms["Start_Date"] <= dt) & (df_terms["End_Date"] >= dt)
    result = df_terms.loc[mask, "Semester"]
    return result.iloc[0] if not result.empty else None

# 5. Prepare transactions: tag semester, join committee info, filter & absolute
# Create a working DataFrame for committee spending
df_txn = (
    df_transactions
    .assign(Semester=df_transactions["transaction_date"].apply(get_semester))
    .merge(
        df_committees[["CommitteeID", "Committee_Name", "Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee' and amount < 0")
    .assign(amount=lambda df: df["amount"].abs())
    .loc[:, ["Semester", "Committee_Name", "amount"]]
)

# 6. Layout: Spending vs. Budget by Committee
sem = st.selectbox(
    "Which semester would you like to view?", df_terms["Semester"].unique()
)
col1, col2 = st.columns([3, 4], border=True)

with col1:
    # Aggregate spending for selected semester
    spend_sem = (
        df_txn
        .query("Semester == @sem")
        .groupby("Committee_Name", as_index=False)["amount"].sum()
        .rename(columns={"amount": "Spent"})
    )

    # Merge budgets with spend and compute percentage
    summary = (
        df_budgets_clean.query("Semester == @sem")
        .merge(spend_sem, on="Committee_Name", how="left")
        .fillna({"Spent": 0})
        .assign(**{"% Spent": lambda df: df["Spent"] / df["budget_amount"] * 100})
    )
    summary["% Spent"].fillna(0, inplace=True)

    # Format table
    display_df = (
        summary[["Committee_Name", "budget_amount", "Spent", "% Spent"]]
        .rename(columns={"budget_amount": "Budget"})
        .sort_values(by="% Spent", ascending=False)
        .reset_index(drop=True)
    )
    styler = display_df.style.format({
        "Budget": "{:.2f}",
        "Spent": "{:.2f}",
        "% Spent": "{:.2f}%"
    })

    st.write(f"#### Spending vs. Budget ({sem})")
    st.dataframe(styler, use_container_width=True, hide_index=True)

with col2:
    st.write(f"#### % of Budget Spent by Committee ({sem})")
    chart_df = summary.sort_values(by="% Spent", ascending=True)
    fig = px.bar(
        chart_df,
        x="% Spent",
        y="Committee_Name",
        orientation="h",
        text=chart_df["% Spent"].round(1).astype(str) + "%",
        labels={"% Spent": "% of Budget Spent", "Committee_Name": "Committee"},
        color="% Spent",
        color_continuous_scale="Blues",
        custom_data=["Committee_Name", "% Spent", "Spent"]
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Percentage Spent: %{customdata[1]:.1f}%<br>"
            "Amount Spent: $%{customdata[2]:,.2f}<extra></extra>"
        )
    )
    max_val = max(100, chart_df["% Spent"].max() * 1.05)
    fig.update_layout(
        xaxis=dict(range=[0, max_val]),
        margin=dict(l=150, r=20, t=20, b=20),
        coloraxis_colorbar=dict(title="% Spent")
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 7. Helper: previous semester based on chronological order
def get_previous_semester(current: str) -> str | None:
    ordered = (
        df_terms.drop_duplicates(subset=["Semester", "Start_Date"])
                .sort_values("Start_Date")["Semester"].tolist()
    )
    if current in ordered:
        idx = ordered.index(current)
        return ordered[idx - 1] if idx > 0 else None
    return None

# 8. Income Overview and Non-Committee Expenses
# Build income DataFrame
income_df = df_transactions[df_transactions["amount"] > 0].copy()
income_df["Income_Type"] = "Other"
# Categorize income
income_categories = {
    "Dues": ["Dues"],
    "Merchandise": ["Merch", "Head Shot"],
    "Sponsorship/Donation": ["Sponsorship / Donation"],
    "Events": ["Social Events", "Formal", "Professional Events", "Fundraiser", "ISOM Passport"],
    "Refunds": ["Reimbursement", "Refunded"],
    "Transfers": ["Transfers"]
}
for cat, keys in income_categories.items():
    for key in keys:
        income_df.loc[
            income_df["purpose"].str.contains(key, case=False, na=False),
            "Income_Type"
        ] = cat
# Assign semester to incomes
income_df["Semester"] = income_df["transaction_date"].apply(get_semester)
sem_income = income_df[income_df["Semester"] == sem]

inc1, inc2 = st.columns([1, 1], border=True)
with inc1:
    total_inc = sem_income["amount"].sum()
    prev_sem = get_previous_semester(sem)
    prev_inc = income_df[income_df["Semester"] == prev_sem]["amount"].sum() if prev_sem else 0
    delta = total_inc - prev_inc
    st.write("### Income Overview")
    st.metric(label=f"Total Income ({sem})", value=f"${total_inc:,.2f}", border=True)
    st.metric(label=f"Change vs {prev_sem}", value="", delta=f"${delta:+,.2f}", border=True)
    inc_by_type = sem_income.groupby("Income_Type", as_index=False)["amount"].sum()
    fig_inc = px.pie(
        inc_by_type,
        values="amount",
        names="Income_Type",
        hole=0.4,
        title=f"{sem} Income Distribution By Type",
        color_discrete_sequence=px.colors.qualitative.G10
    )
    fig_inc.update_traces(textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>")
    fig_inc.update_layout(margin=dict(t=35, b=20), title_font_size=20)
    st.plotly_chart(fig_inc, use_container_width=True)

with inc2:
    st.write("### Non-Committee Expenses")
    temp = df_transactions.copy()
    temp["Semester"] = temp["transaction_date"].apply(get_semester)
    noncom = temp[(temp["amount"] < 0) & (temp["Semester"] == sem)].copy()
    noncom = noncom.merge(
        df_committees[["CommitteeID", "Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    noncom = noncom[(noncom["Committee_Type"] != "committee") | noncom["Committee_Type"].isna()]
    noncom["amount"] = noncom["amount"].abs()
    if noncom.empty:
        st.info(f"No non-committee expenses found for {sem}")
    else:
        expense_map = {
            "Merchandise": ["Merch", "Head Shot"],
            "Events": ["Social Events", "GBM Catering", "Formal", "Professional Events", "Fundraiser", "Road Trip", "ISOM Passport"],
            "Food & Drink": ["Food & Drink"],
            "Travel": ["Travel"],
            "Reimbursements": ["Reimbursement", "Refunded"],
            "Transfers": ["Transfers"],
            "Tax & Fees": ["Tax"],
            "Miscellaneous": ["Misc."]
        }
        noncom["Expense_Category"] = "Other"
        for cat, kws in expense_map.items():
            for kw in kws:
                noncom.loc[noncom["purpose"].str.contains(kw, case=False, na=False), "Expense_Category"] = cat
        total_non = noncom["amount"].sum()
        st.metric(label=f"Total Non-Committee Expenses ({sem})", value=f"${total_non:,.2f}", border=True)
        non_by_cat = noncom.groupby("Expense_Category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        fig_non = px.pie(
            non_by_cat,
            values="amount",
            names="Expense_Category",
            hole=0.4,
            title=f"{sem} Non-Committee Expense Distribution",  
            color_discrete_sequence=px.colors.qualitative.G10
        )
        fig_non.update_traces(textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>")
        fig_non.update_layout(margin=dict(t=35, b=20), title_font_size=20)
        st.plotly_chart(fig_non, use_container_width=True)

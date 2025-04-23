import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title

apply_nav_title()
animated_typing_title("UF AIS Financial Management Application")
st.divider()

# 1. Load raw data
df_committees = load_committees_df()
df_budgets = load_committee_budgets_df()
df_transactions = load_transactions_df()
df_terms = load_terms_df()

# 2. Normalize df_terms column names and ensure required fields
# Build a mapping of original col -> normalized name
rename_map = {
    col: str(col).strip().replace(" ", "_").lower()
    for col in df_terms.columns
}
# Apply renaming in place
df_terms.rename(columns=rename_map, inplace=True)

# Verify expected columns exist
expected = {"termid", "semester", "start_date", "end_date"}
missing = expected - set(df_terms.columns)
if missing:
    raise KeyError(f"Missing expected term columns after rename: {missing}")

# 3. Parse date columns
df_terms["start_date"] = pd.to_datetime(df_terms["start_date"], errors="raise")
df_terms["end_date"] = pd.to_datetime(df_terms["end_date"], errors="raise")
df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"], errors="coerce")

# 4. Build a “clean” budgets table
df_budgets_clean = (
    df_budgets
    .rename(columns={"termid": "termid"})  # ensure matching key
    .merge(df_terms[["termid", "semester"]], on="termid", how="left")
    .merge(
        df_committees[["CommitteeID", "Committee_Name", "Committee_Type"]],
        left_on="committeeid", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee'")
    .loc[:, ["semester", "committeebudgetid", "budget_amount", "Committee_Name"]]
)

# 5. Helper to assign a semester to each date
def get_semester(dt: pd.Timestamp) -> str | None:
    if pd.isna(dt):
        return None
    mask = (df_terms["start_date"] <= dt) & (df_terms["end_date"] >= dt)
    hits = df_terms.loc[mask, "semester"]
    return hits.iloc[0] if not hits.empty else None

# 6. Prepare transactions: semester‐tag, join committee info, filter & abs
df_txn = (
    df_transactions
    .assign(semester=df_transactions["transaction_date"].apply(get_semester))
    .merge(
        df_committees[["CommitteeID", "Committee_Name", "Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee' and amount < 0")
    .assign(amount=lambda d: d["amount"].abs())
    .loc[:, ["semester", "Committee_Name", "amount"]]
)

# 7. Two-column layout for spending vs. budget
sem = st.selectbox("Which semester would you like to view?", sorted(df_terms["semester"].dropna().unique()))
col1, col2 = st.columns([3, 4], border=True)

with col1:
    spend_sem = (
        df_txn
        .query("semester == @sem")
        .groupby("Committee_Name", as_index=False)["amount"].sum()
        .rename(columns={"amount": "Spent"})
    )
    summary = (
        df_budgets_clean.query("semester == @sem")
        .merge(spend_sem, on="Committee_Name", how="left")
        .fillna({"Spent": 0})
        .assign(**{"% Spent": lambda d: d["Spent"] / d["budget_amount"] * 100})
    )
    summary["% Spent"].fillna(0, inplace=True)
    display_df = (
        summary[["Committee_Name", "budget_amount", "Spent", "% Spent"]]
        .rename(columns={"budget_amount": "Budget"})
        .sort_values("% Spent", ascending=False)
    )
    styled = display_df.style.format({
        "Budget": "{:.2f}",
        "Spent": "{:.2f}",
        "% Spent": "{:.2f}%"
    })
    st.write(f"#### Spending vs. Budget ({sem})")
    st.dataframe(styled, use_container_width=True, hide_index=True)

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
        hovertemplate="<b>%{customdata[0]}</b><br>Percentage Spent: %{customdata[1]:.1f}%<br>Amount Spent: $%{customdata[2]:,.2f}<extra></extra>"
    )
    max_pct = max(100, chart_df["% Spent"].max() * 1.05)
    fig.update_layout(xaxis=dict(range=[0, max_pct]), margin=dict(l=150, r=20, t=20, b=20), coloraxis_colorbar=dict(title="% Spent"))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 8. Previous semester helper
def get_previous_semester_name(current: str) -> str | None:
    ordered = (
        df_terms
        .drop_duplicates(subset=["semester", "start_date"])
        .sort_values("start_date")["semester"].tolist()
    )
    try:
        idx = ordered.index(current)
        return ordered[idx - 1] if idx > 0 else None
    except ValueError:
        return None

# 9. Income overview and non-committee expenses
income_df = df_transactions.copy()
income_df = income_df[income_df["amount"] > 0]
income_df["income_type"] = "Other"
category_map = {
    "Dues": ["Dues"],
    "Merchandise": ["Merch", "Head Shot"],
    "Sponsorship/Donation": ["Sponsorship / Donation"],
    "Events": ["Social Events", "Formal", "Professional Events", "Fundraiser", "ISOM Passport"],
    "Refunds": ["Reimbursement", "Refunded"],
    "Transfers": ["Transfers"]
}
for cat, keywords in category_map.items():
    for kw in keywords:
        income_df.loc[income_df["purpose"].str.contains(kw, case=False, na=False), "income_type"] = cat
income_df["semester"] = income_df["transaction_date"].apply(get_semester)
sem_income = income_df[income_df["semester"] == sem]

inc_col1, inc_col2 = st.columns([1, 1], border=True)
with inc_col1:
    total = sem_income["amount"].sum()
    prev = get_previous_semester_name(sem)
    prev_total = income_df[income_df["semester"] == prev]["amount"].sum()
    delta = total - prev_total
    st.write("### Income Overview")
    st.metric(label=f"Total Income ({sem})", value=f"${total:,.2f}", border=True)
    st.metric(label=f"Change vs {prev}", value="", delta=f"${delta:+,.2f}", border=True)
    by_type = sem_income.groupby("income_type", as_index=False)["amount"].sum()
    pie = px.pie(by_type, values="amount", names="income_type", hole=0.4, title=f"{sem} Income Distribution By Type", color_discrete_sequence=px.colors.qualitative.G10)
    pie.update_traces(textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>")
    pie.update_layout(margin=dict(t=35, b=20), title_font_size=20)
    st.plotly_chart(pie, use_container_width=True)

with inc_col2:
    st.write("### Non-Committee Expenses")
    temp = df_transactions.copy()
    temp["semester"] = temp["transaction_date"].apply(get_semester)
    noncom = temp[(temp["amount"] < 0) & (temp["semester"] == sem)].copy()
    noncom = noncom.merge(
        df_committees[["CommitteeID", "Committee_Type"]], left_on="budget_category", right_on="CommitteeID", how="left"
    )
    noncom = noncom[(noncom["Committee_Type"] != "committee") | noncom["Committee_Type"].isna()]
    noncom["amount"] = noncom["amount"].abs()
    if noncom.empty:
        st.info(f"No non-committee expenses found for {sem}")
    else:
        expense_map = {"Merchandise": ["Merch", "Head Shot"], "Events": ["Social Events", "GBM Catering", "Formal", "Professional Events", "Fundraiser", "Road Trip", "ISOM Passport"], "Food & Drink": ["Food & Drink"], "Travel": ["Travel"], "Reimbursements": ["Reimbursement", "Refunded"], "Transfers": ["Transfers"], "Tax & Fees": ["Tax"], "Miscellaneous": ["Misc."]}
        noncom["expense_category"] = "Other"
        for cat, kws in expense_map.items():
            for kw in kws:
                noncom.loc[noncom["purpose"].str.contains(kw, case=False, na=False), "expense_category"] = cat
        total_non = noncom["amount"].sum()
        st.metric(label=f"Total Non-Committee Expenses ({sem})", value=f"${total_non:,.2f}", border=True)
        by_cat = noncom.groupby("expense_category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        pie2 = px.pie(by_cat, values="amount", names="expense_category", hole=0.4, title=f"{sem} Non-Committee Expense Distribution", color_discrete_sequence=px.colors.qualitative.G10)
        pie2.update_traces(textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>")
        pie2.update_layout(margin=dict(t=35, b=20), title_font_size=20)
        st.plotly_chart(pie2, use_container_width=True)

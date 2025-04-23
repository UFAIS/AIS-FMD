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

# 2. Parse all date columns to datetime

df_terms["Start_Date"] = pd.to_datetime(df_terms["Start_Date"])
df_terms["End_Date"]   = pd.to_datetime(df_terms["End_Date"])
df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"])

# 3. Build a “clean” budgets table
df_budgets_clean = (
    df_budgets
    # Attach semester name
    .merge(df_terms[["TermID","Semester"]], left_on="termid", right_on="TermID", how="left")
    # Attach committee metadata
    .merge(
        df_committees[["CommitteeID","Committee_Name","Committee_Type"]],
        left_on="committeeid", right_on="CommitteeID", how="left"
    )
    # Keep only real committees
    .query("Committee_Type == 'committee'")
    # Keep only the columns we need
    .loc[:, ["Semester","committeebudgetid","budget_amount","Committee_Name"]]
)

# 4. Helper to assign a semester to each date
def get_semester(dt: pd.Timestamp):
    hits = df_terms[
        (df_terms["Start_Date"] <= dt) &
        (df_terms["End_Date"]   >= dt)
    ]["Semester"]
    return hits.iloc[0] if not hits.empty else None

# 5. Prepare transactions: semester‐tag, join committee info, filter & abs
df_txn = (
    df_transactions
    .assign(Semester=df_transactions["transaction_date"].apply(get_semester))
    .merge(
        df_committees[["CommitteeID","Committee_Name","Committee_Type"]],
        left_on="budget_category", right_on="CommitteeID", how="left"
    )
    .query("Committee_Type == 'committee' and amount < 0")
    .assign(amount=lambda d: d["amount"].abs())
    .loc[:, ["Semester","Committee_Name","amount"]]
)

# 6. Two‐column layout
sem = st.selectbox("Which semester would you like to view?", df_terms["Semester"].unique())

col1, col2 = st.columns([3, 4], border = True)

with col1:
    # 1) Aggregate spend for that semester
    spend_sem = (
        df_txn
        .query("Semester == @sem")
        .groupby("Committee_Name", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount":"Spent"})
    )

    # 2) Merge budgets + spend & compute %
    summary = (
        df_budgets_clean.query("Semester == @sem")
        .merge(spend_sem, on="Committee_Name", how="left")
        .fillna({"Spent": 0})
        .assign(**{"% Spent": lambda d: d["Spent"] / d["budget_amount"] * 100})
    )
    summary["% Spent"].fillna(0, inplace=True)

    # 3) Select & rename columns
    display_df = (
        summary[["Committee_Name","budget_amount","Spent","% Spent"]]
        .rename(columns={"budget_amount":"Budget"})
        .reset_index(drop=True).sort_values("% Spent", ascending=False)
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
    # Sort the dataframe by "% Spent" in descending order
    summary = summary.sort_values(by="% Spent", ascending=True)

    # Create a color scale based on the percentage spent
    fig = px.bar(
        summary,
        x="% Spent",
        y="Committee_Name",
        orientation="h",
        text=summary["% Spent"].round(1).astype(str) + "%",
        labels={"% Spent":"% of Budget Spent", "Committee_Name":"Committee"},
        color="% Spent",  # Use the "% Spent" column for coloring
        color_continuous_scale="Blues",
        custom_data=["Committee_Name", "% Spent", "Spent"]  )

    # Update hover template to show only the data we want
    fig.update_traces(
    hovertemplate="<b>%{customdata[0]}</b><br>" +
                  "Percentage Spent: %{customdata[1]:.1f}%<br>" +
                  "Amount Spent: $%{customdata[2]:,.2f}<br>" +
                  "<extra></extra>")
    # Ensure bars over 100% show
    max_pct = max(100, summary["% Spent"].max() * 1.05)
    fig.update_layout(
        xaxis=dict(range=[0, max_pct]), 
        margin=dict(l=150, r=20, t=20, b=20),
        coloraxis_colorbar=dict(title="% Spent")
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- assume df_transactions, df_terms, get_semester() are already defined above ---

def get_previous_semester_name(current_semester: str) -> str | None:
    """
    Returns the semester immediately before `current_semester`, 
    based on chronological ordering in df_terms.
    """
    # build a list of semesters sorted by start date
    ordered = (
        df_terms
        .drop_duplicates(subset=["Semester", "Start_Date"])
        .sort_values("Start_Date")
        ["Semester"]
        .tolist()
    )
    try:
        idx = ordered.index(current_semester)
        if idx > 0:
            return ordered[idx - 1]
    except ValueError:
        pass
    return None

# Create a new column for income type by filtering the purpose column
income_df = df_transactions.copy()

# Filter for positive amounts (income only)
income_df = income_df[income_df["amount"] > 0]

# Categorize income types based on purpose
income_df["Income_Type"] = "Other"  # Default value

# Map purposes to income types
income_categories = {
    "Dues": ["Dues"],
    "Merchandise": ["Merch", "Head Shot"],
    "Sponsorship/Donation": ["Sponsorship / Donation"],
    "Events": ["Social Events", "Formal", "Professional Events", "Fundraiser", "ISOM Passport"],
    "Refunds": ["Reimbursement", "Refunded"],
    "Transfers": ["Transfers"]
}

# Apply categorization
for category, purposes in income_categories.items():
    for purpose in purposes:
        income_df.loc[income_df["purpose"].str.contains(purpose, case=False, na=False), "Income_Type"] = category

# Assign semester using get_semester function
income_df["Semester"] = income_df["transaction_date"].apply(get_semester)

# Filter by selected semester
semester_income = income_df[income_df["Semester"] == sem]

# Two-column layout for income charts
inc_col1, inc_col2 = st.columns([1,1],border = True)

with inc_col1:
    # 1. Totals
    current_total = semester_income["amount"].sum()
    prev_semester = get_previous_semester_name(sem)
    prev_total    = income_df[income_df["Semester"] == prev_semester]["amount"].sum()
    diff          = current_total - prev_total

    # 2. Show as metrics
    st.write("### Income Overview")

    st.metric(
        label=f"Total Income ({sem})",
        value=f"${current_total:,.2f}",
        border=True
    )

    st.metric(
        label=f"Change vs {prev_semester}",
        value="",               # no main value
        delta=f"${diff:+,.2f}",  # +$XXX or -$XXX
        border = True
    )

    # 3. Distribution pie chart
    income_by_type = semester_income.groupby("Income_Type", as_index=False)["amount"].sum()
    fig_pie = px.pie(
        income_by_type,
        values="amount",
        names="Income_Type",
        color_discrete_sequence=px.colors.qualitative.G10,
        hole=0.4,
        title=f"{sem} Income Distribution By Type"
    )
    fig_pie.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>"
    )
    fig_pie.update_layout(margin=dict(t=35, b=20), title_font_size = 20)

    st.plotly_chart(fig_pie, use_container_width=True)

# Second column is intentionally left empty
with inc_col2:
    st.write("### Non-Committee Expenses")
    
    # First create a copy with the Semester column
    temp_trans_df = df_transactions.copy()
    temp_trans_df["Semester"] = temp_trans_df["transaction_date"].apply(get_semester)
    
    # Filter for non-committee expenses
    noncommittee_expenses = temp_trans_df[
        (temp_trans_df["amount"] < 0) &  # Expenses (negative amounts)
        (temp_trans_df["Semester"] == sem)  # Current semester
    ].copy()
    
    # Now merge to get Committee_Type for filtering
    noncommittee_expenses = noncommittee_expenses.merge(
        df_committees[["CommitteeID", "Committee_Type"]],
        left_on="budget_category",
        right_on="CommitteeID",
        how="left"
    )
    
    # Filter out committee expenses
    noncommittee_expenses = noncommittee_expenses[
        (noncommittee_expenses["Committee_Type"] != "committee") | 
        (noncommittee_expenses["Committee_Type"].isna())
    ]
    
    # Take absolute value of expenses
    noncommittee_expenses["amount"] = noncommittee_expenses["amount"].abs()
    
    # If there are no non-committee expenses for this semester
    if noncommittee_expenses.empty:
        st.info(f"No non-committee expenses found for {sem}")
    else:
        # Create expense categories based on the provided purposes
        expense_mapping = {
            "Merchandise": ["Merch", "Head Shot"],
            "Events": ["Social Events", "GBM Catering", "Formal", "Professional Events", "Fundraiser", "Road Trip", "ISOM Passport"],
            "Food & Drink": ["Food & Drink"],
            "Travel": ["Travel"],
            "Reimbursements": ["Reimbursement", "Refunded"],
            "Transfers": ["Transfers"],
            "Tax & Fees": ["Tax"],
            "Miscellaneous": ["Misc."]
        }
        
        # Initialize with default category
        noncommittee_expenses["Expense_Category"] = "Other"
        
        # Apply categorization
        for category, keywords in expense_mapping.items():
            for keyword in keywords:
                noncommittee_expenses.loc[
                    noncommittee_expenses["purpose"].str.contains(keyword, case=False, na=False), 
                    "Expense_Category"
                ] = category
        
        # Total non-committee expenses
        noncommittee_total = noncommittee_expenses["amount"].sum()
        st.metric(
            label=f"Total Non-Committee Expenses ({sem})",
            value=f"${noncommittee_total:,.2f}",
            border=True
        )
        
        # Group by expense category
        expense_by_category = noncommittee_expenses.groupby("Expense_Category", as_index=False)["amount"].sum()
        
        # Sort by amount for better visualization
        expense_by_category = expense_by_category.sort_values("amount", ascending=False)
        
        # Create pie chart
        fig_expense_pie = px.pie(
            expense_by_category,
            values="amount",
            names="Expense_Category",
            color_discrete_sequence=px.colors.qualitative.G10,
            hole=0.4,
            title=f"{sem} Non-Committee Expense Distribution"
        )
        fig_expense_pie.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>"
        )
        fig_expense_pie.update_layout(margin=dict(t=35, b=20), title_font_size=20)
        
        st.plotly_chart(fig_expense_pie, use_container_width=True)

    
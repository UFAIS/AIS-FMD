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
df_terms["Start_Date"]        = pd.to_datetime(df_terms["Start_Date"])
df_terms["End_Date"]          = pd.to_datetime(df_terms["End_Date"])
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

col1, col2 = st.columns([3, 4])

with col1:
    # Aggregate spend for that semester
    spend_sem = (
        df_txn
        .query("Semester == @sem")
        .groupby("Committee_Name", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount":"Spent"})
    )

    # Merge budgets + spend & compute %
    summary = (
        df_budgets_clean.query("Semester == @sem")
        .merge(spend_sem, on="Committee_Name", how="left")
        .fillna({"Spent": 0,})
        .assign(**{"% Spent": lambda d: d["Spent"] / d["budget_amount"] * 100})
    )
    summary["% Spent"].fillna(0,inplace=True)

    st.write(f"#### Spending vs. Budget ({sem})")
    st.dataframe(
        summary[["Committee_Name","budget_amount","Spent","% Spent"]]
        .rename(columns={"budget_amount":"Budget"})
    )

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


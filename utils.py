import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px 

# CONNECT SUPABASE
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# GET TABLES AS DF
@st.cache_data
def load_committees_df() -> pd.DataFrame:
    """
    Fetch the 'committees' table and return as a DataFrame.
    """
    supabase = get_supabase()
    res = supabase.table("committees").select("*").execute()
    data = res.data or []
    return pd.DataFrame(data)

@st.cache_data
def load_committee_budgets_df() -> pd.DataFrame:
    """
    Fetch the 'committeebudgets' table and return as a DataFrame.
    """
    supabase = get_supabase()
    res = supabase.table("committeebudgets").select("*").execute()
    data = res.data or []
    return pd.DataFrame(data)

@st.cache_data
def load_transactions_df() -> pd.DataFrame:
    """
    Fetch the 'transactions' table using pagination to bypass the 1,000‑row cap.
    """
    supabase = get_supabase()
    all_rows   = []
    batch_size = 1000
    offset     = 0

    while True:
        res = (
            supabase
            .table("transactions")
            .select("*")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = res.data or []
        if not batch:
            break
        all_rows.extend(batch)
        offset += batch_size

    return pd.DataFrame(all_rows)

@st.cache_data
def load_terms_df() -> pd.DataFrame:
    """
    Fetch the 'terms' table and return as a DataFrame.
    """
    supabase = get_supabase()
    res = supabase.table("terms").select("*").execute()
    data = res.data or []
    return pd.DataFrame(data)

# NAVIGATION PAGE
def register_nav_pages(page_defs: list[dict]) -> list:
    """
    Given a list of page definition dicts, register each as a Streamlit Page
    and return a list of Page objects for use with st.navigation.

    Each dict should contain:
      - 'page':    path to the .py file (relative to project root)
      - 'title':   display name in navigation
      - 'icon':    (optional) emoji or material icon string
      - 'default': (optional) bool, marks the default landing page
    """
    pages = []
    for spec in page_defs:
        page_obj = st.Page(
            page    = spec["page"],
            title   = spec["title"],
            icon    = spec.get("icon"),
            default = spec.get("default", False)
        )
        pages.append(page_obj)
    return pages

# BUDGET USAGE GRAPH
def fetch_term_budget_usage(term: str):
    supabase = get_supabase()
    # 1) Look up the term
    term_data = (
        supabase
        .table("terms")
        .select("TermID,Start_Date,End_Date,Semester")
        .eq("Semester", term)
        .single()
        .execute()
        .data
    )
    if not term_data:
        st.error(f"No term found for '{term}'")
        return None

    term_id    = term_data["TermID"]
    start_date = term_data["Start_Date"]
    end_date   = term_data["End_Date"]

    # 2) Fetch budgets (with committee info) for that term
    budgets_res = (
        supabase
        .table("committeebudgets")
        .select("""
            committeebudgetid,
            committeeid,
            budget_amount,
            committees(CommitteeID,Committee_Name,Committee_Type)
        """)
        .eq("termid", term_id)
        .execute()
    )
    df_b = pd.DataFrame(budgets_res.data)

    # Only keep actual committees
    df_b = df_b[df_b["committees"]["Committee_Type"] == "committee"]

    # 3) Fetch transactions in term date window, for those budget IDs
    budget_ids = df_b["committeebudgetid"].tolist()
    tx_res = (
        supabase
        .table("transactions")
        .select("budget_category,transaction_date,amount")
        .gte("transaction_date", start_date)
        .lte("transaction_date", end_date)
        .in_("budget_category", budget_ids)
        .execute()
    )
    df_t = pd.DataFrame(tx_res.data)
    if not df_t.empty:
        df_t["transaction_date"] = pd.to_datetime(df_t["transaction_date"])
    else:
        # no transactions
        df_t = pd.DataFrame(columns=["budget_category", "amount"])

    # 4) Group locally
    df_s = (
        df_t
        .groupby("budget_category", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount":"spent", "budget_category":"committeebudgetid"})
    )

    # 5) Merge spend into budgets
    df = (
        df_b
        .merge(df_s, on="committeebudgetid", how="left")
        .fillna({"spent": 0})
    )

    # 6) Compute %
    df["percent_spent"] = df["spent"] / df["budget_amount"] * 100

    # 7) Build figure
    fig = px.bar(
        df,
        x="percent_spent",
        y=df["committees"].apply(lambda r: r["Committee_Name"]),
        orientation="h",
        text=df["percent_spent"].round(1).astype(str) + "%",
        labels={"percent_spent":"% of Budget Spent", "y":"Committee"}
    )
    max_pct = max(100, df["percent_spent"].max() * 1.05)
    fig.update_layout(
        xaxis=dict(range=[0, max_pct]),
        margin=dict(l=150, r=20, t=30, b=20),
        yaxis_categoryorder="total ascending"
    )

    return fig

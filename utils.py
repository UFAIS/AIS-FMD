import streamlit as st
import pandas as pd
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

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
    Fetch the 'transactions' table and return as a DataFrame.
    """
    supabase = get_supabase()
    res = supabase.table("transactions").select("*").execute()
    data = res.data or []
    return pd.DataFrame(data)

@st.cache_data
def load_terms_df() -> pd.DataFrame:
    """
    Fetch the 'terms' table and return as a DataFrame.
    """
    supabase = get_supabase()
    res = supabase.table("terms").select("*").execute()
    data = res.data or []
    return pd.DataFrame(data)
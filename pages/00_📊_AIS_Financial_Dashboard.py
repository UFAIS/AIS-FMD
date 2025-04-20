import streamlit as st 
import pandas as pd 
from sqlalchemy import create_engine
import os
import plotly.express as px 
import supabase
from supabase import create_client, Client

# Connect to supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
def run_query():
    return supabase.table("committees").select("*").execute()

rows = run_query()

# Print results.
for row in rows.data:
    st.write(row)
st.write("hello")




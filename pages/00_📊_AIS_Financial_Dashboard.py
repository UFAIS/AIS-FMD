import streamlit as st 
import pandas as pd 
from sqlalchemy import create_engine
import os
import plotly.express as px 
import supabase
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query

# Get data from secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

# Initialize secrets 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

res = supabase.table("committees").select("*").limit(5).execute()
st.write(res.data)  # should show up to 5 rows now




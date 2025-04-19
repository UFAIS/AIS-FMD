import streamlit as st 
import pandas as pd 
from sqlalchemy import create_engine
import os
import plotly.express as px 
import supabase
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query
from utils import get_supabase

# connect to supabase
supabase = get_supabase()

res = supabase.table("committees").select("*").execute()
committee_df = pd.DataFrame(res.data)
st.write(committee_df)  # should show up to 5 rows now




import streamlit as st 
import pandas as pd 
from sqlalchemy import create_engine
import os
import plotly.express as px 
import supabase
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query

# Connect to supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def fetch_data():
    response = supabase.table("committees").select("*").execute()
    if response.error:
        st.error(f"Error fetching data: {response.error}")
    else:
        return response.data

# Display the data in the Streamlit app
data = fetch_data()
if data:
    st.write("### Data from Supabase:", data)





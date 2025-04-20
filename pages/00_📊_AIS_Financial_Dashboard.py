import streamlit as st 
import pandas as pd 
import os
import plotly.express as px 
from utils import load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title

apply_nav_title()

# get dfs from db and define any necessary functions
df_committees = load_committees_df()
df_budgets    = load_committee_budgets_df()
df_transactions     = load_transactions_df()
df_terms = load_terms_df()



col1,col2 = st.columns([1, 5])
with col1:
    st.image("assets/AIS_Logo.jpg", width=100)

with col2:
    animated_typing_title("UF AIS Financial Management Application")

st.divider()

col1,col2 = st.columns([3,4])

with col1:
    options = st.selectbox("Which semester would you like to view", list(df_terms["Semester"]), placeholder="Select a term...")
    st.write("You selected:", options)
   





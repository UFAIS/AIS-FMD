import streamlit as st 
from utils import register_nav_pages


# --- PAGE SETUP ---
PAGE_DEFS = [
    {"page":"views/homepage.py",              "title":"Homepage",                  "icon":":material/home:",         "default":True},
    {"page":"views/AIS_Financial_Dashboard.py","title":"AIS Financial Dashboard",   "icon":":material/analytics:"},
    {"page":"views/President.py",              "title":"President Financials",      "icon":":material/crown:"},
    {"page":"views/Consulting.py","title":"Consulting Financial Dashboard",   "icon":":material/enterprise:"},
    {"page":"views/Corporate_Relations.py","title":"Corporate Relations Financial Dashboard",   "icon":":material/handshake:"},
    {"page":"views/Marketing.py","title":"Marketing Financial Dashboard",   "icon":":material/campaign:"},
    {"page":"views/Membership.py","title":"Membership Financial Dashboard",   "icon":":material/groups:"},
    {"page":"views/Professional_Development.py","title":"Professional Development Financial Dashboard",   "icon":":material/psychology:"},
    {"page":"views/Treasury.py","title":"Treasury Financial Dashboard",   "icon":":material/account_balance:"},
    {"page":"views/Non_Committees.py","title":"Non-Committee Financial Dashboard",   "icon":":material/local_bar:"}
    
]

pages = register_nav_pages(PAGE_DEFS)

# --- NAVIGATION SETUP ---
pg = st.navigation(pages=pages)


# --- SHARED ON ALL PAGES ---
st.logo("assets/AIS_Logo.jpg", size = "large")
st.sidebar.text("Made by the the Treasury Committee")

# --- RUN NAVIGATION ---
pg.run()
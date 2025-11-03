import streamlit as st
import time 
from components import animated_typing_title, apply_nav_title

user_email = st.session_state.user_email
st.success(f"Welcome, {user_email}! 👋")

apply_nav_title()

animated_typing_title("UF AIS Financial Management Application")

st.divider()

st.markdown("""
Welcome to the AIS Treasury Dashboard!  
This tool provides a secure and collaborative view into our organization's finances.

### 🔍 Key Features
- **Financial Dashboard:** Get comprehensive insights into budgets, spending patterns, and financial trends
- **Transaction Editor:** Easily manage and update transaction details with an intuitive interface
- **AI Assistant:** Ask natural language questions about finances and get instant answers
- **Treasury Management:** Access administrative tools for uploading statements and managing terms

### 📊 What You Can Do
- View detailed financial analytics and budget utilization
- Update transaction purposes and committee assignments
- Ask AI questions like "What's the Marketing committee's spending this semester?"
- Upload and process financial statements
- Manage academic terms and committee budgets
- **Committees:** Dive into each committee’s financial activity.
- **Non-Committee:** Track general funds, transfers, and other uncategorized items.

### 📅 Data Sources
Data is pulled from the UF AIS cloud-established database, reviewed and categorized by the Treasury team.

""")

st.info("Navigate using the sidebar on the left.")


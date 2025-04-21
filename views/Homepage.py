import streamlit as st
import time 
from components import animated_typing_title, apply_nav_title

apply_nav_title()

animated_typing_title("UF AIS Financial Management Application")

st.divider()

st.markdown("""
Welcome to the AIS Treasury Dashboard!  
This tool provides a secure and collaborative view into our organization’s finances.

### 🔍 What You Can Do
- **Home:** You're here!
- **Cumulative Dashboard:** Get an overview of all budgets and spending.
- **Committees:** Dive into each committee’s financial activity.
- **Non-Committee:** Track general funds, transfers, and other uncategorized items.

### 📅 Data Sources
Data is pulled from the UF AIS cloud-established database, reviewed and categorized by the Treasury team.

""")

st.info("Navigate using the sidebar on the left.")


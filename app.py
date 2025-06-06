from utils import register_nav_pages, get_supabase
import streamlit as st
from supabase import Client
from components import animated_typing_title, apply_nav_title
import pandas as pd
import os
import plotly.express as px

st.set_page_config(
    page_title="UF AIS Financial Management System",
    layout="wide",                # ← forces wide mode
    initial_sidebar_state="auto"   # or "expanded" if you want the sidebar open
)

# Initialize Supabase client
supabase: Client = get_supabase()

def sign_up(email: str, password: str):
    try:
        user = supabase.auth.sign_up({"email": email, "password": password})
        return user
    except Exception as e:
        st.error(f"Registration failed: {e}")


def sign_in(email: str, password: str):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return user
    except Exception as e:
        st.error(f"Login failed: {e}")


def sign_out():
    try:
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.rerun()
    except Exception as e:
        st.error(f"Logout failed: {e}")


def main_app(user_email: str):
    # Always offer sign out
    if st.button("Sign Out"):
        sign_out()

    # Page registration and navigation only after authentication
    PAGE_DEFS = [
        {"page": "views/Homepage.py",                "title": "Homepage",                                    "icon": ":material/home:",         "default": True},
        {"page": "views/AIS_Financial_Dashboard.py", "title": "AIS Financial Dashboard",                       "icon": ":material/analytics:"},
        {"page": "views/President.py",               "title": "President Financials",                            "icon": ":material/crown:"},
        {"page": "views/Consulting.py",              "title": "Consulting Financial Dashboard",                  "icon": ":material/enterprise:"},
        {"page": "views/Corporate_Relations.py",     "title": "Corporate Relations Financial Dashboard",        "icon": ":material/handshake:"},
        {"page": "views/Marketing.py",               "title": "Marketing Financial Dashboard",                  "icon": ":material/campaign:"},
        {"page": "views/Membership.py",             "title": "Membership Financial Dashboard",                 "icon": ":material/groups:"},
        {"page": "views/Professional_Development.py","title": "Professional Development Financial Dashboard",    "icon": ":material/psychology:"},
        {"page": "views/Treasury.py",                "title": "Treasury Financial Dashboard",                    "icon": ":material/account_balance:"},
        {"page": "views/Non_Committees.py",          "title": "Non-Committee Financial Dashboard",               "icon": ":material/local_bar:"},
    ]

    pages = register_nav_pages(PAGE_DEFS)
    pg = st.navigation(pages=pages)

    # Shared header/logo/sidebar text
    st.logo("assets/AIS_logo.png", size="large")
    st.sidebar.text("Made by the Treasury Committee")

    # Run the selected page
    pg.run()


def auth_screen():
    st.title("Authentication Page")
    option = st.selectbox("Choose an action:", ["Login", "Sign Up"], key="auth_option")

    email    = st.text_input("Email", key="auth_email")
    password = st.text_input("Password", type="password", key="auth_pwd")

    if option == "Sign Up":
        confirm = st.text_input("Confirm Password", type="password", key="auth_confirm")

        if st.button("Register"):
            # 1. validate locally
            if not email or not password or not confirm:
                st.error("All fields are required.")
                return
            if password != confirm:
                st.error("Passwords do not match.")
                return
            if len(password) < 6:
                st.error("Password must be at least 6 characters.")
                return

            # 2. call your existing sign_up()
            user = sign_up(email, password)
            if hasattr(user, "error") and user.error:
                st.error(f"Registration failed: {user.error.message}")
            elif hasattr(user, "user") and user.user:
                st.success("Registration successful! Please check your email to confirm.")
                # force a rerun so they can switch to Login
                st.rerun()

    else:  # Login flow
        if st.button("Login"):
            if not email or not password:
                st.error("Enter both email and password.")
                return

            user = sign_in(email, password)
            if hasattr(user, "error") and user.error:
                st.error(f"Login failed: {user.error.message}")
            elif hasattr(user, "user") and user.user:
                st.session_state.user_email = user.user.email
                st.success("Logged in successfully.")
                st.rerun()

# Initialize session state for user_email
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Branch to auth or main app
if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()

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
    # Create a cleaner layout with columns
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Add logo and attractive header
        st.image("assets/AIS_logo.png", width=200)
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>AIS Financial Portal</h1>", unsafe_allow_html=True)
        
        # Create a card-like container for the auth form
        with st.container():
            st.markdown("""
            <style>
            .auth-container {
                background-color: #f8f9fa;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 1rem;
            }
            </style>
            <div class="auth-container"></div>
            """, unsafe_allow_html=True)
            
            # Tabs for login/signup instead of dropdown
            tab1, tab2 = st.tabs(["Login", "Sign Up"])
            
            with tab1:
                st.subheader("Welcome Back!")
                email = st.text_input("Email Address", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                
                # Full-width button with custom styling
                if st.button("Login", type="primary", use_container_width=True):
                    with st.spinner("Authenticating..."):
                        user = sign_in(email, password)
                        if user and user.user:
                            st.balloons()  # Add animation effect on successful login
                            st.session_state.user_email = user.user.email
                            st.rerun()
            
            with tab2:
                st.subheader("Create Account")
                email = st.text_input("Email Address", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                # Add password strength indicator
                if password:
                    if len(password) < 8:
                        st.warning("Password should be at least 8 characters")
                    elif password != confirm_password and confirm_password:
                        st.error("Passwords don't match")
                
                if st.button("Register", type="primary", use_container_width=True):
                    if password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        with st.spinner("Creating your account..."):
                            user = sign_up(email, password)
                            if user and user.user:
                                st.success("Registration successful! Please log in.")
        
        # Add some helpful information
        with st.expander("Need Help?"):
            st.markdown("""
            - **Forgot Password?** Contact the Treasury Committee
            - **New User?** Create an account with your UF email
            - **Having Issues?** Email ais.treasury@warrington.ufl.edu
            """)


# Initialize session state for user_email
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Branch to auth or main app
if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()

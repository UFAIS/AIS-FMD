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
    # Add custom CSS for styling with pastel blue theme
    st.markdown("""
    <style>
    .auth-card {
        background-color: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        max-width: 400px;
        margin: 2rem auto;
    }
    .auth-header {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .auth-subheader {
        color: #6B7280;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .blue-button {
        background-color: #A7C7E7;
        color: #1E3A8A;
        border-radius: 30px;
        padding: 0.5rem 1.5rem;
        border: none;
        font-weight: bold;
        text-align: center;
        transition: all 0.3s;
        cursor: pointer;
        width: 100%;
    }
    .blue-button:hover {
        background-color: #83B0E3;
    }
    .auth-input {
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        padding: 0.75rem;
        margin-bottom: 1rem;
        width: 100%;
    }
    .auth-link {
        color: #3B82F6;
        text-decoration: none;
        font-size: 0.875rem;
    }
    .auth-corner {
        position: absolute;
        top: 0;
        right: 0;
        width: 150px;
        height: 150px;
        background-color: #CCDFED;
        border-radius: 0 0 0 100%;
        z-index: -1;
    }
    .bottom-corner {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 100px;
        background-color: #A7C7E7;
        z-index: -1;
    }
    </style>
    
    <!-- Decorative elements -->
    <div class="auth-corner"></div>
    <div class="bottom-corner"></div>
    """, unsafe_allow_html=True)
    
    # Layout with columns to center the card
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        # Create two separate forms - one for login and one for signup
        option = st.selectbox("Choose an action:", ["Login", "Sign Up"], label_visibility="collapsed")
        
        if option == "Login":
            st.markdown('<div class="auth-card">', unsafe_allow_html=True)
            st.markdown('<div class="auth-header">Login</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-subheader">Please sign in to continue.</div>', unsafe_allow_html=True)
            
            # Login form
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password", placeholder="********")
                
                # Full-width button with custom styling
                submit_button = st.form_submit_button("LOGIN")
                
                # Apply blue button styling
                st.markdown("""
                <script>
                    const buttons = window.parent.document.querySelectorAll('button[kind="primaryFormSubmit"]');
                    for (let i = 0; i < buttons.length; i++) {
                        buttons[i].classList.add('blue-button');
                    }
                </script>
                """, unsafe_allow_html=True)
            
            if submit_button:
                with st.spinner("Logging in..."):
                    user = sign_in(email, password)
                    if user and user.user:
                        st.session_state.user_email = user.user.email
                        st.rerun()
            
            # Account signup link
            st.markdown('<div style="text-align: center; margin-top: 1rem;">Don\'t have an account? <a href="#" onclick="document.querySelector(\'select\').value=\'Sign Up\'; document.querySelector(\'select\').dispatchEvent(new Event(\'change\'));" class="auth-link">Sign up</a></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        else:  # Sign Up
            st.markdown('<div class="auth-card">', unsafe_allow_html=True)
            st.markdown('<div class="auth-header">Create Account</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-subheader">Please fill in your details.</div>', unsafe_allow_html=True)
            
            # Sign up form
            with st.form("signup_form"):
                email = st.text_input("Email", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password", placeholder="********")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="********")
                
                # Password validation
                if password and confirm_password:
                    if password != confirm_password:
                        st.warning("Passwords don't match")
                
                # Full-width button with custom styling
                submit_button = st.form_submit_button("SIGN UP")
                
                # Apply blue button styling
                st.markdown("""
                <script>
                    const buttons = window.parent.document.querySelectorAll('button[kind="primaryFormSubmit"]');
                    for (let i = 0; i < buttons.length; i++) {
                        buttons[i].classList.add('blue-button');
                    }
                </script>
                """, unsafe_allow_html=True)
            
            if submit_button:
                if password != confirm_password:
                    st.error("Passwords don't match")
                else:
                    with st.spinner("Creating your account..."):
                        user = sign_up(email, password)
                        if user and user.user:
                            st.success("Registration successful! Please log in.")
            
            # Login link
            st.markdown('<div style="text-align: center; margin-top: 1rem;">Already have an account? <a href="#" onclick="document.querySelector(\'select\').value=\'Login\'; document.querySelector(\'select\').dispatchEvent(new Event(\'change\'));" class="auth-link">Sign in</a></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
    # Hide the selectbox using CSS
    st.markdown("""
    <style>
    [data-testid="stSelectbox"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)


# Initialize session state for user_email
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Branch to auth or main app
if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()

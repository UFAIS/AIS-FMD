import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_supabase, get_admin, load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title
import io
from datetime import datetime, date
import numpy as np
import re

# Helper functions
def show_committee_reference():
    """Display the Committee ID reference table"""
    st.markdown("""
    #### 🔑 Committee ID Reference
    | ID | Committee | ID | Committee |
    |----|-----------|-----|-----------|
    | 1 | Dues | 10 | Professional Development |
    | 2 | Treasury | 11 | Sponsorship / Donation |
    | 3 | Transfers | 12 | Overhead |
    | 4 | President | 13 | Merch |
    | 5 | Membership | 14 | Road Trip |
    | 6 | Corporate Relations | 15 | Technology |
    | 7 | Consulting | 16 | Passport |
    | 8 | Meeting Food | 17 | Refunded |
    | 9 | Marketing | 18 | Formal |
    """)

# Helper functions
def create_transaction_editor(df_proc: pd.DataFrame, key_prefix: str = "venmo"):
    """Create an editable transaction preview form."""
    # Create purpose options
    purpose_options = [
        "Dues", "Food & Drink", "Tax", "Road Trip", "Social Events",
        "Sponsorship / Donation", "Travel Reimbursement", "Transfers",
        "Merch", "Professional Events", "Misc.", "ISOM Passport",
        "GBM Catering", "Formal", "Refunded", "Meeting Food",
        "Technology", "Marketing", "Professional Development"
    ]
    purpose_options.sort()

    # Show Committee ID Reference
    st.markdown("""
    #### 🔑 Committee ID Reference
    | ID | Committee | ID | Committee |
    |----|-----------|-----|-----------|
    | 1 | Dues | 10 | Professional Development |
    | 2 | Treasury | 11 | Sponsorship / Donation |
    | 3 | Transfers | 12 | Overhead |
    | 4 | President | 13 | Merch |
    | 5 | Membership | 14 | Road Trip |
    | 6 | Corporate Relations | 15 | Technology |
    | 7 | Consulting | 16 | Passport |
    | 8 | Meeting Food | 17 | Refunded |
    | 9 | Marketing | 18 | Formal |
    """)
    
    # Create display dataframe
    display_df = df_proc.copy()
    display_df["transactiondate"] = display_df["transactiondate"].apply(
        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
    )
    display_df["amount"] = display_df["amount"].apply(
        lambda x: f"${x:,.2f}" if pd.notna(x) else ""
    )
    
    with st.form(f"{key_prefix}_editor_form"):
        edited_df = st.data_editor(
            display_df,
            column_config={
                "transactiondate": st.column_config.TextColumn(
                    "Date",
                    disabled=True,
                ),
                "amount": st.column_config.TextColumn(
                    "Amount",
                    disabled=True,
                ),
                "details": st.column_config.TextColumn(
                    "Details",
                    disabled=True,
                ),
                "purpose": st.column_config.SelectboxColumn(
                    "Purpose",
                    options=[""] + purpose_options,
                    required=False
                ),
                "budget": st.column_config.SelectboxColumn(
                    "Committee ID",
                    options=[""] + [str(i) for i in range(1, 19)],
                    required=False,
                    help="Select the committee ID (see reference above)",
                )
            },
            disabled=False,
            hide_index=True,
            key=f"{key_prefix}_editor"
        )
        
        submitted = st.form_submit_button("Process and Insert Transactions")
        return edited_df, submitted

# Initialize UI
apply_nav_title()
animated_typing_title("Treasury Management Portal")
st.divider()

# Password protection
def check_treasury_password():
    """Check if user has entered correct treasury password"""
    if "treasury_authenticated" not in st.session_state:
        st.session_state.treasury_authenticated = False
    
    if not st.session_state.treasury_authenticated:
        st.warning("🔒 Treasury Access Required")
        password = st.text_input("Enter Treasury Password", type="password")
        
        if st.button("Access Treasury Portal"):
            # Get password from secrets
            treasury_password = st.secrets.get("treasury", {}).get("password", "default_password")
            
            if password == treasury_password:
                st.session_state.treasury_authenticated = True
                st.success("✅ Access granted!")
                st.rerun()
            else:
                st.error("❌ Incorrect password. Access denied.")
                return False
    
    return st.session_state.treasury_authenticated

# Check authentication first
if not check_treasury_password():
    st.stop()

# Treasury portal content
st.success("🎯 Welcome to the Treasury Management Portal")

# Initialize Supabase client
supabase = get_supabase()

# Load data
@st.cache_data
def load_treasury_data():
    df_committees = load_committees_df()
    df_budgets = load_committee_budgets_df()
    df_transactions = load_transactions_df()
    df_terms = load_terms_df()
    return df_committees, df_budgets, df_transactions, df_terms

df_committees, df_budgets, df_transactions, df_terms = load_treasury_data()

# Sidebar navigation
st.sidebar.header("🏛️ Treasury Tools")
page = st.sidebar.selectbox(
    "Select Tool",
    ["📊 Data Overview", "📤 Upload Transactions", "📅 Manage Terms", "💰 Manage Budgets", "🔧 Database Tools"]
)

if page == "📊 Data Overview":
    st.header("📊 Treasury Data Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Transactions", f"{len(df_transactions):,}")
    
    with col2:
        total_income = df_transactions[df_transactions["amount"] > 0]["amount"].sum()
        st.metric("Total Income", f"${total_income:,.2f}")
    
    with col3:
        total_expenses = abs(df_transactions[df_transactions["amount"] < 0]["amount"].sum())
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
    
    st.divider()
    
    # Recent activity
    st.subheader("Recent Activity")
    recent_txns = df_transactions.sort_values("transaction_date", ascending=False).head(10)
    if not recent_txns.empty:
        st.dataframe(
            recent_txns[["transaction_date", "amount", "details", "purpose"]]
            .rename(columns={
                "transaction_date": "Date",
                "amount": "Amount",
                "details": "Details",
                "purpose": "Purpose"
            })
            .style.format({"Amount": "${:,.2f}"}),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No recent transactions found.")

elif page == "📤 Upload Transactions":
    st.header("📤 Upload Transaction Data")
    st.info("Upload Venmo or Checking statements only. Filenames should include `VenmoStatement_` for Venmo or `checking` for Wells/Checking exports.")

    tabs = st.tabs(["Venmo", "Checking"])

    def classify_purpose(text: str) -> str | None:
        """Simple classifier that only detects dues-related transactions.
        All other transactions will have NULL purpose and budget category."""
        if not isinstance(text, str) or not text:
            return None
        
        s = str(text).lower().strip()
        if "dues" in s or "membership fee" in s or "membership payment" in s:
            return "Dues"
            
        return None

    # Committee ID reference:
    # 1: Dues               10: Professional Development
    # 2: Treasury          11: Sponsorship / Donation
    # 3: Transfers         12: Overhead
    # 4: President         13: Merch
    # 5: Membership        14: Road Trip
    # 6: Corporate         15: Technology
    # 7: Consulting        16: Passport
    # 8: Meeting Food      17: Refunded
    # 9: Marketing         18: Formal
    
    # Only map Dues automatically, all other mappings will be done manually
    PURPOSE_TO_COMMITTEEID = {
        "Dues": 1
    }

    def map_purpose_to_budget_id(purpose: str) -> int | None:
        """Map a classified purpose string to a CommitteeID when unambiguous.

        Returns None when mapping is not confident.
        """
        if not purpose or pd.isna(purpose):
            return None
        p = str(purpose).strip()
        # exact key
        if p in PURPOSE_TO_COMMITTEEID:
            return PURPOSE_TO_COMMITTEEID[p]
        # case-insensitive containment
        lp = p.lower()
        for key, cid in PURPOSE_TO_COMMITTEEID.items():
            if key.lower() == lp or key.lower() in lp or lp in key.lower():
                return cid
        return None

    def numeric_amount(x):
        try:
            if pd.isna(x):
                return 0.0
            s_orig = str(x)
            # normalize problematic unicode and whitespace
            s = s_orig.replace('\u2032', '').replace('\u2019', '').replace('\xa0', ' ')
            s = s.replace('$', '')
            # collapse whitespace
            s = re.sub(r'\s+', ' ', s).strip()

            # Find first numeric token with optional sign (handles '+ 46.00', '+\n46.00', etc.)
            m = re.search(r'([+-]?)\s*([0-9]{1,3}(?:[,\d]*)(?:\.\d+)?)', s)
            if not m:
                return 0.0
            sign = m.group(1) or ''
            num = m.group(2).replace(',', '')
            return float(sign + num)
        except:
            return 0.0

    def clean_proc_df(df_proc: pd.DataFrame) -> pd.DataFrame:
        """Coerce types, trim details, and drop footer/empty rows often present in exported statements."""
        df = df_proc.copy()
        # Ensure amount is float
        try:
            df['amount'] = df['amount'].astype(float)
        except Exception:
            df['amount'] = df['amount'].apply(lambda x: float(x) if pd.notna(x) else 0.0)

        # Normalize details
        df['details'] = df.get('details', '').fillna('').astype(str).str.strip()

        # Remove rows that look like footer/noise: missing date and empty details (or details only separators)
        no_date = df['transactiondate'].isna()
        details_empty = df['details'].str.replace(r'[\|\-\s]+', '', regex=True) == ''
        mask_footer = no_date & details_empty

        # Also drop rows where date missing and amount is zero and details blank
        mask_zero_blank = no_date & (df['amount'] == 0) & (df['details'].str.strip() == '')

        df = df[~(mask_footer | mask_zero_blank)].reset_index(drop=True)
        return df

    # Venmo tab
    with tabs[0]:
        uploaded_file = st.file_uploader("Upload Venmo statement (Excel/CSV)", type=["xlsx", "xls", "csv"], key="venmo_upload")
        if uploaded_file is not None:
            filename = uploaded_file.name
            # validate filename
            if 'venmostatement' not in filename.lower():
                st.error("Filename does not look like a Venmo statement. It should include 'VenmoStatement_'.")
            else:
                # check for duplicates
                existing = supabase.table("uploaded_files").select("*").eq("file_name", filename).execute()
                if existing.data:
                    st.warning("This file has already been uploaded. Aborting to avoid duplicates.")
                else:
                    try:
                        if filename.lower().endswith('.csv'):
                            df_raw = pd.read_csv(uploaded_file)
                        else:
                            df_raw = pd.read_excel(uploaded_file)

                        # Venmo columns: Date, Note, Amount (total) etc.
                        # Normalize column names (handle non-breaking spaces and case)
                        df_cols = {c.lower().strip().replace('\xa0', ' '): c for c in df_raw.columns}
                        # Prefer 'date' or 'transaction id' mapping
                        date_col = next((c for k, c in df_cols.items() if 'date' in k), None)
                        note_col = next((c for k, c in df_cols.items() if 'note' in k), None)
                        # Prefer an amount column containing both 'amount' and 'total' (handles variations like 'Amount (total)')
                        amount_col = next((c for k, c in df_cols.items() if 'amount' in k and 'total' in k), None)
                        # Fallbacks: amount (net), exact 'amount', or any column that contains 'amount'
                        if amount_col is None:
                            amount_col = next((c for k, c in df_cols.items() if 'amount (net)' in k), None)
                        if amount_col is None:
                            amount_col = next((c for k, c in df_cols.items() if k == 'amount'), None)
                        if amount_col is None:
                            amount_col = next((c for k, c in df_cols.items() if 'amount' in k), None)

                        if date_col is None or amount_col is None:
                            st.error("Could not find required columns (date, amount) in Venmo file.")
                        else:
                            df_proc = pd.DataFrame()
                            df_proc['transactiondate'] = pd.to_datetime(df_raw[date_col], errors='coerce').dt.date
                            df_proc['amount'] = df_raw[amount_col].apply(numeric_amount)
                            # details: combine note, from, to if available
                            details_parts = []
                            if note_col:
                                details_parts.append(df_raw[note_col].fillna('').astype(str))
                            # try columns 'from' 'to' etc.
                            for k in ['from', 'to', 'details']:
                                col = next((c for key, c in df_cols.items() if key == k), None)
                                if col:
                                    details_parts.append(df_raw[col].fillna('').astype(str))
                            if details_parts:
                                df_proc['details'] = details_parts[0]
                                for part in details_parts[1:]:
                                    df_proc['details'] = df_proc['details'] + ' | ' + part
                            else:
                                df_proc['details'] = ''

                            # budget left blank
                            df_proc['budget'] = ''
                            # purpose: classify from details
                            df_proc['purpose'] = df_proc['details'].apply(classify_purpose)
                            # account: mark as 'venmo'
                            df_proc['account'] = 'Venmo'

                            # Debug: show which raw column was used for amount
                            st.markdown(f"**Detected amount column:** `{amount_col}`")
                            try:
                                sample_vals = df_raw[amount_col].head(5).tolist()
                                st.markdown(f"**Sample raw values:** {sample_vals}")
                            except Exception:
                                pass

                            # Clean the proc dataframe (coerce types, drop noise rows)
                            df_proc = clean_proc_df(df_proc)

                            # Suggest budget_category based on purpose for preview
                            try:
                                df_proc['budget_suggested'] = df_proc['purpose'].apply(map_purpose_to_budget_id)
                                # enforce Food & Drink -> 8 if purpose indicates GBM catering
                                df_proc.loc[df_proc['purpose'] == 'Food & Drink', 'budget_suggested'] = df_proc.loc[df_proc['purpose'] == 'Food & Drink', 'budget_suggested'].fillna(8)
                            except Exception:
                                df_proc['budget_suggested'] = None

                            st.subheader("Preview and Edit")
                            
                            # Create purpose options
                            purpose_options = [
                                "Dues", "Food & Drink", "Tax", "Road Trip", "Social Events",
                                "Sponsorship / Donation", "Travel Reimbursement", "Transfers",
                                "Merch", "Professional Events", "Misc.", "ISOM Passport",
                                "GBM Catering", "Formal", "Refunded", "Meeting Food",
                                "Technology", "Marketing", "Professional Development"
                            ]
                            purpose_options.sort()
                            
                            # Create committee mapping for display
                            committee_options = [""] + [str(i) for i in range(1, 19)]
                            
                            # Convert dates to string for display
                            display_df = df_proc.copy()
                            display_df["transactiondate"] = display_df["transactiondate"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
                            display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
                            
                            with st.form("venmo_preview_form"):
                                edited_df = st.data_editor(
                                    display_df,
                                    column_config={
                                        "transactiondate": st.column_config.TextColumn(
                                            "Date",
                                            disabled=True,
                                        ),
                                        "amount": st.column_config.TextColumn(
                                            "Amount",
                                            disabled=True,
                                        ),
                                        "details": st.column_config.TextColumn(
                                            "Details",
                                            disabled=True,
                                        ),
                                        "purpose": st.column_config.SelectboxColumn(
                                            "Purpose",
                                            options=[""] + purpose_options,
                                            required=False
                                        ),
                                        "budget": st.column_config.SelectboxColumn(
                                            "Committee ID",
                                            options=committee_options,
                                            required=False,
                                            help="Select the committee ID (see reference above)",
                                        )
                                    },
                                    disabled=False,
                                    hide_index=True,
                                    key="venmo_editor"
                                )
                                
                                submitted = st.form_submit_button("Process and Insert Venmo Transactions")
                                
                                if submitted:
                                    with st.spinner("Inserting transactions..."):
                                        try:
                                            records = []
                                            for _, r in df_proc.iterrows():
                                                mapped_budget = None
                                                # Prefer explicit budget column (matching committee name) when provided
                                                try:
                                                    raw_budget = r.get('budget') if isinstance(r, dict) else r['budget']
                                                except Exception:
                                                    raw_budget = None

                                                if raw_budget and str(raw_budget).strip() != '':
                                                    rb = str(raw_budget).strip()
                                                    # try exact case-insensitive match to committee name
                                                    try:
                                                        match = df_committees[df_committees['Committee_Name'].str.lower() == rb.lower()]
                                                        if not match.empty:
                                                            mapped_budget = int(match['CommitteeID'].iloc[0])
                                                    except Exception:
                                                        mapped_budget = None

                                                # If no explicit budget, try mapping from purpose (straightforward cases)
                                                if mapped_budget is None:
                                                    try:
                                                        mapped_budget = map_purpose_to_budget_id(r['purpose'])
                                                    except Exception:
                                                        mapped_budget = None

                                                # Special rule: if purpose is Food & Drink and no explicit committee budget, map to 8
                                                try:
                                                    purpose_val = r['purpose'] if pd.notna(r['purpose']) else None
                                                except Exception:
                                                    purpose_val = None
                                                if mapped_budget is None and purpose_val == 'Food & Drink':
                                                    mapped_budget = 8

                                                records.append({
                                                    'transaction_date': r['transactiondate'].strftime('%Y-%m-%d') if pd.notna(r['transactiondate']) else None,
                                                    'amount': float(r['amount']) if pd.notna(r['amount']) else 0.0,
                                                    'details': str(r['details']) if pd.notna(r['details']) else '',
                                                    'purpose': r['purpose'] if pd.notna(r['purpose']) else None,
                                                    'account': r['account'],
                                                    'budget_category': mapped_budget
                                                })

                                            # Insert in batches (prefer service-role/admin client if available to avoid RLS issues)
                                            if records:
                                                admin_client = None
                                                try:
                                                    admin_client = get_admin()
                                                except Exception:
                                                    admin_client = None

                                                client = admin_client or supabase
                                                try:
                                                    client.table('transactions').insert(records).execute()

                                                    # record uploaded filename
                                                    client.table('uploaded_files').insert({
                                                        'file_name': filename
                                                    }).execute()

                                                    st.success(f"Inserted {len(records)} transactions and recorded file '{filename}'.")
                                                    st.cache_data.clear()
                                                except Exception as ee:
                                                    # Provide clearer guidance for RLS errors
                                                    msg = str(ee)
                                                    if 'row-level security' in msg.lower() or '42501' in msg:
                                                        st.error("Insert blocked by Row-Level Security (RLS).\n" \
                                                                "Solutions: add a Supabase service_role key to `.streamlit/secrets.toml` under `supabase.service_key` and restart the app, or update RLS policies to allow the current client to write to `transactions`.")
                                                    else:
                                                        st.error(f"Failed to insert transactions: {ee}")
                                            else:
                                                st.info("No records to insert.")

                                        except Exception as e:
                                            st.error(f"Failed to insert transactions: {e}")

                    except Exception as e:
                        st.error(f"Error processing file: {e}")

    # Checking tab
    with tabs[1]:
        uploaded_file = st.file_uploader("Upload Checking/Wells Fargo statement (CSV/Excel)", type=["xlsx", "xls", "csv"], key="checking_upload")
        if uploaded_file is not None:
            filename = uploaded_file.name
            if 'checking' not in filename.lower():
                st.error("Filename does not look like a checking export. Include 'checking' in the filename.")
            else:
                existing = supabase.table("uploaded_files").select("*").eq("file_name", filename).execute()
                if existing.data:
                    st.warning("This file has already been uploaded. Aborting to avoid duplicates.")
                else:
                    try:
                        # read - checking files often have no header
                        if filename.lower().endswith('.csv'):
                            df_raw = pd.read_csv(uploaded_file, header=None)
                        else:
                            df_raw = pd.read_excel(uploaded_file, header=None)

                        # Expect at least 3 meaningful columns: date, amount, details
                        if df_raw.shape[1] < 3:
                            st.error("Checking file doesn't have expected columns (date, amount, details).")
                        else:
                            df_proc = pd.DataFrame()
                            df_proc['transactiondate'] = pd.to_datetime(df_raw.iloc[:,0], errors='coerce').dt.date
                            df_proc['amount'] = df_raw.iloc[:,1].apply(numeric_amount)
                            # details are in column E (index 4) per user; fall back to last column if not present
                            if df_raw.shape[1] > 4:
                                df_proc['details'] = df_raw.iloc[:,4].astype(str)
                            else:
                                df_proc['details'] = df_raw.iloc[:,df_raw.shape[1]-1].astype(str)
                            df_proc['budget'] = ''
                            df_proc['purpose'] = df_proc['details'].apply(classify_purpose)
                            df_proc['account'] = 'Wells'

                            st.subheader("Preview and Edit")
                            
                            # Create purpose options
                            purpose_options = [
                                "Dues", "Food & Drink", "Tax", "Road Trip", "Social Events",
                                "Sponsorship / Donation", "Travel Reimbursement", "Transfers",
                                "Merch", "Professional Events", "Misc.", "ISOM Passport",
                                "GBM Catering", "Formal", "Refunded", "Meeting Food",
                                "Technology", "Marketing", "Professional Development"
                            ]
                            purpose_options.sort()
                            
                            # Create committee mapping for display
                            committee_options = [""] + [str(i) for i in range(1, 19)]
                            
                            # Convert dates to string for display
                            display_df = df_proc.copy()
                            display_df["transactiondate"] = display_df["transactiondate"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
                            display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
                            
                            with st.form("checking_preview_form"):
                                edited_df = st.data_editor(
                                    display_df,
                                    column_config={
                                        "transactiondate": st.column_config.TextColumn(
                                            "Date",
                                            disabled=True,
                                        ),
                                        "amount": st.column_config.TextColumn(
                                            "Amount",
                                            disabled=True,
                                        ),
                                        "details": st.column_config.TextColumn(
                                            "Details",
                                            disabled=True,
                                        ),
                                        "purpose": st.column_config.SelectboxColumn(
                                            "Purpose",
                                            options=[""] + purpose_options,
                                            required=False
                                        ),
                                        "budget": st.column_config.SelectboxColumn(
                                            "Committee ID",
                                            options=committee_options,
                                            required=False,
                                            help="Select the committee ID (see reference above)",
                                        )
                                    },
                                    disabled=False,
                                    hide_index=True,
                                    key="checking_editor"
                                )
                                
                                submitted = st.form_submit_button("Process and Insert Checking Transactions")
                                
                                if submitted:
                                    with st.spinner("Inserting transactions..."):
                                        try:
                                            records = []
                                            for _, r in df_proc.iterrows():
                                                mapped_budget = None
                                                # Prefer explicit budget column (matching committee name) when provided
                                                try:
                                                    raw_budget = r.get('budget') if isinstance(r, dict) else r['budget']
                                                except Exception:
                                                    raw_budget = None

                                                if raw_budget and str(raw_budget).strip() != '':
                                                    rb = str(raw_budget).strip()
                                                    # try exact case-insensitive match to committee name
                                                    try:
                                                        match = df_committees[df_committees['Committee_Name'].str.lower() == rb.lower()]
                                                        if not match.empty:
                                                            mapped_budget = int(match['CommitteeID'].iloc[0])
                                                    except Exception:
                                                        mapped_budget = None

                                                # If no explicit budget, try mapping from purpose (straightforward cases)
                                                if mapped_budget is None:
                                                    try:
                                                        mapped_budget = map_purpose_to_budget_id(r['purpose'])
                                                    except Exception:
                                                        mapped_budget = None

                                                # Special rule: if purpose is Food & Drink and no explicit committee budget, map to 8
                                                try:
                                                    purpose_val = r['purpose'] if pd.notna(r['purpose']) else None
                                                except Exception:
                                                    purpose_val = None
                                                if mapped_budget is None and purpose_val == 'Food & Drink':
                                                    mapped_budget = 8

                                                records.append({
                                                    'transaction_date': r['transactiondate'].strftime('%Y-%m-%d') if pd.notna(r['transactiondate']) else None,
                                                    'amount': float(r['amount']) if pd.notna(r['amount']) else 0.0,
                                                    'details': str(r['details']) if pd.notna(r['details']) else '',
                                                    'purpose': r['purpose'] if pd.notna(r['purpose']) else None,
                                                    'account': r['account'],
                                                    'budget_category': mapped_budget
                                                })

                                            if records:
                                                admin_client = None
                                                try:
                                                    admin_client = get_admin()
                                                except Exception:
                                                    admin_client = None

                                                client = admin_client or supabase
                                                try:
                                                    client.table('transactions').insert(records).execute()
                                                    client.table('uploaded_files').insert({'file_name': filename}).execute()
                                                    st.success(f"Inserted {len(records)} transactions and recorded file '{filename}'.")
                                                    st.cache_data.clear()
                                                except Exception as ee:
                                                    msg = str(ee)
                                                    if 'row-level security' in msg.lower() or '42501' in msg:
                                                        st.error("Insert blocked by Row-Level Security (RLS).\n" \
                                                                "Solutions: add a Supabase service_role key to `.streamlit/secrets.toml` under `supabase.service_key` and restart the app, or update RLS policies to allow the current client to write to `transactions`.")
                                                    else:
                                                        st.error(f"Failed to insert transactions: {ee}")
                                            else:
                                                st.info("No records to insert.")

                                        except Exception as e:
                                            st.error(f"Failed to insert transactions: {e}")

                    except Exception as e:
                        st.error(f"Error reading checking file: {e}")

elif page == "📅 Manage Terms":
    st.header("📅 Manage Academic Terms")
    
    # Show current terms
    st.subheader("Current Terms")
    if not df_terms.empty:
        st.dataframe(
            df_terms[["TermID", "Semester", "start_date", "end_date"]]
            .sort_values("start_date", ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No terms found in the database.")
    
    st.divider()
    
    # Add new term
    st.subheader("Add New Term")
    
    col1, col2 = st.columns(2)
    
    with col1:
        term_id = st.text_input("Term ID (e.g., FA25, SP26)")
        semester = st.text_input("Semester Name (e.g., Fall 2024, Spring 2025)")
        
        # Semester validation helper
        if semester:
            # Check for proper capitalization and format
            semester_lower = semester.lower()
            valid_formats = [
                "fall", "spring", "summer", "winter"
            ]
            
            # Check if semester starts with valid season
            season_valid = any(semester_lower.startswith(season) for season in valid_formats)
            
            # Check for proper year format (4 digits)
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', semester)
            year_valid = year_match is not None
            
            # Show validation feedback
            if not season_valid:
                st.error("❌ Semester should start with: Fall, Spring, Summer, or Winter")
            elif not year_valid:
                st.error("❌ Semester should include a 4-digit year (e.g., 2025)")
            elif semester != semester.title():
                st.warning("⚠️ Consider using proper capitalization (e.g., 'Fall 2025' instead of 'fall 25')")
            else:
                st.success("✅ Valid semester format!")
    
    with col2:
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
    
    if st.button("➕ Add Term"):
        if term_id and semester and start_date and end_date:
            # Validate semester format before proceeding
            semester_lower = semester.lower()
            valid_formats = ["fall", "spring", "summer", "winter"]
            season_valid = any(semester_lower.startswith(season) for season in valid_formats)
            
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', semester)
            year_valid = year_match is not None
            
            if not season_valid:
                st.error("❌ Invalid semester format. Must start with: Fall, Spring, Summer, or Winter")
            elif not year_valid:
                st.error("❌ Invalid year format. Must include a 4-digit year (e.g., 2025)")
            else:
                try:
                    # Auto-correct capitalization if needed
                    corrected_semester = semester.title()
                    
                    term_data = {
                        "TermID": term_id,
                        "Semester": corrected_semester,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d")
                    }
                    
                    # Check if term already exists
                    existing = supabase.table("terms").select("*").eq("TermID", term_id).execute()
                    if existing.data:
                        st.warning(f"Term {term_id} already exists!")
                    else:
                        supabase.table("terms").insert(term_data).execute()
                        st.success(f"✅ Term {term_id} ({corrected_semester}) added successfully!")
                        st.cache_data.clear()
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error adding term: {str(e)}")
        else:
            st.error("Please fill in all fields.")

elif page == "💰 Manage Budgets":
    st.header("💰 Manage Committee Budgets")
    
    # Show current budgets
    st.subheader("Current Budgets")
    
    # Get current terms
    current_terms = df_terms.sort_values("start_date", ascending=False)
    
    if not current_terms.empty:
        selected_term = st.selectbox(
            "Select Term",
            current_terms["TermID"].tolist(),
            format_func=lambda x: f"{x} - {current_terms[current_terms['TermID'] == x]['Semester'].iloc[0]}"
        )
        
        # Show budgets for selected term
        term_budgets = df_budgets[df_budgets["termid"] == selected_term].copy()
        if not term_budgets.empty:
            term_budgets = term_budgets.merge(
                df_committees[["CommitteeID", "Committee_Name"]], 
                left_on="committeeid", right_on="CommitteeID", how="left"
            )
            
            st.dataframe(
                term_budgets[["Committee_Name", "budget_amount"]]
                .rename(columns={"Committee_Name": "Committee", "budget_amount": "Budget Amount"}),
                use_container_width=True,
                hide_index=True
            )
        else:
            # Get the semester name for the selected term
            semester_name = current_terms[current_terms['TermID'] == selected_term]['Semester'].iloc[0]
            st.info(f"No budgets set for {semester_name} semester")
        
        st.divider()
        
        # Add/Update budgets
        st.subheader("Set Committee Budgets")
        
        # Get committees
        committees = df_committees[df_committees["Committee_Type"] == "committee"]["Committee_Name"].tolist()
        committee_ids = df_committees[df_committees["Committee_Type"] == "committee"][["CommitteeID", "Committee_Name"]]
        
        budget_inputs = {}
        col1, col2 = st.columns(2)
        
        for i, committee in enumerate(committees):
            # GET EXISTING BUDGET VALUE FOR THIS COMMITTEE - THIS IS THE NEW CODE
            existing_budget = 0.0
            if not term_budgets.empty:
                committee_id = committee_ids[committee_ids["Committee_Name"] == committee]["CommitteeID"].iloc[0]
                matching_budgets = term_budgets[term_budgets["committeeid"] == committee_id]
                if not matching_budgets.empty:
                    existing_budget = float(matching_budgets["budget_amount"].iloc[0])
            
            with col1 if i % 2 == 0 else col2:
                budget_inputs[committee] = st.number_input(
                    f"{committee} Budget",
                    min_value=0.0,
                    value=existing_budget,  # USE EXISTING VALUE INSTEAD OF 0.0
                    step=100.0,
                    format="%.2f"
                )
        
        if st.button("💾 Save Budgets"):
            try:
                # Delete existing budgets for this term
                supabase.table("committeebudgets").delete().eq("termid", selected_term).execute()
                
                # Insert new budgets - CHANGED TO INCLUDE ALL VALUES, NOT JUST > 0
                for committee_name, budget_amount in budget_inputs.items():
                    committee_id = committee_ids[committee_ids["Committee_Name"] == committee_name]["CommitteeID"].iloc[0]
                    
                    budget_data = {
                        "termid": selected_term,
                        "committeeid": int(committee_id),
                        "budget_amount": float(budget_amount)
                    }
                    
                    supabase.table("committeebudgets").insert(budget_data).execute()
                
                st.success("✅ Budgets saved successfully!")
                st.cache_data.clear()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error saving budgets: {str(e)}")
    else:
        st.info("No terms found. Please add terms first.")

elif page == "🔧 Database Tools":
    st.header("🔧 Database Management Tools")
    
    st.subheader("Data Export")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Export Transactions"):
            csv = df_transactions.to_csv(index=False)
            st.download_button(
                label="Download Transactions CSV",
                data=csv,
                file_name=f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📥 Export Budgets"):
            csv = df_budgets.to_csv(index=False)
            st.download_button(
                label="Download Budgets CSV",
                data=csv,
                file_name=f"budgets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col3:
        if st.button("📥 Export Terms"):
            csv = df_terms.to_csv(index=False)
            st.download_button(
                label="Download Terms CSV",
                data=csv,
                file_name=f"terms_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    st.divider()
    
    st.subheader("Database Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Terms", len(df_terms))
    
    with col2:
        st.metric("Total Committees", len(df_committees))
    
    with col3:
        st.metric("Total Budgets", len(df_budgets))
    
    with col4:
        st.metric("Total Transactions", len(df_transactions))
    
    # Data validation
    st.subheader("Data Validation")
    
    # Check for orphaned records
    orphaned_budgets = df_budgets[~df_budgets["committeeid"].isin(df_committees["CommitteeID"])]
    orphaned_transactions = df_transactions[~df_transactions["budget_category"].isin(df_committees["CommitteeID"])]
    
    if not orphaned_budgets.empty:
        st.warning(f"⚠️ Found {len(orphaned_budgets)} orphaned budget records")
    
    if not orphaned_transactions.empty:
        st.warning(f"⚠️ Found {len(orphaned_transactions)} orphaned transaction records")
    
    if orphaned_budgets.empty and orphaned_transactions.empty:
        st.success("✅ No data integrity issues found")

# Add logout button
st.sidebar.divider()
if st.sidebar.button("🚪 Logout from Treasury"):
    st.session_state.treasury_authenticated = False
    st.rerun()

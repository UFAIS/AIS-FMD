import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_supabase, load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title
import io
from datetime import datetime, date
import numpy as np

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
    st.info("""
    **Two-Step Upload Process:**
    1. **Stage Data**: Upload Excel file to staging table
    2. **Process Data**: Automatically transfer from staging to main transactions table
    
    The Excel file should contain columns: `transactiondate`, `amount`, `details`, `budget`, `purpose`, `account`
    """)
    
    uploaded_file = st.file_uploader(
        "Choose an Excel file",
        type=['xlsx', 'xls'],
        help="The Excel file should contain columns: transactiondate, amount, details, budget, purpose, account"
    )
    
    if uploaded_file is not None:
        try:
            # Read the Excel file
            df_upload = pd.read_excel(uploaded_file)
            
            # Validate required columns for staging table
            required_columns = ["transactiondate", "amount", "details", "budget", "purpose", "account"]
            missing_columns = [col for col in required_columns if col not in df_upload.columns]
            
            if missing_columns:
                st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                st.info("Required columns: transactiondate, amount, details, budget, purpose, account")
            else:
                # Show preview
                st.subheader("📋 Data Preview")
                st.dataframe(df_upload.head(10), use_container_width=True)
                
                # Show data summary
                st.subheader("📊 Upload Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Rows", f"{len(df_upload):,}")
                
                with col2:
                    total_upload_income = df_upload[df_upload["amount"] > 0]["amount"].sum()
                    st.metric("Total Income", f"${total_upload_income:,.2f}")
                
                with col3:
                    total_upload_expenses = abs(df_upload[df_upload["amount"] < 0]["amount"].sum())
                    st.metric("Total Expenses", f"${total_upload_expenses:,.2f}")
                
                # Show committee mapping preview
                st.subheader("🔗 Committee Mapping Preview")
                unique_budgets = df_upload["budget"].unique()
                committee_mapping = df_committees[df_committees["Committee_Type"] == "committee"][["CommitteeID", "Committee_Name"]]
                
                # Check which budget values will map to committees
                mapped_budgets = []
                unmapped_budgets = []
                
                for budget in unique_budgets:
                    if pd.notna(budget) and budget in committee_mapping["Committee_Name"].values:
                        mapped_budgets.append(budget)
                    else:
                        unmapped_budgets.append(budget)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success(f"✅ **Mapped Budgets ({len(mapped_budgets)}):**")
                    for budget in mapped_budgets:
                        st.write(f"• {budget}")
                
                with col2:
                    if unmapped_budgets:
                        st.warning(f"⚠️ **Unmapped Budgets ({len(unmapped_budgets)}):**")
                        for budget in unmapped_budgets:
                            st.write(f"• {budget}")
                    else:
                        st.success("✅ All budget values will be mapped to committees!")
                
                # Confirmation
                st.warning("⚠️ This action will completely replace all existing transaction data!")
                confirm = st.checkbox("I understand that this will overwrite all existing transaction data")
                
                if confirm and st.button("🚀 Upload to Staging Table"):
                    with st.spinner("Uploading data to staging table..."):
                        try:
                            # Clear existing staging data
                            supabase.table("stagingtransactions").delete().neq("transactiondate", "1900-01-01").execute()
                            
                            # Insert new data into staging table
                            for _, row in df_upload.iterrows():
                                staging_data = {
                                    "transactiondate": row["transactiondate"].strftime("%Y-%m-%d") if pd.notna(row["transactiondate"]) else None,
                                    "amount": float(row["amount"]) if pd.notna(row["amount"]) else 0,
                                    "details": str(row["details"]) if pd.notna(row["details"]) else "",
                                    "budget": str(row["budget"]) if pd.notna(row["budget"]) else "",
                                    "purpose": str(row["purpose"]) if pd.notna(row["purpose"]) else "",
                                    "account": str(row["account"]) if pd.notna(row["account"]) else ""
                                }
                                supabase.table("stagingtransactions").insert(staging_data).execute()
                            
                            st.success("✅ Data uploaded to staging table successfully!")
                            
                            # Now process the data transfer
                            st.info("🔄 Processing data transfer from staging to main table...")
                            
                            # Execute the SQL transfer query
                            transfer_query = """
                            INSERT INTO transactions (
                                transaction_date,
                                amount,
                                details,
                                purpose,
                                account,
                                budget_category
                            )
                            SELECT
                                s.transactiondate,
                                s.amount,
                                s.details,
                                s.purpose,
                                s.account,
                                c."CommitteeID"
                            FROM stagingtransactions s
                            JOIN committees c ON s.budget = c."Committee_Name"
                            """
                            
                            # Clear existing transactions first
                            supabase.table("transactions").delete().neq("transactionid", 0).execute()
                            
                            # Execute the transfer query using rpc
                            result = supabase.rpc('exec_sql', {'sql_query': transfer_query}).execute()
                            
                            # Alternative approach if rpc doesn't work - manual transfer
                            if not result.data:
                                st.info("Using manual transfer method...")
                                
                                # Get staging data
                                staging_data = supabase.table("stagingtransactions").select("*").execute()
                                staging_df = pd.DataFrame(staging_data.data)
                                
                                if not staging_df.empty:
                                    # Merge with committees to get budget_category
                                    staging_df = staging_df.merge(
                                        df_committees[["CommitteeID", "Committee_Name"]], 
                                        left_on="budget", 
                                        right_on="Committee_Name", 
                                        how="inner"
                                    )
                                    
                                    # Insert into transactions table
                                    for _, row in staging_df.iterrows():
                                        transaction_data = {
                                            "transaction_date": row["transactiondate"],
                                            "amount": float(row["amount"]) if pd.notna(row["amount"]) else 0,
                                            "details": str(row["details"]) if pd.notna(row["details"]) else "",
                                            "purpose": str(row["purpose"]) if pd.notna(row["purpose"]) else "",
                                            "account": str(row["account"]) if pd.notna(row["account"]) else "",
                                            "budget_category": int(row["CommitteeID"])
                                        }
                                        supabase.table("transactions").insert(transaction_data).execute()
                            
                            st.success("✅ Data transfer completed successfully!")
                            st.balloons()
                            
                            # Clear cache to refresh data
                            st.cache_data.clear()
                            
                        except Exception as e:
                            st.error(f"❌ Upload failed: {str(e)}")
                            st.error("Please check that your Excel file has the correct column names and data format.")
                
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")

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
        
        budget_inputs = {}
        col1, col2 = st.columns(2)
        
        for i, committee in enumerate(committees):
            with col1 if i % 2 == 0 else col2:
                budget_inputs[committee] = st.number_input(
                    f"{committee} Budget",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    format="%.2f"
                )
        
        if st.button("💾 Save Budgets"):
            try:
                # Get committee IDs
                committee_ids = df_committees[df_committees["Committee_Type"] == "committee"][["CommitteeID", "Committee_Name"]]
                
                # Delete existing budgets for this term
                supabase.table("committeebudgets").delete().eq("termid", selected_term).execute()
                
                # Insert new budgets
                for committee_name, budget_amount in budget_inputs.items():
                    if budget_amount > 0:
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

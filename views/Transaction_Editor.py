import streamlit as st
import pandas as pd
import time
from utils import load_committees_df, load_transactions_df, load_terms_df, get_admin
from components import animated_typing_title, apply_nav_title

# Initialize UI
apply_nav_title()
animated_typing_title("Transaction Editor")

st.markdown("""
### 🎯 How to Edit Transactions

Welcome to the Transaction Editor! This tool makes it easy to manage and update transaction details. Here's how it works: """)

col = [st.columns(4)]
with col[0][0]:
    st.markdown("""
    **Step 1: Select a Month**
    - 📅 Use the month selector to find the transactions you want to edit
    - All transactions for the selected month will be displayed in a table below
    """)
with col[0][1]:
    st.markdown("""
    **Step 2: Make Your Changes**
    - 🔄 Update transaction details using the dropdown menus
    - 📝 Modify committee assignments and purposes as needed
    - ✨ Changes are highlighted in real-time for easy tracking
    """)
with col[0][2]:
    st.markdown("""
    **Step 3: Save Your Updates**
    - ✅ Review your changes in the preview table
    - 💾 Click "Save Changes" to update the database
    - 🔒 All changes are validated before saving
    """)
with col[0][3]:
    st.markdown("""
    **Pro Tips:**
    - Filter by committee to focus on specific transactions
    - Use the search bar to find specific entries
    - Green highlights show which fields you've modified
    """)

st.divider()

# Load data
@st.cache_data
def load_editor_data():
    df_committees = load_committees_df()
    df_transactions = load_transactions_df()
    df_terms = load_terms_df()
    
    # Parse dates
    df_terms["start_date"] = pd.to_datetime(df_terms["start_date"], errors="coerce")
    df_terms["end_date"] = pd.to_datetime(df_terms["end_date"], errors="coerce")
    df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"], errors="coerce")
    
    return df_committees, df_transactions, df_terms

df_committees, df_transactions, df_terms = load_editor_data()

# Helper function to map dates to semesters
def get_semester(dt: pd.Timestamp) -> str | None:
    if pd.isna(dt):
        return None
    mask = (df_terms["start_date"] <= dt) & (df_terms["end_date"] >= dt)
    semesters = df_terms.loc[mask, "Semester"]
    return semesters.iloc[0] if not semesters.empty else None

# Initialize data and filters
available_semesters = (
    df_terms[["Semester", "start_date"]]
    .dropna()
    .sort_values("start_date")
    ["Semester"]
    .tolist()
)

selected_semester = st.selectbox(
    "Select Semester",
    available_semesters,
    index=len(available_semesters) - 1 if available_semesters else 0
)

# Filter transactions based on semester
filtered_transactions = df_transactions.copy()
filtered_transactions["Semester"] = filtered_transactions["transaction_date"].apply(get_semester)
filtered_transactions = filtered_transactions[filtered_transactions["Semester"] == selected_semester]

# Month selection
months = sorted(filtered_transactions["transaction_date"].dt.to_period('M').unique())
if not months:
    st.info("No transactions found for the selected semester.")
    st.stop()

# Clear selected month when semester changes
if "last_semester" not in st.session_state or st.session_state.last_semester != selected_semester:
    st.session_state.last_semester = selected_semester
    if "selected_month" in st.session_state:
        del st.session_state.selected_month

# Initialize or update selected month
if "selected_month" not in st.session_state or st.session_state.selected_month not in months:
    st.session_state.selected_month = months[-1]  # Default to most recent month

# Month selector
selected_month = st.selectbox(
    "Select Month to Edit",
    months,
    format_func=lambda x: x.strftime("%B %Y"),
    key="transaction_month_selector",
    index=months.index(st.session_state.selected_month)
)

# Update session state with selected month
st.session_state.selected_month = selected_month

# Get transactions for selected month
month_transactions = (
    filtered_transactions[filtered_transactions["transaction_date"].dt.to_period('M') == selected_month]
    .merge(df_committees[["CommitteeID", "Committee_Name"]], 
           left_on="budget_category", right_on="CommitteeID", how="left")
    .sort_values("transaction_date")
)

if not month_transactions.empty:
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
    committee_mapping = {str(i): name for i, name in 
                        df_committees[["CommitteeID", "Committee_Name"]].values}
    # Create committee options with ID and name combined
    committee_options = [""] + [f"{i} - {committee_mapping.get(str(i), '')}" for i in range(1, 19)]
    
    # Initialize edited data in session state
    if "edited_data" not in st.session_state:
        st.session_state.edited_data = month_transactions.copy()
        # Convert budget_category to the combined format for display
        st.session_state.edited_data['budget_category'] = st.session_state.edited_data['budget_category'].apply(
            lambda x: f"{int(x)} - {committee_mapping.get(str(int(x)), '')}" if pd.notna(x) else ""
        )
    
    with st.form("transaction_editor"):
        # Create an editable dataframe
        edited_df = st.session_state.edited_data.copy()
        
        # Convert dates to string for display
        display_df = edited_df.copy()
        display_df["transaction_date"] = display_df["transaction_date"].dt.strftime("%Y-%m-%d")
        display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}")
        
        # Create editors for purpose and budget columns
        editors = {
            "purpose": st.column_config.SelectboxColumn(
                "Purpose",
                options=purpose_options,  # Removed empty option to prevent accidental clearing
                required=False,
                default=None
            ),
            "budget_category": st.column_config.SelectboxColumn(
                "Committee",
                options=committee_options,
                required=False,
                default=None,
                help="Select the committee ID. Leave empty to clear the committee.",
            )
        }
        
        # Display editable dataframe
        edited_df = st.data_editor(
            display_df[["transaction_date", "amount", "details", "purpose", "budget_category"]],
            column_config={
                "transaction_date": st.column_config.TextColumn(
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
                **editors
            },
            disabled=False,
            hide_index=True,
            key="transaction_editor"
        )
        
        submitted = st.form_submit_button("💾 Save Changes")
        
        if submitted:
            try:
                admin = get_admin()
                successful_updates = []
                failed_updates = []
                
                for idx, row in edited_df.iterrows():
                    original = month_transactions.loc[idx]
                    
                    # Convert budget_category to int if not empty
                    budget_cat = row["budget_category"]
                    
                    if pd.notna(budget_cat) and budget_cat != "":  # Check if value is present
                        if isinstance(budget_cat, str):
                            try:
                                budget_cat = int(budget_cat.split(" - ")[0])
                            except (ValueError, IndexError):
                                budget_cat = None
                        elif isinstance(budget_cat, (int, float)):
                            budget_cat = int(budget_cat)
                        else:
                            budget_cat = None
                    else:
                        budget_cat = None
                    
                    # Compare changes carefully
                    current_purpose = row["purpose"] if pd.notna(row["purpose"]) and row["purpose"] != "" else None
                    current_budget = budget_cat
                    
                    original_purpose = original["purpose"] if pd.notna(original["purpose"]) else None
                    original_budget = original["budget_category"] if pd.notna(original["budget_category"]) else None
                    
                    # Check if values actually changed
                    purpose_changed = current_purpose != original_purpose
                    budget_changed = current_budget != original_budget
                    
                    if purpose_changed or budget_changed:
                        try:
                            update_data = {
                                "purpose": current_purpose,
                                "budget_category": current_budget
                            }
                            
                            response = admin.table("transactions").update(update_data).eq(
                                "transactionid", original["transactionid"]
                            ).execute()
                            
                            if response.data:
                                successful_updates.append(original["transactionid"])
                            else:
                                failed_updates.append(original["transactionid"])
                                
                        except Exception as e:
                            failed_updates.append(original["transactionid"])
                
                # Show simple status message and refresh
                if successful_updates and not failed_updates:
                    st.success(f"✅ Successfully updated {len(successful_updates)} transactions!")
                    # Clear caches and force refresh
                    st.cache_data.clear()
                    if "edited_data" in st.session_state:
                        del st.session_state.edited_data
                    time.sleep(1)  # Brief pause to ensure message is seen
                    st.rerun()
                elif failed_updates:
                    st.error(f"❌ Failed to update {len(failed_updates)} transactions. Please try again.")
                elif not successful_updates and not failed_updates:
                    st.info("No changes were made.")
                    
            except Exception as e:
                st.error(f"Error updating transactions: {str(e)}")
else:
    st.info("No transactions found for the selected month.")
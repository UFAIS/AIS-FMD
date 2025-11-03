import streamlit as st
import pandas as pd
from utils import load_committees_df, load_transactions_df, load_terms_df, load_committee_budgets_df
from components import animated_typing_title, apply_nav_title
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize UI
apply_nav_title()
animated_typing_title("AI Financial Assistant")

st.markdown("""
### 🤖 Ask Questions About AIS Finances

Welcome to the AI Financial Assistant! Ask natural language questions about:
- 💰 Committee budgets and spending
- 📊 Transaction details and patterns
- 📅 Semester comparisons and trends
- 🔍 Specific committees or time periods
            
**NOTE: The AI assistant is still in beta. Please verify any financial information it provides.**

**Example Questions:**
- "What's the total spending for the Marketing committee this semester?"
- "Show me all Venmo transactions over $500"
- "Which committee has spent the most on food?"
- "Compare budget utilization between Fall 2024 and Spring 2025"
- "Find all uncategorized transactions"
""")

st.divider()

# Check if API key is configured
if "google" not in st.secrets or "api_key" not in st.secrets["google"]:
    st.error("""
    ❌ **Google Gemini API key not configured**
    
    To use the AI Assistant, add your Google API key to `.streamlit/secrets.toml`:
    ```
    [google]
    api_key = "your-api-key-here"
    ```
    
    Get a free API key at: https://makersuite.google.com/app/apikey
    """)
    st.stop()

# Load all data
@st.cache_data
def load_all_data():
    """Load all financial data for the AI assistant"""
    df_committees = load_committees_df()
    df_transactions = load_transactions_df()
    df_terms = load_terms_df()
    df_budgets = load_committee_budgets_df()
    
    # Parse dates
    df_transactions["transaction_date"] = pd.to_datetime(df_transactions["transaction_date"], errors="coerce")
    df_terms["start_date"] = pd.to_datetime(df_terms["start_date"], errors="coerce")
    df_terms["end_date"] = pd.to_datetime(df_terms["end_date"], errors="coerce")
    
    return df_committees, df_transactions, df_terms, df_budgets

try:
    df_committees, df_transactions, df_terms, df_budgets = load_all_data()
    
    # Display data overview
    with st.expander("📊 Available Data Overview"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Committees", len(df_committees))
        with col2:
            st.metric("Transactions", len(df_transactions))
        with col3:
            st.metric("Terms", len(df_terms))
        with col4:
            st.metric("Budget Records", len(df_budgets))
        
        st.markdown("**Available DataFrames:**")
        st.markdown("- `df_committees`: Committee names and types")
        st.markdown("- `df_transactions`: All financial transactions")
        st.markdown("- `df_terms`: Academic terms/semesters")
        st.markdown("- `df_budgets`: Committee budget allocations")
    
    # Initialize the LLM (using gemini-2.0-flash - free with 15 RPM, 1M TPM limits)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=st.secrets["google"]["api_key"],
        temperature=0
    )
    
    # Helper function to generate context from dataframes
    def get_data_context():
        """Generate a comprehensive summary with schema information for the LLM"""
        context = f"""
You are a financial AI assistant for the UF AIS (Association for Information Systems) organization. You have access to the following financial database:

═══════════════════════════════════════════════════════════════
📋 TABLE 1: COMMITTEES
═══════════════════════════════════════════════════════════════
Purpose: List of all committees and their types
Columns:
  - CommitteeID (int): Primary key, unique identifier
  - Committee_Name (text): Name of the committee (e.g., "Marketing", "Events")
  - Committee_Type (text): Type classification (e.g., "committee", "executive")

Data ({len(df_committees)} committees):
{df_committees[['CommitteeID', 'Committee_Name', 'Committee_Type']].to_string(index=False)}

═══════════════════════════════════════════════════════════════
💰 TABLE 2: TRANSACTIONS
═══════════════════════════════════════════════════════════════
Purpose: All financial transactions (income and expenses)
Columns:
  - transactionid (int): Primary key, unique identifier
  - transaction_date (date): Date when transaction occurred
  - amount (decimal): Dollar amount (POSITIVE = income, NEGATIVE = expense)
  - details (text): Description of the transaction
  - budget_category (int): Foreign key to CommitteeID (which committee this is for)
  - purpose (text): Purpose/category of transaction (e.g., "Membership Dues", "Food")
  - account (text): Payment method - "Venmo" or "Wells Fargo"

Summary Statistics:
  - Total transactions: {len(df_transactions)}
  - Date range: {df_transactions['transaction_date'].min()} to {df_transactions['transaction_date'].max()}
  - Total income (amount > 0): ${df_transactions[df_transactions['amount'] > 0]['amount'].sum():,.2f}
  - Total expenses (amount < 0): ${abs(df_transactions[df_transactions['amount'] < 0]['amount'].sum()):,.2f}
  - Available accounts: {', '.join(df_transactions['account'].dropna().unique())}

Sample transactions:
{df_transactions[['transaction_date', 'amount', 'purpose', 'account']].head(5).to_string(index=False)}

═══════════════════════════════════════════════════════════════
📅 TABLE 3: TERMS/SEMESTERS
═══════════════════════════════════════════════════════════════
Purpose: Academic term definitions with date ranges
Columns:
  - TermID (text): Primary key (e.g., "FA24", "SP25")
  - Semester (text): Human-readable name (e.g., "Fall 2024", "Spring 2025")
  - start_date (date): First day of the semester
  - end_date (date): Last day of the semester

Data ({len(df_terms)} terms):
{df_terms[['TermID', 'Semester', 'start_date', 'end_date']].to_string(index=False)}

═══════════════════════════════════════════════════════════════
💵 TABLE 4: COMMITTEE BUDGETS
═══════════════════════════════════════════════════════════════
Purpose: Budget allocations for each committee per semester
Columns:
  - committeebudgetid (int): Primary key
  - termid (text): Foreign key to Terms.TermID
  - committeeid (int): Foreign key to Committees.CommitteeID
  - budget_amount (decimal): Allocated budget in dollars

Summary:
  - Total budget records: {len(df_budgets)}
  - Total allocated budget: ${df_budgets['budget_amount'].sum():,.2f}

═══════════════════════════════════════════════════════════════
🎯 IMPORTANT QUERY PATTERNS
═══════════════════════════════════════════════════════════════
1. To filter by semester: Use start_date and end_date from Terms table
2. To calculate income: Filter transactions where amount > 0
3. To calculate expenses: Filter transactions where amount < 0
4. To filter by account: Use the 'account' column (values: "Venmo" or "Wells Fargo")
5. To get committee spending: Join transactions.budget_category with committees.CommitteeID

When answering questions:
✓ Always include relevant data that supports your answer
✓ Format currency with $ and commas (e.g., $1,234.56)
✓ Reference committee names, not IDs
✓ Show calculations when doing math
✓ If filtering by semester, mention the date range
✓ If data is insufficient, explain what's missing
"""
        return context
    
    # Helper function to query specific data
    def query_data(question: str) -> str:
        """Query the data based on the question and return relevant data with dates"""
        try:
            # Convert question to lowercase for easier parsing
            q_lower = question.lower()
            
            # Check for semester/term mentions
            semester_match = None
            for term in df_terms['Semester'].values:
                if term.lower() in q_lower:
                    semester_match = term
                    break
            
            # Committee-specific queries
            if "committee" in q_lower or "committees" in q_lower:
                committee_summary = df_committees.to_string(index=False)
                return f"Committee Information:\n{committee_summary}"
            
            # Transaction queries - include date filtering
            if "transaction" in q_lower:
                if semester_match:
                    term_info = df_terms[df_terms['Semester'] == semester_match].iloc[0]
                    filtered_txns = df_transactions[
                        (df_transactions['transaction_date'] >= term_info['start_date']) &
                        (df_transactions['transaction_date'] <= term_info['end_date'])
                    ]
                    return f"Transactions for {semester_match}:\n{filtered_txns[['transaction_date', 'amount', 'details', 'purpose', 'account']].to_string(index=False)}"
                else:
                    recent_transactions = df_transactions.sort_values('transaction_date', ascending=False).head(20)
                    return f"Recent Transactions:\n{recent_transactions[['transaction_date', 'amount', 'details', 'purpose', 'account']].to_string(index=False)}"
            
            # Income queries - WITH FULL DATE DATA for calculations
            if "income" in q_lower or "revenue" in q_lower or "generated" in q_lower or "money" in q_lower:
                income_txns = df_transactions[df_transactions['amount'] > 0].copy()
                
                # Check for account filter (Venmo, Wells Fargo)
                account_filter = None
                if "venmo" in q_lower:
                    account_filter = "Venmo"
                    income_txns = income_txns[income_txns['account'].str.contains('Venmo', case=False, na=False)]
                elif "wells" in q_lower or "wells fargo" in q_lower:
                    account_filter = "Wells Fargo"
                    income_txns = income_txns[income_txns['account'].str.contains('Wells', case=False, na=False)]
                
                if semester_match:
                    term_info = df_terms[df_terms['Semester'] == semester_match].iloc[0]
                    income_txns = income_txns[
                        (income_txns['transaction_date'] >= term_info['start_date']) &
                        (income_txns['transaction_date'] <= term_info['end_date'])
                    ]
                    total_income = income_txns['amount'].sum()
                    account_text = f" from {account_filter}" if account_filter else ""
                    return f"Income transactions{account_text} for {semester_match} ({term_info['start_date']} to {term_info['end_date']}):\n{income_txns[['transaction_date', 'amount', 'account', 'purpose', 'details']].to_string(index=False)}\n\nTotal Income: ${total_income:,.2f}"
                else:
                    # Include date ranges from terms for context
                    terms_context = df_terms[['Semester', 'start_date', 'end_date']].to_string(index=False)
                    account_text = f" from {account_filter}" if account_filter else ""
                    income_summary = income_txns[['transaction_date', 'amount', 'account', 'purpose']].to_string(index=False, max_rows=50)
                    return f"Available Term Dates:\n{terms_context}\n\nAll Income Transactions{account_text}:\n{income_summary}\n\nTotal Income: ${income_txns['amount'].sum():,.2f}"
            
            # Spending/expense queries - WITH DATE DATA
            if "spend" in q_lower or "expense" in q_lower:
                expenses = df_transactions[df_transactions['amount'] < 0].copy()
                expenses['amount'] = expenses['amount'].abs()
                
                if semester_match:
                    term_info = df_terms[df_terms['Semester'] == semester_match].iloc[0]
                    expenses = expenses[
                        (expenses['transaction_date'] >= term_info['start_date']) &
                        (expenses['transaction_date'] <= term_info['end_date'])
                    ]
                    spending_by_committee = expenses.merge(
                        df_committees[['CommitteeID', 'Committee_Name']], 
                        left_on='budget_category', 
                        right_on='CommitteeID'
                    ).groupby('Committee_Name')['amount'].sum().sort_values(ascending=False)
                    return f"Spending by Committee for {semester_match}:\n{spending_by_committee.to_string()}\n\nTotal Spending: ${expenses['amount'].sum():,.2f}"
                else:
                    spending_by_committee = expenses.merge(
                        df_committees[['CommitteeID', 'Committee_Name']], 
                        left_on='budget_category', 
                        right_on='CommitteeID'
                    ).groupby('Committee_Name')['amount'].sum().sort_values(ascending=False)
                    return f"Spending by Committee (all time):\n{spending_by_committee.to_string()}"
            
            # Budget queries
            if "budget" in q_lower:
                budget_summary = df_budgets.merge(
                    df_committees[['CommitteeID', 'Committee_Name']], 
                    left_on='committeeid', 
                    right_on='CommitteeID'
                ).merge(
                    df_terms[['TermID', 'Semester']], 
                    left_on='termid', 
                    right_on='TermID'
                )[['Semester', 'Committee_Name', 'budget_amount']]
                
                if semester_match:
                    budget_summary = budget_summary[budget_summary['Semester'] == semester_match]
                    
                return f"Budget Information:\n{budget_summary.to_string(index=False)}"
            
            # Default: provide term context
            terms_context = df_terms[['Semester', 'start_date', 'end_date']].to_string(index=False)
            return f"Available Terms:\n{terms_context}\n\nI'll analyze the data to answer your question."
            
        except Exception as e:
            return f"Error querying data: {str(e)}"
    
    # Initialize chat history
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []
    
    # Display chat history
    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about AIS finances..."):
        # Add user message to chat history
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing data..."):
                try:
                    # Get relevant data context
                    data_info = query_data(prompt)
                    context = get_data_context()
                    
                    # Create the full prompt
                    full_prompt = f"""{context}

**Relevant Data:**
{data_info}

**User Question:** {prompt}

Please provide a clear, concise answer using the data provided. Format numbers with commas and currency with $."""
                    
                    # Get response from LLM
                    from langchain_core.messages import HumanMessage
                    response = llm.invoke([HumanMessage(content=full_prompt)])
                    answer = response.content
                    
                    st.markdown(answer)
                    
                    # Add assistant response to chat history
                    st.session_state.ai_messages.append({"role": "assistant", "content": answer})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}\n\nTry rephrasing your question or asking something simpler."
                    st.error(error_msg)
                    st.session_state.ai_messages.append({"role": "assistant", "content": error_msg})
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.ai_messages = []
        st.rerun()

except Exception as e:
    st.error(f"❌ Failed to load data or initialize AI: {str(e)}")
    st.info("Please check your Gemini API key and data connections.")

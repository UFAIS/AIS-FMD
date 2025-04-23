import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_committees_df, load_committee_budgets_df, load_transactions_df, load_terms_df
from components import animated_typing_title, apply_nav_title

# Initialize UI
apply_nav_title()
animated_typing_title("UF AIS Financial Management Application")
st.divider()

# 1. Load raw data
df_committees   = load_committees_df()
df_budgets      = load_committee_budgets_df()
df_transactions = load_transactions_df()
df_terms        = load_terms_df()

# 2. Detect and standardize term columns dynamically
def norm_col(c): return c.lower().replace(' ', '_')
col_map = {norm_col(c): c for c in df_terms.columns}
required = ['termid','semester','start_date','end_date']
missing = [r for r in required if r not in col_map]
if missing:
    st.error(f"Term table missing columns: {missing}")
    st.stop()
# Rename to consistent fields
df_terms_std = df_terms.rename(columns={
    col_map['termid']: 'termid',
    col_map['semester']: 'semester',
    col_map['start_date']: 'Start_Date',
    col_map['end_date']: 'End_Date'
})
# Parse dates
df_terms_std['Start_Date'] = pd.to_datetime(df_terms_std['Start_Date'], errors='raise')
df_terms_std['End_Date']   = pd.to_datetime(df_terms_std['End_Date'], errors='raise')
df_transactions['transaction_date'] = pd.to_datetime(df_transactions['transaction_date'], errors='coerce')

# 3. Clean budgets table
df_budgets_clean = (
    df_budgets
    .merge(df_terms_std[['termid','semester']], on='termid', how='left')
    .merge(df_committees[['CommitteeID','Committee_Name','Committee_Type']],
           left_on='committeeid', right_on='CommitteeID', how='left')
    .query("Committee_Type == 'committee'")
    .loc[:, ['semester','committeebudgetid','budget_amount','Committee_Name']]
)

# 4. Helper: find semester for a given date
def get_semester(dt: pd.Timestamp) -> str | None:
    if pd.isna(dt): return None
    mask = (df_terms_std['Start_Date'] <= dt) & (df_terms_std['End_Date'] >= dt)
    sem = df_terms_std.loc[mask, 'semester']
    return sem.iloc[0] if not sem.empty else None

# 5. Prepare committee transactions
df_txn = (
    df_transactions
    .assign(semester=df_transactions['transaction_date'].apply(get_semester))
    .merge(df_committees[['CommitteeID','Committee_Name','Committee_Type']],
           left_on='budget_category', right_on='CommitteeID', how='left')
    .query("Committee_Type == 'committee' and amount < 0")
    .assign(amount=lambda d: d['amount'].abs())
    .loc[:, ['semester','Committee_Name','amount']]
)

# 6. Display Spending vs. Budget
sem = st.selectbox("Which semester to view?", df_terms_std['semester'].dropna().unique())
col1, col2 = st.columns([3,4], border=True)

with col1:
    spend = (
        df_txn.query("semester == @sem")
        .groupby('Committee_Name', as_index=False)['amount'].sum()
        .rename(columns={'amount':'Spent'})
    )
    summary = (
        df_budgets_clean.query("semester == @sem")
        .merge(spend, on='Committee_Name', how='left')
        .fillna({'Spent':0})
        .assign(**{'% Spent': lambda d: d['Spent'] / d['budget_amount'] * 100})
    )
    summary['% Spent'].fillna(0, inplace=True)
    df_disp = summary.rename(columns={'budget_amount':'Budget'})[['Committee_Name','Budget','Spent','% Spent']]
    st.write(f"#### Spending vs Budget ({sem})")
    st.dataframe(df_disp.sort_values('% Spent', ascending=False)
                 .style.format({'Budget':'{:.2f}','Spent':'{:.2f}','% Spent':'{:.2f}%'}),
                 use_container_width=True, hide_index=True)

with col2:
    chart = summary.sort_values('% Spent', ascending=True)
    fig = px.bar(chart,
                 x='% Spent', y='Committee_Name', orientation='h',
                 text=chart['% Spent'].round(1).astype(str)+'%',
                 labels={'% Spent':'% of Budget Spent','Committee_Name':'Committee'},
                 color='% Spent', color_continuous_scale='Blues',
                 custom_data=['Committee_Name','% Spent','Spent'])
    fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>% Spent: %{customdata[1]:.1f}%<br>Spent: $%{customdata[2]:,.2f}<extra></extra>")
    maxv = max(100, chart['% Spent'].max() * 1.05)
    fig.update_layout(xaxis=dict(range=[0, maxv]), margin=dict(l=150,r=20,t=20,b=20),
                      coloraxis_colorbar=dict(title='% Spent'))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 7. Helper: previous semester chronologically
def prev_sem(current: str) -> str | None:
    order = (
        df_terms_std[['semester','Start_Date']]
        .drop_duplicates()
        .sort_values('Start_Date')['semester'].tolist()
    )
    if current in order:
        idx = order.index(current)
        return order[idx-1] if idx>0 else None
    return None

# 8. Income Overview and Non-Committee Expenses
# Income DataFrame
income_df = df_transactions[df_transactions['amount'] > 0].copy()
income_df['Income_Type'] = 'Other'
inc_map = {
    'Dues':['Dues'],
    'Merchandise':['Merch','Head Shot'],
    'Sponsorship/Donation':['Sponsorship / Donation'],
    'Events':['Social Events','Formal','Professional Events','Fundraiser','ISOM Passport'],
    'Refunds':['Reimbursement','Refunded'],
    'Transfers':['Transfers']
}
for cat, kws in inc_map.items():
    for kw in kws:
        income_df.loc[income_df['purpose'].str.contains(kw, case=False, na=False),'Income_Type'] = cat
income_df['semester'] = income_df['transaction_date'].apply(get_semester)
sem_income = income_df[income_df['semester'] == sem]

inc1, inc2 = st.columns([1,1], border=True)
with inc1:
    total_inc = sem_income['amount'].sum()
    prev = prev_sem(sem)
    prev_amt = income_df[income_df['semester']==prev]['amount'].sum() if prev else 0
    delta = total_inc - prev_amt
    st.write('### Income Overview')
    st.metric(label=f'Total Income ({sem})', value=f'${total_inc:,.2f}', border=True)
    st.metric(label=f'Change vs {prev}', value='', delta=f'${delta:+,.2f}', border=True)
    by_type = sem_income.groupby('Income_Type', as_index=False)['amount'].sum()
    fig_inc = px.pie(by_type, values='amount', names='Income_Type', hole=0.4,
                     title=f'{sem} Income Distribution By Type',
                     color_discrete_sequence=px.colors.qualitative.G10)
    fig_inc.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>')
    fig_inc.update_layout(margin=dict(t=35,b=20), title_font_size=20)
    st.plotly_chart(fig_inc, use_container_width=True)

with inc2:
    st.write('### Non-Committee Expenses')
    tmp = df_transactions.copy()
    tmp['semester'] = tmp['transaction_date'].apply(get_semester)
    noncom = tmp[(tmp['amount']<0)&(tmp['semester']==sem)].copy()
    noncom = noncom.merge(df_committees[['CommitteeID','Committee_Type']],
                          left_on='budget_category', right_on='CommitteeID', how='left')
    noncom = noncom[(noncom['Committee_Type']!='committee')|noncom['Committee_Type'].isna()]
    noncom['amount']=noncom['amount'].abs()
    if noncom.empty:
        st.info(f'No non-committee expenses found for {sem}')
    else:
        exp_map={
            'Merchandise':['Merch','Head Shot'],
            'Events':['Social Events','GBM Catering','Formal','Professional Events','Fundraiser','Road Trip','ISOM Passport'],
            'Food & Drink':['Food & Drink'],
            'Travel':['Travel'],
            'Reimbursements':['Reimbursement','Refunded'],
            'Transfers':['Transfers'],
            'Tax & Fees':['Tax'],
            'Miscellaneous':['Misc.']
        }
        noncom['expense_category']='Other'
        for cat, kws in exp_map.items():
            for kw in kws:
                noncom.loc[noncom['purpose'].str.contains(kw, case=False, na=False),'expense_category']=cat
        total_non = noncom['amount'].sum()
        st.metric(label=f'Total Non-Committee Expenses ({sem})', value=f'${total_non:,.2f}', border=True)
        by_cat = noncom.groupby('expense_category', as_index=False)['amount'].sum().sort_values('amount', ascending=False)
        fig_non = px.pie(by_cat, values='amount', names='expense_category', hole=0.4,
                         title=f'{sem} Non-Committee Expense Distribution',
                         color_discrete_sequence=px.colors.qualitative.G10)
        fig_non.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>')
        fig_non.update_layout(margin=dict(t=35,b=20), title_font_size=20)
        st.plotly_chart(fig_non, use_container_width=True)

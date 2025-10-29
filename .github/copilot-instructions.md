## Purpose

Short, actionable guidance for AI coding agents working on the UF AIS Financial Management System.
Focus on the app structure, important developer workflows, conventions to follow, and known risky operations.

## Big picture (what this repo is)
- Single-process Streamlit app (`app.py`) that registers three pages under `views/` (Homepage, Financial Dashboard, Treasury Management).
- Data layer: Supabase (Postgres). Access is centralized in `utils.py` with cached helpers: `get_supabase()`, `load_committees_df()`, `load_transactions_df()`, `load_terms_df()`, and `fetch_term_budget_usage()`.
- UI helpers in `components.py` (animated title + CSS nav injection). Assets (logo) live in `assets/`.

## Key files to read first
- `app.py` — bootstraps Streamlit, auth flows, session-state layout and page registration.
- `utils.py` — all Supabase access, caching decorators (`@st.cache_data`, `@st.cache_resource`), and data-shaping helpers. Critical for data model expectations.
- `views/Financial_Dashboard.py` — main analytics UI and most business logic (semester mapping, budget vs spend, category heuristics).
- `views/Treasury_Management.py` — upload and administration flows. Contains destructive DB operations (see "Dangerous ops").
- `views/Homepage.py` and `components.py` — lightweight UI patterns and shared helpers.

## Data model & naming conventions (must match DB)
- Tables consulted in code: `committees`, `terms`, `committeebudgets`, `transactions`, and `stagingtransactions`.
- Important column names expected by code:
  - committees: `CommitteeID`, `Committee_Name`, `Committee_Type`
  - terms: `TermID`, `Semester`, `start_date`, `end_date`
  - committeebudgets: `committeebudgetid`, `termid`, `committeeid`, `budget_amount`
  - transactions: `transactionid`, `transaction_date`, `amount`, `details`, `budget_category`, `purpose`, `account`
- Date parsing: code converts `transaction_date`, `start_date`, `end_date` via `pd.to_datetime()` and maps transactions into semesters using the `terms` date ranges (see `get_semester` in `Financial_Dashboard.py`).

## Session state and caching conventions
- Session keys used across the app:
  - `st.session_state.user_email` — authenticated user's email
  - `st.session_state.user_specific_data` — dict keyed by `current_user_key` for per-user state
  - `st.session_state.current_user_key` — string like `user_{hash(email)}`
  - `st.session_state.treasury_authenticated` — boolean gate for admin portal
- Cache strategy: use `@st.cache_resource` for long-lived objects (Supabase client) and `@st.cache_data(ttl=300)` for table loads. When code updates data, call `st.cache_data.clear()` and `st.cache_resource.clear()` where appropriate.

## Developer workflow (how to run & debug)
1. Install dependencies: `pip install -r requirements.txt`.
2. Run locally: `streamlit run app.py` (port can be set with `--server.port`).
3. Use the sidebar's "Show Debug Info" checkbox in `Financial_Dashboard` for quick runtime insights (semesters, deltas).
4. After data changes (uploads / budget saves), code calls `st.cache_data.clear()`; if you change a cached function signature, restart Streamlit.

## Integration points & external dependencies
- Supabase: credentials live in Streamlit secrets (`.streamlit/secrets.toml`) and accessed via `st.secrets['supabase']` in `utils.get_supabase()`.
- The Treasury upload flow uses a staging table `stagingtransactions` and attempts to run a SQL transfer via `supabase.rpc('exec_sql', {'sql_query': transfer_query})` as a primary approach; it falls back to a manual Python transfer if RPC returns no data. Changes here may require a service role key.

## Project-specific patterns & gotchas (do not change lightly)
- Uploads are destructive by default: in `views/Treasury_Management.py` the code deletes existing transactions or staging entries before inserting new ones. Always preserve backups and test on a non-production DB before changing behavior.
- Budget mapping in uploads expects the Excel `budget` column to match `Committee_Name`. If you add alternative mapping logic, update both the preview logic (unmapped detection) and the insert path.
- Many UI heuristics for categorizing transactions (purpose → category) live in `views/Financial_Dashboard.py` and `Treasury_Management.py` as hard-coded keyword lists — update cautiously and include unit tests for classification if you change them.
- Navigation registration uses `utils.register_nav_pages(PAGE_DEFS)` which constructs `st.Page` objects from relative paths (e.g., `views/Homepage.py`). Changing path layouts requires updating `PAGE_DEFS` in `app.py`.

## Dangerous operations (double-check PRs that touch these)
- `supabase.table("transactions").delete().neq("transactionid", 0).execute()` — clears transactions (used during upload). Avoid running on production without explicit confirmation.
- `supabase.table("committeebudgets").delete().eq("termid", selected_term).execute()` — replaces budgets for a term.

## Small examples (where to edit for common tasks)
- Add a new dashboard widget: edit `views/Financial_Dashboard.py` — load data via the existing cached `load_data()` helper and rely on `get_semester()` for semester mapping.
- Change Supabase queries: edit `utils.py` so all table-access helpers remain cached and centralized.
- Change the Treasury password check: `views/Treasury_Management.py` reads `st.secrets['treasury']['password']`.

## Security note
- Sensitive credentials should live in `.streamlit/secrets.toml` or the Streamlit Cloud secrets UI. Avoid committing real service keys into the repo. The repo currently shows a `.streamlit/secrets.toml` path in the workspace — treat that as a secret and rotate if it is a real key.

## If you're unsure
- Prefer small, well-scoped PRs. Run locally with a non-production Supabase instance when changing DB migration, upload, or delete logic.
- When editing data load/cache behavior, include a short note in the PR about which caches must be cleared and why.

---
If anything is unclear or you'd like more detail (table DDL, example rows, or sample Excel file formats), tell me which section to expand and I will iterate.

## Supabase DDL
-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.committeebudgets (
  committeebudgetid integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  termid text NOT NULL,
  committeeid integer NOT NULL,
  budget_amount numeric,
  CONSTRAINT committeebudgets_pkey PRIMARY KEY (committeebudgetid),
  CONSTRAINT committeebudgets_committeeid_fkey FOREIGN KEY (committeeid) REFERENCES public.committees(CommitteeID),
  CONSTRAINT committeebudgets_termid_fkey FOREIGN KEY (termid) REFERENCES public.terms(TermID)
);
CREATE TABLE public.committees (
  CommitteeID integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  Committee_Name text NOT NULL UNIQUE,
  Committee_Type text NOT NULL DEFAULT 'committee'::text,
  CONSTRAINT committees_pkey PRIMARY KEY (CommitteeID)
);
CREATE TABLE public.stagingtransactions (
  transactiondate date,
  amount numeric,
  details text,
  budget text,
  purpose text,
  account text
);
CREATE TABLE public.terms (
  TermID text NOT NULL,
  Semester text,
  start_date date,
  end_date date,
  CONSTRAINT terms_pkey PRIMARY KEY (TermID)
);
CREATE TABLE public.transactions (
  transactionid integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  transaction_date date NOT NULL,
  amount numeric NOT NULL,
  details text,
  budget_category integer,
  purpose text,
  account text,
  CONSTRAINT transactions_pkey PRIMARY KEY (transactionid),
  CONSTRAINT transactions_budgetcategory_fkey FOREIGN KEY (budget_category) REFERENCES public.committees(CommitteeID)
);
CREATE TABLE public.uploaded_files (
  id integer NOT NULL DEFAULT nextval('uploaded_files_id_seq'::regclass),
  file_name text NOT NULL UNIQUE,
  uploaded_at timestamp with time zone DEFAULT now(),
  CONSTRAINT uploaded_files_pkey PRIMARY KEY (id)
);
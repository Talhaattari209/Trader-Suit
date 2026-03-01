# Trader-Suit UI — Design Best Practices

This document defines layout, components, accessibility, and patterns for the Streamlit-based Trader-Suit UI so all 8 pages feel consistent and maintainable.

---

## 1. Layout System

### 1.1 Page-level layout

- **Wide layout**: Use `st.set_page_config(layout="wide")` once in the main entry point.
- **Sidebar vs main**: Use config-driven ratios so we can tweak in one place:
  - **Default**: `st.columns([1, 4])` → sidebar 1, main 4 (spec 1:4).
  - **Narrow sidebar** (more main content): `[1, 5]` for Dashboard, No-Code Builder.
  - **Wide sidebar** (more controls): `[1, 3]` for Alpha Idea Lab, Backtester, Execution & Reports.
- **Main area splits**: Use `st.columns([2, 1])` or `[1, 1]` inside main when the spec says “2:1” or “1:1” (e.g. charts + table, file list + preview).

### 1.2 Grid patterns

- **Dashboard**: One row of 4 metric cards → one row of 2 chart columns → one full-width table. Use `st.columns(4)` for metrics, `st.columns(2)` for charts.
- **Forms / wizards**: Prefer vertical flow in main; use `st.tabs` for step-based flows (e.g. No-Code Builder) to avoid overwhelming the user.
- **Lists + detail**: Top = search + filters + table; bottom = detail (2:1 summary | journal or chart). Keep table to ~10–20 rows with pagination or “Load more” if needed.

### 1.3 Spacing and density

- Use `st.divider()` between major sections.
- Limit to **2–4 charts per page** (spec) to avoid clutter; put secondary charts in expanders.
- Aim for **10–20 interactive components per page** (inputs, buttons, tables, charts) so pages stay scannable.

---

## 2. Theming and Visual Hierarchy

### 2.1 Dark theme (default)

- **Background**: `#0d1117` (app container).
- **Surface**: `#161b22` (cards, sidebar).
- **Border**: `#30363d`.
- **Text**: `#e6edf3` (primary), `#8b949e` (muted).
- **Accent**: `#58a6ff` (links, section headers).
- **Semantic**: Success `#3fb950`, Warning `#f59e0b`, Danger `#ef4444`.

All theme values live in `src/dashboard/config.THEME` and are applied once via `components.apply_theme()`.

### 2.2 Section headers

- Use a consistent class (e.g. `.panel-header`) or a small helper that renders a styled section title (uppercase, accent color, border-bottom) so every page uses the same pattern.

### 2.3 Metric cards

- Use `st.metric(label, value, delta)` for KPIs.
- **Color-coding**: Green when value meets target (e.g. Sharpe ≥ 1), red when it does not. Use `components.metric_card()` or the threshold helpers (`metric_sharpe`, `metric_max_dd`, etc.) so logic is centralized.
- Show **deltas** where meaningful (e.g. “+0.2 from last week”) for trend context.

---

## 3. Components and Patterns

### 3.1 Forms and inputs

- **Labels**: Always use clear `label=` on every input; avoid unlabeled controls for accessibility.
- **Defaults**: Prefill from `st.session_state` when available (e.g. date range, selected strategy) so state persists across pages.
- **Validation**: On “Next” or “Submit”, validate required fields and use `st.error` or `st.warning` next to the field or at top of section; avoid silent failure.

### 3.2 Buttons and actions

- Primary action per section: one prominent button (e.g. “Generate Hypothesis”, “Run Monte Carlo Pro”). Use `st.button` with clear label.
- Destructive actions (e.g. “Journal Failure”, “Delete”): use `st.button` and confirm via dialog or second step to avoid accidental clicks.
- Navigation: use sidebar page links (Streamlit multipage) or session state + “Proceed to Builder” so the user doesn’t get lost.

### 3.3 Tables

- Use `st.dataframe` for read-only tabular data; keep columns to a reasonable set (e.g. Timestamp, Event, Status).
- For “select one row”: use `st.dataframe` with `selection_mode="single row"` (Streamlit 1.33+) or a selectbox populated from the table data.
- Paginate or limit to 10–20 rows when the spec says “5 rows” or “20 rows” so the page stays fast.

### 3.4 Charts

- **Library**: Use **Plotly** for all charts (`st.plotly_chart`) for zoom, pan, hover.
- **Consistency**: Reuse the same `layout` defaults (background, font color) from theme so all charts match the dark UI. Set `paper_bgcolor`, `plot_bgcolor`, `font_color` from `config.THEME`.
- **Count**: 2–4 visible charts per page; extra charts in `st.expander`.

### 3.5 Expanders

- Use `st.expander` for “Advanced” options, long journals, system status details, and code snippets. Keeps the main view focused.

### 3.6 Alerts

- `st.info`: informational (e.g. decay warning, agent suggestion).
- `st.warning`: redundancy or non-blocking issue (e.g. “Similar hypothesis exists”).
- `st.error`: failure or blocked action (e.g. decayed strategy, validation failed).
- `st.success`: confirmation (e.g. “File uploaded”, “Scan complete”). Place near the action that triggered it.

---

## 4. State and Navigation

### 4.1 Session state

- **Initialize once** in the main `app.py` via `session_state.init_session_state()`.
- **Keys**: Use the same keys across pages (e.g. `selected_strategy_id`, `date_range_start`, `regime_filters`) so that “Proceed to Builder” or “View Details” carries context to the next page.
- **Read/write**: Prefer helpers in `session_state.py` (e.g. `get_date_range()`, `set_selected_strategy()`) so we don’t scatter raw `st.session_state` access.

### 4.2 Navigation

- Use Streamlit’s **multipage** structure: main script + `pages/` folder. Page names (with optional emoji) become sidebar links.
- Cross-page actions: set session state then use `st.switch_page("pages/4_No_Code_Builder.py")` (Streamlit 1.30+) or tell the user “Go to No-Code Builder” with a link.

---

## 5. Loading and Errors

### 5.1 Loading states

- For slow API calls (Librarian, Monte Carlo, training): use `with st.spinner("Generating hypothesis…")` or `st.status` (Streamlit 1.29+) around the call. Optionally show a progress bar for long runs.
- Avoid full-page reload without feedback; keep at least the sidebar and a message visible.

### 5.2 Error handling

- **API unreachable**: Catch requests errors, show `st.error("Cannot reach API. Check TRADER_API_URL and try again.")` and optional retry button.
- **Empty data**: Use `st.info("No strategies yet. Create one in Alpha Idea Lab.")` instead of empty tables or charts.
- **Validation failure**: Show which field failed and what to fix; don’t only log to console.

---

## 6. Accessibility and Usability

### 6.1 Labels and focus

- Every input has an associated label (Streamlit does this by default with `label=`).
- Avoid “Click here”; use action-oriented text (“Generate Hypothesis”, “Run Monte Carlo Pro”).

### 6.2 Contrast

- Rely on the defined palette (text on background, muted on surface) so contrast meets WCAG AA where possible. Accent and semantic colors are used for emphasis, not long paragraphs.

### 6.3 Responsiveness

- Streamlit’s default behavior adapts to width. Use `use_container_width=True` on charts so they scale. Test with a narrow window to ensure sidebar and columns don’t break.

---

## 7. File and Module Usage

| Concern            | Use |
|--------------------|-----|
| Layout ratios      | `config.LAYOUT_*` |
| Theme colors       | `config.THEME` |
| Metric thresholds  | `config.SHARPE_TARGET_MIN`, etc. |
| Session state      | `session_state.init_session_state()`, `get_date_range()`, `set_selected_strategy()` |
| Global CSS         | `components.apply_theme()` |
| Metric cards       | `components.metric_card`, `metric_sharpe`, `metric_max_dd`, etc. |
| Sidebar/main split | `components.layout_sidebar_main(ratio)` or `st.columns([1,4])` |

---

## 8. Checklist for New Pages

When adding or refactoring a page:

1. Use the correct sidebar:main ratio from the spec (1:3, 1:4, or 1:5).
2. Apply theme via the shared `apply_theme()` (no page-specific CSS unless necessary).
3. Use session state for cross-page values (strategy, date range, filters).
4. Use Plotly for charts with theme-matched layout.
5. Use shared metric helpers for Sharpe, Sortino, DD, Hit Rate, e-ratio.
6. Add loading (spinner/status) for any slow call.
7. Handle API errors and empty data with clear messages.
8. Keep component count in the 10–20 range and charts in the 2–4 range.

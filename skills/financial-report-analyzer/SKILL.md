---
name: financial-report-analyzer
description: This skill should be used when the user asks to "analyze a financial report", "analyze this annual report", "analyze this quarterly report", "分析财报", "分析年报", "分析季报", "financial report analysis", or provides a path to a PDF/text file that appears to be a financial report. Provides systematic financial report analysis including data extraction, ratio calculation, chart generation, and professional HTML report output.
version: 2.1.0
python-env: "C:\\anaconda\\envs\\financial"
allowed-tools: [Bash, Read, Write, Glob, Grep]
---

# Financial Report Analyzer

You are a professional financial analysis tool. Follow this workflow systematically when analyzing financial reports (annual reports, quarterly reports).

## Runtime Environment

- **Python**: Use the `financial` conda environment at `C:\anaconda\envs\financial`
- **Invoke scripts with**: `"C:/anaconda/envs/financial/python.exe" <script_path> [args]`
- **Dependencies (pre-installed)**: pdfplumber, matplotlib

## Workflow

### Step 1: Data Extraction

Run the extraction script to pull core financial data from the report file:

```bash
"C:/anaconda/envs/financial/python.exe" "${CLAUDE_PLUGIN_ROOT}/scripts/extract_financials.py" '{"file_path": "<path to report file>"}'
```

This supports PDF (via pdfplumber) and plain text files. The output is JSON with keys: `revenue`, `net_profit`, `total_assets`, `total_liabilities`, `equity`, `operating_cash_flow`, `cost_of_sales`, `company_name`, `report_year`, plus expanded fields: `segment_data`, `operating_kpis`, expense breakdown, cash flow details, and prior-year comparatives.

Record this output as `raw_data`.

**IMPORTANT**: After extraction, cross-check the extracted numbers against the original report text. If the extraction script failed to capture key fields (especially for HK-listed companies with different terminology), **manually supplement** the `raw_data` JSON with values you read from the PDF. Pay special attention to:
- Segment data (分部收入/成本/毛利率)
- Expense breakdown (销售/管理/研发费用)
- Balance sheet details (流动资产/负债, 应收, 存货)
- Cash flow details (投资/筹资活动现金流)
- Prior year comparatives (上期数据)

### Step 2: Financial Ratio Calculation

Pass the augmented `raw_data` JSON to the ratio calculation script:

```bash
"C:/anaconda/envs/financial/python.exe" "${CLAUDE_PLUGIN_ROOT}/scripts/calculate_ratios.py" '<raw_data_json>'
```

This computes 60+ template placeholder values including:
- Formatted amounts and YoY growth rates
- Profitability ratios (gross margin, net margin, operating margin, ROE)
- Solvency indicators (asset-liability ratio, current ratio, quick ratio)
- Efficiency metrics (AR turnover, inventory turnover, total asset turnover)
- Cash flow quality (net cash ratio, free cash flow, funding gap)
- Auto-generated HTML blocks for segment breakdown, expense table, solvency table, etc.

Record output as `ratio_data`.

### Step 3: Chart Generation

Generate up to 6 visualization charts:

```bash
"C:/anaconda/envs/financial/python.exe" "${CLAUDE_PLUGIN_ROOT}/scripts/generate_charts.py" --output-dir "<report_output_directory>" '<raw_data_json>'
```

Charts produced (in the specified `--output-dir`, or `${CLAUDE_PLUGIN_ROOT}/scripts/` as fallback):
- `financial_overview.png` — bar chart of key metrics (always generated)
- `profitability.png` — horizontal bar chart of profitability ratios (always generated)
- `asset_structure.png` — donut chart of asset structure (always generated)
- `segment_margins.png` — dual-axis chart of segment revenue & margins (conditional: requires segment_data)
- `cash_flow_structure.png` — grouped bar chart of cash flow types (conditional: requires cash flow data)
- `efficiency_metrics.png` — horizontal bar chart of turnover ratios (conditional: requires efficiency data)

### Step 4: Deep Analysis Writing

Reference the analysis framework at `${CLAUDE_PLUGIN_ROOT}/references/analysis_framework.md` and financial metrics definitions at `${CLAUDE_PLUGIN_ROOT}/references/financial_metrics.md`.

Write the following analysis segments:

**Core Analysis (7 segments)**:
1. **PROFITABILITY_ANALYSIS**: Analyze gross margin trends by segment, expense control (cost ratios vs revenue growth), non-recurring P&L impact. Connect to business context. Include segment-level profitability gradient analysis.
2. **SOLVENCY_ANALYSIS**: Analyze debt-to-asset ratio, current ratio, interest-bearing debt scale, and financial safety. Compare against industry health benchmarks.
3. **EFFICIENCY_ANALYSIS**: Analyze AR turnover, inventory turnover, total asset turnover. Explain changes in terms of business operations (e.g., seasonal stocking, customer mix changes).
4. **CASHFLOW_ANALYSIS**: Compare net profit vs operating cash flow (cash-to-profit ratio), assess profit quality, analyze investing/financing cash flow structure and its alignment with corporate strategy.
5. **ADVANTAGES_LIST**: 3-4 core strengths as HTML `<li>advantage</li>` elements.
6. **RISKS_LIST**: 3-4 main risks as HTML `<li>risk</li>` elements.
7. **OVERALL_ASSESSMENT**: Comprehensive evaluation with forward-looking outlook.

**BP Probe Sections (3 segments)** — Write as `.bp-callout` HTML divs:
8. **BP_PROBE_PROFITABILITY**: Based on actual data anomalies, ask probing questions. E.g., if gross margin declined: "是成本推动还是价格竞争？改善路径？追踪指标建议." If expenses grew faster than revenue: "获客成本是否上升？转化率能否同步提升？"
9. **BP_PROBE_SOLVENCY**: Based on balance sheet patterns. E.g., if inventory grew significantly: "存货积压是否合理？需关注存货跌价风险." If capex is high: "投资回报周期和效率如何？"
10. **BP_PROBE_CASHFLOW**: Based on cash flow patterns. E.g., if net cash ratio < 1.0: "利润含金量评估，应收/存货质量分析." If investing CF is very negative: "投资节奏是否与收入增长匹配？"

**BP Decision Support Sections (3 segments)**:
11. **SEGMENT_STRATEGY**: For each business segment, provide strategic recommendations based on its BCG quadrant positioning. Include specific tracking KPIs using `<span class="kpi-badge">KPI名称</span>` format.
12. **RED_LINE_MANAGEMENT**: Define operational red-line thresholds with trigger conditions and recommended actions. Format as `.red-line` HTML divs for critical items.
13. **CAPITAL_PLANNING**: Outline short-term (Q), medium-term (FY), and long-term (1-3yr) capital planning roadmap with concrete targets.

**Formatting guidelines**:
- BP probes MUST use: `<div class="bp-callout"><strong>BP追问：</strong>... <strong>建议追踪：</strong>...</div>`
- Red-line alerts MUST use: `<div class="red-line"><strong>红线预警：</strong>...</div>`
- KPI badges: `<span class="kpi-badge">追踪KPI</span>`, `<span class="kpi-badge ok">达标KPI</span>`, `<span class="kpi-badge warn">预警KPI</span>`
- BCG strategy items: `<li><strong>业务名——"象限"策略：</strong>具体建议。追踪KPI：<span class="kpi-badge">KPI1</span> <span class="kpi-badge ok">KPI2</span></li>`

**After writing all analysis segments, save them to `analysis_sections.json`** in the report output directory. This file is required for the archival step (Step 7).

### Step 5: Report Rendering

Read the HTML template:

```
${CLAUDE_PLUGIN_ROOT}/templates/report_template.html
```

Fill ALL `{{PLACEHOLDER}}` tags in the template:
- **Data metrics** (from `ratio_data`): `{{COMPANY_NAME}}`, `{{YEAR}}`, `{{DATE}}`, `{{REVENUE}}`, `{{NET_PROFIT}}`, `{{GROSS_MARGIN}}`, `{{ROE}}`, `{{OPERATING_MARGIN}}`, `{{NET_MARGIN}}`, `{{OPERATING_CASH_FLOW}}`, and all `_GROWTH`, `_CLASS`, `_CHANGE`, `_INDUSTRY_AVG` variants
- **Chart paths** (use absolute `file:///` paths): `{{CHART_FINANCIAL_OVERVIEW}}`, `{{CHART_SEGMENT_MARGINS}}`, `{{CHART_PROFITABILITY}}`, `{{CHART_EFFICIENCY}}`, `{{CHART_CASH_FLOW}}`, `{{CHART_ASSET_STRUCTURE}}`
- **HTML blocks** (from `ratio_data`): `{{SECTION_SEGMENT_BREAKDOWN}}`, `{{SECTION_OPERATIONAL_KPIS}}`, `{{EXPENSE_TABLE}}`, `{{SOLVENCY_TABLE}}`, `{{EFFICIENCY_TABLE}}`, `{{CASHFLOW_TABLE}}`, `{{CASHFLOW_QUALITY_TABLE}}`, `{{BCG_MATRIX_TABLE}}`
- **Analysis text** (from Step 4): `{{PROFITABILITY_ANALYSIS}}`, `{{SOLVENCY_ANALYSIS}}`, `{{EFFICIENCY_ANALYSIS}}`, `{{CASHFLOW_ANALYSIS}}`, `{{BP_PROBE_PROFITABILITY}}`, `{{BP_PROBE_SOLVENCY}}`, `{{BP_PROBE_CASHFLOW}}`, `{{SEGMENT_STRATEGY}}`, `{{RED_LINE_MANAGEMENT}}`, `{{CAPITAL_PLANNING}}`, `{{ADVANTAGES_LIST}}`, `{{RISKS_LIST}}`, `{{OVERALL_ASSESSMENT}}`

IMPORTANT: If any data field is missing, fill with "N/A" — NEVER delete template rows or columns.
For optional sections (segments, operational KPIs), if the `ratio_data` provides an empty string, keep it empty in the final HTML.

Save the filled HTML as `<company_name>_<year>_财报分析报告.html` in the same directory as the input report file, or at a user-specified path.

### Step 6: Completion

Output a brief summary with:
- The generated report file path
- 2-3 key findings from the analysis
- Any data quality concerns (missing fields, unusual values)
- The archive location (after Step 7)

### Step 7: Data Archival (NEW in v2.1)

Archive all analysis outputs to the standardized data directory for future time-series and industry comparison analysis:

```bash
"C:/anaconda/envs/financial/python.exe" "${CLAUDE_PLUGIN_ROOT}/scripts/archive_data.py" \
  --company "<company_name>" \
  --period "<FY2025 or FY2025Q1>" \
  --raw-data "<path_to_raw_data.json>" \
  --ratio-data "<path_to_ratio_data.json>" \
  --analysis "<path_to_analysis_sections.json>" \
  --charts <list_of_chart_png_paths> \
  --report "<path_to_html_report>" \
  --base-dir "C:/financial/data" \
  --source-file "<original_pdf_filename>" \
  --report-type "<annual|quarterly|semi-annual>"
```

The archival script:
1. Creates the standardized directory: `C:/financial/data/{company}/{period}/`
2. Copies all files with standardized naming (`{company}_{period}_{filename}`)
3. Updates the master index at `C:/financial/data/manifest.json`
4. Prints a summary JSON confirming archival

Report the archive path in the completion summary.

## Important Rules

- All scripts must be invoked via the `financial` conda environment Python (`C:/anaconda/envs/financial/python.exe`)
- The `financial` conda environment has all dependencies pre-installed (pdfplumber, matplotlib). If scripts fail with import errors, verify the environment at `C:\anaconda\envs\financial` is intact.
- Always cross-check extracted numbers against the original report when possible
- When the extraction script misses key fields, manually read the PDF text and supplement the `raw_data` JSON
- Pay attention to non-recurring profit/loss to assess true core business profitability
- If comparing multiple years, identify trends rather than just reporting point values
- The HTML template structure MUST be preserved — do not delete sections or modify table columns
- Chart images must use absolute file paths (file:/// protocol) for display in the HTML report
- For Chinese font support in charts, the script auto-detects available CJK fonts
- **BP analysis must be data-driven**: every BP probe should reference specific numbers from the report
- **Red-line thresholds must be concrete**: give specific trigger values, not vague descriptions

# Financial Report Analyzer

> Claude Code Skill for automated financial report analysis of listed companies.

A Claude Code plugin that systematically analyzes financial reports (annual/quarterly) through data extraction, ratio calculation, chart generation, and professional HTML report output with BP-perspective decision support.

## Features

- **Automated Data Extraction** — Parses PDF/text financial reports, extracts revenue, profit, assets, liabilities, segment data, expense breakdowns, cash flow details, and prior-year comparatives
- **60+ Financial Ratios** — Computes profitability (gross margin, net margin, ROE), solvency (debt ratio, current ratio), efficiency (turnover ratios), and cash flow quality metrics
- **6 Visualization Charts** — Financial overview, profitability, asset structure, segment margins, cash flow structure, efficiency metrics (conditional generation)
- **13 Analysis Segments** — Including BP (Business Partner) probing questions, BCG matrix positioning, red-line management, and capital planning
- **Standardized Data Archival** (v2.1) — Automatic archival to structured directories with a manifest.json master index for time-series and cross-company analysis

## Requirements

- Python 3.12+ (conda environment recommended)
- `pdfplumber` — PDF text extraction
- `matplotlib` — Chart generation

```bash
pip install pdfplumber matplotlib
```

## Installation

This is a Claude Code plugin. Install by placing it in the Claude Code plugins directory:

```
~/.claude/plugins/marketplaces/local/plugins/financial-report-analyzer/
```

Or clone directly:

```bash
cd ~/.claude/plugins/marketplaces/local/plugins/
git clone https://github.com/geogeoman/financial-report-analyzer.git
```

## Usage

### Trigger in Claude Code

The skill activates automatically when you ask Claude Code to:

- "Analyze this financial report: /path/to/report.pdf"
- "分析这份财报: /path/to/report.pdf"
- "Analyze this annual report"
- "分析年报"

### Manual Script Invocation

```bash
# Step 1: Extract financial data
python scripts/extract_financials.py '{"file_path": "/path/to/report.pdf"}'

# Step 2: Calculate ratios
python scripts/calculate_ratios.py '<raw_data_json>'

# Step 3: Generate charts
python scripts/generate_charts.py --output-dir "/output/dir" '<raw_data_json>'

# Step 7: Archive results
python scripts/archive_data.py \
  --company "Meituan" --period "FY2025" \
  --raw-data "raw_data.json" --ratio-data "ratio_data.json" \
  --analysis "analysis_sections.json" \
  --charts chart1.png chart2.png \
  --report "report.html" \
  --base-dir "C:/financial/data"
```

## Workflow (7 Steps)

```
Step 1: Data Extraction        → raw_data.json
Step 2: Ratio Calculation       → ratio_data.json (60+ placeholders)
Step 3: Chart Generation        → 6 PNG charts
Step 4: Deep Analysis Writing   → analysis_sections.json (13 segments)
Step 5: Report Rendering        → HTML report with filled template
Step 6: Completion Summary      → Key findings + data quality notes
Step 7: Data Archival           → Standardized directory + manifest.json
```

## Output Structure

### Per-Analysis Output

```
{output_dir}/
├── raw_data.json                  # Extracted financial data
├── ratio_data.json                # Computed ratios & HTML table fragments
├── analysis_sections.json         # AI-written analysis (13 segments)
├── financial_overview.png
├── profitability.png
├── asset_structure.png
├── segment_margins.png            # (conditional)
├── cash_flow_structure.png        # (conditional)
├── efficiency_metrics.png         # (conditional)
└── {company}_{year}_财报分析报告.html
```

### Archive Structure (v2.1)

```
C:/financial/data/
├── manifest.json                  # Master index
├── Meituan/
│   └── FY2025/
│       ├── Meituan_FY2025_raw_data.json
│       ├── Meituan_FY2025_ratio_data.json
│       ├── Meituan_FY2025_analysis_sections.json
│       ├── Meituan_FY2025_financial_overview.png
│       ├── Meituan_FY2025_profitability.png
│       ├── Meituan_FY2025_asset_structure.png
│       ├── Meituan_FY2025_segment_margins.png
│       ├── Meituan_FY2025_cash_flow_structure.png
│       ├── Meituan_FY2025_efficiency_metrics.png
│       └── Meituan_FY2025_report.html
└── Tencent/
    └── FY2026Q1/
        └── ...
```

### manifest.json

The master index enables cross-company and cross-period analysis:

```json
{
  "version": "2.1",
  "last_updated": "2026-05-18T23:33:12",
  "companies": {
    "Meituan": {
      "display_name": "美团(Meituan)",
      "analyses": {
        "FY2025": {
          "archived_at": "2026-05-18T23:33:12",
          "source_file": "Meituan 2025.pdf",
          "report_type": "annual",
          "files": { ... },
          "key_metrics": {
            "revenue": 364854746.0,
            "net_profit": -23354194.0,
            "gross_margin": 0.3043,
            "currency": "千元人民币"
          }
        }
      }
    }
  }
}
```

## Report Structure

The generated HTML report contains 4 chapters:

1. **Core Business Data Overview** — Overall metrics, segment revenue & growth, operational KPIs
2. **Three Statements Deep Analysis** — Profitability, solvency, efficiency, cash flow analysis with BP probing questions
3. **BP Decision Support** — BCG matrix positioning, segment strategy, red-line management, capital planning
4. **Conclusions** — Core advantages, key risks, overall assessment

## Project Structure

```
financial-report-analyzer/
├── .claude-plugin/
│   └── plugin.json                # Plugin metadata
├── SKILL.md                       # Top-level skill description (Chinese)
├── README.md                      # This file
├── skills/
│   └── financial-report-analyzer/
│       └── SKILL.md               # Skill definition (trigger rules + 7-step workflow)
├── scripts/
│   ├── extract_financials.py      # Step 1: PDF/text data extraction
│   ├── calculate_ratios.py        # Step 2: 60+ financial ratio calculation
│   ├── generate_charts.py         # Step 3: Chart generation (up to 6)
│   └── archive_data.py            # Step 7: Standardized data archival
├── templates/
│   ├── report_template.html       # HTML report template with CSS
│   └── report_template.md         # Markdown template (legacy)
└── references/
    ├── analysis_framework.md      # Analysis framework reference
    └── financial_metrics.md       # Financial metrics definitions
```

## Configuration

### Python Environment

By default, the skill expects Python at `C:\anaconda\envs\financial\python.exe`. To use a different environment, update the `python-env` field in `skills/financial-report-analyzer/SKILL.md`:

```yaml
python-env: "path/to/your/python"
```

### Archive Directory

Default archive base directory is `C:/financial/data/`. Override with `--base-dir` when running `archive_data.py`.

## Changelog

### v2.1.0 (Current)

- **Standardized Data Archival** — Automatic archival to `C:/financial/data/{company}/{period}/` with standardized naming
- **Master Index** — `manifest.json` for cross-company, cross-period time-series and industry comparison
- **Python Environment** — Unified conda environment specification
- **Chart Output Control** — `--output-dir` flag for `generate_charts.py`
- **New Script** — `archive_data.py` for data archival and manifest management
- **Version Alignment** — Fixed version inconsistency between plugin.json and SKILL.md

### v2.0.0

- Segment revenue analysis with margin charts
- Core operational KPIs
- Expense structure, solvency, efficiency, and cash flow quality tables
- BP-perspective decision support (BCG matrix, red-line management, capital planning)
- BP probing callouts (`.bp-callout` / `.red-line` / `.kpi-badge` components)
- Charts expanded from 3 to 6
- Ratio calculation expanded from ~20 to 60+ placeholders

### v1.0.0

- Initial release with basic financial report extraction and analysis

## License

MIT

## Author

Financial Analysis Team

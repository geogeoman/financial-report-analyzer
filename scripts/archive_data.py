"""
archive_data.py — v2.1 标准化数据归档工具

将财报分析的所有产出（raw_data、ratio_data、analysis_sections、charts、report）
归档至统一目录结构，并维护 manifest.json 主索引，支持跨公司、跨期间的时间序列
和行业对比分析。

Usage:
    python archive_data.py \
        --company "美团(Meituan)" \
        --period "FY2025" \
        --raw-data "C:/path/raw_data.json" \
        --ratio-data "C:/path/ratio_data.json" \
        --analysis "C:/path/analysis_sections.json" \
        --charts "C:/path/chart1.png" "C:/path/chart2.png" \
        --report "C:/path/report.html" \
        --base-dir "C:/financial/data" \
        --stock-code "03690.HK" \
        --report-type annual \
        --source-file "Meituan 2025.pdf"
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Known company name → directory code mapping
# ---------------------------------------------------------------------------
KNOWN_COMPANIES = {
    "美团": "Meituan",
    "阿里巴巴": "Alibaba",
    "腾讯": "Tencent",
    "小米": "Xiaomi",
    "华特达因": "HuateDaiyin",
    "比亚迪": "BYD",
    "京东": "JD",
    "百度": "Baidu",
    "网易": "NetEase",
    "拼多多": "Pinduoduo",
    "快手": "Kuaishou",
    "理想汽车": "LiAuto",
    "蔚来": "NIO",
    "小鹏汽车": "XPeng",
}

# Chart type keywords → canonical names
CHART_TYPES = {
    "financial_overview": "financial_overview",
    "profitability": "profitability",
    "asset_structure": "asset_structure",
    "segment_margins": "segment_margins",
    "cash_flow_structure": "cash_flow_structure",
    "efficiency_metrics": "efficiency_metrics",
}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------
def derive_company_code(company_name: str) -> str:
    """Derive a directory-safe company code from a display name.

    Strategy:
    1. Check known mapping (substring match)
    2. Extract parenthesized English name: "美团(Meituan)" → "Meituan"
    3. Extract Chinese characters and look up
    4. Fallback: replace spaces with underscores
    """
    if not company_name:
        return "Unknown"

    # 1. Known mapping (check if any key is a substring)
    for cn, code in KNOWN_COMPANIES.items():
        if cn in company_name:
            return code

    # 2. Parenthesized English name
    m = re.search(r"\(([^)]+)\)", company_name)
    if m:
        return m.group(1).strip().replace(" ", "_")

    # 3. Chinese characters → lookup
    cn_chars = re.findall(r"[一-鿿]+", company_name)
    for segment in cn_chars:
        if segment in KNOWN_COMPANIES:
            return KNOWN_COMPANIES[segment]

    # 4. Fallback
    return re.sub(r"[^\w\-]", "_", company_name.strip())


def chart_type_from_filename(filename: str, company_code: str, period: str) -> str:
    """Map a source chart filename to a standardized archive name.

    Input: "financial_overview.png" → Output: "Meituan_FY2025_financial_overview.png"
    """
    stem = os.path.splitext(os.path.basename(filename))[0].lower()

    # Strip company name prefix if present (e.g., "Meituan_FY2025_financial_overview")
    for ct in CHART_TYPES:
        if ct in stem:
            return f"{company_code}_{period}_{ct}.png"

    # Unknown chart type — use stem as-is
    return f"{company_code}_{period}_{stem}.png"


def extract_key_metrics(raw_data_path: str) -> dict:
    """Read raw_data.json and extract key metrics for manifest indexing."""
    try:
        with open(raw_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    metrics = {}

    # Revenue
    rev = data.get("revenue")
    if rev is not None:
        try:
            metrics["revenue"] = float(rev)
        except (ValueError, TypeError):
            pass

    # Net profit
    np_ = data.get("net_profit")
    if np_ is not None:
        try:
            metrics["net_profit"] = float(np_)
        except (ValueError, TypeError):
            pass

    # Gross margin (computed)
    if rev and data.get("cost_of_sales"):
        try:
            rev_f = float(rev)
            cost_f = float(data["cost_of_sales"])
            if rev_f != 0:
                metrics["gross_margin"] = round((rev_f - cost_f) / rev_f, 4)
        except (ValueError, TypeError):
            pass

    # Currency
    metrics["currency"] = data.get("currency", "N/A")

    return metrics


def update_manifest(
    base_dir: str,
    company_code: str,
    company_name: str,
    period: str,
    files_dict: dict,
    key_metrics: dict,
    stock_code: str = "",
    report_type: str = "annual",
    source_file: str = "",
):
    """Create or update manifest.json with a new analysis entry."""
    manifest_path = os.path.join(base_dir, "manifest.json")

    # Read existing or create skeleton
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, IOError):
            manifest = {}
    else:
        manifest = {}

    # Ensure structure
    manifest.setdefault("version", "2.1")
    manifest["last_updated"] = datetime.now().isoformat(timespec="seconds")
    manifest.setdefault("companies", {})

    # Company entry
    company = manifest["companies"].setdefault(company_code, {})
    company["display_name"] = company_name
    if stock_code:
        company["stock_code"] = stock_code
    company.setdefault("analyses", {})

    # Analysis entry
    analysis = company["analyses"].setdefault(period, {})
    analysis["archived_at"] = datetime.now().isoformat(timespec="seconds")
    if source_file:
        analysis["source_file"] = source_file
    analysis["report_type"] = report_type
    analysis["files"] = files_dict
    if key_metrics:
        analysis["key_metrics"] = key_metrics

    # Write
    os.makedirs(base_dir, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest_path


# ---------------------------------------------------------------------------
# Main archival logic
# ---------------------------------------------------------------------------
def archive_files(args) -> dict:
    """Core archival: copy files, rename charts, update manifest."""
    company_code = derive_company_code(args.company)
    period = args.period

    # Target directory
    target_dir = os.path.join(args.base_dir, company_code, period)
    os.makedirs(target_dir, exist_ok=True)

    files_dict = {}
    warnings = []

    # --- Copy standard files ---
    file_map = {
        "raw_data": args.raw_data,
        "ratio_data": args.ratio_data,
        "analysis": args.analysis,
        "report": args.report,
    }

    for key, src_path in file_map.items():
        if not src_path:
            continue
        src_path = os.path.normpath(src_path)
        if not os.path.exists(src_path):
            warnings.append(f"File not found, skipped: {src_path}")
            continue

        orig_name = os.path.basename(src_path)
        dest_name = f"{company_code}_{period}_{orig_name}"
        dest_path = os.path.join(target_dir, dest_name)
        shutil.copy2(src_path, dest_path)
        files_dict[key] = dest_name

    # --- Copy and rename charts ---
    chart_names = []
    if args.charts:
        for chart_path in args.charts:
            chart_path = os.path.normpath(chart_path)
            if not os.path.exists(chart_path):
                warnings.append(f"Chart not found, skipped: {chart_path}")
                continue

            dest_name = chart_type_from_filename(chart_path, company_code, period)
            dest_path = os.path.join(target_dir, dest_name)
            shutil.copy2(chart_path, dest_path)
            chart_names.append(dest_name)

    if chart_names:
        files_dict["charts"] = chart_names

    # --- Extract key metrics from raw_data ---
    key_metrics = {}
    if args.raw_data and os.path.exists(args.raw_data):
        key_metrics = extract_key_metrics(args.raw_data)

    # --- Update manifest ---
    manifest_path = update_manifest(
        base_dir=args.base_dir,
        company_code=company_code,
        company_name=args.company,
        period=period,
        files_dict=files_dict,
        key_metrics=key_metrics,
        stock_code=args.stock_code or "",
        report_type=args.report_type,
        source_file=args.source_file or "",
    )

    # --- Build summary ---
    summary = {
        "status": "success",
        "company_code": company_code,
        "period": period,
        "archive_dir": target_dir,
        "manifest_path": manifest_path,
        "files_archived": len(files_dict) + len(chart_names),
        "files": files_dict,
    }
    if warnings:
        summary["warnings"] = warnings

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Archive financial report analysis outputs to a standardized directory structure."
    )
    parser.add_argument("--company", required=True, help='Company display name, e.g. "美团(Meituan)"')
    parser.add_argument("--period", required=True, help='Reporting period, e.g. "FY2025", "FY2025Q1"')
    parser.add_argument("--raw-data", help="Path to raw_data.json")
    parser.add_argument("--ratio-data", help="Path to ratio_data.json")
    parser.add_argument("--analysis", help="Path to analysis_sections.json")
    parser.add_argument("--charts", nargs="*", help="Paths to chart PNG files")
    parser.add_argument("--report", help="Path to final HTML report")
    parser.add_argument("--base-dir", default="C:/financial/data", help="Base archive directory")
    parser.add_argument("--stock-code", default="", help='Stock code, e.g. "03690.HK"')
    parser.add_argument("--report-type", default="annual", choices=["annual", "quarterly", "semi-annual"],
                        help="Type of report")
    parser.add_argument("--source-file", default="", help="Original PDF filename")
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.raw_data:
        print(json.dumps({"error": "--raw-data is required"}, ensure_ascii=False))
        sys.exit(1)

    try:
        summary = archive_files(args)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

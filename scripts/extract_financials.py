import re
import json
import sys
import os


def read_file_content(file_path):
    """Read content from a file, supporting both text and PDF formats."""
    _, ext = os.path.splitext(file_path.lower())

    if ext == ".pdf":
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            raise RuntimeError(
                "pdfplumber is required to read PDF files. "
                "Install it with: pip install pdfplumber"
            )
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


def _first_number(text, patterns):
    """Try each pattern on *text*, return the first numeric match (float).

    Returns ``None`` when no pattern matches.
    """
    for regex in patterns:
        match = re.search(regex, text)
        if match:
            val_str = match.group(1).replace(",", "").replace(" ", "")
            try:
                return float(val_str)
            except ValueError:
                continue
    return None


def _first_number_multi(text, pattern, group_idx=1):
    """Try a single multi-group pattern, returning a tuple of floats.

    Returns ``None`` when no match.
    """
    match = re.search(pattern, text)
    if match:
        try:
            vals = []
            for i in group_idx if isinstance(group_idx, (list, tuple)) else [group_idx]:
                val_str = match.group(i).replace(",", "").replace(" ", "")
                vals.append(float(val_str))
            return tuple(vals)
        except (ValueError, IndexError):
            return None
    return None


def _find_section(text, start_pattern, end_pattern=None, max_lines=200):
    """Find a section of text between *start_pattern* and *end_pattern*.

    Returns the matched text slice or empty string.
    """
    m = re.search(start_pattern, text)
    if not m:
        return ""
    start = m.start()
    if end_pattern:
        e = re.search(end_pattern, text[start:])
        if e:
            return text[start:start + e.end()]
    lines = text[start:].split("\n")
    return "\n".join(lines[:max_lines])


def extract_from_text(text):
    """Extract key financial data from text using regex.

    Scans Chinese / HK-listed financial reports for common accounting line
    items and returns the first numeric match found for each metric.
    """
    data = {
        "company_name": None,
        "report_year": None,
        "report_date": None,
        "revenue": None,
        "net_profit": None,
        "total_assets": None,
        "total_liabilities": None,
        "equity": None,
        "operating_cash_flow": None,
        "cost_of_sales": None,
        # --- NEW fields ---
        "operating_profit": None,
        "selling_expenses": None,
        "admin_expenses": None,
        "rd_expenses": None,
        "investing_cash_flow": None,
        "financing_cash_flow": None,
        "capital_expenditure": None,
        "current_assets": None,
        "current_liabilities": None,
        "trade_receivables": None,
        "inventory": None,
        # Previous year counterparts
        "prev_revenue": None,
        "prev_cost_of_sales": None,
        "prev_net_profit": None,
        "prev_total_assets": None,
        "prev_total_liabilities": None,
        "prev_equity": None,
        "prev_operating_cash_flow": None,
        "prev_operating_profit": None,
        "prev_selling_expenses": None,
        "prev_admin_expenses": None,
        "prev_rd_expenses": None,
        "prev_investing_cash_flow": None,
        "prev_financing_cash_flow": None,
        "prev_current_assets": None,
        "prev_current_liabilities": None,
        "prev_trade_receivables": None,
        "prev_inventory": None,
        # Segment data & operational KPIs
        "segment_data": None,
        "operational_kpis": None,
    }

    # ── Extract basic info: company name, year, date ──────────────
    company_patterns = [
        r"公司名称[：:\s]*([一-龥]{2,}(?:股份有限公司|有限责任公司|有限公司|集团|公司))",
        r"([一-龥]{2,}(?:股份有限公司|有限责任公司|有限公司))\s*\d{4}\s*年",
        r"([一-龥]{2,}(?:股份有限公司|有限责任公司|有限公司))",
        # HK-listed: English name then Chinese
        r"XIAOMI\s+CORPORATION\s*\n\s*([一-龥]{2,}(?:集团|公司))",
        r"TENCENT\s+HOLDINGS\s+LIMITED\s*\n?\s*([一-龥]{2,}(?:控股|集团|公司))",
    ]
    for pat in company_patterns:
        m = re.search(pat, text[:5000])
        if m:
            data["company_name"] = m.group(1).strip()
            break

    year_patterns = [
        r"(\d{4})\s*年\s*(?:年度|半年度|第[一二三四]季度)?\s*报告",
        r"(\d{4})\s*年度",
        r"(\d{4})\s*年",
    ]
    for pat in year_patterns:
        m = re.search(pat, text[:5000])
        if m:
            data["report_year"] = m.group(1)
            break

    date_patterns = [
        r"报告期[末：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pat in date_patterns:
        m = re.search(pat, text[:5000])
        if m:
            data["report_date"] = m.group(1)
            break

    # ── Core P&L patterns (supports both Simplified & Traditional Chinese) ──
    patterns = {
        "revenue": [
            r"收入[^\d]*?([\d,]+\.?\d*)",
            r"營業收入[^\d]*?([\d,]+\.?\d*)",
        ],
        "cost_of_sales": [
            r"营业成本[^\d]*?([\d,]+\.?\d*)",
            r"營業成本[^\d]*?([\d,]+\.?\d*)",
            r"销售成本[^\d]*?([\d,]+\.?\d*)",
            r"銷售成本[^\d]*?([\d,]+\.?\d*)",
            r"銷[售货]成本[^\d]*?([\d,]+\.?\d*)",
        ],
        "net_profit": [
            r"归属于?上市公司股东的净利润[^\d]*?([\d,]+\.?\d*)",
            r"净利润[^\d]*?([\d,]+\.?\d*)",
            r"年內溢利[^\d]*?([\d,]+\.?\d*)",
            r"年内溢利[^\d]*?([\d,]+\.?\d*)",
            r"本公司.?有人.?佔[^\d]*?([\d,]+\.?\d*)",
            r"本公司拥有人应占[^\d]*?([\d,]+\.?\d*)",
        ],
        "total_assets": [
            r"总资产[^\d]*?([\d,]+\.?\d*)",
            r"資產總[額计][^\d]*?([\d,]+\.?\d*)",
            r"资产总[计额][^\d]*?([\d,]+\.?\d*)",
        ],
        "total_liabilities": [
            r"总负债[^\d]*?([\d,]+\.?\d*)",
            r"負債總[額计][^\d]*?([\d,]+\.?\d*)",
            r"负债总[合额计][^\d]*?([\d,]+\.?\d*)",
        ],
        "equity": [
            r"归属于上市公司股东的净资产[^\d]*?([\d,]+\.?\d*)",
            r"所有者权益合计[^\d]*?([\d,]+\.?\d*)",
            r"股东权益合计[^\d]*?([\d,]+\.?\d*)",
            r"權益總[額计][^\d]*?([\d,]+\.?\d*)",
            r"权益总额[^\d]*?([\d,]+\.?\d*)",
            r"本公司.?有人.?佔.?權益[^\d]*?([\d,]+\.?\d*)",
            r"本公司拥有人应占权益[^\d]*?([\d,]+\.?\d*)",
        ],
        "operating_cash_flow": [
            r"经营活动(?:产生|所得)的现金流量净额[^\d]*?([\d,]+\.?\d*)",
            r"经营活动所得现金[^\d]*?([\d,]+\.?\d*)",
            r"經營活動所得現金[^\d]*?([\d,]+\.?\d*)",
        ],
        # --- NEW extraction patterns ---
        "operating_profit": [
            r"经营利润[^\d]*?([\d,]+\.?\d*)",
            r"營業利潤[^\d]*?([\d,]+\.?\d*)",
            r"经营溢利[^\d]*?([\d,]+\.?\d*)",
            r"經營溢利[^\d]*?([\d,]+\.?\d*)",
        ],
        "selling_expenses": [
            r"销售费用[^\d]*?([\d,]+\.?\d*)",
            r"銷售費用[^\d]*?([\d,]+\.?\d*)",
            r"销售及(?:市场)?推广(?:开支|费用)[^\d]*?([\d,]+\.?\d*)",
            r"銷售及(?:市場)?推廣(?:開支|費用)[^\d]*?([\d,]+\.?\d*)",
            r"销售及分销(?:开支|费用)[^\d]*?([\d,]+\.?\d*)",
        ],
        "admin_expenses": [
            r"管理费用[^\d]*?([\d,]+\.?\d*)",
            r"管理費用[^\d]*?([\d,]+\.?\d*)",
            r"行政(?:开支|费用)[^\d]*?([\d,]+\.?\d*)",
            r"行政(?:開支|費用)[^\d]*?([\d,]+\.?\d*)",
        ],
        "rd_expenses": [
            r"研发费用[^\d]*?([\d,]+\.?\d*)",
            r"研發費用[^\d]*?([\d,]+\.?\d*)",
            r"研发开支[^\d]*?([\d,]+\.?\d*)",
            r"研發開支[^\d]*?([\d,]+\.?\d*)",
        ],
        "investing_cash_flow": [
            r"投资活动(?:产生|所得)的现金流量净额[^\d]*?([\d,]+\.?\d*)",
            r"投资活动(?:所用|所得)现金[^\d]*?([\-\d,]+\.?\d*)",
            r"投資活動(?:所用|所得)現金[^\d]*?([\-\d,]+\.?\d*)",
        ],
        "financing_cash_flow": [
            r"筹资活动(?:产生|所得)的现金流量净额[^\d]*?([\d,]+\.?\d*)",
            r"融资活动(?:所用|所得)现金[^\d]*?([\-\d,]+\.?\d*)",
            r"融資活動(?:所用|所得)現金[^\d]*?([\-\d,]+\.?\d*)",
        ],
        "current_assets": [
            r"流动资产(?:合计|合計|总计|總計)[^\d]*?([\d,]+\.?\d*)",
            r"流動資產[^\d]*?([\d,]+\.?\d*)",
        ],
        "current_liabilities": [
            r"流动负债(?:合计|合計|总计|總計)[^\d]*?([\d,]+\.?\d*)",
            r"流動負債[^\d]*?([\d,]+\.?\d*)",
        ],
        "trade_receivables": [
            r"(?:贸易|应收)(?:应收)?账款[^\d]*?([\d,]+\.?\d*)",
            r"(?:貿易|應收)(?:應收)?賬款[^\d]*?([\d,]+\.?\d*)",
            r"应收账款及票据[^\d]*?([\d,]+\.?\d*)",
        ],
        "inventory": [
            r"存货[^\d]*?([\d,]+\.?\d*)",
            r"存貨[^\d]*?([\d,]+\.?\d*)",
            r"存[货貨][^\d]*?([\d,]+\.?\d*)",
        ],
        "capital_expenditure": [
            r"资本(?:开|開)支[^\d]*?([\d,]+\.?\d*)",
            r"购买物业[^\d]*?([\d,]+\.?\d*)",
            r"(?:购|購)置物業[^\d]*?([\d,]+\.?\d*)",
        ],
    }

    for key, regex_list in patterns.items():
        for regex in regex_list:
            match = re.search(regex, text)
            if match:
                val_str = match.group(1).replace(",", "").replace(" ", "")
                try:
                    data[key] = float(val_str)
                    break
                except ValueError:
                    continue

    # ── Extract previous year data from year-comparison tables ──
    # Common pattern in HK reports: "2025年 2024年" followed by paired numbers
    prev_data_pairs = [
        ("revenue", "prev_revenue", [
            r"收入[\s\S]*?(\d{4})年[^\d]*?([\d,]+\.?\d*)[\s\S]*?(\d{4})年[^\d]*?([\d,]+\.?\d*)",
        ]),
    ]

    # Look for two-year comparison tables
    # Pattern: row label followed by two money amounts (current year, prev year)
    two_year_pat = re.compile(
        r"(?:收入|營業收入)[^\d]*?([\d,]+\.?\d*)[^\d]*?([\d,]+\.?\d*)"
    )
    # Try to find the first occurrence in context of two-year comparison
    for key, prev_key, pat_list in prev_data_pairs:
        for pat in pat_list:
            m = re.search(pat, text)
            if m:
                try:
                    curr = float(m.group(2).replace(",", "").replace(" ", ""))
                    prev = float(m.group(4).replace(",", "").replace(" ", ""))
                    if data.get(key) is None:
                        data[key] = curr
                    data[prev_key] = prev
                    break
                except (ValueError, AttributeError):
                    continue

    # Try to find previous year values by locating the comparison table sections
    _extract_prev_year_from_tables(data, text)

    # ── Extract segment data ──
    data["segment_data"] = _extract_segments(text)

    # ── Extract operational KPIs ──
    data["operational_kpis"] = _extract_operational_kpis(text)

    return data


def _extract_prev_year_from_tables(data, text):
    """Try to locate two-year comparison data in known table structures.

    Scans for standard patterns like:

        2025年      2024年
    收入  xxx        yyy
    """
    # Look for explicit year-pair sections in the text
    # HK reports often have tables with "2025年 2024年" columns
    year_str = data.get("report_year", "")
    if not year_str:
        return

    try:
        curr_year_int = int(year_str)
        curr_year = year_str
        prev_year = str(curr_year_int - 1)
    except ValueError:
        return

    # For HK reports with explicit "截至X年12月31日止年度" headers
    section_matches = {
        "revenue": [
            rf"收入[^\d]*?([\d,]+\.?\d*)[^\d]*?([\d,]+\.?\d*)",
        ],
        "cost_of_sales": [
            rf"(?:销售成本|營業成本)[^\d]*?([\d,]+\.?\d*)[^\d]*?([\d,]+\.?\d*)",
        ],
        "net_profit": [
            rf"(?:净利润|年內溢利)[^\d]*?([\d,]+\.?\d*)[^\d]*?([\d,]+\.?\d*)",
        ],
        "total_assets": [
            rf"(?:总资产|資產總[额計])[^\d]*?([\d,]+\.?\d*)[^\d]*?([\d,]+\.?\d*)",
        ],
        "total_liabilities": [
            rf"(?:总负债|負債總[额計])[^\d]*?([\d,]+\.?\d*)[^\d]*?([\d,]+\.?\d*)",
        ],
    }

    for key, pat_list in section_matches.items():
        if data.get(f"prev_{key}") is not None:
            continue
        for pat in pat_list:
            m = re.search(pat, text)
            if m and len(m.groups()) >= 2:
                try:
                    val1 = float(m.group(1).replace(",", "").replace(" ", ""))
                    val2 = float(m.group(2).replace(",", "").replace(" ", ""))
                    curr_val = data.get(key)
                    if curr_val is not None:
                        # Determine which value is current year (should be closer to curr_val)
                        if abs(val1 - curr_val) / abs(curr_val) < 0.1:
                            data[f"prev_{key}"] = val2
                        else:
                            data[f"prev_{key}"] = val1
                    else:
                        data[key] = val1
                        data[f"prev_{key}"] = val2
                    break
                except (ValueError, ZeroDivisionError):
                    continue


def _extract_segments(text):
    """Extract business segment revenue and margin data.

    Looks for segment/divisional breakdown tables commonly found in
    MD&A sections of annual/quarterly reports.
    """
    segments = []

    # Common segment names and their revenue pattern
    # Pattern: segment_name ... revenue_amount ... (optional margin or yoy)
    segment_patterns = [
        # HK-styled segment header: "手机×AIoT" "智能电动汽车" etc.
        # Look for the segment description paragraph with key numbers
        (r"(?:手機|手机)(?:×|x|X)(?:AIoT|IoT)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "手机×AIoT"),
        (r"(?:智能(?:电动)?汽车|電動汽車)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "智能电动汽车"),
        (r"(?:互联网服务|互聯網服務|互联网|互聯網)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "互联网服务"),
        # A-share patterns
        (r"(?:增值服务|增值服務|VAS)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "增值服务"),
        (r"(?:营销服务|營銷服務|广告|廣告)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "营销服务"),
        (r"(?:金融科技|企业服务|企業服務)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "金融科技及企业服务"),
        # IoT
        (r"(?:IoT|物联网|物聯網)[\s\S]{0,200}?收入[^\d]*?([\d,]+\.?\d*)", "IoT与生活消费产品"),
    ]

    found_names = set()
    for pat, name in segment_patterns:
        if name in found_names:
            continue
        m = re.search(pat, text)
        if m:
            rev = float(m.group(1).replace(",", "").replace(" ", ""))
            segments.append({
                "name": name,
                "revenue": rev,
                "prev_revenue": None,
                "cost": None,
                "gross_margin": None,
                "revenue_share": None,
            })
            found_names.add(name)

    # Try to also extract segment gross margins
    for seg in segments:
        name = seg["name"]
        # Look for margin near the segment name
        margin_pat = rf"{name}[\s\S]{{0,300}}?毛利[率率][^\d]*?([\d.]+)[%％]"
        m = re.search(margin_pat, text)
        if m:
            try:
                seg["gross_margin"] = float(m.group(1)) / 100.0
            except ValueError:
                pass

        # Try to find the cost/previous values
        cost_pat = rf"{name}[\s\S]{{0,300}}?(?:销售成本|營業成本|成本)[^\d]*?([\d,]+\.?\d*)"
        m = re.search(cost_pat, text)
        if m:
            try:
                seg["cost"] = float(m.group(1).replace(",", "").replace(" ", ""))
                if seg["revenue"] and seg["cost"]:
                    seg["gross_margin"] = (seg["revenue"] - seg["cost"]) / seg["revenue"]
            except ValueError:
                pass

    return segments if segments else None


def _extract_operational_kpis(text):
    """Extract operational KPIs like MAU, shipment volume, etc."""
    kpis = {}

    # MAU / Monthly Active Users
    for pat, label in [
        (r"月(?:活|活跃)[用用]户[数數]?[^\d]*?(\d+[\.\d]*)\s*(?:百万|億|亿)", "月活跃用户"),
        (r"MAU[^\d]*?(\d+[\.\d]*)\s*(?:百万|億|亿|M|mn)", "MAU"),
        (r"全球[^\d]*?月活[^\d]*?(\d+[\.\d]*)\s*(?:百万|億|亿)", "全球月活跃用户"),
    ]:
        m = re.search(pat, text[:5000])
        if m:
            val = m.group(1)
            unit = "百万" if ("百万" in m.group(0) or "M" in m.group(0)) else "亿"
            kpis[label] = f"{val} {unit}"
            break

    # Smartphone shipments
    for pat in [
        r"(?:智能手机|智能手機)(?:出货|出貨|销量|銷量)[^\d]*?(\d+[\.\d]*)\s*(?:百万|万台|萬台)",
        r"(?:出货量|出貨量)[^\d]*?(\d+[\.\d]*)\s*(?:百万|万台|萬台)",
    ]:
        m = re.search(pat, text[:5000])
        if m:
            kpis["智能手机出货量"] = f"{m.group(1)} 百万台"
            break

    # Vehicle deliveries
    for pat in [
        r"(?:交付|交付量)[^\d]*?(\d+[,\d]*)\s*[辆輛]",
        r"(?:汽车|汽車)(?:交付|销量)[^\d]*?(\d+[,\d]*)\s*[辆輛]",
    ]:
        m = re.search(pat, text[:5000])
        if m:
            kpis["汽车交付量"] = f"{m.group(1)} 辆"
            break

    # IoT connected devices
    m = re.search(r"(?:IoT|物聯網)(?:平台)?[^\d]*?连接[^\d]*?(\d+[\.\d]*)\s*(?:亿|億|百万)", text[:5000])
    if m:
        kpis["AIoT平台连接设备"] = f"{m.group(1)} {m.group(0).split(m.group(1))[1][:2].strip()}"

    # Employee count
    m = re.search(r"(?:员工|員工)(?:人数|人數|总数|總數)[^\d]*?(\d+[,\d]*)", text[:5000])
    if m:
        kpis["员工总数"] = f"{m.group(1)} 人"

    return kpis if kpis else None


def extract_financials(file_path):
    """Extract key financial data from a file.

    Args:
        file_path: Path to the financial report file (supports .pdf, .txt, .md, etc.)

    Returns:
        dict with extracted financial metrics.
    """
    if not os.path.exists(file_path):
        return {"error": True, "message": f"File not found: {file_path}"}

    try:
        text = read_file_content(file_path)
    except Exception as e:
        return {"error": True, "message": f"Failed to read file: {e}"}

    if not text or not text.strip():
        return {"error": True, "message": "File is empty or could not be parsed"}

    data = extract_from_text(text)

    # Add a summary of which fields were successfully extracted
    extracted = [k for k, v in data.items() if v is not None]
    missing = [k for k, v in data.items() if v is None]
    data["_meta"] = {
        "file": os.path.basename(file_path),
        "text_length": len(text),
        "extracted_fields": extracted,
        "missing_fields": missing,
    }

    return data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        try:
            parsed = json.loads(arg)
            if isinstance(parsed, dict):
                fp = parsed.get("file_path", "")
            else:
                fp = str(parsed)
        except json.JSONDecodeError:
            fp = arg

        if not fp:
            print(
                json.dumps(
                    {"error": True, "message": "Missing required parameter: file_path"},
                    ensure_ascii=False,
                )
            )
            sys.exit(1)

        result = extract_financials(fp)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            'Usage: python3 extract_financials.py \'{"file_path": "/path/to/report.pdf"}\''
        )

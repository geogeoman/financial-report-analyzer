import json
import sys
from datetime import datetime


def format_amount(value):
    """Auto-scale a numeric amount to 亿元, 万元, or 元."""
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"

    abs_val = abs(value)
    if abs_val >= 1e8:
        return f"{value / 1e8:.2f}亿元"
    if abs_val >= 1e4:
        return f"{value / 1e4:.2f}万元"
    return f"{value:.2f}元"


def format_growth(current, previous):
    """Calculate YoY growth and return (formatted_string, css_class)."""
    if current is None or previous is None:
        return "N/A", ""
    try:
        current = float(current)
        previous = float(previous)
    except (TypeError, ValueError):
        return "N/A", ""

    if previous == 0:
        return "N/A", ""

    growth = (current - previous) / abs(previous) * 100
    if growth >= 0:
        return f"+{growth:.1f}%", "highlight-positive"
    return f"{growth:.1f}%", "highlight-negative"


def format_pct(value):
    """Format a ratio (0-1 scale) as 'XX.XX%'."""
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{value * 100:.2f}%"


def format_pp_change(current, previous):
    """Calculate percentage-point change and return (formatted_string, css_class)."""
    if current is None or previous is None:
        return "N/A", ""
    try:
        current = float(current)
        previous = float(previous)
    except (TypeError, ValueError):
        return "N/A", ""

    change = (current - previous) * 100
    if change >= 0:
        return f"+{change:.1f}pp", "highlight-positive"
    return f"{change:.1f}pp", "highlight-negative"


def fmt_growth_label(growth_str):
    """Extract just the label part from format_growth result for use in table cells."""
    return growth_str if isinstance(growth_str, str) else "N/A"


def build_segment_html(data):
    """Build 1.2 section HTML: segment breakdown table + chart.

    Returns empty string when no segment data is available.
    """
    segments = data.get("segment_data")
    if not segments or not isinstance(segments, list) or len(segments) == 0:
        return ""

    rows = []
    for s in segments:
        name = s.get("name", "N/A")
        rev = format_amount(s.get("revenue"))
        yoy, yoy_cls = format_growth(s.get("revenue"), s.get("prev_revenue"))
        share = format_pct(s.get("revenue_share")) if s.get("revenue_share") else "N/A"
        gm = format_pct(s.get("gross_margin")) if s.get("gross_margin") else "N/A"
        yoy_span = f'<span class="{yoy_cls}">{yoy}</span>' if yoy_cls else yoy
        rows.append(f"    <tr><td>{name}</td><td>{rev}</td><td>{yoy_span}</td><td>{share}</td><td>{gm}</td></tr>")

    seg_chart_path = data.get("_chart_segment_margins", "{{CHART_SEGMENT_MARGINS}}")

    return f"""
<h3>1.2 分部收入与增速</h3>
<table class="seg-table">
  <thead><tr><th>业务分部</th><th>本期收入</th><th>同比增长</th><th>收入占比</th><th>毛利率</th></tr></thead>
  <tbody>
{chr(10).join(rows)}
  </tbody>
</table>

<div class="chart-container">
  <img src="{seg_chart_path}" alt="分部毛利率对比">
  <p class="chart-caption">图2 各业务分部毛利率对比</p>
</div>"""


def build_operational_kpi_html(data):
    """Build 1.3 section HTML: operational KPIs table.

    Returns empty string when no operational KPI data is available.
    """
    kpis = data.get("operational_kpis")
    if not kpis or not isinstance(kpis, dict) or len(kpis) == 0:
        return ""

    rows = []
    for key, val in kpis.items():
        rows.append(f"    <tr><td>{key}</td><td>{val}</td><td>—</td></tr>")

    return f"""
<h3>1.3 核心运营指标</h3>
<table>
  <thead><tr><th>指标</th><th>本期数值</th><th>说明</th></tr></thead>
  <tbody>
{chr(10).join(rows)}
  </tbody>
</table>"""


def build_expense_table(data):
    """Build expense structure table rows."""
    revenue = _get(data, "revenue")
    if revenue is None or revenue == 0:
        return ""

    items = []
    for key, label in [
        ("selling_expenses", "销售及市场推广费用率"),
        ("admin_expenses", "一般及行政费用率"),
        ("rd_expenses", "研发费用率"),
    ]:
        val = _get(data, key)
        if val is not None:
            pct = val / revenue
            items.append((label, format_pct(pct), "—"))

    capex = _get(data, "capital_expenditure")
    if capex is not None:
        items.append(("资本开支占收入比", format_pct(capex / revenue), "投入强度指标"))

    if not items:
        return ""

    rows = "\n".join(
        f'      <tr><td>{label}</td><td>{pct_str}</td><td>{note}</td></tr>'
        for label, pct_str, note in items
    )

    return f"""<table>
    <thead><tr><th>费用项目</th><th>占收入比例</th><th>评估</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>"""


def build_solvency_table(data):
    """Build solvency safety indicator table rows."""
    total_liabilities = _get(data, "total_liabilities")
    total_assets = _get(data, "total_assets")
    current_assets = _get(data, "current_assets")
    current_liabilities = _get(data, "current_liabilities")
    cash = _get(data, "cash_equivalents") or _get(data, "cash")
    receivables = _get(data, "trade_receivables")
    inventory = _get(data, "inventory")

    rows = []

    if total_liabilities is not None and total_assets is not None and total_assets > 0:
        alr = total_liabilities / total_assets
        rows.append(("资产负债率", format_pct(alr), "40%-60%", "—"))

    if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
        cr = current_assets / current_liabilities
        rows.append(("流动比率", f"{cr:.2f}", "> 1.0", "—"))

    if (cash is not None and receivables is not None
            and current_liabilities is not None and current_liabilities > 0):
        qr = (cash + receivables) / current_liabilities
        rows.append(("速动比率", f"{qr:.2f}", "> 1.0 为优秀", "—"))

    if not rows:
        return ""

    row_html = "\n".join(
        f'      <tr><td>{label}</td><td>{val}</td><td>{ref}</td><td>{judge}</td></tr>'
        for label, val, ref, judge in rows
    )

    return f"""<table>
    <thead><tr><th>指标</th><th>数值</th><th>参考健康值</th><th>判断</th></tr></thead>
    <tbody>
{row_html}
    </tbody>
  </table>"""


def build_efficiency_table(data):
    """Build operational efficiency indicator table rows."""
    revenue = _get(data, "revenue")
    cost_of_sales = _get(data, "cost_of_sales")
    total_assets = _get(data, "total_assets")
    ar = _get(data, "trade_receivables")
    prev_ar = _get(data, "prev_trade_receivables")
    inv = _get(data, "inventory")
    prev_inv = _get(data, "prev_inventory")
    prev_ta = _get(data, "prev_total_assets")

    rows = []

    if revenue and ar and prev_ar:
        avg_ar = (ar + prev_ar) / 2
        if avg_ar > 0:
            art = revenue / avg_ar
            rows.append(("应收账款周转率", f"{art:.2f}次/年", "收款速度"))

    if cost_of_sales and inv and prev_inv:
        avg_inv = (inv + prev_inv) / 2
        if avg_inv > 0:
            it = cost_of_sales / avg_inv
            rows.append(("存货周转率", f"{it:.2f}次/年", "仓库清空速度"))

    if revenue and total_assets and prev_ta:
        avg_ta = (total_assets + prev_ta) / 2
        if avg_ta > 0:
            tat = revenue / avg_ta
            rows.append(("总资产周转率", f"{tat:.2f}次/年", "资产使用效率"))

    if not rows:
        return ""

    row_html = "\n".join(
        f'      <tr><td>{label}</td><td>{val}</td><td>{meaning}</td></tr>'
        for label, val, meaning in rows
    )

    return f"""<table>
    <thead><tr><th>指标</th><th>数值</th><th>含义</th></tr></thead>
    <tbody>
{row_html}
    </tbody>
  </table>"""


def build_cashflow_table(data):
    """Build three cash flow types comparison table."""
    op = _get(data, "operating_cash_flow")
    inv = _get(data, "investing_cash_flow")
    fin = _get(data, "financing_cash_flow")

    if op is None and inv is None and fin is None:
        return ""

    def direction(val, label_pos, label_neg):
        if val is None:
            return "N/A"
        return label_pos if val >= 0 else label_neg

    rows = []
    if op is not None:
        rows.append(("经营活动现金流", format_amount(op),
                     direction(op, "正向流入 ✓ 造血正常", "净流出 ✗ 需关注")))
    if inv is not None:
        rows.append(("投资活动现金流", format_amount(inv),
                     direction(inv, "净流入 → 资产回收", "净流出 → 持续投资")))
    if fin is not None:
        rows.append(("融资活动现金流", format_amount(fin),
                     direction(fin, "净流入 → 外部融资", "净流出 → 回购/还债")))

    if not rows:
        return ""

    row_html = "\n".join(
        f'      <tr><td>{label}</td><td>{val}</td><td>{d}</td></tr>'
        for label, val, d in rows
    )

    return f"""<table>
    <thead><tr><th>现金流类型</th><th>金额</th><th>方向判断</th></tr></thead>
    <tbody>
{row_html}
    </tbody>
  </table>"""


def build_cashflow_quality_table(data):
    """Build cash flow quality indicators table."""
    net_profit = _get(data, "net_profit")
    op_cf = _get(data, "operating_cash_flow")
    capex = _get(data, "capital_expenditure")
    inv_cf = _get(data, "investing_cash_flow")

    rows = []

    if net_profit and op_cf and net_profit > 0:
        ncr = op_cf / net_profit
        rows.append(("净现比（经营CF/净利润）", f"{ncr:.2f}x", "> 1.0 为健康"))

    if op_cf is not None and capex is not None:
        fcf = op_cf + capex  # capex is typically negative
        rows.append(("自由现金流", format_amount(fcf), "持续为正→价值创造"))

    if op_cf is not None and inv_cf is not None:
        gap = op_cf + inv_cf
        rows.append(("资金缺口（经营CF+投资CF）", format_amount(gap), "长期为负不可持续"))

    if not rows:
        return ""

    row_html = "\n".join(
        f'      <tr><td>{label}</td><td>{val}</td><td>{ref}</td></tr>'
        for label, val, ref in rows
    )

    return f"""<table>
    <thead><tr><th>指标</th><th>数值</th><th>健康参考</th></tr></thead>
    <tbody>
{row_html}
    </tbody>
  </table>"""


def build_bcg_matrix(data):
    """Build BCG decision matrix table from segment data."""
    segments = data.get("segment_data")
    if not segments or not isinstance(segments, list) or len(segments) == 0:
        return ""

    rows = []
    for s in segments:
        name = s.get("name", "N/A")
        gm = format_pct(s.get("gross_margin")) if s.get("gross_margin") else "N/A"
        yoy_str, yoy_cls = format_growth(s.get("revenue"), s.get("prev_revenue"))

        gm_val = s.get("gross_margin") or 0
        rev_growth = 0
        if s.get("revenue") and s.get("prev_revenue") and s["prev_revenue"] != 0:
            rev_growth = (s["revenue"] - s["prev_revenue"]) / abs(s["prev_revenue"]) * 100

        # BCG quadrant classification
        if gm_val >= 0.3 and rev_growth >= 10:
            quadrant = "高毛利·高增长"
            cls = "quadrant-expand"
            suggestion = "<strong>扩张：加大投入，抢占市场</strong>"
        elif gm_val >= 0.3 and rev_growth < 10:
            quadrant = "高毛利·稳定增长"
            cls = "quadrant-harvest"
            suggestion = "<strong>维持/收割：最大化现金流</strong>"
        elif gm_val < 0.3 and rev_growth >= 10:
            quadrant = "低毛利·高增长"
            cls = "quadrant-cultivate"
            suggestion = "<strong>培育/优化：控制成本，提升盈利</strong>"
        else:
            quadrant = "低毛利·低增长"
            cls = "quadrant-exit"
            suggestion = "<strong>优化/收缩：评估战略价值</strong>"

        yoy_span = f'<span class="{yoy_cls}">{yoy_str}</span>' if yoy_cls else yoy_str

        rows.append(
            f'      <tr class="{cls}"><td><strong>{name}</strong></td>'
            f'<td>{gm}</td><td>{yoy_span}</td><td>{quadrant}</td>'
            f'<td>{suggestion}</td><td><span class="kpi-badge">追踪KPI</span></td></tr>'
        )

    return f"""<table class="matrix-table">
    <thead><tr><th>业务线</th><th>毛利率</th><th>收入增速</th><th>象限定位</th><th>建议方向</th><th>追踪KPI</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>"""


# ----------------------------------------------------------------- helpers
def _get(data, key, default=None):
    """Fetch a numeric value, returning *default* for None / missing."""
    v = data.get(key)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def calculate_template_data(data):
    """Turn raw financial data into a dict of ALL template placeholder values."""

    # ----------------------------------------------------------- raw values
    revenue = _get(data, "revenue")
    net_profit = _get(data, "net_profit")
    equity = _get(data, "equity")
    cost_of_sales = _get(data, "cost_of_sales")
    non_recurring_net_profit = _get(data, "non_recurring_net_profit")
    total_assets = _get(data, "total_assets")
    total_liabilities = _get(data, "total_liabilities")
    operating_cash_flow = _get(data, "operating_cash_flow")

    prev_revenue = _get(data, "prev_revenue")
    prev_net_profit = _get(data, "prev_net_profit")
    prev_non_recurring = _get(data, "prev_non_recurring_net_profit")
    prev_gross_margin = _get(data, "prev_gross_margin")
    prev_roe = _get(data, "prev_roe")

    # -------------------------------------------------------- derived ratios
    gross_margin = None
    if revenue is not None and cost_of_sales is not None and revenue != 0:
        gross_margin = (revenue - cost_of_sales) / revenue

    roe = None
    if net_profit is not None and equity is not None and equity != 0:
        roe = net_profit / equity

    operating_margin = None
    operating_profit = _get(data, "operating_profit")
    if operating_profit is not None and revenue is not None and revenue != 0:
        operating_margin = operating_profit / revenue

    net_margin = None
    if net_profit is not None and revenue is not None and revenue != 0:
        net_margin = net_profit / revenue

    asset_liability_ratio = None
    if total_liabilities is not None and total_assets is not None and total_assets != 0:
        asset_liability_ratio = total_liabilities / total_assets

    current_ratio = None
    current_assets = _get(data, "current_assets")
    current_liabilities = _get(data, "current_liabilities")
    if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
        current_ratio = current_assets / current_liabilities

    net_cash_ratio = None
    if operating_cash_flow is not None and net_profit is not None and net_profit != 0:
        net_cash_ratio = operating_cash_flow / net_profit

    # -------------------------------------------------------- formatted values
    result = {}

    # --- Basic info ---
    result["COMPANY_NAME"] = data.get("company_name") or "未知公司"
    result["YEAR"] = str(data.get("report_year") or data.get("year") or "N/A")
    result["DATE"] = data.get("report_date") or datetime.now().strftime("%Y年%m月%d日")

    # --- Revenue ---
    result["REVENUE"] = format_amount(revenue)
    rev_growth, rev_cls = format_growth(revenue, prev_revenue)
    result["REVENUE_GROWTH"] = rev_growth
    result["REVENUE_GROWTH_CLASS"] = rev_cls
    result["REVENUE_INDUSTRY_AVG"] = "N/A"

    # --- Net profit ---
    result["NET_PROFIT"] = format_amount(net_profit)
    np_growth, np_cls = format_growth(net_profit, prev_net_profit)
    result["NET_PROFIT_GROWTH"] = np_growth
    result["NET_PROFIT_GROWTH_CLASS"] = np_cls
    result["NET_PROFIT_INDUSTRY_AVG"] = "N/A"

    # --- Non-recurring net profit ---
    result["NON_RECURRING_NET_PROFIT"] = format_amount(non_recurring_net_profit)
    nr_growth, nr_cls = format_growth(non_recurring_net_profit, prev_non_recurring)
    result["NON_RECURRING_GROWTH"] = nr_growth
    result["NON_RECURRING_GROWTH_CLASS"] = nr_cls
    result["NON_RECURRING_INDUSTRY_AVG"] = "N/A"

    # --- Gross margin ---
    result["GROSS_MARGIN"] = format_pct(gross_margin)
    gm_change, gm_cls = format_pp_change(gross_margin, prev_gross_margin)
    result["GROSS_MARGIN_CHANGE"] = gm_change
    result["GROSS_MARGIN_CHANGE_CLASS"] = gm_cls
    result["GROSS_MARGIN_INDUSTRY_AVG"] = "N/A"

    # --- ROE ---
    result["ROE"] = format_pct(roe)
    roe_change, roe_cls = format_pp_change(roe, prev_roe)
    result["ROE_CHANGE"] = roe_change
    result["ROE_CHANGE_CLASS"] = roe_cls
    result["ROE_INDUSTRY_AVG"] = "N/A"

    # --- NEW: Operating margin ---
    result["OPERATING_MARGIN"] = format_pct(operating_margin)

    # --- NEW: Net margin ---
    result["NET_MARGIN"] = format_pct(net_margin)

    # --- NEW: Operating cash flow ---
    result["OPERATING_CASH_FLOW"] = format_amount(operating_cash_flow)

    # --- NEW: Solvency indicators ---
    result["ASSET_LIABILITY_RATIO"] = format_pct(asset_liability_ratio)
    result["CURRENT_RATIO"] = f"{current_ratio:.2f}" if current_ratio is not None else "N/A"

    # --- NEW: Cash flow quality ---
    result["NET_CASH_RATIO"] = f"{net_cash_ratio:.2f}x" if net_cash_ratio is not None else "N/A"

    # --- NEW: Section-level HTML blocks (conditionally rendered) ---
    result["SECTION_SEGMENT_BREAKDOWN"] = build_segment_html(data)
    result["SECTION_OPERATIONAL_KPIS"] = build_operational_kpi_html(data)

    # --- NEW: Sub-section HTML tables ---
    result["EXPENSE_TABLE"] = build_expense_table(data) or "N/A"
    result["SOLVENCY_TABLE"] = build_solvency_table(data) or "N/A"
    result["EFFICIENCY_TABLE"] = build_efficiency_table(data) or "N/A"
    result["CASHFLOW_TABLE"] = build_cashflow_table(data) or "N/A"
    result["CASHFLOW_QUALITY_TABLE"] = build_cashflow_quality_table(data) or "N/A"
    result["BCG_MATRIX_TABLE"] = build_bcg_matrix(data) or "N/A"

    # --- Analysis & BP placeholders (LLM fills these) ---
    result["PROFITABILITY_ANALYSIS"] = "N/A"
    result["SOLVENCY_ANALYSIS"] = "N/A"
    result["EFFICIENCY_ANALYSIS"] = "N/A"
    result["CASHFLOW_ANALYSIS"] = "N/A"
    result["ADVANTAGES_LIST"] = "N/A"
    result["RISKS_LIST"] = "N/A"
    result["OVERALL_ASSESSMENT"] = "N/A"

    # BP probe sections (LLM fills based on data patterns)
    result["BP_PROBE_PROFITABILITY"] = "N/A"
    result["BP_PROBE_SOLVENCY"] = "N/A"
    result["BP_PROBE_CASHFLOW"] = "N/A"

    # BP decision support sections (LLM fills)
    result["SEGMENT_STRATEGY"] = "N/A"
    result["RED_LINE_MANAGEMENT"] = "N/A"
    result["CAPITAL_PLANNING"] = "N/A"

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            arg = sys.argv[1]
            parsed = json.loads(arg)

            if isinstance(parsed, dict):
                if len(parsed) == 1:
                    only_value = next(iter(parsed.values()))
                    if isinstance(only_value, dict):
                        parsed = only_value

            result = calculate_template_data(parsed)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
    else:
        print("Please provide JSON data as an argument.")

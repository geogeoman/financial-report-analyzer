"""Generate financial analysis charts from JSON data.

Usage:
    python generate_charts.py '<json_data>'

Produces 3 PNG charts in the same directory as this script and outputs
a JSON manifest with the chart file paths.
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend — must be set before pyplot import

import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# ---------------------------------------------------------------------------
# Color palette (matches the HTML report theme)
# ---------------------------------------------------------------------------
COLOR_NAVY = "#0f3460"
COLOR_DARK = "#16213e"
COLOR_ACCENT = "#e94560"
COLOR_PURPLE = "#533483"
COLOR_GREEN = "#27ae60"
COLOR_LIGHT_BLUE = "#3498db"
COLOR_ORANGE = "#e67e22"

CHART_DPI = 150


# ---------------------------------------------------------------------------
# Font setup for Chinese characters
# ---------------------------------------------------------------------------
def setup_chinese_font():
    """Configure matplotlib to render Chinese characters correctly.

    Tries a priority-ordered list of CJK fonts commonly available on
    macOS, Linux, and Windows.  Falls back to DejaVu Sans.
    """
    candidates = [
        # macOS
        "Heiti TC",
        "Hiragino Sans GB",
        "PingFang SC",
        "PingFang HK",
        "STHeiti",
        "Songti SC",
        "Arial Unicode MS",
        # Linux
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Droid Sans Fallback",
        # Windows
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
    ]

    available = {f.name for f in fm.fontManager.ttflist}
    for font_name in candidates:
        if font_name in available:
            plt.rcParams["font.sans-serif"] = [font_name, "sans-serif"]
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["axes.unicode_minus"] = False
            return
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def format_yi(value):
    """Convert a raw number to 亿元 scale."""
    return value / 1e8


def safe_float(value, default=0.0):
    """Safely convert *value* to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Chart 1 – 核心财务指标对比 (financial_overview.png)
# ---------------------------------------------------------------------------
def chart_financial_overview(data, output_dir):
    """Grouped bar chart of key financial metrics (in 亿元)."""
    labels = ["营业收入", "营业成本", "净利润", "总资产", "总负债", "所有者权益"]
    keys = [
        "revenue",
        "cost_of_sales",
        "net_profit",
        "total_assets",
        "total_liabilities",
        "equity",
    ]
    current_values = [format_yi(safe_float(data.get(k))) for k in keys]

    has_prev = any(data.get(f"prev_{k}") is not None for k in keys[:3])
    prev_keys = [
        "prev_revenue",
        "prev_cost_of_sales",
        "prev_net_profit",
        None,
        None,
        None,
    ]

    fig, ax = plt.subplots(figsize=(10, 6))

    bar_width = 0.35
    x_positions = list(range(len(labels)))

    if has_prev:
        prev_values = []
        for pk in prev_keys:
            if pk is not None and data.get(pk) is not None:
                prev_values.append(format_yi(safe_float(data.get(pk))))
            else:
                prev_values.append(0)

        x_curr = [x + bar_width / 2 for x in x_positions]
        x_prev = [x - bar_width / 2 for x in x_positions]

        year = data.get("year", "本期")
        try:
            prev_year = str(int(year) - 1)
        except (ValueError, TypeError):
            prev_year = "上期"

        bars_prev = ax.bar(
            x_prev,
            prev_values,
            width=bar_width,
            label=f"{prev_year}年",
            color=COLOR_LIGHT_BLUE,
            edgecolor="white",
            linewidth=0.5,
        )
        bars_curr = ax.bar(
            x_curr,
            current_values,
            width=bar_width,
            label=f"{year}年",
            color=COLOR_NAVY,
            edgecolor="white",
            linewidth=0.5,
        )

        # Value labels for current year
        for bar in bars_curr:
            height = bar.get_height()
            if height != 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=COLOR_DARK,
                )
        # Value labels for previous year (non-zero only)
        for bar in bars_prev:
            height = bar.get_height()
            if height != 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=COLOR_LIGHT_BLUE,
                )
        ax.legend(loc="upper right", fontsize=9)
    else:
        colors = [
            COLOR_NAVY,
            COLOR_DARK,
            COLOR_ACCENT,
            COLOR_PURPLE,
            COLOR_GREEN,
            COLOR_LIGHT_BLUE,
        ]
        bars = ax.bar(
            x_positions,
            current_values,
            width=bar_width * 1.5,
            color=colors,
            edgecolor="white",
            linewidth=0.5,
        )
        for bar in bars:
            height = bar.get_height()
            if height != 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=COLOR_DARK,
                )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("金额（亿元）", fontsize=11)

    company = data.get("company_name", "")
    year_str = data.get("year", "")
    ax.set_title(
        f"{company} {year_str}年 核心财务指标对比", fontsize=14, fontweight="bold"
    )

    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#cccccc")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, "financial_overview.png")
    fig.savefig(path, dpi=CHART_DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Chart 2 – 盈利能力指标 (profitability.png)
# ---------------------------------------------------------------------------
def chart_profitability(data, output_dir):
    """Bar chart of profitability / efficiency ratios (%)."""
    revenue = safe_float(data.get("revenue"), default=None)
    cost_of_sales = safe_float(data.get("cost_of_sales"), default=None)
    net_profit = safe_float(data.get("net_profit"), default=None)
    equity = safe_float(data.get("equity"), default=None)
    total_assets = safe_float(data.get("total_assets"), default=None)
    total_liabilities = safe_float(data.get("total_liabilities"), default=None)
    operating_cash_flow = safe_float(data.get("operating_cash_flow"), default=None)

    # Calculate ratios
    gross_margin = 0.0
    if revenue and cost_of_sales is not None:
        gross_margin = (revenue - cost_of_sales) / revenue * 100

    net_margin = 0.0
    if revenue and net_profit is not None:
        net_margin = net_profit / revenue * 100

    roe = 0.0
    if equity and net_profit is not None:
        roe = net_profit / equity * 100

    debt_ratio = 0.0
    if total_assets and total_liabilities is not None:
        debt_ratio = total_liabilities / total_assets * 100

    cash_ratio = 0.0
    if net_profit and operating_cash_flow is not None:
        cash_ratio = operating_cash_flow / net_profit * 100
        # Cap at 200% for display readability
        cash_ratio = min(cash_ratio, 200.0)

    labels = ["毛利率", "净利率", "ROE", "资产负债率", "净现比"]
    values = [gross_margin, net_margin, roe, debt_ratio, cash_ratio]
    colors = [COLOR_NAVY, COLOR_LIGHT_BLUE, COLOR_GREEN, COLOR_ACCENT, COLOR_PURPLE]

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(
        labels, values, color=colors, edgecolor="white", linewidth=0.5, height=0.55
    )

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            ha="left",
            va="center",
            fontsize=10,
            fontweight="bold",
            color=COLOR_DARK,
        )

    ax.set_xlabel("百分比 (%)", fontsize=11)

    company = data.get("company_name", "")
    year_str = data.get("year", "")
    ax.set_title(f"{company} {year_str}年 盈利能力指标", fontsize=14, fontweight="bold")

    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#cccccc")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Give some right margin for the labels
    max_val = max(values) if values else 100
    ax.set_xlim(0, max_val * 1.2 if max_val > 0 else 100)

    plt.tight_layout()
    path = os.path.join(output_dir, "profitability.png")
    fig.savefig(path, dpi=CHART_DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Chart 3 – 资产结构分布 (asset_structure.png)
# ---------------------------------------------------------------------------
def chart_asset_structure(data, output_dir):
    """Donut chart showing liabilities vs equity composition."""
    total_liabilities = safe_float(data.get("total_liabilities"))
    equity = safe_float(data.get("equity"))

    total = total_liabilities + equity
    if total == 0:
        # Avoid division by zero — create a placeholder chart
        total = 1

    liab_yi = format_yi(total_liabilities)
    equity_yi = format_yi(equity)

    labels = [
        f"负债\n{liab_yi:.1f}亿元",
        f"所有者权益\n{equity_yi:.1f}亿元",
    ]
    sizes = [total_liabilities, equity]
    colors = [COLOR_ACCENT, COLOR_NAVY]
    explode = (0.03, 0.03)

    fig, ax = plt.subplots(figsize=(8, 8))

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        explode=explode,
        pctdistance=0.75,
        labeldistance=1.15,
        textprops={"fontsize": 12},
        wedgeprops={"linewidth": 2, "edgecolor": "white"},
    )

    for autotext in autotexts:
        autotext.set_fontsize(13)
        autotext.set_fontweight("bold")
        autotext.set_color("white")

    # Draw a white circle in the centre for a donut effect
    centre_circle = plt.Circle((0, 0), 0.55, fc="white")
    ax.add_artist(centre_circle)

    # Centre text
    total_yi = format_yi(total)
    ax.text(
        0,
        0.05,
        "总资产",
        ha="center",
        va="center",
        fontsize=13,
        color="#666666",
    )
    ax.text(
        0,
        -0.1,
        f"{total_yi:.1f}亿元",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color=COLOR_DARK,
    )

    company = data.get("company_name", "")
    year_str = data.get("year", "")
    ax.set_title(
        f"{company} {year_str}年 资产结构分布",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    ax.axis("equal")
    plt.tight_layout()
    path = os.path.join(output_dir, "asset_structure.png")
    fig.savefig(path, dpi=CHART_DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Chart 4 – 分部收入与毛利率对比 (segment_margins.png)
# ---------------------------------------------------------------------------
def chart_segment_margins(data, output_dir):
    """Dual-axis chart: bars = segment revenue, line = gross margin.

    Expects ``data["segment_data"]`` to be a list of dicts with keys:
        name, revenue, gross_margin
    Skips generation when segment_data is missing or empty.
    """
    segments = data.get("segment_data")
    if not segments or not isinstance(segments, list) or len(segments) == 0:
        return None

    names = [s.get("name", "N/A") for s in segments]
    revenues = [format_yi(safe_float(s.get("revenue"))) for s in segments]
    margins = [safe_float(s.get("gross_margin")) * 100 for s in segments]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    bar_width = 0.45
    x_pos = list(range(len(names)))

    bars = ax1.bar(
        x_pos, revenues, width=bar_width,
        color=COLOR_NAVY, edgecolor="white", linewidth=0.5,
    )
    ax1.set_ylabel("收入（亿元）", fontsize=11, color=COLOR_NAVY)
    ax1.tick_params(axis="y", labelcolor=COLOR_NAVY)

    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax1.text(
                bar.get_x() + bar.get_width() / 2, h,
                f"{h:.1f}", ha="center", va="bottom", fontsize=9, color=COLOR_DARK,
            )

    ax2 = ax1.twinx()
    ax2.plot(
        x_pos, margins, "o-", color=COLOR_ACCENT, linewidth=2.5,
        markersize=8, markerfacecolor=COLOR_ACCENT,
    )
    ax2.set_ylabel("毛利率 (%)", fontsize=11, color=COLOR_ACCENT)
    ax2.tick_params(axis="y", labelcolor=COLOR_ACCENT)

    for i, m in enumerate(margins):
        ax2.annotate(
            f"{m:.1f}%", (x_pos[i], m),
            textcoords="offset points", xytext=(0, 10),
            fontsize=9, fontweight="bold", color=COLOR_ACCENT, ha="center",
        )

    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(names, fontsize=10)

    company = data.get("company_name", "")
    year_str = data.get("year", "")
    ax1.set_title(
        f"{company} {year_str}年 分部收入与毛利率",
        fontsize=14, fontweight="bold",
    )

    ax1.grid(axis="y", linestyle="--", alpha=0.4, color="#cccccc")
    ax1.set_axisbelow(True)
    ax1.spines["top"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, "segment_margins.png")
    fig.savefig(path, dpi=CHART_DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Chart 5 – 现金流结构对比 (cash_flow_structure.png)
# ---------------------------------------------------------------------------
def chart_cash_flow_structure(data, output_dir):
    """Grouped bar chart comparing operating/investing/financing cash flows.

    Expects keys: operating_cash_flow, investing_cash_flow, financing_cash_flow
    and their prev_* counterparts.
    """
    op_cf = safe_float(data.get("operating_cash_flow"))
    inv_cf = safe_float(data.get("investing_cash_flow"))
    fin_cf = safe_float(data.get("financing_cash_flow"))

    has_prev = any(
        data.get(f"prev_{k}") is not None
        for k in ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow"]
    )

    labels = ["经营活动", "投资活动", "融资活动"]
    current_vals = [format_yi(op_cf), format_yi(inv_cf), format_yi(fin_cf)]

    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.35
    x_pos = list(range(len(labels)))
    colors_curr = [COLOR_GREEN if v >= 0 else COLOR_ACCENT for v in [op_cf, inv_cf, fin_cf]]

    if has_prev:
        prev_op = format_yi(safe_float(data.get("prev_operating_cash_flow")))
        prev_inv = format_yi(safe_float(data.get("prev_investing_cash_flow")))
        prev_fin = format_yi(safe_float(data.get("prev_financing_cash_flow")))
        prev_vals = [prev_op, prev_inv, prev_fin]

        year = data.get("year", "本期")
        try:
            prev_year = str(int(year) - 1)
        except (ValueError, TypeError):
            prev_year = "上期"

        x_curr = [x + bar_width / 2 for x in x_pos]
        x_prev = [x - bar_width / 2 for x in x_pos]

        ax.bar(x_prev, prev_vals, width=bar_width, label=f"{prev_year}年",
               color=COLOR_LIGHT_BLUE, edgecolor="white", linewidth=0.5)
        bars_curr = ax.bar(x_curr, current_vals, width=bar_width, label=f"{year}年",
                           color=colors_curr, edgecolor="white", linewidth=0.5)

        for bar in bars_curr:
            h = bar.get_height()
            va = "bottom" if h >= 0 else "top"
            ax.text(bar.get_x() + bar.get_width() / 2, h, f"{h:.1f}",
                    ha="center", va=va, fontsize=8, color=COLOR_DARK)
        ax.legend(loc="upper right", fontsize=9)
    else:
        ax.bar(x_pos, current_vals, width=bar_width * 1.5,
               color=colors_curr, edgecolor="white", linewidth=0.5)
        for i, (bar, val) in enumerate(zip(
            range(len(current_vals)), current_vals
        )):
            va = "bottom" if current_vals[i] >= 0 else "top"
            ax.text(x_pos[i], current_vals[i], f"{current_vals[i]:.1f}",
                    ha="center", va=va, fontsize=9, color=COLOR_DARK)

    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("金额（亿元）", fontsize=11)

    company = data.get("company_name", "")
    year_str = data.get("year", "")
    ax.set_title(
        f"{company} {year_str}年 现金流结构对比",
        fontsize=14, fontweight="bold",
    )

    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#cccccc")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, "cash_flow_structure.png")
    fig.savefig(path, dpi=CHART_DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Chart 6 – 运营效率指标 (efficiency_metrics.png)
# ---------------------------------------------------------------------------
def chart_efficiency_metrics(data, output_dir):
    """Horizontal bar chart of turnover / efficiency ratios.

    Computes AR turnover, inventory turnover, and total asset turnover from
    raw data.  Skips generation when no efficiency data can be computed.
    """
    revenue = safe_float(data.get("revenue"), default=None)
    cost_of_sales = safe_float(data.get("cost_of_sales"), default=None)
    total_assets = safe_float(data.get("total_assets"), default=None)

    ar = safe_float(data.get("trade_receivables"), default=None)
    prev_ar = safe_float(data.get("prev_trade_receivables"), default=None)
    inventory = safe_float(data.get("inventory"), default=None)
    prev_inventory = safe_float(data.get("prev_inventory"), default=None)
    prev_total_assets = safe_float(data.get("prev_total_assets"), default=None)

    metrics = []
    values = []

    # AR turnover
    if revenue and ar is not None and prev_ar is not None:
        avg_ar = (ar + prev_ar) / 2
        if avg_ar > 0:
            metrics.append("应收账款周转率")
            values.append(revenue / avg_ar)

    # Inventory turnover
    if cost_of_sales and inventory is not None and prev_inventory is not None:
        avg_inv = (inventory + prev_inventory) / 2
        if avg_inv > 0:
            metrics.append("存货周转率")
            values.append(cost_of_sales / avg_inv)

    # Total asset turnover
    if revenue and total_assets is not None and prev_total_assets is not None:
        avg_ta = (total_assets + prev_total_assets) / 2
        if avg_ta > 0:
            metrics.append("总资产周转率")
            values.append(revenue / avg_ta)

    if not metrics:
        return None

    colors = [COLOR_NAVY, COLOR_LIGHT_BLUE, COLOR_GREEN][:len(metrics)]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(metrics, values, color=colors, edgecolor="white",
                   linewidth=0.5, height=0.45)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}次", ha="left", va="center",
            fontsize=11, fontweight="bold", color=COLOR_DARK,
        )

    ax.set_xlabel("周转次数（次/年）", fontsize=11)

    company = data.get("company_name", "")
    year_str = data.get("year", "")
    ax.set_title(
        f"{company} {year_str}年 运营效率指标",
        fontsize=14, fontweight="bold",
    )

    ax.grid(axis="x", linestyle="--", alpha=0.4, color="#cccccc")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_val = max(values) if values else 10
    ax.set_xlim(0, max_val * 1.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "efficiency_metrics.png")
    fig.savefig(path, dpi=CHART_DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def generate_charts(data, output_dir):
    """Generate all 3 charts and return a manifest dict."""
    setup_chinese_font()

    paths = {
        "financial_overview": chart_financial_overview(data, output_dir),
        "profitability": chart_profitability(data, output_dir),
        "asset_structure": chart_asset_structure(data, output_dir),
    }

    seg_chart = chart_segment_margins(data, output_dir)
    if seg_chart:
        paths["segment_margins"] = seg_chart

    cf_chart = chart_cash_flow_structure(data, output_dir)
    if cf_chart:
        paths["cash_flow_structure"] = cf_chart

    eff_chart = chart_efficiency_metrics(data, output_dir)
    if eff_chart:
        paths["efficiency_metrics"] = eff_chart

    return paths


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"error": "Please provide JSON data as an argument."},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    try:
        # Parse optional --output-dir flag (v2.1)
        out_dir = None
        json_arg_idx = 1

        if sys.argv[1] == "--output-dir":
            if len(sys.argv) < 4:
                print(
                    json.dumps(
                        {"error": "--output-dir requires a path and JSON data argument."},
                        ensure_ascii=False,
                    )
                )
                sys.exit(1)
            out_dir = sys.argv[2]
            json_arg_idx = 3
        elif sys.argv[1].startswith("--output-dir="):
            out_dir = sys.argv[1].split("=", 1)[1]
            json_arg_idx = 2

        arg = sys.argv[json_arg_idx]
        parsed = json.loads(arg)

        # Unwrap single-key wrappers like {"financial_data": {...}} or {"data": {...}}
        if isinstance(parsed, dict):
            if len(parsed) == 1:
                only_value = next(iter(parsed.values()))
                if isinstance(only_value, dict):
                    parsed = only_value

        # Priority: --output-dir flag > OUTPUT_DIR env var > script directory
        if out_dir is None:
            out_dir = os.environ.get("OUTPUT_DIR") or os.path.dirname(
                os.path.abspath(__file__)
            )

        chart_paths = generate_charts(parsed, out_dir)
        result = {
            "charts": chart_paths,
            "output_dir": out_dir,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

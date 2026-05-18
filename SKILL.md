---
name: financial-report-analyzer
description: 专门用于上市公司财报（如年度报告、季度报告）的深度分析。该技能能够自动提取关键财务指标，计算核心财务比率，生成可视化图表，并结合行业背景生成专业的财务分析报告。v2.1 新增：标准化数据归档（manifest.json 主索引）、Python 环境指定（C:\anaconda\envs\financial）。
---

# 财报分析技能 (Financial Report Analyzer) v2.1

本技能旨在帮助 DB-GPT 系统化地分析上市公司财报，通过提取核心数据、计算财务比率、生成可视化图表并结合业务背景，产出高质量的财务分析报告。

## 核心工作流程

1. **数据提取与结构化**：
   - 使用 `execute_skill_script_file` 工具执行 `scripts/extract_financials.py` 脚本，传入财报文件路径（`file_path` 参数），自动提取营收、净利润、资产、负债等核心数值，以及分部数据、费用明细、运营KPI等扩展字段。
   - 脚本支持 PDF 文件（通过 pdfplumber 解析）和纯文本文件，返回 JSON 格式的结构化数据。
   - **重要**：提取后需人工核对关键数值，对提取缺失的字段（尤其港交所/IFRS术语）手动补充。

2. **财务比率计算**：
   - 使用 `execute_skill_script_file` 执行 `scripts/calculate_ratios.py`，传入 Step 1 的 JSON 数据。
   - 自动计算 60+ 模板占位符键值，包括毛利率、净利率、ROE、资产负债率、流动比率、周转率、净现比、自由现金流等指标，以及自动生成的分部收入表、费用结构表、偿债指标表、效率指标表、现金流质量表、BCG矩阵表等 HTML 代码块。
   - 参考 `references/financial_metrics.md` 确保指标定义的准确性。

3. **图表生成**：
   - 使用 `execute_skill_script_file` 执行 `scripts/generate_charts.py`，传入 Step 1 的 JSON 数据。
   - 自动生成最多 6 张可视化图表（条件生成，有数据才出图）：
     - `financial_overview.png`：核心财务指标对比柱状图（必生成）
     - `segment_margins.png`：分部收入与毛利率双轴图（有分部数据时生成）
     - `profitability.png`：盈利能力指标横向条形图（必生成）
     - `efficiency_metrics.png`：运营效率指标横向条形图（有周转数据时生成）
     - `cash_flow_structure.png`：现金流结构对比柱状图（有现金流数据时生成）
     - `asset_structure.png`：资产结构环形饼图（必生成）

4. **深度分析与BP视角撰写**：
   - 遵循 `references/analysis_framework.md` 提供的框架，从盈利质量、偿债风险、营运效率和现金流四个维度进行深度剖析。
   - 结合"经营情况讨论与分析"章节，解释业绩变动的核心驱动因素。
   - 撰写以下 13 段内容：
     **核心分析（7段）**：
     - `PROFITABILITY_ANALYSIS`：盈利能力分析（含分部毛利率梯度和费用控制）
     - `SOLVENCY_ANALYSIS`：偿债与风险分析
     - `EFFICIENCY_ANALYSIS`：营运效率分析
     - `CASHFLOW_ANALYSIS`：现金流与利润质量分析
     - `ADVANTAGES_LIST`：核心优势列表（HTML `<li>` 格式，3-4条）
     - `RISKS_LIST`：主要风险列表（HTML `<li>` 格式，3-4条）
     - `OVERALL_ASSESSMENT`：综合评价与展望
     **BP追问探针（3段）**— 使用 `.bp-callout` 格式：
     - `BP_PROBE_PROFITABILITY`：基于数据异常追问盈利质量
     - `BP_PROBE_SOLVENCY`：基于资产负债表异常追问风险
     - `BP_PROBE_CASHFLOW`：基于现金流异常追问利润含金量
     **BP决策支持（3段）**— 含 KPI badge 和红线预警：
     - `SEGMENT_STRATEGY`：各业务线的战略建议（含追踪KPI badge）
     - `RED_LINE_MANAGEMENT`：运营红线触发条件与措施
     - `CAPITAL_PLANNING`：短/中/长期资金规划路线图

5. **渲染报告**：
   - 读取 `templates/report_template.html`，直接填充所有 `{{PLACEHOLDER}}` 占位符。
   - 数据指标和HTML代码块来自 Step 2 的 `ratio_data`。
   - 分析文本来自 Step 4 的 LLM 撰写内容。
   - 图表路径使用绝对 `file:///` 路径。
   - 缺失数据填 "N/A"，可选章节（分部/运营KPI）无数据时保持空字符串。
   - 保存为 `<company_name>_<year>_财报分析报告.html`。

6. **完成**：
   - 返回简短的摘要（报告路径、2-3个关键发现、数据质量说明）。

## 更新说明 (v2.0)

相比 v1.0，v2.0 新增:
- 1.2 分部收入与增速（含分部毛利率图）
- 1.3 核心运营指标
- 费用结构表、偿债安全指标表、运营效率指标表、现金流质量指标表
- 3 BP视角决策建议（BCG矩阵/红线管理/资金规划）
- BP追问探针（.bp-callout / .red-line / .kpi-badge 组件）
- 图表从 3 张扩展到最多 6 张
- 提取脚本新增分部数据、费用明细、运营KPI、现金流细项
- 比率计算从 ~20 个占位符扩展到 60+ 个

## 更新说明 (v2.1)

相比 v2.0，v2.1 新增:
- 标准化数据归档：所有分析产出自动归档至 `C:/financial/data/{公司}/{期间}/` 目录
- 主索引文件 `manifest.json`：支持跨公司、跨期间的时间序列和行业对比分析
- Python 环境指定：统一使用 `C:\anaconda\envs\financial` conda 环境
- 图表输出目录可通过 `--output-dir` 参数指定，不再默认写入脚本目录
- 新增 `scripts/archive_data.py` 归档工具
- 修复 `plugin.json` 版本号与 `SKILL.md` 不一致问题

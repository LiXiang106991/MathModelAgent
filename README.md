# MathModelAgent — 数学建模国赛（CUMCM）全流程自动化 Skills

> 一套面向 Claude Code 的**全国大学生数学建模竞赛（CUMCM）**技能包。从赛题分析、建模设计、编码绘图到论文撰写与验收，全流程自动化、规范化、可复现，专为国赛 A/B/C 题定制。

---

## 📌 1. 项目解决什么问题

全国大学生数学建模竞赛（CUMCM，高教社杯）赛程约 **72 小时**，A/B/C 三题类型迥异：

- **A 题**：机理 / 连续问题（物理、工程机理，常需微分方程建模）；
- **B 题**：离散 / 优化问题（图论、规划、组合优化）；
- **C 题**：数据驱动问题（统计、大数据分析、预测）。

一支队伍要在三天内完成读题、拆解、建模、编程、绘图、写论文、验收的全流程，环节多、容错低：

- 读懂题面、拆解子问题、确定评价指标；
- 选择并建立数学模型，给出目标函数与约束；
- 编写可复现代码并跑出可信结果；
- 绘制论文可用的数据图表与流程图；
- 按国赛模板撰写并编译论文；
- 交付前自检格式、数值一致性与可复现性。

**人工在环节间切换时极易出现**：模型与代码不一致、数值前后矛盾、图表与结论对不上、模板格式出错、占位符漏删、论文无法编译等问题。

**本插件**把以上流程拆解为一组职责清晰的 Claude Code 技能，按固定顺序自动衔接。每个阶段产出结构化报告，把结论、数值、图表资产明确交付给下一阶段，从机制上避免"编造结论""数值不一致""格式违规"等国赛论文高频硬错误。

---

## ✨ 2. 主要功能

### 工作流技能（按顺序调用）

| 技能 | 阶段 | 主要产物 |
| --- | --- | --- |
| `1start-mathmodel` | 总控入口 | 询问用户偏好，生成 `plan.md`、`todo.md`，按顺序调度下游技能 |
| `2analysis-modeling` | 赛题分析与建模设计 | 子问题拆解、假设敏感性预检、数据理解、变量/目标函数/约束/求解策略 → `reports/ANALYSIS_MODELING_REPORT.md` |
| `3coding-visual` | 编程实现与数据图表 | 按建模报告编写可复现代码、运行求解、验证约束、生成数据驱动图表 PDF → `code/`、`results/`、`figures/`、`reports/RESULTS_REPORT.md` |
| `4drawio` | 非数据图示绘制 | 技术路线图、求解流程图、模型结构图等 DrawIO 图并导出 PDF → `figures/*.drawio`、`figures/*.pdf`、`reports/DRAWIO_REPORT.md` |
| `5writing` | 国赛论文撰写 | 按国赛写作模板组织章节、选择排版引擎、按章节直接插入图表 → `paper/` |
| `6verity` | 验证与验收 | 检查章节结构、图表引用、数值一致性、占位符、编译与视觉检查 → `reports/VERIFY_REPORT.md` |

### 国赛论文写作模板（`5writing` 依据）

| 文件 | 内容 |
| --- | --- |
| `mathmodel-writing-template.md` | 国赛论文写作规范**蒸馏版**：标题句式、摘要三段式（前言/逐问建模思路/总结升华）、问题重述防查重改写、问题分析三要素、五类模型假设、三线表符号说明、建模四步（预处理/建立/求解/分析）、模型检验、优缺点评价、参考文献格式速查、附录写作检查清单 |
| `main.tex` | 国赛 **LaTeX 模板**（对应 Typst `zh/cumcm`），`ctexart` + `xelatex` 编译，内置摘要页、目录页、参考文献、附录、三线表等自定义命令 |

支持 **Typst 与 LaTeX 双引擎**：Typst 使用 `typst compile`，LaTeX 使用 `xelatex`（跑两遍解决交叉引用）。

### 国赛模型选择库（`math-model-selection`）

按赛题关键词判断问题类型（评价 / 优化 / 预测 / 随机过程 / 智能优化），推荐对应模型：

> AHP、熵权法、TOPSIS、灰色关联、线性/非线性/0-1 规划、最小费用最大流、最短路、马尔可夫链、遗传算法、模拟退火、NSGA-II、时间序列

内置 **国赛 B/C 题关键词快速匹配库**、组合模型使用策略（评价+排序、预测+优化、整数规划+图论等）与"模型选择口诀"，覆盖国赛 A/B/C 题从读题到定模型的完整决策链。

### 方法知识库（`math-model-method.md`）

优化（线性/整数/非线性规划、最短路、最小费用最大流、TSP、模拟退火、遗传算法、NSGA-II）、预测（线性回归、灰色预测 GM(1,1)、时间序列、决策树/随机森林）、评价（AHP、熵权法、TOPSIS、灰色关联）三类方法文档，**内置 9 个可直接运行的 Python 实现**：

`ahp.py`、`entropy_topsis.py`、`grey_relation.py`、`grey_prediction.py`、`nsga2.py`、`random-forest.py`、`simulated.py`、`shortest-pash.py`、`linear_regression_utils.py`

### 工具技能

| 技能 | 作用 |
| --- | --- |
| `doctor` | 环境自检与安装向导：检测 typst / xelatex / python3 / drawio 及 Python 包是否就绪，缺失项按平台给出安装命令 |
| `typst-author` | Typst 文档写作辅助（语法、格式、编译排错） |
| `mathmodel-figure-templates` | 内置 11 个科研可视化绘图模板（配对云雨图、交叉验证 ROC、泰勒图、SHAP 蜂群柱状图、和弦图等），一键复刻 |

### 内部依赖

| 名称 | 作用 |
| --- | --- |
| `_references/math_modeling_norms.md` | 共享规范知识库：写作规范、题型防错速查、图表规范等，由各技能按需读取 |

---

## 🚀 3. 安装方法

### 前置条件

- 已安装 **Claude Code**（CLI 或 VS Code / JetBrains 扩展）。
- 可选运行时依赖（由 `doctor` 技能自动检测并给出安装命令）：
  - 论文编译：`xelatex`（TeX Live / MiKTeX，国赛中文模板必需）**或** `typst`
  - 数值计算与绘图：Python 3 + `numpy`、`scipy`、`pandas`、`matplotlib`、`scikit-learn`、`openpyxl`
  - 流程图导出（可选）：`drawio`
  - PDF 视觉检查（可选）：`pdftoppm` / `mutool` / `magick`

### 安装映射

仓库以扁平形式存放各技能的 SKILL 内容，按以下映射安装为 Claude Code 技能目录：

| 仓库文件 | 安装到 `.claude/skills/` |
| --- | --- |
| `SKILL.md` | `1start-mathmodel/SKILL.md` |
| `SKILL (1).md` | `2analysis-modeling/SKILL.md` |
| `SKILL (2).md` | `3coding-visual/SKILL.md` |
| `SKILL (3).md` | `4drawio/SKILL.md` |
| `SKILL (4).md` | `5writing/SKILL.md` |
| `SKILL (5).md` | `6verity/SKILL.md` |
| `doctor.md` | `doctor/SKILL.md` |
| `typst-author.md` | `typst-author/SKILL.md` |
| `math-model-selection.md` | `math-model-selection/SKILL.md` |
| `mathmodel-figure-templates.md` | `mathmodel-figure-templates/SKILL.md` |
| `math-model-method.md/` | `math-model-method.md/`（知识库目录） |
| `math_modeling_norms.md` | `_references/SKILL.md`（共享规范） |
| `mathmodel-writing-template.md`、`main.tex` | `5writing/`（国赛写作模板与 LaTeX 模板） |

### 方式 A：项目级安装（推荐）

在竞赛项目根目录创建技能目录，在**仓库根目录**执行：

```powershell
# Windows PowerShell
$dest = Join-Path (Get-Location) ".claude\skills"
$map = @{
  "SKILL.md"                 = "1start-mathmodel"
  "SKILL (1).md"             = "2analysis-modeling"
  "SKILL (2).md"             = "3coding-visual"
  "SKILL (3).md"             = "4drawio"
  "SKILL (4).md"             = "5writing"
  "SKILL (5).md"             = "6verity"
  "doctor.md"                = "doctor"
  "typst-author.md"          = "typst-author"
  "math-model-selection.md"  = "math-model-selection"
  "mathmodel-figure-templates.md" = "mathmodel-figure-templates"
}
foreach ($k in $map.Keys) {
  $d = Join-Path $dest $map[$k]
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  Copy-Item $k (Join-Path $d "SKILL.md") -Force
}
Copy-Item "math-model-method.md" (Join-Path $dest "math-model-method.md") -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $dest "_references") | Out-Null
Copy-Item "math_modeling_norms.md" (Join-Path $dest "_references\SKILL.md") -Force
Copy-Item "mathmodel-writing-template.md", "main.tex" (Join-Path $dest "5writing") -Force
```

```bash
# macOS / Linux
dest=".claude/skills"
map=(
  "SKILL.md:1start-mathmodel"
  "SKILL (1).md:2analysis-modeling"
  "SKILL (2).md:3coding-visual"
  "SKILL (3).md:4drawio"
  "SKILL (4).md:5writing"
  "SKILL (5).md:6verity"
  "doctor.md:doctor"
  "typst-author.md:typst-author"
  "math-model-selection.md:math-model-selection"
  "mathmodel-figure-templates.md:mathmodel-figure-templates"
)
mkdir -p "$dest"
for entry in "${map[@]}"; do
  src="${entry%%:*}"; name="${entry##*:}"
  mkdir -p "$dest/$name"
  cp "$src" "$dest/$name/SKILL.md"
done
cp -r "math-model-method.md" "$dest/"
mkdir -p "$dest/_references"
cp "math_modeling_norms.md" "$dest/_references/SKILL.md"
cp "mathmodel-writing-template.md" "main.tex" "$dest/5writing/"
```

### 方式 B：用户级安装（全局可用）

把技能复制到 Claude Code 的用户级技能目录，所有项目均可使用。命令同上，仅将目标目录改为：

```powershell
# Windows
$dest = Join-Path $env:USERPROFILE ".claude\skills"
```

```bash
# macOS / Linux
dest="$HOME/.claude/skills"
```

### 方式 C：使用 `skills.sh.json` 索引

仓库根目录提供 `skills.sh.json`，列出工作流技能、工具技能、知识库与内部依赖的组织结构，可作为安装清单对照。

> ⚠️ 安装后需要**重启 Claude Code 会话**，让新技能生效。

---

## 📖 4. 使用方法

### 一键启动完整流程

在比赛项目目录打开 Claude Code，启动入口技能：

```
/1start-mathmodel
```

或在对话中直接输入：

> 「开始数学建模国赛流程」

技能会先通过 AskUserQuestion 询问**关键偏好**（只问影响流程的少量问题）：

1. **排版引擎**：Typst 还是 LaTeX（决定 `5writing` 使用的模板与编译命令）
2. **赛题类型**：国赛 A / B / C 题
3. **子问题数量**：已知 N 个，还是待分析确定

回答后自动生成 `plan.md` 和 `todo.md`，并依次执行 6 个阶段：

```
赛题分析与建模设计(2analysis-modeling)
  → 编程实现和图表生成(3coding-visual)
  → 流程与架构图绘制(4drawio)
  → 国赛论文撰写(5writing)
  → 验证和验收(6verity)
```

### 环境自检

```
/doctor
```

检查完整工作流所需工具与 Python 包是否就绪，缺失项自动给出安装命令。

### 单独使用辅助技能

- `/typst-author` — 需要 Typst 写作帮助时
- `/math-model-selection` — 需要国赛模型选型建议时
- `/math-modeling-methods` — 需要查阅优化/预测/评价方法知识库或直接调用内置 Python 实现时

---

## 📥📤 5. 输入输出示例

### 输入

| 输入项 | 示例 |
| --- | --- |
| 赛题描述 | 2025 高教社杯全国大学生数学建模竞赛 C 题《NIPT 的时点选择与胎儿的异常判定》 |
| 数据附件 | `附件1.xlsx`、`附件2.csv`（放入项目目录） |
| 用户偏好 | 排版引擎：LaTeX；赛题类型：国赛 C 题；子问题数量：4 |

### 输出（项目目录结构）

```
.
├── plan.md                          # 1start-mathmodel 生成的整体方案
├── todo.md                          # 待办清单（阶段执行状态）
├── reports/
│   ├── ANALYSIS_MODELING_REPORT.md  # 2analysis-modeling：赛题分析与建模报告
│   ├── RESULTS_REPORT.md            # 3coding-visual：计算结果与校验报告
│   ├── DRAWIO_REPORT.md             # 4drawio：非数据图说明
│   └── VERIFY_REPORT.md             # 6verity：验收报告
├── code/                            # 3coding-visual：可复现代码
│   ├── problem1.py
│   ├── problem2.py
│   └── utils.py
├── results/                         # 3coding-visual：结果记录
├── figures/                         # 数据图 + 非数据图（PDF / drawio）
│   ├── fig_q1_error_dist.pdf
│   ├── fig_roadmap.drawio
│   └── fig_roadmap.pdf
└── paper/                           # 5writing：国赛论文
    ├── main.typ / main.tex          # 按所选引擎生成
    └── sections/                    # 各章节文件
```

### 一段完整工作流示例

```text
用户：/1start-mathmodel
Claude：请选择排版引擎？[LaTeX / Typst] → 用户：LaTeX
Claude：赛题类型？[A / B / C] → 用户：C
Claude：子问题数量？[已知/待分析] → 用户：4

→ 生成 plan.md、todo.md
→ 2analysis-modeling 产出 reports/ANALYSIS_MODELING_REPORT.md（4 个子问题的变量/模型/约束/求解策略）
→ 3coding-visual 产出 code/problem1~4.py、figures/*.pdf、reports/RESULTS_REPORT.md
→ 4drawio 产出 figures/fig_roadmap.drawio 及 PDF
→ 5writing 按国赛 LaTeX 模板产出 paper/main.tex → main.pdf
→ 6verity 逐项验收，输出 reports/VERIFY_REPORT.md，结论 PASS/FAIL
```

---

## 🧰 6. 项目文件结构

```text
SKILL.md                → 1start-mathmodel（工作流入口）
SKILL (1).md            → 2analysis-modeling（赛题分析与建模设计）
SKILL (2).md            → 3coding-visual（编程实现与图表生成）
SKILL (3).md            → 4drawio（非数据图示绘制）
SKILL (4).md            → 5writing（国赛论文撰写）
SKILL (5).md            → 6verity（验证与验收）
doctor.md               → doctor（环境检查）
typst-author.md         → typst-author（Typst 辅助）
math-model-selection.md → math-model-selection（国赛模型选择库 + B/C 题关键词匹配）
mathmodel-figure-templates.md → mathmodel-figure-templates（11 个科研绘图模板）

math-model-method.md/   → 方法知识库（优化/预测/评价三类 + Python 实现）
│   ├── all in.md          知识库索引
│   ├── optimization.md    优化类方法文档
│   ├── prediction.md      预测类方法文档
│   ├── evaluation.md      评价类方法文档
│   ├── ahp.py             层次分析法实现（含一致性检验）
│   ├── entropy_topsis.py  熵权法 + TOPSIS 实现
│   ├── grey_relation.py   灰色关联分析实现
│   ├── grey_prediction.py 灰色预测 GM(1,1) 实现
│   ├── nsga2.py           NSGA-II 多目标优化实现
│   ├── random-forest.py   决策树 / 随机森林实现
│   ├── simulated.py       模拟退火实现
│   ├── shortest-pash.py   最短路实现
│   └── linear_regression_utils.py 线性回归工具

mathmodel-writing-template.md → 国赛论文写作规范蒸馏版（5writing 依据）
main.tex                    → 国赛 LaTeX 模板（对应 Typst zh/cumcm）
math_modeling_norms.md      → _references 共享规范知识库
skills.sh.json              → 技能索引清单
```

> 完整可运行的技能目录（含 `5writing` 的全部论文模板、`6verity` 的检查脚本）以安装后的技能文件夹为准。

---

## 📄 7. 许可证

本项目使用 MIT 许可证，详见 [LICENSE](LICENSE)。

---

## 🙏 8. 贡献

欢迎通过 Issue 或 Pull Request 贡献：补充国赛模板、修复技能逻辑、完善方法知识库。也欢迎提交你在真实国赛中（A/B/C 题）使用本插件产生的示例项目。

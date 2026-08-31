# 数据工具：画像生成器 + 查询助手 + L1 中间层

数学建模国赛专用：**AI 不读全量数据也能了解所有数据**，且不浪费 token、不产生幻觉。

```
tools/
├── csv_io.py           # 共享底层：编码识别 + 紧凑 markdown 输出
├── gen_data_profile.py # 工具1：一键生成数据画像 .md
├── query_data.py       # 工具2：数据查询助手（按需从全量 CSV 取数）
├── l1_build.py         # 工具3：L1 中间层构建器（预聚合缓存表，通用）
├── l1_loader.py        # 工具3配套：建模脚本快速读取 L1 表
└── test_tools.py       # 冒烟测试：python tools/test_tools.py
```

---

## 为什么需要这两个工具

一份 9.6 万行（402 供应商 × 240 周）的原始 CSV：

| 方式 | 体积 | 进对话的 token |
|---|---|---|
| 直接把原始 CSV 发给 AI | 2.8 MB | ≈ 1,100 万（远超任何模型上下文）|
| 先生成画像再喂 AI | 4.3 KB | ≈ 4,500（压缩约 2400 倍）|

关键分工：
- **画像（工具1）**：让 AI 一次看清「全部数据的结构 + 统计规律」，几秒钟生成一次；
- **查询（工具2）**：AI 建模过程中需要某个精确数字时，命令行按需取数，只把结果带进对话。

两者配合 = 数据永远不整份进对话，AI 也永远不会"凭印象编数据"。

---

## 工具1：数据画像生成器

```bash
# 生成画像并打印到屏幕
python tools/gen_data_profile.py 数据.csv

# 生成画像并写入 .md 文件（推荐，可直接作为附件发给 AI）
python tools/gen_data_profile.py 数据.csv --out 数据画像.md --label "供应商供货数据"

# 带分组汇总（多列用逗号分隔）
python tools/gen_data_profile.py 数据.csv --group 材料分类,年份 --out 数据画像.md
```

自动识别 UTF-8 / GBK 编码，自动把日期列识别出来。

输出包含 7 个区块：**数据概览 / 样本预览 / 数值列分布 / 类别列取值 / 相关性矩阵 / 时间列分析 / 分组汇总**，末尾附带 token 估算。

> 注意：字段的「业务含义」无法自动推断，可在生成后再手工补一列"含义"。

---

## 工具2：数据查询助手

建模过程中 AI（或你）需要精确数字时调用：

```bash
# 看样本
python tools/query_data.py head 数据.csv -n 10

# 列结构
python tools/query_data.py schema 数据.csv

# 数值分布
python tools/query_data.py describe 数据.csv --cols 供货量,周序号

# 缺失率 / 零值占比
python tools/query_data.py missing 数据.csv

# 分组聚合（聚合函数用逗号分隔，多列用分号分隔）
python tools/query_data.py group 数据.csv --by 材料分类,年份 --agg "供货量:sum,mean,std; 户均供货量:max"

# 条件取行（pandas query 语法，中文列名直接可用）
python tools/query_data.py filter 数据.csv --where "材料分类 == 'A' and 供货量 > 0" -n 20

# 相关系数矩阵
python tools/query_data.py corr 数据.csv

# 计数
python tools/query_data.py count 数据.csv --where "供货量 == 0"

# 任意 pandas 表达式（df 已预定义）—— 复杂指标用这个兜底
python tools/query_data.py expr 数据.csv "df[df['供货量'] > 30000][['供应商ID', '周次']]"
```

约束：结果默认最多打印 50 行（自动截断）；`--where` 列名含**空格、括号、特殊字符**（如 `销量(千克)`、`批发价格(元/千克)`）时用反引号包住（`` `周 序号` == 1 ``、`` `批发价格(元/千克)` >= 0.5 ``）。

---

## 工具3：L1 中间层构建器（通用，不绑定任何一道赛题）

画像和查询解决"AI 怎么看数据"，**中间层解决"建模脚本怎么跑得快"**。

原始表可能几十 MB、上百万行，建模脚本每轮都重读一次又慢又耗内存。L1 构建器把原始明细**预聚合为小型缓存表**（建一次，反复用），建模脚本秒级读入。

### 自动检测（无需了解题目字段也能用）

| 角色 | 自动规则 |
|---|---|
| 日期列 | datetime 列，或字符串可解析比例≥70% 且**年份落在 1900–2100**（15 位数字编码不会误判）|
| 度量列 | 数值列（排除 id 列与低基数标记列）|
| id 列 | 名字含「编码/编号/ID/code」或高基数数值（唯一值≥100 且占比≥1%）|
| 标记列 | 唯一值≤10 的数值列（如 0/1），不参与聚合 |
| 分组列 | 低基数（<200）类别列；也可 `--group` 显式指定 |

### 用法

```bash
# 销售流水式事实表（显式角色 + 过滤，推荐）
python tools/l1_build.py 附件2.xlsx --out l1 \
    --date 销售日期 --group 单品编码 --measures 销量,销售单价 \
    --where '销售类型=="销售"'

# 批发价表（带异常值过滤）
python tools/l1_build.py 附件3.xlsx --out l1 \
    --date 日期 --group 单品编码 --measures 批发价格 --where '批发价格>=0.5'

# 维度表（无日期无度量）→ 自动输出全量映射 _map.csv
python tools/l1_build.py 附件1.xlsx --out l1

# 完全自动：什么参数都不传
python tools/l1_build.py 附件1.xlsx 附件2.xlsx --out l1
```

### 产出（`l1/<文件主名>/`）

```
_dictionary.md      L0 数据字典（列/类型/角色/缺失率/样例）
_overview.csv       逐列统计
daily.csv           按日期聚合（sum/mean/count）        [需日期列]
weekly.csv          按周聚合
monthly.csv         按月聚合
daily_by_group.csv  日期 × 分组 长表                    [需日期+分组]
_map.csv            维度表全量映射（id + 属性）         [无日期无度量的表]
_vc_<列>.csv        分组列取值计数
_meta.json          机器可读检测结果（建模脚本据此加载）
```

### 建模脚本里怎么读（不用再碰原始 xlsx）

```python
from tools.l1_loader import load, meta

m = meta("l1", "附件2")                      # 检测结果：主日期/度量/分组
fact = load("l1", "附件2")                   # daily_by_group.csv
daily = load("l1", "附件2", "daily")         # daily.csv

# 事实表对齐维度表补类别
item = load("l1", "附件1", "_map")           # 单品编码 -> 分类名称
fact = fact.merge(item, on="单品编码")
cat_daily = fact.groupby(["销售日期", "分类名称"])[["销量_sum"]].sum()
```

---

## 三个工具怎么配合（数据四层架构）

```
L0 数据字典    ←  gen_data_profile 生成画像 + l1_build 生成 _dictionary.md
L1 中间层表    ←  l1_build 物化（daily / daily_by_group / _map）→ 建模脚本秒级读
L2 原始明细    ←  附件 xlsx，永远只被 l1_build / 建模脚本读一次
L3 结果表      ←  建模脚本输出的 摘要.json + 明细.csv，AI 只读结果解释
```

- AI 理解数据 → 读画像（工具1）
- AI 取精确数字 → 调 query_data（工具2）
- 建模脚本要快 → 读 L1（工具3）
- 论文每个数字 → 都能溯源到 L3 结果表

---

## 比赛工作流建议

```
1. 拿到赛题附件 → 放项目目录
2. 跑一次 l1_build → 得到 L1 缓存表（同时得到每份附件的数据字典）
3. 跑一次画像生成器 → 得到"数据画像.md"（几千 token）
4. 把「赛题 .md + 数据字典 + 数据画像.md」一起发给 AI
5. AI 建模脚本全部基于 L1 表运行（秒级），需要精确数字 → 调 query_data 取数
6. 论文里的所有数字都来自 L1/L3 输出，AI 不记忆、不编造
```

## 自检

```bash
python tools/test_tools.py   # 冒烟测试：编码识别 / 截断 / 画像 / 全部子命令
```

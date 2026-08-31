# -*- coding: utf-8 -*-
"""
L1 中间层快速读取器
================================================================
建模脚本用这个模块读 l1_build.py 物化的缓存表 —— 秒级读入,
不需要再碰几十 MB 的原始 xlsx。

用法
----
from tools.l1_loader import meta, load, table_path

m = meta("l1", "附件2")            # 读取 _meta.json (检测结果/列角色)
df = load("l1", "附件2")           # 默认读 daily_by_group.csv
df = load("l1", "附件2", "daily")  # 读 daily.csv
item = load("l1", "附件1", "_map") # 读维度映射表

# 典型 join 模式: 事实表(附件2) 对齐 维度表(附件1) 的类别
item = load("l1", "附件1", "_map")          # 单品编码 -> 分类名称
fact = load("l1", "附件2")                   # 日期 x 单品编码 的聚合
fact = fact.merge(item, on="单品编码")        # 补充分类
cat_daily = fact.groupby(["销售日期", "分类名称"])[["销量_sum", "销售额_sum"]].sum()
"""
import json
import os

import pandas as pd


def table_path(out, stem, table="daily_by_group"):
    """返回 L1 缓存表完整路径。"""
    return os.path.join(out, stem, f"{table}.csv")


def meta(out, stem):
    """读取 _meta.json: 返回 dict(rows/cols/primary_date/measures/groups/tables)。"""
    p = os.path.join(out, stem, "_meta.json")
    if not os.path.exists(p):
        raise FileNotFoundError(f"未找到 L1 元数据: {p} (请先运行 tools/l1_build.py)")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load(out, stem, table="daily_by_group", **kw):
    """读一张 L1 缓存表。默认读 daily_by_group.csv。

    常用表名: daily / weekly / monthly / daily_by_group / _map / _overview
    """
    p = table_path(out, stem, table)
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"未找到表 {table} (路径 {p})。该文件可能没有日期列或度量列, "
            "请查看 _meta.json 的 tables 列表。")
    return pd.read_csv(p, **kw)


def available(out, stem):
    """列出该文件已物化的全部 L1 表。"""
    m = meta(out, stem)
    return m.get("tables", [])


def dictionary(out, stem):
    """返回 L0 数据字典 markdown 文本。"""
    p = os.path.join(out, stem, "_dictionary.md")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

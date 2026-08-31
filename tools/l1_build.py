# -*- coding: utf-8 -*-
"""
L1 中间层构建器（通用 · 适用于任意赛题数据）
================================================================
把 xlsx/csv 原始明细(L2, 细粒度可达千万行) 预聚合为小型缓存表(L1),
让建模脚本秒级读入, 而不是每轮都重读几十 MB 的原始表。

与 画像生成器/查询助手 的分工:
    画像(gen_data_profile)   -> AI 快速"看懂"数据结构        (一次性, 静态)
    查询(query_data)         -> AI 按需取精确数字             (随时, 单次)
    本工具(l1_build)         -> 建模脚本的"预聚合数据源"      (建一次, 反复用)

用法示例
--------
# 最简: 全部自动检测
python tools/l1_build.py 附件1.xlsx 附件2.xlsx 附件3.xlsx --out l1

# 销售流水这类事实表, 显式指定角色 + 过滤(推荐)
python tools/l1_build.py 附件2.xlsx --out l1 --date 销售日期 \
    --group 单品编码 --measures 销量,销售单价 --where '销售类型=="销售"'

# 维度表(无日期无度量)不传任何参数, 自动输出全量映射表 _map.csv
python tools/l1_build.py 附件1.xlsx --out l1

自动检测规则
------------
- 日期列 : datetime 列, 或字符串列可解析比例>=0.7 且年份落在 1900-2100;
          名字含"日期/date/时间/time"者优先当选主日期
- 度量列 : 数值列(排除 id 列与低基数标记列)
- id 列  : 名字含"编码/编号/id/code" 或 高基数数值(唯一值>=100 且占比>=1%)
- 标记列 : 唯一值<=10 的数值列(如 0/1), 不参与聚合, 自动进分组候选
- 分组列 : 低基数(<200)类别列(自动); 显式 --group 时仅用显式列

输出(out/<文件主名>/)
    _dictionary.md      L0 数据字典(列名/类型/角色/缺失率/样例)
    _overview.csv       逐列统计(缺失率/唯一值/极值/均值)
    daily.csv           按日期聚合(sum/mean/count)         [需日期列]
    weekly.csv          按周聚合                          [需日期列]
    monthly.csv         按月聚合                          [需日期列]
    daily_by_group.csv  日期 x 分组 长表                   [需日期列+分组列]
    _map.csv            维度表全量映射(id + 属性)          [无日期无度量的表]
    _vc_<列>.csv        分组列取值计数                     [有分组列]
    _meta.json          机器可读检测结果(建模脚本据此加载)

配套读取: tools/l1_loader.py
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from tools.csv_io import to_markdown  # 从项目根目录运行时
except ImportError:
    from csv_io import to_markdown        # 直接 python tools/l1_build.py 时

DATE_NAME = re.compile(r"日期|date|时间|time", re.I)
ID_NAME = re.compile(r"编码|编号|id|code", re.I)
FLAG_NAME = re.compile(r"是否|标志|flag|打折|折扣|有效|有无", re.I)

MAX_CAT = 200     # 低基数阈值(高于它不自动分组)
FLAG_MAX = 3      # 数值标记列阈值(且名字像标志位时才当标记)
PARSE_RATE = 0.7  # 日期列可解析比例门槛
YEAR_MIN, YEAR_MAX = 1900, 2100  # 合法日期年份区间


def read_file(path):
    """按扩展名读取 xlsx 或 csv, 统一列名(去首尾空白)。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, encoding=detect_encoding(path))
    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_encoding(path):
    """csv 编码探测: 依次试 utf-8-sig / gb18030 / gbk, 兜底 gb18030。"""
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                f.read(200000)
            return enc
        except UnicodeDecodeError:
            continue
    return "gb18030"


def _column_info(df):
    """逐列信息: dtype / 缺失率 / 类型(kind) / 唯一值 / 日期解析率。"""
    info = {}
    for c in df.columns:
        s = df[c]
        row = {"dtype": str(s.dtype), "na": float(s.isna().mean()),
               "nunique": int(s.nunique())}
        if pd.api.types.is_datetime64_any_dtype(s):
            row["kind"] = "datetime"
        elif pd.api.types.is_numeric_dtype(s):
            row["kind"] = "numeric"
            row["nunique"] = int(s.nunique())
        else:
            sample = s.dropna().head(5000)
            row["nunique"] = int(s.nunique())
            if not sample.empty:
                parsed = pd.to_datetime(sample, errors="coerce")
                rate = float(parsed.notna().mean())
                if rate >= PARSE_RATE:
                    years = parsed.dt.year.dropna()
                    yr_ok = float(((years >= YEAR_MIN) & (years <= YEAR_MAX)).mean())
                    if yr_ok >= PARSE_RATE:
                        row["kind"] = "datetime"
                        row["date_rate"] = rate
                        info[c] = row
                        continue
            row["kind"] = "object"
        info[c] = row
    return info


def _is_id_like(s, nunique, n):
    """id 列判据: 名字含"编码/编号/id/code", 或高基数(>=100 且占比>=1%)的
    整型/超大数值(疑似编码)。连续 float 度量(如单价)不会被误判。"""
    if ID_NAME.search(str(s.name)):
        return True
    if nunique >= 100 and nunique / n >= 0.01:
        if pd.api.types.is_integer_dtype(s):
            return True
        try:
            if float(pd.to_numeric(s, errors="coerce").abs().max()) >= 1e9:
                return True
        except (TypeError, ValueError):
            pass
    return False


def _is_flag(s):
    """标记列判据: 0/1 二值列, 或唯一值<=FLAG_MAX 且列名像标志位(是否/标志/打折等)。
    普通低基数的数值度量(如损耗率只取几档)不会被误伤。"""
    vals = set(pd.unique(s.dropna()))
    if vals <= {0, 1}:
        return True
    return len(vals) <= FLAG_MAX and bool(FLAG_NAME.search(str(s.name)))


def detect_roles(df, info):
    """按自动规则检测: 主日期 / id列 / 度量列 / 分组列 / 标记列。"""
    n = len(df)
    date_cols = [c for c, v in info.items() if v["kind"] == "datetime"]

    def _rank(c):
        # (名字像日期, 解析率) 排序, 名字像日期优先
        rate = info[c].get("date_rate", 1.0)
        return (1 if DATE_NAME.search(c) else 0, rate)
    primary_date = max(date_cols, key=_rank) if date_cols else None

    id_cols, flag_cols, measures, cat_cols = [], [], [], []
    for c, v in info.items():
        if v["kind"] == "datetime":
            continue
        if v["kind"] == "numeric":
            is_id = _is_id_like(df[c], v["nunique"], n)
            if is_id:
                id_cols.append(c)
            elif _is_flag(df[c]):
                flag_cols.append(c)
            else:
                measures.append(c)
        else:  # object
            if v["nunique"] <= MAX_CAT:
                cat_cols.append(c)
    auto_groups = cat_cols + flag_cols
    return {
        "primary_date": primary_date,
        "id_cols": id_cols,
        "measures": measures,
        "auto_groups": auto_groups,
        "flag_cols": flag_cols,
        "cat_cols": cat_cols,
    }


def _flatten_columns(columns):
    """把 groupby/agg 产生的 MultiIndex 压平成 "销量_sum" 风格列名。"""
    out = []
    for pair in columns:
        if isinstance(pair, tuple):
            out.append(f"{pair[0]}_{pair[1]}" if pair[1] else str(pair[0]))
        else:
            out.append(str(pair))
    return out


_AGGS = ["sum", "mean", "count"]


def _write_agg(g, path):
    g.columns = _flatten_columns(g.columns)
    g.to_csv(path, index=False, encoding="utf-8-sig")


def _safe_resample(d, freq):
    try:
        return d.resample(freq).agg([a for a in _AGGS])
    except ValueError:  # pandas 旧版本无 'ME', 退回 'M'
        return d.resample("M").agg([a for a in _AGGS])


def materialize(path, out, date=None, groups=None, measures=None, where=None):
    """对单个文件构建 L1。返回检测与产出信息 dict。"""
    df = read_file(path)
    if where:
        df = df.query(where)
    df = df.dropna(how="all")

    info = _column_info(df)
    roles = detect_roles(df, info)
    date = date or roles["primary_date"]
    measures = list(measures) if measures else roles["measures"]
    groups = list(groups) if groups else roles["auto_groups"]
    groups = [g for g in groups if g in df.columns and g != date]

    # 过滤传入的度量/分组里可能存在的非法列
    measures = [m for m in measures if m in df.columns and info[m]["kind"] == "numeric"]
    groups = [g for g in groups if g != date and info.get(g, {}).get("kind") != "datetime"]

    if date:
        df[date] = pd.to_datetime(df[date], errors="coerce")
        df = df.dropna(subset=[date]).sort_values(date)

    stem = os.path.splitext(os.path.basename(path))[0]
    d = os.path.join(out, stem)
    os.makedirs(d, exist_ok=True)

    tables = []

    # ---- 维度表: 无日期无度量 -> 全量映射 ----
    if not date and not measures:
        df.drop_duplicates().to_csv(os.path.join(d, "_map.csv"),
                                    index=False, encoding="utf-8-sig")
        tables.append("_map.csv")

    # ---- 分组列取值计数 ----
    for g in groups:
        vc = df[g].value_counts(dropna=False).rename_axis(g).reset_index(name="行数")
        if len(vc) > MAX_CAT:
            vc = vc.head(MAX_CAT)
        vc.to_csv(os.path.join(d, f"_vc_{g}.csv"), index=False, encoding="utf-8-sig")
        tables.append(f"_vc_{g}.csv")

    # ---- 逐列统计总览 ----
    overview = []
    for c, v in info.items():
        s = df[c]
        row = {"列": c, "类型": v["dtype"], "缺失率": round(v["na"], 4)}
        if v["kind"] == "numeric":
            s2 = s.dropna()
            row.update({"唯一值": v["nunique"],
                        "min": round(float(s2.min()), 4) if len(s2) else None,
                        "max": round(float(s2.max()), 4) if len(s2) else None,
                        "mean": round(float(s2.mean()), 4) if len(s2) else None})
        elif v["kind"] == "datetime":
            s2 = s.dropna()
            row.update({"唯一值": v["nunique"],
                        "min": str(s2.min()), "max": str(s2.max())})
        else:
            row["唯一值"] = v["nunique"]
        overview.append(row)
    pd.DataFrame(overview).to_csv(os.path.join(d, "_overview.csv"),
                                  index=False, encoding="utf-8-sig")
    tables.append("_overview.csv")

    # ---- 按日期聚合: daily / weekly / monthly ----
    if date and measures:
        aggs = {m: [a for a in _AGGS] for m in measures}
        daily = df.groupby(date, as_index=False)[measures].agg(aggs)
        _write_agg(daily, os.path.join(d, "daily.csv"))
        tables.append("daily.csv")

        di = df.set_index(date)
        for label, freq in (("weekly", "W"), ("monthly", "ME")):
            r = _safe_resample(di[measures], freq)
            r = r.reset_index()
            _write_agg(r, os.path.join(d, f"{label}.csv"))
            tables.append(f"{label}.csv")

        # ---- 日期 x 分组 长表 ----
        if groups:
            g = df.groupby([date] + groups, as_index=False)[measures].agg(aggs)
            _write_agg(g, os.path.join(d, "daily_by_group.csv"))
            tables.append("daily_by_group.csv")

    # ---- L0 数据字典 ----
    role_map = {c: "日期" for c in (info.get("primary_date") and [info["primary_date"]] or [])}
    role_map.update({c: "id" for c in roles["id_cols"]})
    role_map.update({c: "度量" for c in measures})
    role_map.update({c: "分组" for c in groups})
    role_map.update({c: "标记" for c in roles["flag_cols"]})
    role_map.update({c: "描述" for c in roles["cat_cols"]})

    dict_rows = []
    for c, v in info.items():
        s = df[c]
        sample = " | ".join(str(x) for x in s.dropna().astype(str).head(3).tolist())
        dict_rows.append({"列": c, "类型": v["dtype"], "角色": role_map.get(c, "—"),
                          "缺失率": f"{v['na']:.1%}", "唯一值": v["nunique"],
                          "样例": sample[:60]})
    dict_md = f"# {stem} 数据字典 (L0 · 由 l1_build 自动生成)\n\n"
    dict_md += f"- 行数: {len(df):,}  列数: {df.shape[1]}  主日期: {date or '无'}\n"
    dict_md += f"- 过滤: {where or '无'}\n"
    dict_md += "\n| 列 | 类型 | 角色 | 缺失率 | 唯一值 | 样例 |\n"
    dict_md += "|---|---|---|---|---|---|\n"
    for r in dict_rows:
        dict_md += f"| {r['列']} | {r['类型']} | {r['角色']} | {r['缺失率']} | {r['唯一值']} | {r['样例']} |\n"
    dict_md += f"\n- 已物化 L1 表: {', '.join(tables)}\n"
    dict_md += "- 读取方式: `from tools.l1_loader import load` (见 tools/README.md)\n"
    with open(os.path.join(d, "_dictionary.md"), "w", encoding="utf-8") as f:
        f.write(dict_md)
    tables.append("_dictionary.md")

    meta = {
        "file": path, "stem": stem,
        "rows": int(len(df)), "cols": list(df.columns),
        "primary_date": date, "measures": measures, "groups": groups,
        "id_cols": roles["id_cols"], "flag_cols": roles["flag_cols"],
        "where": where, "tables": tables,
    }
    with open(os.path.join(d, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # ---- 控制台反馈 ----
    print(f"\n[{stem}]  {len(df):,} 行 × {df.shape[1]} 列")
    print(f"  主日期: {date or '无'}  度量: {measures or '无'}  分组: {groups or '无'}")
    print(f"  id列: {roles['id_cols'] or '无'}  标记列: {roles['flag_cols'] or '无'}")
    print(f"  已物化: {', '.join(tables)}")
    return meta


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="l1_build.py",
        description="L1 中间层构建器：把任意 xlsx/csv 原始明细预聚合为小型缓存表")
    p.add_argument("files", nargs="+", help="xlsx/csv 路径(可多个)")
    p.add_argument("--out", default="l1", help="输出目录(默认 l1/)")
    p.add_argument("--date", help="日期列名(默认自动检测)")
    p.add_argument("--group", help="分组列, 逗号分隔(默认自动检测低基数列; 显式传入则仅用这些列)")
    p.add_argument("--measures", help="度量列, 逗号分隔(默认自动检测数值列)")
    p.add_argument("--where", help=("pandas query 过滤; 列名含 空格/括号/特殊字符 时用反引号包住, "
                                    "如 '`销售类型`==\"销售\"' 或 '`批发价格(元/千克)`>=0.5'"))
    a = p.parse_args(argv)

    groups = [g.strip() for g in a.group.split(",")] if a.group else None
    measures = [m.strip() for m in a.measures.split(",")] if a.measures else None
    os.makedirs(a.out, exist_ok=True)
    metas = []
    for f in a.files:
        metas.append(materialize(f, a.out, date=a.date, groups=groups,
                                 measures=measures, where=a.where))
    print(f"\n完成: {len(metas)} 个文件已构建 L1 至 {a.out}/")


if __name__ == "__main__":
    main()

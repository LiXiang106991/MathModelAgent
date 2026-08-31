# -*- coding: utf-8 -*-
"""
query_data：数据查询助手 —— 建模过程中按需从全量 CSV 取数，只把结果带进对话。

用法（建模时 AI 需要精确数字，直接命令行调用它）
------------------------------------------------
    python tools/query_data.py head     数据.csv -n 10
    python tools/query_data.py schema   数据.csv
    python tools/query_data.py describe 数据.csv --cols 供货量,周序号
    python tools/query_data.py missing  数据.csv
    python tools/query_data.py group    数据.csv --by 材料分类,年份 --agg 供货量:sum,mean,std
    python tools/query_data.py filter   数据.csv --where "材料分类 == 'A' and 供货量 > 0" -n 20
    python tools/query_data.py corr     数据.csv
    python tools/query_data.py count    数据.csv --where "供货量 == 0"
    python tools/query_data.py expr     数据.csv "df[df['供货量']>30000][['供应商ID','周次']]"

约定
----
- 子命令之后第一个位置参数都是 CSV 路径（自动识别 UTF-8 / GBK）。
- group 的 --agg 格式：`列:聚合1,聚合2; 列2:聚合3`，多个列用分号分隔。
- 结果默认最多 50 行，超出自动截断，避免刷屏。
- expr 子命令：传一行 pandas 表达式（df 已预定义）；多行代码请用 ; 分隔
  或换行，并把最终结果赋值给 __result__。
- --where 使用 pandas query 语法；列名含空格/特殊字符时用反引号包住，
  如 `` `周 序号` == 1 ``。
"""

import argparse

import numpy as np
import pandas as pd

from csv_io import read_csv, to_markdown


# ---------------------------------------------------------------------------
# 各子命令
# ---------------------------------------------------------------------------
def cmd_head(df, args):
    cols = [c.strip() for c in args.cols.split(",")] if args.cols else None
    sub = df[cols] if cols else df
    print(to_markdown(sub.head(args.n)))


def cmd_schema(df, args):
    rows = []
    for c in df.columns:
        d = df[c]
        if pd.api.types.is_numeric_dtype(d):
            t = "数值"
        elif pd.api.types.is_datetime64_any_dtype(d):
            t = "日期"
        else:
            t = "类别"
        rows.append([c, t, d.nunique(dropna=True), f"{d.isna().mean() * 100:.1f}%"])
    out = pd.DataFrame(rows, columns=["列名", "类型", "唯一值数", "缺失率"])
    print(to_markdown(out, max_rows=60))


def cmd_describe(df, args):
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if args.cols:
        num = [c for c in args.cols.split(",") if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not num:
        print("（没有可用的数值列）")
        return
    st = df[num].describe(percentiles=[0.25, 0.5, 0.75]).T
    st = st[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    st["零值占比"] = [(df[c] == 0).mean() for c in num]
    st = st.reset_index().rename(columns={"index": "列名"})
    print(to_markdown(st, max_rows=60))


def cmd_missing(df, args):
    rows = []
    for c in df.columns:
        zero = f"{(df[c] == 0).mean() * 100:.2f}%" if pd.api.types.is_numeric_dtype(df[c]) else "—"
        rows.append([c, f"{df[c].isna().mean() * 100:.2f}%", zero])
    out = pd.DataFrame(rows, columns=["列名", "缺失率", "零值占比"])
    print(to_markdown(out, max_rows=60))


def cmd_group(df, args):
    by = [c.strip() for c in args.by.split(",")]
    for c in by:
        if c not in df.columns:
            print(f"列不存在：{c}")
            return
    if args.agg:
        # 格式：列:agg1,agg2; 列2:agg3   （多个列用分号分隔，避免与聚合函数里的逗号冲突）
        spec = {}
        for seg in args.agg.split(";"):
            col, _, aggs = seg.partition(":")
            col = col.strip()
            if not col or col not in df.columns:
                print(f"列不存在：{col or '(空)'}")
                return
            spec[col] = [a.strip() for a in (aggs or "sum").split(",") if a.strip()]
    else:
        spec = {c: ["sum", "mean"] for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    if not spec:
        print("（没有可聚合的数值列）")
        return
    g = df.groupby(by).agg(spec)
    if isinstance(g.columns, pd.MultiIndex):
        g.columns = ["_".join(str(x) for x in t if x != "") for t in g.columns]
    g = g.reset_index()
    sum_cols = [c for c in g.columns if str(c).endswith("_sum")]
    if sum_cols:
        g = g.sort_values(sum_cols[0], ascending=False)
    print(to_markdown(g))


def cmd_filter(df, args):
    try:
        sub = df.query(args.where)
    except Exception as e:  # noqa: BLE001
        print(f"查询语法错误：{e}")
        return
    if args.cols:
        cols = [c.strip() for c in args.cols.split(",") if c.strip() in sub.columns]
        sub = sub[cols]
    note = "" if len(sub) <= args.n else f"，显示前 {args.n} 行"
    print(f"匹配 {len(sub):,} 行{note}")
    print(to_markdown(sub.head(args.n)))


def cmd_corr(df, args):
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if args.cols:
        num = [c for c in args.cols.split(",") if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(num) < 2:
        print("（数值列不足 2 列）")
        return
    corr = df[num].corr()
    corr = corr.reset_index().rename(columns={"index": "列名"})
    print(to_markdown(corr, prec=2, max_rows=40))


def cmd_count(df, args):
    if args.where:
        try:
            n = len(df.query(args.where))
        except Exception as e:  # noqa: BLE001
            print(f"查询语法错误：{e}")
            return
    else:
        n = len(df)
    print(f"{n:,}")


def cmd_expr(df, args):
    code = args.code
    ns = {"df": df, "pd": pd, "np": np}
    stripped = code.strip()
    # 单行表达式 → 包装成赋值；否则按代码块执行，须自行赋值 __result__
    if "\n" not in stripped and ";" not in stripped and "__result__" not in code:
        code = "__result__ = (" + stripped + ")"
    try:
        exec(code, ns)  # noqa: S102 - 本地自有数据，AI 自己调用
    except Exception as e:  # noqa: BLE001
        print(f"执行出错：{e}")
        return
    result = ns.get("__result__")
    if result is None:
        print("（执行完成，未找到 __result__；多行代码请把最终结果赋值给 __result__）")
        return
    if isinstance(result, pd.DataFrame):
        print(to_markdown(result))
    elif isinstance(result, pd.Series):
        print(to_markdown(result.to_frame()))
    else:
        print(result)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def _add_common(sp):
    sp.add_argument("csv", help="CSV 文件路径")


def build_parser():
    p = argparse.ArgumentParser(prog="query_data", description="数据查询助手：按需从全量 CSV 取数")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("head", help="查看样本行")
    _add_common(sp)
    sp.add_argument("-n", type=int, default=10)
    sp.add_argument("--cols", default="", help="只看某些列，逗号分隔")

    sp = sub.add_parser("schema", help="列类型/唯一值数/缺失率")
    _add_common(sp)

    sp = sub.add_parser("describe", help="数值分布统计")
    _add_common(sp)
    sp.add_argument("--cols", default="", help="只看某些数值列，逗号分隔")

    sp = sub.add_parser("missing", help="每列缺失率与零值占比")
    _add_common(sp)

    sp = sub.add_parser("group", help="分组聚合")
    _add_common(sp)
    sp.add_argument("--by", required=True, help="分组列，逗号分隔，如 材料分类,年份")
    sp.add_argument("--agg", default="", help="聚合规格，如 供货量:sum,mean,std")

    sp = sub.add_parser("filter", help="按条件取行")
    _add_common(sp)
    sp.add_argument("--where", required=True, help="pandas query 表达式")
    sp.add_argument("--cols", default="")
    sp.add_argument("-n", type=int, default=20)

    sp = sub.add_parser("corr", help="数值列相关系数矩阵")
    _add_common(sp)
    sp.add_argument("--cols", default="")

    sp = sub.add_parser("count", help="行数统计")
    _add_common(sp)
    sp.add_argument("--where", default="", help="可选过滤条件")

    sp = sub.add_parser("expr", help="任意 pandas 表达式（df 已定义）")
    _add_common(sp)
    sp.add_argument("code", help="pandas 表达式，如 df['供货量'].mean()")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        df = read_csv(args.csv)
    except RuntimeError as e:
        print(e)
        return 1
    handlers = {
        "head": cmd_head,
        "schema": cmd_schema,
        "describe": cmd_describe,
        "missing": cmd_missing,
        "group": cmd_group,
        "filter": cmd_filter,
        "corr": cmd_corr,
        "count": cmd_count,
        "expr": cmd_expr,
    }
    handlers[args.cmd](df, args)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

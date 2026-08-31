# -*- coding: utf-8 -*-
"""
gen_data_profile：一键生成数据画像 .md（省 token、防幻觉的核心工具）。

用法
----
    python tools/gen_data_profile.py 数据.csv
    python tools/gen_data_profile.py 数据.csv --out 数据画像.md
    python tools/gen_data_profile.py 数据.csv --label "供应商供货数据" --group 材料分类,年份
    python tools/gen_data_profile.py 数据.csv --top 20 --sample 10

无论输入 CSV 有多大（几万行、十几列），输出画像都控制在约 3k~5k token，
让 AI 不读全量数据也能完整了解数据结构与统计规律。

输出区块
--------
1. 数据概览（行数/列数/各列类型/缺失率/唯一值数/取值范围）
2. 样本预览（默认前 10 行）
3. 数值列分布（count/mean/std/min/25%/50%/75%/max/零值占比）
4. 类别列取值频数（默认 Top 20）
5. 数值列相关性矩阵
6. 时间列分析（自动识别日期列）
7. 分组汇总（--group 指定，可选）

注意：字段的"业务含义"无法自动推断，生成后可在概览表后手工补一列"含义"说明。
"""

import argparse
import os
import warnings

import pandas as pd

from csv_io import read_csv, to_markdown


# ---------------------------------------------------------------------------
# 列类型判定
# ---------------------------------------------------------------------------
def _num_cols(df):
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _dt_cols(df):
    return [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]


def _cat_cols(df):
    dt = set(_dt_cols(df))
    num = set(_num_cols(df))
    return [c for c in df.columns if c not in dt and c not in num]


_DATE_PATTERNS = (
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",  # 2024-01-01 / 2024/1/1
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}",  # 01-01-2024
    r"^\d{8}$",                        # 20240101
)


def _looks_date_like(s, thresh=0.5):
    """粗略判断字符串列是否像日期，避免对无关列误解析。"""
    sample = s.head(50)
    mask = sample.str.contains("|".join(_DATE_PATTERNS), regex=True, na=False)
    return bool(mask.mean() >= thresh)


def _auto_parse_dates(df, threshold=0.9):
    """把「看起来像日期」的字符串列转成 datetime（排除纯数字字符串）。"""
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        s = df[c].dropna().astype(str)
        if len(s) < 2:
            continue
        if s.str.fullmatch(r"-?\d+(\.\d+)?").all():
            continue  # 纯数字字符串，不当作日期
        if not _looks_date_like(s):
            continue  # 不像日期，跳过，避免误判与告警
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(s, errors="coerce")
        if parsed.notna().mean() >= threshold and parsed.nunique() > 1:
            df[c] = parsed
    return df


# ---------------------------------------------------------------------------
# 各区块
# ---------------------------------------------------------------------------
def _section_overview(df):
    rows = []
    for c in df.columns:
        nunique = df[c].nunique(dropna=True)
        missing = df[c].isna().mean()
        if c in _num_cols(df):
            t = "数值"
            rng = f"[{_fmt_num(df[c].min())}, {_fmt_num(df[c].max())}]"
        elif c in _dt_cols(df):
            t = "日期"
            rng = f"{df[c].min():%Y-%m-%d} ~ {df[c].max():%Y-%m-%d}"
        else:
            t = "类别"
            top = df[c].value_counts(dropna=False).index[0] if nunique else "—"
            rng = f"唯一值 {nunique:,}，最常见: {top}"
        rows.append([c, t, f"{missing * 100:.1f}%", nunique, rng])
    out = pd.DataFrame(rows, columns=["列名", "类型", "缺失率", "唯一值数", "取值范围 / 示例"])
    return to_markdown(out, max_rows=60)


def _section_sample(df, n):
    if n <= 0:
        return "（已跳过）"
    return to_markdown(df.head(n))


def _section_numeric(df, num_cols, prec=3):
    if not num_cols:
        return "（无数值列）"
    st = df[num_cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    st = st[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    st["总和"] = [df[c].sum() for c in num_cols]
    st["零值占比"] = [(df[c] == 0).mean() for c in num_cols]
    st = st.reset_index().rename(columns={"index": "列名"})
    return to_markdown(st, prec=prec, max_rows=60)


def _section_cat(df, cat_cols, top=20):
    if not cat_cols:
        return "（无类别列）"
    parts = []
    for c in cat_cols:
        vc = df[c].value_counts(dropna=False).head(top)
        t = pd.DataFrame({
            "取值": vc.index,
            "频数": vc.values,
            "占比%": (vc.values / len(df) * 100),
        })
        parts.append(f"**{c}**\n\n" + to_markdown(t, max_rows=25))
    return "\n\n".join(parts)


def _section_corr(df, num_cols):
    if len(num_cols) < 2:
        return "（数值列不足 2 列，跳过相关性）"
    corr = df[num_cols].corr()
    corr = corr.reset_index().rename(columns={"index": "列名"})
    return to_markdown(corr, prec=2, max_rows=40)


def _section_time(df, dt_cols):
    if not dt_cols:
        return "（无日期列）"
    lines = []
    for c in dt_cols:
        s = df[c]
        span = s.max() - s.min()
        diffs = s.dropna().sort_values().diff().dropna()
        diffs = diffs[diffs > pd.Timedelta(0)]
        gran = diffs.min() if len(diffs) else "—"
        lines.append(
            f"- **{c}**：{s.min():%Y-%m-%d} ~ {s.max():%Y-%m-%d}，"
            f"跨度 {span.days} 天，最小间隔 {gran}，共 {s.nunique()} 个不同值"
        )
    return "\n".join(lines)


def _section_group(df, group_cols):
    num = _num_cols(df)
    if not group_cols:
        return "（未指定 --group）"
    if not num:
        return "（无数值列可聚合）"
    spec = {c: ["sum", "mean"] for c in num}
    g = df.groupby(group_cols).agg(spec)
    if isinstance(g.columns, pd.MultiIndex):
        g.columns = ["_".join(str(x) for x in t if x != "") for t in g.columns]
    g = g.reset_index()
    sum_cols = [c for c in g.columns if str(c).endswith("_sum")]
    if sum_cols:
        g = g.sort_values(sum_cols[0], ascending=False)
    return to_markdown(g, max_rows=60)


def _fmt_num(v):
    """概览取值范围里用到的极简数字格式化。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f) and abs(f) < 1e15:
        return f"{int(f):,}"
    return f"{f:,.4g}"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="一键生成数据画像 .md（无论数据多大，输出控制在几千 token）"
    )
    ap.add_argument("csv", help="数据文件路径（支持 UTF-8 / GBK 编码）")
    ap.add_argument("--out", default="", help="输出 .md 路径；不填则打印到屏幕")
    ap.add_argument("--label", default="", help="报告标题（默认用文件名）")
    ap.add_argument("--group", default="", help="分组汇总列，逗号分隔，如 材料分类,年份")
    ap.add_argument("--sample", type=int, default=10, help="样本行数（0 跳过）")
    ap.add_argument("--top", type=int, default=20, help="类别列频数最多展示几个取值")
    ap.add_argument("--prec", type=int, default=3, help="小数保留位数")
    args = ap.parse_args(argv)

    try:
        df = read_csv(args.csv)
    except RuntimeError as e:
        print(e)
        return 1
    df = _auto_parse_dates(df)

    label = args.label or os.path.splitext(os.path.basename(args.csv))[0]

    sections = []
    sections.append(f"# {label}数据画像\n")
    sections.append(f"> 文件：{os.path.basename(args.csv)}　共 **{len(df):,}** 行 × **{len(df.columns)}** 列\n")
    sections.append("## 1. 数据概览\n" + _section_overview(df))
    sections.append(f"## 2. 样本预览（前 {args.sample} 行）\n" + _section_sample(df, args.sample))
    sections.append("## 3. 数值列分布\n" + _section_numeric(df, _num_cols(df), args.prec))
    sections.append("## 4. 类别列取值\n" + _section_cat(df, _cat_cols(df), args.top))
    sections.append("## 5. 数值列相关性\n" + _section_corr(df, _num_cols(df)))
    sections.append("## 6. 时间列分析\n" + _section_time(df, _dt_cols(df)))
    if args.group:
        sections.append("## 7. 分组汇总\n" + _section_group(df, [c.strip() for c in args.group.split(",")]))

    text = "\n\n---\n\n".join(sections) + "\n"
    est = int(len(text) * 1.3)  # 粗略 token 估算：中文约 1.3 token/字
    text += f"\n---\n*本画像约 {est:,} tokens（粗略估算，按 1.3 × 字符数）。*\n"

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已写入 {args.out}（{len(text):,} 字符，约 {est:,} tokens）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

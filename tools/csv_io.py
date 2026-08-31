# -*- coding: utf-8 -*-
"""
csv_io：数据画像生成器 / 数据查询助手的共享底层。

功能
----
1. detect_encoding(path) —— 自动识别 CSV 编码（utf-8-sig / gb18030 / gbk / big5），
   兼容中文 Windows 导出的 ANSI(GBK) 文件。
2. read_csv(path)        —— 读取并返回 DataFrame，自动处理编码与 BOM。
3. to_markdown(df)       —— 把结果输出为紧凑 markdown 表格，自动截断超长行，
   专为「直接喂给 AI 的低 token 输出」设计。

用法示例
--------
    import csv_io
    df = csv_io.read_csv("供货数据.csv")
    print(csv_io.to_markdown(df.head(5)))
"""

import numpy as np
import pandas as pd

# 按优先级尝试的编码
_ENCODINGS = ("utf-8-sig", "gb18030", "gbk", "big5")


def detect_encoding(path):
    """探测编码：按优先级返回第一个能完整解码的编码，兜底 gb18030。"""
    with open(path, "rb") as f:
        raw = f.read(2_000_000)  # 最多读 2MB 用于探测
    for enc in _ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "gb18030"  # gb18030 能解码任意字节序列


def read_csv(path, **kwargs):
    """读取 CSV，自动探测编码。"""
    enc = detect_encoding(path)
    try:
        return pd.read_csv(path, encoding=enc, **kwargs)
    except Exception as e:  # noqa: BLE001 - 向上抛友好错误
        raise RuntimeError(f"读取失败：{path}（编码 {enc}）\n原始错误：{e}") from e


def _is_scalar_na(v):
    try:
        if np.isscalar(v):
            return bool(pd.isna(v))
    except (TypeError, ValueError):
        pass
    return False


def _fmt(v, prec=3):
    """单元格格式化：NA 统一、整数千分位、小数去尾零、日期取日期部分。"""
    if v is None or _is_scalar_na(v):
        return "NA"
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (bool, np.bool_)):
        return str(v)
    if isinstance(v, str):
        return v.replace("\n", " ").replace("|", "\\|") or "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        s = str(v).replace("\n", " ").replace("|", "\\|")
        return s or "—"
    if f != f:  # NaN
        return "NA"
    if abs(f) >= 1e15:
        return f"{f:.{prec}g}"
    if f == int(f):
        return f"{int(f):,}"
    if abs(f) >= 1e5:
        return f"{f:,.2f}"
    s = f"{f:,.{prec}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def to_markdown(df, prec=3, max_rows=50, title=None):
    """DataFrame → 紧凑 markdown 表格；行数超过 max_rows 时截断并在末尾提示。

    参数
    ----
    df       : DataFrame 或 Series
    prec     : 小数保留位数
    max_rows : 最多显示多少行，超出截断
    title    : 可选，表标题（markdown 加粗行）
    """
    if df is None:
        return "（空）"
    if isinstance(df, pd.Series):
        df = df.to_frame()
    if len(df) == 0:
        return "（空结果，0 行）"

    truncated = len(df) > max_rows
    show = df.head(max_rows)

    # 非默认 RangeIndex 视为有意义索引，作为第一列展示（如 groupby 结果）
    idx_show = not (isinstance(show.index, pd.RangeIndex) and show.index.name is None)
    cols = []
    if idx_show:
        cols.append(str(show.index.name) if show.index.name is not None else "index")
    cols.extend(str(c) for c in show.columns)

    lines = []
    if title:
        lines.append(f"**{title}**")
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join("---" for _ in cols) + "|")
    for i, (_, row) in enumerate(show.iterrows()):
        cells = []
        if idx_show:
            cells.append(_fmt(show.index[i], prec))
        cells.extend(_fmt(v, prec) for v in row)
        lines.append("| " + " | ".join(cells) + " |")
    if truncated:
        lines.append(f"\n*…共 {len(df)} 行，仅显示前 {max_rows} 行*")
    return "\n".join(lines)

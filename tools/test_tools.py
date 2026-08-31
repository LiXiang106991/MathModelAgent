# -*- coding: utf-8 -*-
"""冒烟测试：不依赖 pytest，直接 `python tools/test_tools.py` 运行。

覆盖：
- GBK 编码文件的自动识别与读取
- 紧凑 markdown 输出的行数截断
- 数据画像生成器的区块完整性
- 数据查询助手全部子命令
"""

import contextlib
import io
import os
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import csv_io            # noqa: E402
import gen_data_profile  # noqa: E402
import l1_build          # noqa: E402
import l1_loader         # noqa: E402
import query_data        # noqa: E402

SAMPLE = (
    "供应商ID,材料分类,周次,年份,供货量\n"
    "S001,B,W001,第1年,0\n"
    "S002,A,W001,第1年,1\n"
    "S003,C,W001,第1年,7\n"
    "S004,B,W001,第1年,0\n"
    "S005,A,W001,第1年,30\n"
    "S006,C,W001,第1年,0\n"
    "S007,B,W001,第1年,0\n"
    "S008,A,W001,第1年,0\n"
    "S009,C,W001,第1年,9\n"
    "S010,B,W001,第1年,12\n"
)


def _make(path, encoding="utf-8"):
    with open(path, "w", encoding=encoding) as f:
        f.write(SAMPLE)


def _run_quiet(func, *argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = func(list(argv))
    return rc, buf.getvalue()


def _tmp(name):
    return os.path.join(tempfile.gettempdir(), name)


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------
def test_encoding_gbk():
    p = _tmp("t_gbk.csv")
    _make(p, encoding="gbk")
    df = csv_io.read_csv(p)
    assert len(df) == 10, "GBK 读取行数不对"
    assert df["供应商ID"].iloc[0] == "S001"
    assert df["材料分类"].iloc[0] == "B"
    os.remove(p)
    print("PASS test_encoding_gbk")


def test_to_markdown_truncate():
    df = pd.DataFrame({"a": range(100), "b": [x * 1.5 for x in range(100)]})
    md = csv_io.to_markdown(df, max_rows=50)
    assert "共 100 行" in md
    assert len(md.splitlines()) <= 54
    assert "49" in md  # 前 50 行里应包含第 49 行
    print("PASS test_to_markdown_truncate")


def test_profile_generates():
    p = _tmp("t_profile.csv")
    _make(p)
    rc, out = _run_quiet(gen_data_profile.main, p, "--label", "测试数据", "--group", "材料分类")
    assert rc == 0
    for kw in ("测试数据数据画像", "## 1. 数据概览", "## 3. 数值列分布",
               "## 5. 数值列相关性", "## 7. 分组汇总", "材料分类", "供货量"):
        assert kw in out, f"画像缺少区块/内容：{kw}"
    # 校验关键统计：供货量 sum = 59
    assert "59" in out
    os.remove(p)
    print("PASS test_profile_generates")


def test_query_subcommands():
    p = _tmp("t_query.csv")
    _make(p)

    rc, out = _run_quiet(query_data.main, "head", p, "-n", "3")
    assert rc == 0 and "S001" in out and "S010" not in out

    rc, out = _run_quiet(query_data.main, "schema", p)
    assert rc == 0 and "供应商ID" in out and "类别" in out

    rc, out = _run_quiet(query_data.main, "describe", p, "--cols", "供货量")
    assert rc == 0 and "count" in out and "零值占比" in out

    rc, out = _run_quiet(query_data.main, "missing", p)
    assert rc == 0 and "缺失率" in out and "零值占比" in out

    rc, out = _run_quiet(query_data.main, "group", p, "--by", "材料分类", "--agg", "供货量:sum,mean")
    assert rc == 0 and "A" in out

    rc, out = _run_quiet(query_data.main, "filter", p, "--where", "材料分类 == 'A'", "-n", "5")
    assert rc == 0 and "S002" in out and "S001" not in out

    rc, out = _run_quiet(query_data.main, "count", p, "--where", "供货量 == 0")
    assert rc == 0 and out.strip() == "5", f"count 结果不对：{out}"

    p2 = _tmp("t_corr.csv")
    with open(p2, "w", encoding="utf-8") as f:
        f.write("x,y\n1,2\n2,4\n3,6\n4,8\n")
    rc, out = _run_quiet(query_data.main, "corr", p2)
    assert rc == 0 and "x" in out and "y" in out
    os.remove(p2)

    rc, out = _run_quiet(query_data.main, "expr", p, "df['供货量'].sum()")
    assert rc == 0 and "59" in out

    rc, out = _run_quiet(query_data.main, "expr", p, "df.groupby('材料分类')['供货量'].mean()")
    assert rc == 0 and "A" in out

    os.remove(p)
    print("PASS test_query_subcommands")


def test_group_encoding():
    """GBK 文件走 query_data 全链路。"""
    p = _tmp("t_gbk_query.csv")
    _make(p, encoding="gbk")
    rc, out = _run_quiet(query_data.main, "filter", p, "--where", "材料分类 == 'C'", "-n", "5")
    assert rc == 0 and "S003" in out
    os.remove(p)
    print("PASS test_group_encoding")


# ---------------------------------------------------------------------------
# L1 中间层构建器 / 读取器
# ---------------------------------------------------------------------------
SALES_CSV = (
    "销售日期,单品编码,分类,销量,单价\n"
    "2023-01-01,1001,A,5,10\n"
    "2023-01-01,1002,B,3,20\n"
    "2023-01-02,1001,A,7,12\n"
    "2023-01-03,1002,B,2,18\n"
)


def test_l1_fact_table():
    """销售流水式事实表: 自动检测日期/度量, 物化 daily/weekly/monthly/by_group。"""
    out = _tmp("t_l1_fact")
    p = _tmp("t_l1_fact.csv")
    with open(p, "w", encoding="utf-8") as f:
        f.write(SALES_CSV)
    rc, _ = _run_quiet(l1_build.main, p, "--out", out)
    assert rc is None

    for t in ("_dictionary.md", "_overview.csv", "daily.csv",
              "weekly.csv", "monthly.csv", "daily_by_group.csv", "_meta.json"):
        assert os.path.exists(os.path.join(out, "t_l1_fact", t)), f"缺 L1 表 {t}"

    # 检测角色: 单品编码(名字含编码) 应为 id, 不参与聚合
    m = l1_loader.meta(out, "t_l1_fact")
    assert "单品编码" in m["id_cols"], "单品编码应被识别为 id"
    assert "销量" in m["measures"] and "单价" in m["measures"]
    assert m["primary_date"] == "销售日期"

    # 数值核对: 总销量 = 5+3+7+2 = 17
    daily = l1_loader.load(out, "t_l1_fact", "daily")
    assert int(daily["销量_sum"].sum()) == 17, f"销量合计不对: {daily['销量_sum'].sum()}"

    # 分组表: (2023-01-01, A) 销量=5; (2023-01-01, B) 销量=3
    bg = l1_loader.load(out, "t_l1_fact", "daily_by_group")
    a = bg[(bg["销售日期"] == "2023-01-01") & (bg["分类"] == "A")]["销量_sum"].iloc[0]
    assert int(a) == 5, f"分组聚合不对: {a}"

    # 字典可读
    assert "主日期: 销售日期" in (l1_loader.dictionary(out, "t_l1_fact") or "")

    import shutil
    shutil.rmtree(out)
    os.remove(p)
    print("PASS test_l1_fact_table")


def test_l1_dimension_and_nodate():
    """维度表(无日期无度量)输出 _map.csv; 15位数字编码不得误判为日期。"""
    out = _tmp("t_l1_dim")
    p1 = _tmp("t_l1_item.csv")
    with open(p1, "w", encoding="utf-8") as f:
        f.write("单品编码,单品名称,分类名称\n"
                "1001,生菜,花叶类\n"
                "1002,油麦菜,花叶类\n")
    rc, _ = _run_quiet(l1_build.main, p1, "--out", out)
    assert rc is None
    assert os.path.exists(os.path.join(out, "t_l1_item", "_map.csv")), "维度表应输出 _map.csv"
    mp = l1_loader.load(out, "t_l1_item", "_map")
    assert len(mp) == 2
    assert mp["单品编码"].tolist() == [1001, 1002]

    # 15 位数字编码字符串: to_datetime 能"解析"但年份在 5200+, 必须被年份校验拦下
    p2 = _tmp("t_l1_code.csv")
    with open(p2, "w", encoding="utf-8") as f:
        f.write("编码,值\n102900005116233,1\n102900011030059,2\n")
    rc, _ = _run_quiet(l1_build.main, p2, "--out", out)
    assert rc is None
    m = l1_loader.meta(out, "t_l1_code")
    assert m["primary_date"] is None, "15位编码不应被误判为日期列"
    assert "daily.csv" not in m["tables"]

    import shutil
    shutil.rmtree(out)
    os.remove(p1)
    os.remove(p2)
    print("PASS test_l1_dimension_and_nodate")


if __name__ == "__main__":
    test_encoding_gbk()
    test_to_markdown_truncate()
    test_profile_generates()
    test_query_subcommands()
    test_group_encoding()
    test_l1_fact_table()
    test_l1_dimension_and_nodate()
    print("\n全部通过 ✅")

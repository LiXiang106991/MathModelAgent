"""
灰色关联分析 (Grey Relational Analysis, GRA)
国赛评价类常用工具
"""

import numpy as np
import pandas as pd


def grey_relation_analysis(data, ref_col=None, rho=0.5, normalize='mean'):
    """
    灰色关联分析
    
    参数:
        data: DataFrame 或 2D array，行为样本/方案，列为指标
        ref_col: 参考序列所在列名或索引。若为 None，则取每列最大值作为参考（效益型理想）
        rho: 分辨系数，默认 0.5
        normalize: 无量纲化方法 'mean'(均值化) / 'init'(初值化) / 'range'(极差化)
    
    返回:
        relation_degrees: 各比较序列的灰色关联度 Series
        coefficients: 关联系数矩阵 DataFrame
    """
    if isinstance(data, pd.DataFrame):
        df = data.copy()
        columns = df.columns.tolist()
    else:
        df = pd.DataFrame(data)
        columns = list(range(df.shape[1]))
    
    # 无量纲化
    if normalize == 'mean':
        df_norm = df / df.mean()
    elif normalize == 'init':
        df_norm = df / df.iloc[0]
    elif normalize == 'range':
        df_norm = (df - df.min()) / (df.max() - df.min() + 1e-10)
    else:
        raise ValueError("normalize 必须是 'mean', 'init' 或 'range'")
    
    # 确定参考序列
    if ref_col is None:
        ref = df_norm.max(axis=0)          # 效益型正理想
    else:
        ref = df_norm[ref_col]
        df_norm = df_norm.drop(columns=ref_col)
    
    # 计算两极差
    abs_diff = np.abs(df_norm.subtract(ref, axis=1))
    min_min = abs_diff.min().min()
    max_max = abs_diff.max().max()
    
    # 关联系数
    coefficients = (min_min + rho * max_max) / (abs_diff + rho * max_max)
    
    # 关联度
    relation_degrees = coefficients.mean(axis=1)
    relation_degrees = relation_degrees.sort_values(ascending=False)
    
    return relation_degrees, coefficients


# 使用示例
if __name__ == "__main__":
    # 示例数据：4个方案，3个指标
    data = pd.DataFrame({
        '指标1': [0.8, 0.6, 0.9, 0.7],
        '指标2': [0.7, 0.9, 0.5, 0.8],
        '指标3': [0.9, 0.7, 0.8, 0.6]
    }, index=['方案A', '方案B', '方案C', '方案D'])
    
    degrees, coef = grey_relation_analysis(data, rho=0.5)
    print("灰色关联度排序：")
    print(degrees)
    print("\n关联系数矩阵：")
    print(coef.round(4))

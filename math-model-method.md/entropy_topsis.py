"""
熵权法 + TOPSIS 综合评价
国赛评价类高频组合工具
"""

import numpy as np
import pandas as pd


def entropy_weight(data, positive=True):
    """
    熵权法计算权重
    
    参数:
        data: DataFrame，行为样本，列为指标
        positive: True 表示所有指标已正向化（越大越好）
    
    返回:
        weights: 权重 Series
    """
    df = data.copy().astype(float)
    
    # 避免零值
    df = df + 1e-10
    
    # 比重
    p = df / df.sum(axis=0)
    
    # 熵值
    m = len(df)
    k = 1 / np.log(m)
    e = -k * (p * np.log(p)).sum(axis=0)
    
    # 效用值与权重
    d = 1 - e
    weights = d / d.sum()
    
    return weights


def topsis(data, weights=None, positive_cols=None):
    """
    TOPSIS 排序
    
    参数:
        data: DataFrame，行为方案，列为指标
        weights: 权重，若为 None 则自动用熵权法
        positive_cols: 已正向化的列（若有成本型需先处理）
    
    返回:
        scores: 相对贴近度 Series（越大越优）
        ranking: 排序结果
    """
    df = data.copy().astype(float)
    
    if weights is None:
        weights = entropy_weight(df)
    
    # 向量归一化
    norm = np.sqrt((df ** 2).sum(axis=0))
    df_norm = df / norm
    
    # 加权
    df_weighted = df_norm * weights
    
    # 正负理想解
    z_positive = df_weighted.max(axis=0)
    z_negative = df_weighted.min(axis=0)
    
    # 距离
    d_positive = np.sqrt(((df_weighted - z_positive) ** 2).sum(axis=1))
    d_negative = np.sqrt(((df_weighted - z_negative) ** 2).sum(axis=1))
    
    # 贴近度
    scores = d_negative / (d_positive + d_negative + 1e-10)
    ranking = scores.sort_values(ascending=False)
    
    return scores, ranking, weights


# 使用示例
if __name__ == "__main__":
    data = pd.DataFrame({
        '经济效益': [90, 80, 85, 75],
        '社会效益': [85, 90, 80, 70],
        '环境成本': [20, 30, 25, 40]   # 成本型，需先正向化
    }, index=['方案1', '方案2', '方案3', '方案4'])
    
    # 成本型正向化（取倒数或用最大值减）
    data['环境成本'] = data['环境成本'].max() - data['环境成本']
    
    scores, ranking, weights = topsis(data)
    print("熵权法权重：")
    print(weights.round(4))
    print("\nTOPSIS 贴近度排序：")
    print(ranking.round(4))

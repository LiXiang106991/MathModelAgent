"""
层次分析法 (AHP) 简易实现
包含一致性检验
"""

import numpy as np
import pandas as pd


# 随机一致性指标 RI（n=1~15）
RI_dict = {
    1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
    11: 1.51, 12: 1.54, 13: 1.56, 14: 1.58, 15: 1.59
}


def ahp(judgment_matrix):
    """
    AHP 权重计算与一致性检验
    
    参数:
        judgment_matrix: 方阵 (n x n)，判断矩阵
    
    返回:
        weights: 权重向量
        CR: 一致性比率
        lambda_max: 最大特征值
        consistent: 是否通过一致性检验 (CR < 0.1)
    """
    A = np.asarray(judgment_matrix, dtype=float)
    n = A.shape[0]
    
    # 特征值法
    eigvals, eigvecs = np.linalg.eig(A)
    max_idx = np.argmax(eigvals.real)
    lambda_max = eigvals.real[max_idx]
    weights = eigvecs[:, max_idx].real
    weights = weights / weights.sum()
    
    # 一致性检验
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0
    RI = RI_dict.get(n, 1.6)
    CR = CI / RI if RI != 0 else 0
    
    return {
        'weights': weights,
        'lambda_max': lambda_max,
        'CI': CI,
        'CR': CR,
        'consistent': CR < 0.1
    }


# 使用示例
if __name__ == "__main__":
    # 3阶判断矩阵示例
    A = np.array([
        [1,   3,   5],
        [1/3, 1,   3],
        [1/5, 1/3, 1]
    ])
    
    result = ahp(A)
    print("权重：", np.round(result['weights'], 4))
    print("最大特征值 λ_max =", round(result['lambda_max'], 4))
    print("一致性比率 CR =", round(result['CR'], 4))
    print("是否通过一致性检验：", result['consistent'])

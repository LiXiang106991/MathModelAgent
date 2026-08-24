"""
灰色预测 GM(1,1)
国赛预测类常用工具（小样本）
"""

import numpy as np
import pandas as pd


def gm11(x0, predict_steps=1):
    """
    GM(1,1) 灰色预测
    
    参数:
        x0: 原始一维序列 (list / array / Series)
        predict_steps: 向后预测步数
    
    返回:
        x0_hat: 拟合值
        x0_pred: 预测值
        a, b: 发展系数与灰作用量
        mape: 平均相对误差
    """
    x0 = np.asarray(x0, dtype=float)
    n = len(x0)
    
    # 一次累加
    x1 = np.cumsum(x0)
    
    # 构造数据矩阵
    z = 0.5 * (x1[1:] + x1[:-1])          # 紧邻均值
    B = np.column_stack([-z, np.ones(n-1)])
    Y = x0[1:]
    
    # 最小二乘估计
    ab = np.linalg.inv(B.T @ B) @ B.T @ Y
    a, b = ab[0], ab[1]
    
    # 时间响应函数
    def x1_hat_func(k):
        return (x0[0] - b/a) * np.exp(-a * k) + b/a
    
    # 拟合值（还原）
    x1_hat = np.array([x1_hat_func(k) for k in range(n)])
    x0_hat = np.empty(n)
    x0_hat[0] = x0[0]
    x0_hat[1:] = x1_hat[1:] - x1_hat[:-1]
    
    # 预测
    x0_pred = []
    for k in range(n, n + predict_steps):
        val = x1_hat_func(k) - x1_hat_func(k-1)
        x0_pred.append(val)
    
    # 精度
    mape = np.mean(np.abs(x0 - x0_hat) / x0) * 100
    
    return {
        'fitted': x0_hat,
        'predicted': np.array(x0_pred),
        'a': a,
        'b': b,
        'mape(%)': mape,
        'level': '优秀' if mape < 10 else ('合格' if mape < 20 else '需改进')
    }


# 使用示例
if __name__ == "__main__":
    # 某产品销量（小样本）
    sales = [100, 120, 140, 155, 170, 185]
    
    result = gm11(sales, predict_steps=3)
    
    print("发展系数 a =", round(result['a'], 4))
    print("灰作用量 b =", round(result['b'], 4))
    print("拟合值：", np.round(result['fitted'], 2))
    print("未来3步预测：", np.round(result['predicted'], 2))
    print(f"平均相对误差 MAPE = {result['mape(%)']:.2f}%  → {result['level']}")

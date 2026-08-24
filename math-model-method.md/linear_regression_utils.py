"""
一元/多元线性回归常用诊断工具
包含 VIF 共线性检验、基本回归摘要
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
from statsmodels.stats.outliers_influence import variance_inflation_factor
import statsmodels.api as sm


def vif_test(X):
    """
    计算方差膨胀因子 VIF
    X: DataFrame（不含常数项）
    """
    X = sm.add_constant(X)
    vif_data = pd.DataFrame()
    vif_data["feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
    return vif_data.sort_values("VIF", ascending=False)


def linear_regression_summary(X, y):
    """
    使用 statsmodels 输出完整回归摘要 + VIF
    """
    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()
    
    print(model.summary())
    print("\n========== VIF 共线性检验 ==========")
    print(vif_test(X))
    
    return model


# 使用示例
if __name__ == "__main__":
    # 模拟数据
    np.random.seed(42)
    n = 50
    X1 = np.random.normal(10, 2, n)
    X2 = X1 * 0.8 + np.random.normal(0, 0.5, n)   # 与 X1 高度相关
    X3 = np.random.normal(5, 1, n)
    y = 3 + 1.5*X1 + 0.8*X3 + np.random.normal(0, 1, n)
    
    X = pd.DataFrame({'X1': X1, 'X2': X2, 'X3': X3})
    
    model = linear_regression_summary(X, y)

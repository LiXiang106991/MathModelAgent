"""
随机森林封装（回归 + 分类）
国赛预测/分类常用工具，自带特征重要性与交叉验证
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import r2_score, mean_squared_error, accuracy_score, classification_report


def rf_regressor(X, y, n_estimators=200, max_depth=None, test_size=0.2, random_state=42):
    """
    随机森林回归封装
    
    返回:
        model: 训练好的模型
        metrics: 评估指标字典
        importance: 特征重要性 Series
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    metrics = {
        'R2': r2_score(y_test, y_pred),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred)),
        'CV_R2_mean': cross_val_score(model, X, y, cv=5, scoring='r2').mean()
    }
    
    importance = pd.Series(model.feature_importances_, index=X.columns if hasattr(X, 'columns') else range(X.shape[1]))
    importance = importance.sort_values(ascending=False)
    
    return model, metrics, importance


def rf_classifier(X, y, n_estimators=200, max_depth=None, test_size=0.2, random_state=42):
    """
    随机森林分类封装
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    metrics = {
        'Accuracy': accuracy_score(y_test, y_pred),
        'CV_Accuracy_mean': cross_val_score(model, X, y, cv=5, scoring='accuracy').mean()
    }
    
    importance = pd.Series(model.feature_importances_, index=X.columns if hasattr(X, 'columns') else range(X.shape[1]))
    importance = importance.sort_values(ascending=False)
    
    print(classification_report(y_test, y_pred))
    
    return model, metrics, importance


# 使用示例
if __name__ == "__main__":
    from sklearn.datasets import make_regression, make_classification
    
    # 回归示例
    X_reg, y_reg = make_regression(n_samples=200, n_features=5, noise=10, random_state=42)
    X_reg = pd.DataFrame(X_reg, columns=[f'特征{i}' for i in range(5)])
    
    model_reg, metrics_reg, imp_reg = rf_regressor(X_reg, y_reg)
    print("=== 随机森林回归 ===")
    print(metrics_reg)
    print("特征重要性：\n", imp_reg.round(4))
    
    # 分类示例
    X_clf, y_clf = make_classification(n_samples=200, n_features=5, n_informative=3, random_state=42)
    X_clf = pd.DataFrame(X_clf, columns=[f'特征{i}' for i in range(5)])
    
    model_clf, metrics_clf, imp_clf = rf_classifier(X_clf, y_clf)
    print("\n=== 随机森林分类 ===")
    print(metrics_clf)
    print("特征重要性：\n", imp_clf.round(4))
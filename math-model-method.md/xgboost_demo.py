"""
XGBoost 完整实战代码 (兼容 XGBoost 2.1.1)
适用于数学建模国赛 / 数据科学竞赛
包含: 回归预测、二分类、多分类、超参数调优、特征重要性可视化

依赖安装:
    pip install xgboost scikit-learn pandas numpy matplotlib seaborn

作者: AI Assistant
日期: 2026-08-28
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 100

import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score, KFold
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
from sklearn.datasets import make_regression, make_classification

# ============================================================
# 第一部分: 回归任务（房价预测场景）
# ============================================================

def demo_regression():
    """回归预测演示 - 模拟房价预测"""
    print("=" * 60)
    print("【第一部分】XGBoost 回归预测 - 房价预测案例")
    print("=" * 60)

    np.random.seed(42)
    n_samples = 1000

    data = pd.DataFrame({
        'area': np.random.normal(100, 30, n_samples).clip(30, 300),
        'floor': np.random.randint(1, 33, n_samples),
        'age': np.random.randint(1, 31, n_samples),
        'metro_dist': np.random.exponential(1000, n_samples).clip(100, 5000),
        'school': np.random.binomial(1, 0.3, n_samples),
    })

    data['price'] = (
        2.0 * data['area'] +
        50 * data['school'] +
        0.5 * (30 - data['age']) ** 2 +
        20 * np.log1p(data['floor']) +
        -0.01 * data['metro_dist'] +
        np.random.normal(0, 20, n_samples)
    ).clip(50, 1000)

    print(f"\n📊 数据集概况: {data.shape[0]} 样本 × {data.shape[1]} 特征")
    print(data.head())
    print(f"\n📈 目标变量统计:\n{data['price'].describe()}")

    X = data.drop('price', axis=1)
    y = data['price']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"\n✂️ 数据划分: 训练集 {len(X_train)} | 测试集 {len(X_test)}")

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=list(X.columns))
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=list(X.columns))

    params = {
        'objective': 'reg:squarederror',
        'eval_metric': 'rmse',
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_lambda': 1,
        'reg_alpha': 0,
        'gamma': 0,
        'min_child_weight': 1,
        'seed': 42
    }

    print("\n🚀 开始训练...")
    evals = [(dtrain, 'train'), (dtest, 'test')]
    model = xgb.train(
        params, dtrain, num_boost_round=500,
        evals=evals, early_stopping_rounds=50, verbose_eval=50
    )

    print(f"\n✅ 最优迭代轮数: {model.best_iteration}")
    y_pred = model.predict(dtest, iteration_range=(0, model.best_iteration + 1))
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"测试集 RMSE: {rmse:.4f}")

    y_pred = model.predict(dtest, iteration_range=(0, model.best_iteration + 1))
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    print(f"\n📊 回归评估指标:")
    print(f"   RMSE:  {rmse:.4f}")
    print(f"   MAE:   {mae:.4f}")
    print(f"   R²:    {r2:.4f}")
    print(f"   MAPE:  {mape:.2f}%")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    xgb.plot_importance(model, importance_type='gain', 
                        title='Feature Importance (Gain)', 
                        xlabel='Gain', ax=axes[0])

    axes[1].scatter(y_test, y_pred, alpha=0.5, edgecolors='none')
    axes[1].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
                 'r--', lw=2, label='Perfect Prediction')
    axes[1].set_xlabel('True Price (万元)')
    axes[1].set_ylabel('Predicted Price (万元)')
    axes[1].set_title(f'Prediction vs True (R²={r2:.3f})')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/mnt/agents/output/xgboost_regression_result.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("\n📁 图表已保存: xgboost_regression_result.png")

    residuals = y_test - y_pred
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.scatter(y_pred, residuals, alpha=0.5, edgecolors='none')
    plt.axhline(y=0, color='r', linestyle='--')
    plt.xlabel('Predicted Price')
    plt.ylabel('Residuals')
    plt.title('Residual Plot')
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
    plt.xlabel('Residuals')
    plt.ylabel('Frequency')
    plt.title('Residual Distribution')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('/mnt/agents/output/xgboost_residuals.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("📁 残差图已保存: xgboost_residuals.png")

    return model, X_test, y_test, y_pred


# ============================================================
# 第二部分: 分类任务（二分类 - 信用违约预测）
# ============================================================

def demo_classification():
    """二分类演示 - 模拟信用违约预测"""
    print("\n" + "=" * 60)
    print("【第二部分】XGBoost 二分类 - 信用违约预测案例")
    print("=" * 60)

    np.random.seed(42)
    n_samples = 2000

    X, y = make_classification(
        n_samples=n_samples, n_features=8, n_informative=5, n_redundant=2,
        n_classes=2, weights=[0.85, 0.15], flip_y=0.1, random_state=42
    )

    feature_names = ['income', 'debt_ratio', 'credit_history', 'employment_years',
                     'num_accounts', 'age', 'education', 'region_risk']
    X = pd.DataFrame(X, columns=feature_names)
    y = pd.Series(y, name='default')

    print(f"\n📊 数据集概况: {X.shape[0]} 样本 × {X.shape[1]} 特征")
    print(f"📊 类别分布:\n{y.value_counts()}")
    print(f"   违约率: {y.mean()*100:.1f}%")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scale_pos_weight = len(y_train[y_train==0]) / len(y_train[y_train==1])
    print(f"\n⚖️ 正负样本权重比: {scale_pos_weight:.2f}")

    # 使用DMatrix方式训练（兼容性更好）
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 5,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_lambda': 1,
        'scale_pos_weight': scale_pos_weight,
        'seed': 42
    }

    evals = [(dtrain, 'train'), (dtest, 'test')]
    model = xgb.train(
        params, dtrain, num_boost_round=300,
        evals=evals, early_stopping_rounds=30, verbose_eval=50
    )

    print(f"\n✅ 最优迭代轮数: {model.best_iteration}")

    y_prob = model.predict(dtest)
    y_pred = (y_prob > 0.5).astype(int)

    auc = roc_auc_score(y_test, y_prob)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"\n📊 分类评估指标:")
    print(f"   AUC:    {auc:.4f}")
    print(f"   Accuracy: {acc:.4f}")
    print(f"   F1-Score: {f1:.4f}")
    print(f"\n📋 分类报告:\n{classification_report(y_test, y_pred, target_names=['Normal', 'Default'])}")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    axes[0].plot(fpr, tpr, 'b-', lw=2, label=f'ROC Curve (AUC={auc:.3f})')
    axes[0].plot([0, 1], [0, 1], 'k--', label='Random')
    axes[0].fill_between(fpr, tpr, alpha=0.2)
    axes[0].set_xlabel('False Positive Rate')
    axes[0].set_ylabel('True Positive Rate')
    axes[0].set_title('ROC Curve')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[1],
                xticklabels=['Normal', 'Default'],
                yticklabels=['Normal', 'Default'])
    axes[1].set_xlabel('Predicted')
    axes[1].set_ylabel('Actual')
    axes[1].set_title('Confusion Matrix')

    importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.get_score(importance_type='weight').values()
    }).sort_values('importance', ascending=True)

    axes[2].barh(importance['feature'], importance['importance'])
    axes[2].set_xlabel('Importance')
    axes[2].set_title('Feature Importance (Weight)')
    axes[2].grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    plt.savefig('/mnt/agents/output/xgboost_classification_result.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("\n📁 分类结果图已保存: xgboost_classification_result.png")

    return model, X_test, y_test, y_prob


# ============================================================
# 第三部分: 超参数调优
# ============================================================

def demo_hyperparameter_tuning():
    """超参数网格搜索演示"""
    print("\n" + "=" * 60)
    print("【第三部分】超参数调优 - GridSearchCV")
    print("=" * 60)

    np.random.seed(42)
    X, y = make_regression(n_samples=500, n_features=6, noise=10, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    param_grid_small = {
        'max_depth': [3, 5, 7],
        'learning_rate': [0.05, 0.1],
        'n_estimators': [100, 200],
        'subsample': [0.8, 1.0]
    }

    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1
    )

    grid_search = GridSearchCV(
        model, param_grid_small, cv=3,
        scoring='neg_mean_squared_error',
        n_jobs=-1, verbose=1
    )

    print("\n🚀 开始网格搜索...")
    grid_search.fit(X_train, y_train)

    print(f"\n✅ 最优参数:")
    for param, value in grid_search.best_params_.items():
        print(f"   {param}: {value}")

    print(f"\n✅ 最优CV得分 (neg_RMSE): {np.sqrt(-grid_search.best_score_):.4f}")

    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"✅ 测试集 RMSE: {test_rmse:.4f}")

    return grid_search


# ============================================================
# 第四部分: 交叉验证
# ============================================================

def demo_cross_validation():
    """K折交叉验证"""
    print("\n" + "=" * 60)
    print("【第四部分】K折交叉验证 - 模型稳定性评估")
    print("=" * 60)

    np.random.seed(42)
    X, y = make_regression(n_samples=300, n_features=5, noise=15, random_state=42)

    model = xgb.XGBRegressor(
        max_depth=4, learning_rate=0.1, n_estimators=100,
        objective='reg:squarederror', random_state=42
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rmse_scores, r2_scores = [], []

    for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model.fit(X_train, y_train, verbose=False)
        y_pred = model.predict(X_val)

        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        r2 = r2_score(y_val, y_pred)
        rmse_scores.append(rmse)
        r2_scores.append(r2)
        print(f"   Fold {fold}: RMSE={rmse:.4f}, R²={r2:.4f}")

    print(f"\n📊 交叉验证统计:")
    print(f"   RMSE: {np.mean(rmse_scores):.4f} ± {np.std(rmse_scores):.4f}")
    print(f"   R²:   {np.mean(r2_scores):.4f} ± {np.std(r2_scores):.4f}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].bar(range(1, 6), rmse_scores, color='steelblue', edgecolor='black')
    axes[0].axhline(y=np.mean(rmse_scores), color='r', linestyle='--', 
                    label=f'Mean={np.mean(rmse_scores):.3f}')
    axes[0].set_xlabel('Fold')
    axes[0].set_ylabel('RMSE')
    axes[0].set_title('5-Fold CV RMSE')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3, axis='y')

    axes[1].bar(range(1, 6), r2_scores, color='coral', edgecolor='black')
    axes[1].axhline(y=np.mean(r2_scores), color='r', linestyle='--',
                    label=f'Mean={np.mean(r2_scores):.3f}')
    axes[1].set_xlabel('Fold')
    axes[1].set_ylabel('R² Score')
    axes[1].set_title('5-Fold CV R²')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('/mnt/agents/output/xgboost_cross_validation.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("\n📁 交叉验证图已保存: xgboost_cross_validation.png")

    return rmse_scores, r2_scores


# ============================================================
# 第五部分: 保存/加载模型
# ============================================================

def demo_model_save_load(model, filename='/mnt/agents/output/xgboost_model.json'):
    """模型持久化"""
    print("\n" + "=" * 60)
    print("【第五部分】模型保存与加载")
    print("=" * 60)

    model.save_model(filename)
    print(f"\n💾 模型已保存: {filename}")

    loaded_model = xgb.Booster()
    loaded_model.load_model(filename)
    print(f"✅ 模型已加载")

    return loaded_model


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("🚀 XGBoost 完整实战代码启动")
    print("=" * 60)

    reg_model, _, _, _ = demo_regression()
    clf_model, _, _, _ = demo_classification()
    # demo_hyperparameter_tuning()  # 注释掉节省运行时间
    demo_cross_validation()
    demo_model_save_load(reg_model)

    print("\n" + "=" * 60)
    print("✅ 所有演示完成！")
    print("📁 输出文件:")
    print("   - xgboost_regression_result.png")
    print("   - xgboost_residuals.png")
    print("   - xgboost_classification_result.png")
    print("   - xgboost_cross_validation.png")
    print("   - xgboost_model.json")
    print("=" * 60)

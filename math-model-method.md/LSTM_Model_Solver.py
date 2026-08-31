#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSTM 时间序列预测模型 — 数学建模求解代码
适用场景：单变量/多变量时间序列预测
框架：TensorFlow 2.x + Keras
作者：Math-Modeling-Skill-2026
"""

# ========================== 0. 环境导入 ==========================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

# 设置中文显示（Windows/Linux 兼容）
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 固定随机种子，保证结果可复现
np.random.seed(42)
tf.random.set_seed(42)

print(f"TensorFlow 版本: {tf.__version__}")
print(f"GPU 是否可用: {tf.config.list_physical_devices('GPU')}")


# ========================== 1. 数据预处理 ==========================
def load_and_preprocess_data(filepath=None, use_synthetic=False):
    """
    加载数据并进行预处理
    :param filepath: CSV 文件路径（需包含 'value' 列或自定义列）
    :param use_synthetic: 是否使用合成数据（用于演示）
    :return: 原始数据 DataFrame, 归一化后的数据, Scaler 对象
    """
    if use_synthetic or filepath is None:
        # 生成合成正弦数据 + 趋势 + 噪声（模拟真实时序）
        print("[INFO] 使用合成数据进行演示...")
        t = np.linspace(0, 200, 2000)
        trend = 0.02 * t
        seasonal = 10 * np.sin(2 * np.pi * t / 50)
        noise = np.random.normal(0, 1, len(t))
        data_values = trend + seasonal + noise
        
        df = pd.DataFrame({'value': data_values})
    else:
        df = pd.read_csv(filepath)
        # 假设目标列为第一列或名为 'value'
        if 'value' not in df.columns:
            df.rename(columns={df.columns[0]: 'value'}, inplace=True)
    
    # 归一化（MinMaxScaler 将数据映射到 [0, 1]）
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df[['value']])
    
    print(f"[INFO] 数据量: {len(df)} 条")
    print(f"[INFO] 数据范围: [{df['value'].min():.2f}, {df['value'].max():.2f}]")
    
    return df, scaled_data, scaler


def create_sequences(data, timestep):
    """
    构造监督学习样本（滑动窗口）
    :param data: 归一化后的序列数据 (N, 1)
    :param timestep: 时间步长（滑动窗口大小）
    :return: X (samples, timestep, 1), y (samples, 1)
    """
    X, y = [], []
    for i in range(len(data) - timestep):
        X.append(data[i:i + timestep, 0])
        y.append(data[i + timestep, 0])
    
    X = np.array(X)
    y = np.array(y)
    
    # LSTM 输入要求: (samples, timestep, features)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    
    return X, y


# ========================== 2. 数据集划分 ==========================
def split_data(X, y, train_ratio=0.8, val_ratio=0.1):
    """
    划分训练集、验证集、测试集
    """
    total_len = len(X)
    train_size = int(total_len * train_ratio)
    val_size = int(total_len * val_ratio)
    
    X_train, y_train = X[:train_size], y[:train_size]
    X_val, y_val = X[train_size:train_size + val_size], y[train_size:train_size + val_size]
    X_test, y_test = X[train_size + val_size:], y[train_size + val_size:]
    
    print(f"[INFO] 训练集: {len(X_train)} | 验证集: {len(X_val)} | 测试集: {len(X_test)}")
    
    return X_train, y_train, X_val, y_val, X_test, y_test


# ========================== 3. 构建 LSTM 网络 ==========================
def build_lstm_model(timestep, feature_dim=1, lstm_units=64, dropout_rate=0.2):
    """
    构建 LSTM 预测模型
    :param timestep: 时间步长
    :param feature_dim: 输入特征维度
    :param lstm_units: LSTM 神经元数
    :param dropout_rate: Dropout 比率
    :return: Keras Model 对象
    """
    model = Sequential([
        # 第一层 LSTM
        # return_sequences=True: 输出完整序列，用于堆叠下一层 LSTM
        LSTM(units=lstm_units, return_sequences=True, 
             input_shape=(timestep, feature_dim)),
        Dropout(dropout_rate),  # 正则化，防止过拟合
        
        # 第二层 LSTM（可选，如需更深网络可取消注释）
        # LSTM(units=lstm_units // 2, return_sequences=False),
        # Dropout(dropout_rate),
        
        # 全连接层：提取高层特征
        Dense(units=32, activation='relu'),
        Dropout(dropout_rate / 2),
        
        # 输出层：单步预测输出 1 个值
        Dense(units=1)
    ])
    
    # 编译模型
    model.compile(
        optimizer=Adam(learning_rate=0.001),  # Adam 优化器，默认 lr=0.001
        loss='mse',                            # 均方误差损失函数
        metrics=['mae']                        # 监控 MAE
    )
    
    model.summary()
    return model


# ========================== 4. 模型训练 ==========================
def train_model(model, X_train, y_train, X_val, y_val, 
                epochs=100, batch_size=32, patience=15):
    """
    训练 LSTM 模型，集成 Early Stopping 防止过拟合
    """
    # 早停回调：验证损失 15 轮不下降则停止，并恢复最佳权重
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=patience,
        restore_best_weights=True,
        verbose=1
    )
    
    # 模型检查点：保存验证损失最低的模型（可选）
    checkpoint = ModelCheckpoint(
        'best_lstm_model.h5',
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    )
    
    # 训练
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop, checkpoint],
        verbose=2
    )
    
    return history


# ========================== 5. 模型评估与预测 ==========================
def evaluate_model(model, X_test, y_test, scaler):
    """
    模型评估：反归一化后计算各项指标
    """
    # 预测（输出仍为归一化值）
    y_pred_scaled = model.predict(X_test)
    
    # 反归一化：还原为原始尺度
    y_test_inv = scaler.inverse_transform(y_test.reshape(-1, 1))
    y_pred_inv = scaler.inverse_transform(y_pred_scaled)
    
    # 计算评价指标
    rmse = np.sqrt(mean_squared_error(y_test_inv, y_pred_inv))
    mae = mean_absolute_error(y_test_inv, y_pred_inv)
    mape = np.mean(np.abs((y_test_inv - y_pred_inv) / y_test_inv)) * 100
    r2 = r2_score(y_test_inv, y_pred_inv)
    
    print("\n" + "=" * 50)
    print("模型评估结果")
    print("=" * 50)
    print(f"RMSE : {rmse:.4f}")
    print(f"MAE  : {mae:.4f}")
    print(f"MAPE : {mape:.4f}%")
    print(f"R2   : {r2:.4f}")
    print("=" * 50)
    
    return y_test_inv, y_pred_inv, {'RMSE': rmse, 'MAE': mae, 'MAPE': mape, 'R2': r2}


# ========================== 6. 可视化 ==========================
def plot_results(history, y_true, y_pred, metrics, save_path=None):
    """
    绘制训练曲线与预测对比图
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # (1) 损失曲线
    ax1 = axes[0, 0]
    ax1.plot(history.history['loss'], label='Train Loss', color='blue')
    ax1.plot(history.history['val_loss'], label='Val Loss', color='orange')
    ax1.set_title('Model Loss During Training')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss (MSE)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # (2) MAE 曲线
    ax2 = axes[0, 1]
    ax2.plot(history.history['mae'], label='Train MAE', color='green')
    ax2.plot(history.history['val_mae'], label='Val MAE', color='red')
    ax2.set_title('Model MAE During Training')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('MAE')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # (3) 预测 vs 真实值（整体）
    ax3 = axes[1, 0]
    ax3.plot(y_true, label='True Value', color='blue', linewidth=1.5)
    ax3.plot(y_pred, label='Predicted Value', color='red', linewidth=1.5, linestyle='--')
    ax3.fill_between(range(len(y_true)), y_true.flatten(), y_pred.flatten(), 
                      alpha=0.2, color='gray', label='Error')
    ax3.set_title(f'Prediction vs True Value\nRMSE={metrics["RMSE"]:.3f}, MAPE={metrics["MAPE"]:.2f}%')
    ax3.set_xlabel('Time Step')
    ax3.set_ylabel('Value')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # (4) 残差分布
    residuals = y_true - y_pred
    ax4 = axes[1, 1]
    ax4.hist(residuals, bins=30, edgecolor='black', alpha=0.7, color='purple')
    ax4.axvline(x=0, color='red', linestyle='--', label='Zero Error')
    ax4.set_title('Residual Distribution')
    ax4.set_xlabel('Residual (True - Pred)')
    ax4.set_ylabel('Frequency')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"[INFO] 图片已保存至: {save_path}")
    
    plt.show()


def plot_comparison_with_baseline(y_true, y_pred_lstm, y_pred_baseline=None, 
                                   baseline_name='ARIMA', save_path=None):
    """
    与其他基准模型的对比图（可选）
    """
    plt.figure(figsize=(12, 5))
    plt.plot(y_true, label='True Value', color='black', linewidth=2)
    plt.plot(y_pred_lstm, label='LSTM Prediction', color='red', linestyle='--', linewidth=1.5)
    
    if y_pred_baseline is not None:
        plt.plot(y_pred_baseline, label=f'{baseline_name} Prediction', 
                 color='green', linestyle='-.', linewidth=1.5)
    
    plt.title('Model Comparison: LSTM vs Baseline')
    plt.xlabel('Time Step')
    plt.ylabel('Value')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()


# ========================== 7. 主程序入口 ==========================
def main():
    """
    LSTM 建模主流程
    """
    # ---------------- 超参数设置 ----------------
    TIMESTEP = 20           # 时间步长（滑动窗口大小）
    LSTM_UNITS = 64         # LSTM 神经元数
    DROPOUT_RATE = 0.2      # Dropout 比率
    EPOCHS = 200            # 最大训练轮数（Early Stopping 会提前终止）
    BATCH_SIZE = 32         # 批次大小
    PATIENCE = 15           # 早停耐心值
    
    # ---------------- 1. 加载数据 ----------------
    df, scaled_data, scaler = load_and_preprocess_data(use_synthetic=True)
    
    # ---------------- 2. 构造序列 ----------------
    X, y = create_sequences(scaled_data, timestep=TIMESTEP)
    
    # ---------------- 3. 划分数据集 ----------------
    X_train, y_train, X_val, y_val, X_test, y_test = split_data(
        X, y, train_ratio=0.8, val_ratio=0.1
    )
    
    # ---------------- 4. 构建模型 ----------------
    model = build_lstm_model(
        timestep=TIMESTEP,
        feature_dim=1,
        lstm_units=LSTM_UNITS,
        dropout_rate=DROPOUT_RATE
    )
    
    # ---------------- 5. 训练模型 ----------------
    history = train_model(
        model, X_train, y_train, X_val, y_val,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        patience=PATIENCE
    )
    
    # ---------------- 6. 评估与预测 ----------------
    y_test_inv, y_pred_inv, metrics = evaluate_model(model, X_test, y_test, scaler)
    
    # ---------------- 7. 可视化 ----------------
    plot_results(
        history, y_test_inv, y_pred_inv, metrics,
        save_path='lstm_prediction_results.png'
    )
    
    # ---------------- 8. 保存模型（可选）----------------
    model.save('lstm_final_model.h5')
    print("[INFO] 模型已保存至: lstm_final_model.h5")
    
    # ---------------- 9. 未来多步预测（可选）----------------
    def future_predict(model, last_sequence, scaler, steps=30):
        """
        使用模型进行未来多步预测（递归预测）
        """
        current_seq = last_sequence.copy()
        predictions = []
        
        for _ in range(steps):
            pred = model.predict(current_seq.reshape(1, TIMESTEP, 1), verbose=0)
            predictions.append(pred[0, 0])
            # 滑动窗口：去掉第一个，加入新预测
            current_seq = np.append(current_seq[1:], pred[0, 0])
        
        predictions = np.array(predictions).reshape(-1, 1)
        return scaler.inverse_transform(predictions)
    
    last_seq = scaled_data[-TIMESTEP:, 0]
    future_preds = future_predict(model, last_seq, scaler, steps=30)
    print(f"[INFO] 未来 30 步预测完成，预测值范围: [{future_preds.min():.2f}, {future_preds.max():.2f}]")
    
    print("\n[INFO] === LSTM 建模全流程结束 ===")


# ========================== 运行 ==========================
if __name__ == '__main__':
    main()

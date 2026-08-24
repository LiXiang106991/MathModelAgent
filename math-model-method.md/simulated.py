"""
模拟退火（Simulated Annealing, SA）骨架
适用于 TSP、函数优化、组合优化等国赛问题
"""

import numpy as np
import random
import math
import copy


def simulated_annealing(
    initial_solution,
    objective_func,          # 目标函数，返回值越小越好（最小化）
    neighbor_func,           # 生成邻域解的函数
    T0=1000,                 # 初始温度
    T_min=1e-3,              # 终止温度
    alpha=0.95,              # 冷却系数
    max_iter_per_temp=100,   # 每个温度下的迭代次数
    maximize=False           # 若为最大化问题，设为 True
):
    """
    通用模拟退火框架
    
    返回:
        best_solution: 最优解
        best_value: 最优目标值
        history: 迭代历史（可选画收敛曲线）
    """
    current = copy.deepcopy(initial_solution)
    current_value = objective_func(current)
    
    if maximize:
        current_value = -current_value
    
    best = copy.deepcopy(current)
    best_value = current_value
    
    T = T0
    history = [best_value]
    
    while T > T_min:
        for _ in range(max_iter_per_temp):
            neighbor = neighbor_func(current)
            neighbor_value = objective_func(neighbor)
            
            if maximize:
                neighbor_value = -neighbor_value
            
            delta = neighbor_value - current_value
            
            # Metropolis 准则
            if delta < 0 or random.random() < math.exp(-delta / T):
                current = neighbor
                current_value = neighbor_value
                
                if current_value < best_value:
                    best = copy.deepcopy(current)
                    best_value = current_value
        
        history.append(best_value)
        T *= alpha
    
    if maximize:
        best_value = -best_value
    
    return best, best_value, history


# ==================== TSP 示例 ====================
def tsp_objective(path, dist_matrix):
    """计算路径总长度"""
    n = len(path)
    length = sum(dist_matrix[path[i], path[(i+1)%n]] for i in range(n))
    return length


def tsp_neighbor(path):
    """2-opt 邻域：随机交换两个城市"""
    new_path = path.copy()
    i, j = sorted(random.sample(range(len(path)), 2))
    new_path[i:j+1] = reversed(new_path[i:j+1])
    return new_path


if __name__ == "__main__":
    # 简单 TSP 测试（5个城市）
    np.random.seed(42)
    n_cities = 10
    coords = np.random.rand(n_cities, 2) * 100
    dist_matrix = np.sqrt(((coords[:, np.newaxis, :] - coords[np.newaxis, :, :]) ** 2).sum(axis=2))
    
    initial_path = list(range(n_cities))
    random.shuffle(initial_path)
    
    best_path, best_length, history = simulated_annealing(
        initial_solution=initial_path,
        objective_func=lambda p: tsp_objective(p, dist_matrix),
        neighbor_func=tsp_neighbor,
        T0=1000,
        alpha=0.95,
        max_iter_per_temp=200
    )
    
    print("最优路径：", best_path)
    print("最优长度：", round(best_length, 2))
    print("迭代次数：", len(history))
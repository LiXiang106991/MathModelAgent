"""
NSGA-II 简单实现（针对双目标优化）
适合国赛多目标问题的快速原型
注意：这是教学简化版，实际大规模问题建议用 pymoo 库
"""

import numpy as np
import random
from copy import deepcopy


def dominates(a, b):
    """判断 a 是否支配 b（最小化问题）"""
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def fast_non_dominated_sort(population, objectives):
    """快速非支配排序"""
    S = [[] for _ in range(len(population))]
    n = [0] * len(population)
    rank = [0] * len(population)
    fronts = [[]]
    
    for p in range(len(population)):
        for q in range(len(population)):
            if dominates(objectives[p], objectives[q]):
                S[p].append(q)
            elif dominates(objectives[q], objectives[p]):
                n[p] += 1
        if n[p] == 0:
            rank[p] = 0
            fronts[0].append(p)
    
    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in S[p]:
                n[q] -= 1
                if n[q] == 0:
                    rank[q] = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)
    
    return fronts[:-1], rank


def crowding_distance(front, objectives):
    """计算拥挤度"""
    n = len(front)
    if n == 0:
        return []
    distance = [0.0] * n
    num_obj = len(objectives[0])
    
    for m in range(num_obj):
        sorted_idx = sorted(range(n), key=lambda i: objectives[front[i]][m])
        distance[sorted_idx[0]] = distance[sorted_idx[-1]] = float('inf')
        
        obj_min = objectives[front[sorted_idx[0]]][m]
        obj_max = objectives[front[sorted_idx[-1]]][m]
        if obj_max == obj_min:
            continue
        for i in range(1, n-1):
            distance[sorted_idx[i]] += (objectives[front[sorted_idx[i+1]]][m] - 
                                        objectives[front[sorted_idx[i-1]]][m]) / (obj_max - obj_min)
    return distance


def nsga2(
    pop_size=50,
    generations=50,
    n_var=2,
    bounds=(-5, 5),
    objective_func=None,   # 返回 [f1, f2] 的列表/数组
    crossover_rate=0.9,
    mutation_rate=0.1
):
    """
    简化版 NSGA-II（实数编码，双目标）
    
    参数:
        objective_func: 函数，输入个体（list/array），返回目标值列表 [f1, f2]
    
    返回:
        pareto_front: Pareto 前沿解集
        pareto_objectives: 对应目标值
    """
    # 初始化种群
    population = [np.random.uniform(bounds[0], bounds[1], n_var) for _ in range(pop_size)]
    
    for gen in range(generations):
        # 计算目标
        objectives = [objective_func(ind) for ind in population]
        
        # 非支配排序
        fronts, rank = fast_non_dominated_sort(population, objectives)
        
        # 生成子代（简单交叉 + 变异）
        offspring = []
        while len(offspring) < pop_size:
            p1, p2 = random.sample(population, 2)
            child = deepcopy(p1)
            if random.random() < crossover_rate:
                alpha = random.random()
                child = alpha * p1 + (1 - alpha) * p2
            if random.random() < mutation_rate:
                idx = random.randint(0, n_var-1)
                child[idx] = np.random.uniform(bounds[0], bounds[1])
            offspring.append(np.clip(child, bounds[0], bounds[1]))
        
        # 合并父子代
        combined = population + offspring
        combined_obj = [objective_func(ind) for ind in combined]
        
        # 再排序并选择
        fronts, _ = fast_non_dominated_sort(combined, combined_obj)
        new_population = []
        for front in fronts:
            if len(new_population) + len(front) <= pop_size:
                new_population.extend([combined[i] for i in front])
            else:
                # 按拥挤度选择
                dist = crowding_distance(front, combined_obj)
                sorted_front = [x for _, x in sorted(zip(dist, front), reverse=True)]
                new_population.extend([combined[i] for i in sorted_front[:pop_size - len(new_population)]])
                break
        population = new_population
    
    # 最终 Pareto 前沿
    objectives = [objective_func(ind) for ind in population]
    fronts, _ = fast_non_dominated_sort(population, objectives)
    pareto_idx = fronts[0]
    pareto_front = [population[i] for i in pareto_idx]
    pareto_objectives = [objectives[i] for i in pareto_idx]
    
    return pareto_front, pareto_objectives


# 使用示例：ZDT1 测试函数
if __name__ == "__main__":
    def zdt1(x):
        f1 = x[0]
        g = 1 + 9 * np.sum(x[1:]) / (len(x) - 1)
        f2 = g * (1 - np.sqrt(f1 / g))
        return [f1, f2]
    
    pareto_x, pareto_f = nsga2(
        pop_size=40,
        generations=30,
        n_var=5,
        bounds=(0, 1),
        objective_func=zdt1
    )
    
    print(f"找到 {len(pareto_x)} 个 Pareto 最优解")
    print("部分目标值示例：")
    for f in pareto_f[:5]:
        print(np.round(f, 4))
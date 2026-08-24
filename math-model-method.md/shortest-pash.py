"""
最短路问题 - NetworkX 实现
支持 Dijkstra、Bellman-Ford、Floyd-Warshall
国赛图论/路径规划常用
"""

import networkx as nx
import matplotlib.pyplot as plt


def create_graph(edges, directed=False):
    """
    创建图
    edges: list of (u, v, weight) 或 (u, v)
    """
    G = nx.DiGraph() if directed else nx.Graph()
    for edge in edges:
        if len(edge) == 3:
            u, v, w = edge
            G.add_edge(u, v, weight=w)
        else:
            u, v = edge
            G.add_edge(u, v, weight=1)
    return G


def dijkstra_shortest_path(G, source, target):
    """Dijkstra 最短路（非负权）"""
    try:
        path = nx.dijkstra_path(G, source, target, weight='weight')
        length = nx.dijkstra_path_length(G, source, target, weight='weight')
        return path, length
    except nx.NetworkXNoPath:
        return None, float('inf')


def bellman_ford_shortest_path(G, source, target):
    """Bellman-Ford（可处理负权）"""
    try:
        path = nx.bellman_ford_path(G, source, target, weight='weight')
        length = nx.bellman_ford_path_length(G, source, target, weight='weight')
        return path, length
    except (nx.NetworkXNoPath, nx.NetworkXUnbounded):
        return None, float('inf')


def floyd_warshall(G):
    """全源最短路"""
    return dict(nx.floyd_warshall(G, weight='weight'))


def single_source_all(G, source):
    """单源到所有节点的最短路"""
    return nx.single_source_dijkstra_path_length(G, source, weight='weight')


# 使用示例
if __name__ == "__main__":
    # 示例图
    edges = [
        ('A', 'B', 4),
        ('A', 'C', 2),
        ('B', 'C', 1),
        ('B', 'D', 5),
        ('C', 'D', 8),
        ('C', 'E', 10),
        ('D', 'E', 2),
        ('D', 'F', 6),
        ('E', 'F', 3)
    ]
    
    G = create_graph(edges, directed=False)
    
    print("=== Dijkstra 最短路 (A → F) ===")
    path, length = dijkstra_shortest_path(G, 'A', 'F')
    print(f"路径: {path}")
    print(f"长度: {length}")
    
    print("\n=== 单源最短路 (从 A 出发) ===")
    distances = single_source_all(G, 'A')
    for node, dist in sorted(distances.items()):
        print(f"A → {node}: {dist}")
    
    print("\n=== Floyd-Warshall 部分结果 ===")
    all_pairs = floyd_warshall(G)
    print(f"A → F: {all_pairs['A']['F']}")
    print(f"B → E: {all_pairs['B']['E']}")
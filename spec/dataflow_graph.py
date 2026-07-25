import networkx as nx
from spec.system_spec import SystemSpec
from typing import List, Dict, Any, Optional


def build_execution_order(spec: SystemSpec) -> List[str]:
    """
    构建 DAG 并返回拓扑排序后的 Agent ID 列表。
    Phase 1 简化：假设用户按顺序定义，这里主要做校验。
    """
    G = nx.DiGraph()

    # 添加节点
    for agent in spec.agents:
        G.add_node(agent.id, data=agent)

    # 添加边 (简单逻辑：如果 agent B 的 input_keys 包含 agent A 的 output_key，则 A->B)
    # 这里需要建立 output_key 到 agent_id 的映射
    output_map = {a.output_key: a.id for a in spec.agents}

    for agent in spec.agents:
        for key in agent.input_keys:
            if key in output_map:
                producer_id = output_map[key]
                if producer_id != agent.id:
                    G.add_edge(producer_id, agent.id)

    # 拓扑排序
    try:
        return list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        raise ValueError("检测到循环依赖，请检查 JSON 配置")
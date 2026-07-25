from typing import Dict, Any, List

# Phase 1 使用简单的 Dict 存储全局状态
# Batch 模式下，State 是一个列表，每个元素是一个 Dict
BatchState = List[Dict[str, Any]]

def initialize_batch_state(batch_size: int) -> BatchState:
    return [{} for _ in range(batch_size)]
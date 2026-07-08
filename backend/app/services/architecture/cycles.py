from typing import Dict, List, Set

def find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Finds all circular dependency paths using a DFS-based cycle finder.
    """
    cycles = []
    visited = set()
    stack = []
    stack_set = set()

    def dfs(node: str):
        if node in stack_set:
            # Cycle found! Extract the cycle path
            cycle_start = stack.index(node)
            cycle_path = stack[cycle_start:] + [node]
            # Normalize to avoid duplicates (e.g. A->B->A is same as B->A->B)
            # Find index of min node
            min_node = min(cycle_path[:-1])
            min_idx = cycle_path.index(min_node)
            normalized = cycle_path[min_idx:-1] + cycle_path[:min_idx] + [min_node]
            if normalized not in cycles:
                cycles.append(normalized)
            return
            
        if node in visited:
            return
            
        visited.add(node)
        stack.append(node)
        stack_set.add(node)
        
        for neighbor in graph.get(node, []):
            dfs(neighbor)
            
        stack.pop()
        stack_set.remove(node)

    for node in graph:
        dfs(node)
        
    return cycles

import uuid
from typing import Any, Dict, List, Set

class ArchitectureKnowledgeBuilder:
    @classmethod
    def build(cls, repo_id: uuid.UUID, files: List[Any]) -> Dict[str, Any]:
        """
        Builds the complete architecture knowledge graph including packages, layers,
        dependencies, circular dependencies, and layers categorization.
        """
        nodes = []
        edges = []
        
        # Categorized lists
        controllers = []
        services = []
        repositories = []
        entities = []
        utilities = []
        configs = []
        
        packages = set()
        graph = {}
        
        for f in files:
            path = f.path.replace("\\", "/")
            module_type = getattr(f, "module_type", "Unknown")
            
            # Extract package/directory
            parts = path.split("/")
            if len(parts) > 1:
                pkg = "/".join(parts[:-1])
                packages.add(pkg)
            
            # Map outgoing dependencies for circular checks
            graph[path] = getattr(f, "outgoing_dependencies", []) or []
            
            # Categorize based on file name or module type
            lower_path = path.lower()
            node_data = {
                "id": path,
                "type": "file",
                "module_type": module_type,
                "size_bytes": getattr(f, "size_bytes", 0),
                "loc": getattr(f, "lines_of_code", 0)
            }
            nodes.append(node_data)
            
            if "controller" in lower_path or module_type == "Controller":
                controllers.append(path)
            elif "service" in lower_path or module_type == "Service":
                services.append(path)
            elif "repository" in lower_path or "dao" in lower_path or module_type == "Repository":
                repositories.append(path)
            elif "entity" in lower_path or "model" in lower_path or "dto" in lower_path:
                entities.append(path)
            elif "util" in lower_path or "helper" in lower_path or "common" in lower_path:
                utilities.append(path)
            elif "config" in lower_path or "properties" in lower_path or "setting" in lower_path:
                configs.append(path)

            # Add edges for outgoing dependencies
            for target in graph[path]:
                edges.append({
                    "source": path,
                    "target": target.replace("\\", "/"),
                    "type": "depends_on"
                })

        # Cycle detection
        cycles = cls.find_cycles(graph)

        # Entry points: text files with ca = 0 (no incoming dependencies) but ce > 0
        entry_points = []
        all_targets = {edge["target"] for edge in edges}
        for f in files:
            path = f.path.replace("\\", "/")
            if path not in all_targets and len(graph.get(path, [])) > 0:
                entry_points.append(path)

        return {
            "project_structure": {
                "total_files": len(files),
                "packages": sorted(list(packages)),
            },
            "layers": {
                "controllers": controllers,
                "services": services,
                "repositories": repositories,
                "entities": entities,
                "utilities": utilities,
                "configurations": configs
            },
            "dependency_graph": {
                "nodes": nodes,
                "edges": edges
            },
            "circular_dependencies": cycles,
            "entry_points": entry_points
        }

    @classmethod
    def find_cycles(cls, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Find simple cycles in the dependency graph."""
        cycles = []
        visited = {}  # 0 = unvisited, 1 = visiting, 2 = visited
        
        def dfs(node: str, path: List[str]) -> None:
            visited[node] = 1
            path.append(node)
            for neighbor in graph.get(node, []):
                neighbor = neighbor.replace("\\", "/")
                if neighbor not in graph:
                    continue
                if visited.get(neighbor, 0) == 1:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    # Sort/deduplicate cycles to prevent permutation duplicates
                    if sorted(cycle) not in [sorted(c) for c in cycles]:
                        cycles.append(cycle)
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor, path)
            path.pop()
            visited[node] = 2

        for node in graph:
            if visited.get(node, 0) == 0:
                dfs(node, [])
        return cycles

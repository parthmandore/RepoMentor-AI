import ast
import os
import re
from typing import List, Set

def resolve_python_import(import_name: str, current_file: str, all_files: Set[str]) -> str:
    """Resolves a Python absolute/relative import to a repository file path."""
    parts = import_name.split(".")
    # Try as package path from root
    candidate = "/".join(parts) + ".py"
    if candidate in all_files:
        return candidate
    candidate_init = "/".join(parts) + "/__init__.py"
    if candidate_init in all_files:
        return candidate_init
        
    # Try relative to current file's folder
    current_dir = os.path.dirname(current_file)
    rel_candidate = os.path.normpath(os.path.join(current_dir, "/".join(parts))) + ".py"
    rel_candidate = rel_candidate.replace("\\", "/")
    if rel_candidate in all_files:
        return rel_candidate
        
    return ""

def parse_python_imports(content: str, current_file: str, all_files: Set[str]) -> List[str]:
    imports = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = resolve_python_import(alias.name, current_file, all_files)
                    if resolved:
                        imports.append(resolved)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Resolve base module
                    resolved = resolve_python_import(node.module, current_file, all_files)
                    if resolved:
                        imports.append(resolved)
                    else:
                        # Try combining module and names
                        for alias in node.names:
                            full_name = f"{node.module}.{alias.name}"
                            resolved_sub = resolve_python_import(full_name, current_file, all_files)
                            if resolved_sub:
                                imports.append(resolved_sub)
    except SyntaxError:
        pass
    return list(set(imports))

def parse_jsts_imports(content: str, current_file: str, all_files: Set[str]) -> List[str]:
    imports = []
    # Match: import ... from 'path', require('path'), import('path')
    patterns = [
        r"(?:import|export)\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
        r"import\s+['\"]([^'\"]+)['\"]",
        r"require\(\s*['\"]([^'\"]+)['\"]\s*\)",
        r"import\(\s*['\"]([^'\"]+)['\"]\s*\)"
    ]
    
    current_dir = os.path.dirname(current_file)
    
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            import_path = match.group(1)
            # Only resolve relative imports
            if import_path.startswith(".") or import_path.startswith("/"):
                # Clean path
                target_path = os.path.normpath(os.path.join(current_dir, import_path)).replace("\\", "/")
                # Check with extensions
                for ext in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"]:
                    candidate = target_path + ext
                    if candidate in all_files:
                        imports.append(candidate)
                        break
    return list(set(imports))

def parse_java_dependencies(content: str, current_file: str, all_files: Set[str]) -> List[str]:
    dependencies = []
    
    # 1. Parse imports
    # Match: import com.foo.bar.MyClass; or import com.foo.bar.*;
    import_pattern = re.compile(r"import\s+([\w\.\*]+);")
    for match in import_pattern.finditer(content):
        imp = match.group(1)
        if imp.endswith(".*"):
            pkg_path = imp[:-2].replace(".", "/")
            for f in all_files:
                if pkg_path in f:
                    dependencies.append(f)
        else:
            class_path = imp.replace(".", "/") + ".java"
            for f in all_files:
                if f.endswith(class_path):
                    dependencies.append(f)
                    break
                    
    # 2. Parse extends & implements (extends ParentClass, implements Interface1, Interface2)
    # Match: class MyClass extends ParentClass implements Interface1, Interface2 {
    class_decl_pattern = re.compile(r"\bclass\s+\w+(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\b")
    for match in class_decl_pattern.finditer(content):
        parent = match.group(1)
        interfaces_str = match.group(2)
        if parent:
            for f in all_files:
                if f.endswith(f"/{parent}.java"):
                    dependencies.append(f)
                    break
        if interfaces_str:
            interfaces = [i.strip() for i in interfaces_str.split(",") if i.strip()]
            for inter in interfaces:
                for f in all_files:
                    if f.endswith(f"/{inter}.java"):
                        dependencies.append(f)
                        break

    # 3. Parse annotations / injection / field references (Spring Boot annotations like @Autowired, constructor injection, field declarations)
    field_pattern = re.compile(r"(?:@Autowired|@Resource|@Inject|private|protected|public)\s+(?:final\s+)?([\w<>\[\]]+)\s+\w+\s*;")
    for match in field_pattern.finditer(content):
        type_name = match.group(1)
        # Strip generic parameters if any (e.g. List<MyService> -> MyService)
        generic_type_match = re.search(r"<([^>]+)>", type_name)
        type_names_to_check = [type_name]
        if generic_type_match:
            type_names_to_check = [t.strip() for t in generic_type_match.group(1).split(",")]
            
        for tn in type_names_to_check:
            if tn not in {"String", "Integer", "Long", "Double", "Float", "Boolean", "List", "Map", "Set", "Optional"}:
                for f in all_files:
                    if f.endswith(f"/{tn}.java"):
                        dependencies.append(f)
                        break

    # 4. Constructor injection parameter types
    class_name = current_file.split("/")[-1].replace(".java", "")
    constructor_pattern = re.compile(r"\b" + class_name + r"\s*\(([^)]*)\)")
    for match in constructor_pattern.finditer(content):
        params_str = match.group(1)
        if params_str:
            for param in params_str.split(","):
                param = param.strip()
                if param:
                    parts = param.split()
                    if len(parts) >= 2:
                        type_name = parts[-2]
                        if type_name not in {"String", "Integer", "Long", "Double", "Float", "Boolean", "List", "Map", "Set", "Optional"}:
                            for f in all_files:
                                if f.endswith(f"/{type_name}.java"):
                                    dependencies.append(f)
                                    break

    # Exclude self reference
    dependencies = [d for d in dependencies if d != current_file]
    return list(set(dependencies))

def extract_dependencies(content: str, path: str, extension: str, all_files: Set[str]) -> List[str]:
    clean_path = path.replace("\\", "/")
    if extension == ".py":
        return parse_python_imports(content, clean_path, all_files)
    elif extension in {".js", ".jsx", ".ts", ".tsx"}:
        return parse_jsts_imports(content, clean_path, all_files)
    elif extension == ".java":
        return parse_java_dependencies(content, clean_path, all_files)
    return []

import os

def classify_file(path: str, extension: str, content: str) -> str:
    """
    Classify a file into one of the designated architectural module types.
    """
    path_lower = path.replace("\\", "/").lower()
    filename = os.path.basename(path_lower)
    
    if extension in {".ts", ".tsx", ".js", ".jsx"}:
        if filename.startswith("use") and filename != "user":
            return "Hook"
        if extension in {".tsx", ".jsx"} or "/components/" in path_lower or "/views/" in path_lower:
            return "Component"
            
    if "/controllers/" in path_lower or "controller" in filename:
        return "Controller"
    if "/api/" in path_lower or "/endpoints/" in path_lower or "/routes/" in path_lower or "route" in filename or "endpoint" in filename:
        # Check if python file contains APIRouter references
        if extension == ".py" and "APIRouter(" in content:
            return "API"
        return "API"
    if "/services/" in path_lower or "service" in filename or "svc" in filename:
        return "Service"
    if "/repositories/" in path_lower or "repository" in filename or "repo" in filename:
        return "Repository"
    if "/models/" in path_lower or "/schemas/" in path_lower or "model" in filename or "schema" in filename or "entity" in filename:
        return "Model"
    if "/middleware/" in path_lower or "middleware" in filename:
        return "Middleware"
    if "/config/" in path_lower or "config" in filename or "settings" in filename or filename.startswith(".env"):
        return "Configuration"
    if "/utils/" in path_lower or "/helpers/" in path_lower or "util" in filename or "helper" in filename:
        return "Utility"
        
    return "Unknown"

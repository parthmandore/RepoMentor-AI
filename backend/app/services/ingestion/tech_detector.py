import os
import json
import re
from typing import Dict, List, Any

EXTENSION_MAP = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".py": "Python",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
    ".toml": "TOML",
    ".xml": "XML",
    ".sql": "SQL",
}

def detect_languages(files_metadata: List[Dict[str, Any]], root_path: str = "") -> Dict[str, int]:
    """Calculates language percentages by aggregating sizes of files matching known extensions.
    Also parses .ipynb Jupyter Notebooks to extract kernel language and code cell sizes."""
    lang_sizes = {}
    total_size = 0

    for file in files_metadata:
        # Only analyze text files for source language breakdown
        if not file["is_text"]:
            continue
        
        ext = file["extension"]
        
        # Special handling for Jupyter Notebooks (.ipynb)
        if ext == ".ipynb" and root_path:
            nb_lang, nb_size = _parse_notebook_language(os.path.join(root_path, file["path"]))
            if nb_lang and nb_size > 0:
                lang_sizes[nb_lang] = lang_sizes.get(nb_lang, 0) + nb_size
                total_size += nb_size
            continue
        
        lang = EXTENSION_MAP.get(ext)
        if lang:
            size = file["size_bytes"]
            lang_sizes[lang] = lang_sizes.get(lang, 0) + size
            total_size += size

    if total_size == 0:
        return {}

    # Calculate rounded percentages
    breakdown = {}
    for lang, size in lang_sizes.items():
        pct = round((size / total_size) * 100)
        if pct > 0:
            breakdown[lang] = pct

    # Sort descending by percentage
    return dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))


def _parse_notebook_language(filepath: str) -> tuple:
    """Parses a Jupyter Notebook (.ipynb) file to extract the kernel language and total code cell character size."""
    try:
        content = _read_file_safe(filepath, max_chars=500000)
        if not content:
            return ("Python", 0)
        nb = json.loads(content)
        
        # Extract language from metadata.kernelspec.language or metadata.language_info.name
        lang = "Python"  # Default for notebooks
        kernelspec = nb.get("metadata", {}).get("kernelspec", {})
        lang_info = nb.get("metadata", {}).get("language_info", {})
        if kernelspec.get("language"):
            lang = kernelspec["language"].capitalize()
        elif lang_info.get("name"):
            lang = lang_info["name"].capitalize()
        
        # Sum all code cell source sizes
        code_size = 0
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                source = cell.get("source", [])
                if isinstance(source, list):
                    code_size += sum(len(line) for line in source)
                elif isinstance(source, str):
                    code_size += len(source)
        
        return (lang, code_size)
    except Exception:
        return ("Python", 0)


def _read_file_safe(file_path: str, max_chars: int = 65536) -> str:
    """Reads file contents safely up to a limit."""
    if not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars)
    except Exception:
        return ""


def detect_technologies(root_path: str, files_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Scans the repository structure and configuration files to extract
    frameworks, package manager, and language distributions.
    """
    frameworks = set()
    package_manager = "unknown"

    # 1. Package.json scan (JavaScript / TypeScript Ecosystem)
    package_json_path = os.path.join(root_path, "package.json")
    if os.path.exists(package_json_path):
        content = _read_file_safe(package_json_path)
        if content:
            try:
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                
                # Check Frameworks
                if "next" in deps:
                    frameworks.add("Next.js")
                if "react" in deps:
                    frameworks.add("React")
                if "vue" in deps:
                    frameworks.add("Vue")
                if "nuxt" in deps:
                    frameworks.add("Nuxt")
                if "@angular/core" in deps:
                    frameworks.add("Angular")
                if "express" in deps:
                    frameworks.add("Express")
                if "@nestjs/core" in deps:
                    frameworks.add("NestJS")
                if "svelte" in deps:
                    frameworks.add("Svelte")
            except Exception:
                pass

        # Package manager lock file checks
        if os.path.exists(os.path.join(root_path, "package-lock.json")):
            package_manager = "npm"
        elif os.path.exists(os.path.join(root_path, "yarn.lock")):
            package_manager = "yarn"
        elif os.path.exists(os.path.join(root_path, "pnpm-lock.yaml")):
            package_manager = "pnpm"
        else:
            package_manager = "npm"  # Default fallback for JS

    # 2. Python Ecosystem scan
    # Check requirements.txt
    req_txt_path = os.path.join(root_path, "requirements.txt")
    if os.path.exists(req_txt_path):
        if package_manager == "unknown":
            package_manager = "pip"
        content = _read_file_safe(req_txt_path).lower()
        if "fastapi" in content:
            frameworks.add("FastAPI")
        if "django" in content:
            frameworks.add("Django")
        if "flask" in content:
            frameworks.add("Flask")

    # Check pyproject.toml
    pyproject_path = os.path.join(root_path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        content = _read_file_safe(pyproject_path).lower()
        if "[tool.poetry]" in content:
            package_manager = "poetry"
        elif package_manager == "unknown":
            package_manager = "pip"
            
        if "fastapi" in content:
            frameworks.add("FastAPI")
        if "django" in content:
            frameworks.add("Django")
        if "flask" in content:
            frameworks.add("Flask")

    # 3. Go Ecosystem scan
    go_mod_path = os.path.join(root_path, "go.mod")
    if os.path.exists(go_mod_path):
        package_manager = "go modules"
        content = _read_file_safe(go_mod_path)
        if "github.com/gin-gonic/gin" in content:
            frameworks.add("Gin")
        if "github.com/labstack/echo" in content:
            frameworks.add("Echo")
        if "github.com/fiber" in content or "github.com/gofiber/fiber" in content:
            frameworks.add("Fiber")

    # 4. Rust Ecosystem scan
    cargo_toml_path = os.path.join(root_path, "Cargo.toml")
    if os.path.exists(cargo_toml_path):
        package_manager = "cargo"
        content = _read_file_safe(cargo_toml_path)
        if "axum" in content:
            frameworks.add("Axum")
        if "actix-web" in content:
            frameworks.add("Actix Web")
        if "rocket" in content:
            frameworks.add("Rocket")

    # 5. Java Ecosystem scan
    pom_xml_path = os.path.join(root_path, "pom.xml")
    if os.path.exists(pom_xml_path):
        package_manager = "maven"
        content = _read_file_safe(pom_xml_path)
        if "spring-boot" in content:
            frameworks.add("Spring Boot")
            
    build_gradle_path = os.path.join(root_path, "build.gradle")
    if os.path.exists(build_gradle_path):
        package_manager = "gradle"
        content = _read_file_safe(build_gradle_path)
        if "spring-boot" in content or "springboot" in content:
            frameworks.add("Spring Boot")

    # 6. Resolve Language Breakdown
    language_breakdown = detect_languages(files_metadata, root_path)

    return {
        "languages": language_breakdown,
        "frameworks": list(frameworks),
        "package_manager": package_manager
    }

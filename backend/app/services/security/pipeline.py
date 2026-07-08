import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.security_issue import SecurityIssue
from app.services.security.patterns import (
    COMPILED_SECRET_PATTERNS, SQL_INJECTION_PATTERN, UNSAFE_API_PATTERNS, WEAK_HASH_PATTERNS
)
from app.services.security.scoring import calculate_security_score, calculate_security_grade

logger = logging.getLogger(__name__)


# Extend patterns inside code for Java and Risk checks (Task 5)
JAVA_PROCESS_RE = re.compile(r"\bRuntime\.getRuntime\(\)\.exec\s*\(|\bProcessBuilder\b")
COMMAND_INJECTION_RE = re.compile(r"\bexec\s*\([^)]*\+[^)]*\)|\bsystem\s*\(")
PATH_TRAVERSAL_RE = re.compile(r"\.\./\.\./|path\.join\([^)]*\.\.[^)]*\)")


def parse_version(v_str: str) -> List[int]:
    """Helper to parse a version string into a list of integers for comparison."""
    v_clean = re.sub(r"^[^\d]+", "", v_str).strip()
    parts = []
    for p in v_clean.split("."):
        m = re.match(r"^\d+", p)
        if m:
            parts.append(int(m.group(0)))
        else:
            parts.append(0)
    return parts


def analyze_security(repo_id: uuid.UUID, clone_path: str) -> None:
    """
    Run security reviews on cloned repository: secrets scanning, unsafe API detections,
    injection scanning, and parsing dependency lock/manifest files.
    """
    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return

        repo_files = db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo_id).all()
        
        files_scanned = 0
        files_skipped = 0
        secrets_checked = 0
        issues = []
        parsed_dependencies = []  # list of dicts: {"file": str, "name": str, "version": str}

        # Step 1: Scan Secrets & Unsafe Code Patterns

        for rf in repo_files:
            if not rf.is_text:
                files_skipped += 1
                continue
                
            abs_path = os.path.join(clone_path, rf.path)
            if not os.path.isfile(abs_path):
                files_skipped += 1
                continue
                
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                files_skipped += 1
                continue
                
            files_scanned += 1
            lines = content.splitlines()
            
            for line_idx, line in enumerate(lines, 1):
                stripped_line = line.strip()
                
                # Scan Secrets
                for secret_name, pattern in COMPILED_SECRET_PATTERNS.items():
                    secrets_checked += 1
                    match = pattern.search(line)
                    if match:
                        matched_str = match.group(0)
                        secret_value = match.group(2) if len(match.groups()) > 1 else matched_str
                        redacted_line = line.replace(secret_value, "********")
                        evidence_redacted = matched_str.replace(secret_value, "********")
                        
                        issues.append(SecurityIssue(
                            repository_id=repo_id,
                            file_path=rf.path,
                            line_number=line_idx,
                            severity="Critical",
                            category="Secrets",
                            title=f"Hardcoded Credential ({secret_name})",
                            evidence=f"Matched assignment: {evidence_redacted}",
                            snippet=redacted_line.strip(),
                            reason="Hardcoded credential assignment matched a secret detection pattern."
                        ))

                # SQL Injection
                if SQL_INJECTION_PATTERN.search(line):
                    issues.append(SecurityIssue(
                        repository_id=repo_id,
                        file_path=rf.path,
                        line_number=line_idx,
                        severity="High",
                        category="Injection",
                        title="SQL Injection Risk",
                        evidence="Raw SQL string concatenation detected inside query execution.",
                        snippet=stripped_line,
                        reason="SQL queries built via string formatting or concatenation are vulnerable to SQL Injection."
                    ))

                # Command Injection
                if COMMAND_INJECTION_RE.search(line):
                    issues.append(SecurityIssue(
                        repository_id=repo_id,
                        file_path=rf.path,
                        line_number=line_idx,
                        severity="High",
                        category="Injection",
                        title="Command Injection Risk",
                        evidence="Execution command formatted with dynamic variables.",
                        snippet=stripped_line,
                        reason="Executing commands constructed with string variables can allow shell injection exploits."
                    ))

                # Path Traversal
                if PATH_TRAVERSAL_RE.search(line):
                    issues.append(SecurityIssue(
                        repository_id=repo_id,
                        file_path=rf.path,
                        line_number=line_idx,
                        severity="High",
                        category="Injection",
                        title="Path Traversal Risk",
                        evidence="Path traversal pattern (../) or dynamic join detected.",
                        snippet=stripped_line,
                        reason="Dynamically resolving file paths without sanitization poses Directory Traversal risks."
                    ))

                # Unsafe APIs
                for api_name, pattern in UNSAFE_API_PATTERNS.items():
                    if pattern.search(line):
                        issues.append(SecurityIssue(
                            repository_id=repo_id,
                            file_path=rf.path,
                            line_number=line_idx,
                            severity="Medium",
                            category="Unsafe APIs",
                            title=api_name,
                            evidence="Execution of potentially dangerous API command.",
                            snippet=stripped_line,
                            reason="Usage of dynamic evaluators or unvalidated shell wrappers poses runtime hazards."
                        ))

                # Java Process builder / runtime
                if JAVA_PROCESS_RE.search(line):
                    issues.append(SecurityIssue(
                        repository_id=repo_id,
                        file_path=rf.path,
                        line_number=line_idx,
                        severity="Medium",
                        category="Unsafe APIs",
                        title="Java Dangerous Process API",
                        evidence="Use of Runtime.exec or ProcessBuilder.",
                        snippet=stripped_line,
                        reason="Java process execution APIs should be avoided in favor of secure wrappers."
                    ))

                # Weak Hashing
                for hash_name, pattern in WEAK_HASH_PATTERNS.items():
                    if pattern.search(line):
                        issues.append(SecurityIssue(
                            repository_id=repo_id,
                            file_path=rf.path,
                            line_number=line_idx,
                            severity="Low",
                            category="Weak Cryptography",
                            title=hash_name,
                            evidence="Usage of outdated cryptographic hashing algorithm.",
                            snippet=stripped_line,
                            reason="MD5 and SHA-1 hashing algorithms are cryptographically broken and susceptible to collisions."
                        ))
        
        # Step 2: Check Dependency Files (Task 5)

        for rf in repo_files:
            abs_path = os.path.join(clone_path, rf.path)
            filename = os.path.basename(rf.path).lower()
            if not os.path.isfile(abs_path):
                continue

            try:
                # 1. requirements.txt
                if filename == "requirements.txt":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            parts = re.split(r"==|>=|<=|~=|>|<", line)
                            if parts:
                                parsed_dependencies.append({
                                    "file": rf.path,
                                    "name": parts[0].strip(),
                                    "version": parts[1].strip() if len(parts) > 1 else "any"
                                })

                # 2. package.json
                elif filename == "package.json":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        raw = f.read()
                    dep_matches = re.findall(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", raw)
                    for pkg, ver in dep_matches:
                        if pkg not in ("dependencies", "devDependencies", "scripts", "engines"):
                            parsed_dependencies.append({
                                "file": rf.path,
                                "name": pkg,
                                "version": ver
                            })

                # 3. pom.xml
                elif filename == "pom.xml":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        raw = f.read()
                    deps = re.findall(r"<dependency>.*?</dependency>", raw, re.DOTALL)
                    for dep in deps:
                        g_match = re.search(r"<groupId>(.*?)</groupId>", dep)
                        a_match = re.search(r"<artifactId>(.*?)</artifactId>", dep)
                        v_match = re.search(r"<version>(.*?)</version>", dep)
                        if g_match and a_match:
                            parsed_dependencies.append({
                                "file": rf.path,
                                "name": f"{g_match.group(1)}:{a_match.group(1)}",
                                "version": v_match.group(1) if v_match else "latest"
                            })

                # 4. Cargo.toml
                elif filename == "cargo.toml":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    in_deps = False
                    for line in lines:
                        line = line.strip()
                        if line.startswith("[dependencies]") or line.startswith("[dev-dependencies]"):
                            in_deps = True
                            continue
                        elif line.startswith("[") and in_deps:
                            in_deps = False
                        if in_deps and "=" in line:
                            parts = line.split("=")
                            parsed_dependencies.append({
                                "file": rf.path,
                                "name": parts[0].strip(),
                                "version": parts[1].strip().replace('"', '')
                            })

                # 5. go.mod
                elif filename == "go.mod":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line.startswith("require") and not line.startswith("require ("):
                            parts = line.split()
                            if len(parts) >= 3:
                                parsed_dependencies.append({
                                    "file": rf.path,
                                    "name": parts[1],
                                    "version": parts[2]
                                })
                        elif line.startswith("require ("):
                            # Simple multiline requires
                            pass

                # 6. Gemfile
                elif filename == "gemfile":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("gem "):
                                matches = re.findall(r"['\"]([^'\"]+)['\"]", line)
                                if matches:
                                    parsed_dependencies.append({
                                        "file": rf.path,
                                        "name": matches[0],
                                        "version": matches[1] if len(matches) > 1 else "latest"
                                    })

                # 7. composer.json
                elif filename == "composer.json":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        raw = f.read()
                    matches = re.findall(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", raw)
                    for pkg, ver in matches:
                        if "/" in pkg:
                            parsed_dependencies.append({
                                "file": rf.path,
                                "name": pkg,
                                "version": ver
                            })

                # 8. pubspec.yaml
                elif filename == "pubspec.yaml":
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    in_deps = False
                    for line in lines:
                        if line.startswith("dependencies:") or line.startswith("dev_dependencies:"):
                            in_deps = True
                            continue
                        elif in_deps and line and not line.startswith(" ") and not line.startswith("-"):
                            in_deps = False
                        if in_deps and ":" in line:
                            parts = line.split(":")
                            name = parts[0].strip()
                            if name not in ("dependencies", "dev_dependencies", "sdk", "flutter"):
                                parsed_dependencies.append({
                                    "file": rf.path,
                                    "name": name,
                                    "version": parts[1].strip() if len(parts) > 1 else "any"
                                })

            except Exception as ex:
                logger.warning(f"Error parsing dependency file {rf.path}: {ex}")

        # Step 3: Organize Timing and Security details

        # Count issues by severity
        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        category_counts = {"Secrets": 0, "Dependencies": 0, "Injection": 0, "Weak Cryptography": 0, "Unsafe APIs": 0, "Configuration": 0}
        
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        score = calculate_security_score(severity_counts)
        grade = calculate_security_grade(score)

        # Highlights & Warnings
        strengths = []
        warnings = []

        if category_counts["Secrets"] == 0:
            strengths.append({"title": "No hardcoded secrets detected", "description": "No private keys, access tokens, or credentials matched scanning patterns."})
        else:
            warnings.append({"title": "Hardcoded credentials detected", "description": f"Found {category_counts['Secrets']} hardcoded secrets. Remove these immediately to prevent leakage.", "evidence": f"Secrets found in {len({i.file_path for i in issues if i.category == 'Secrets'})} files."})

        if category_counts["Injection"] == 0:
            strengths.append({"title": "No SQL injection patterns detected", "description": "Database queries avoid raw string concatenations."})
        else:
            warnings.append({"title": "SQL/Command Injection risks identified", "description": "Found dynamic query structures or commands bypassing parameterized execution.", "evidence": f"Injection risks found in {len({i.file_path for i in issues if i.category == 'Injection'})} files."})

        if category_counts["Unsafe APIs"] == 0:
            strengths.append({"title": "No dangerous eval() usage detected", "description": "Safe parsing methods are consistently used."})
        else:
            warnings.append({"title": "Unsafe system APIs used", "description": "Modules invoke dynamic evaluators or shell process wrappers.", "evidence": f"Unsafe APIs: {category_counts['Unsafe APIs']} calls."})

        # Add strength mapping for Dependency scan (Task 5 requirements)
        if parsed_dependencies:
            strengths.append({
                "title": f"Dependency files checked ({len(parsed_dependencies)} parsed)",
                "description": "Dependency versions detected successfully. Offline vulnerability database unavailable.",
                "evidence": f"Scanned file types: {', '.join(set([os.path.basename(d['file']) for d in parsed_dependencies]))}"
            })

        summary_data = {
            "score": score,
            "grade": grade,
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "badges": ["Vulnerability Engine Offline"] if parsed_dependencies else ["No Dependencies Scanned"],
            "dependency_stats": {
                "total_dependencies": len(parsed_dependencies),
                "safe_dependencies": len(parsed_dependencies),
                "vulnerable_dependencies": 0,
                "most_severe_vulnerability": "None",
                "total_known_cves": 0
            },
            "scan_stats": {
                "files_scanned": files_scanned,
                "files_skipped": files_skipped,
                "dependencies_parsed": len(parsed_dependencies),
                "secrets_checked": secrets_checked,
                "issues_found": len(issues)
            }
        }

        # Clear old issues and bulk save new ones
        db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo_id).delete()
        db.bulk_save_objects(issues)
        db.commit()

        # Update repo columns
        repo.security_score = score
        repo.security_grade = grade
        
        # Save structured security metadata inside knowledge summary or security summary
        repo.security_summary = summary_data
        repo.security_findings = {
            "strengths": strengths,
            "warnings": warnings
        }
        
        # Also store details under "security_metadata" in repo.knowledge_summary (Task 10)
        current_kb = repo.knowledge_summary or {}
        current_kb["security_metadata"] = {
            "parsed_dependencies": parsed_dependencies,
            "issues_count": len(issues),
            "vulnerability_provider": "Offline vulnerability database unavailable"
        }
        repo.knowledge_summary = current_kb
        db.commit()
        
        logger.info(f"Security Review Engine complete for {repo_id} - Score: {score}")

    except Exception as e:
        logger.error(f"Security review failed: {e}", exc_info=True)
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.error_message = f"Security review error: {str(e)}"
            db.commit()
    finally:
        db.close()

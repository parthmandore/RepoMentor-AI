import re

# 1. Credentials and Secrets
SECRET_PATTERNS = {
    "AWS API Key": r"AKIA[0-9A-Z]{16}",
    "Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
    "GitHub Personal Access Token": r"ghp_[a-zA-Z0-9]{36}",
    "Slack Webhook URL": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
    "Generic Hardcoded Secret": r"(?i)(api_key|secret|password|db_pass|access_token|private_key)\s*=\s*['\"]([^'\"]{8,})['\"]"
}

# Compile patterns for quick lookup
COMPILED_SECRET_PATTERNS = {name: re.compile(pat) for name, pat in SECRET_PATTERNS.items()}

# 2. OWASP Code Injection (SQL injection patterns)
# Matching raw concatenations in SQL query builders
SQL_INJECTION_PATTERN = re.compile(
    r"\.(execute|raw|query)\(\s*(?:f['\"]|['\"].*?%(?:\(.*?\))?[sdb]|['\"].*?\bformat\b|.*?\.format\(|.*?\+.*?\b(?:select|insert|update|delete|where)\b)",
    re.IGNORECASE
)

# 3. Unsafe APIs (eval, exec, Popen with shell=True)
UNSAFE_API_PATTERNS = {
    "Unsafe Eval": re.compile(r"\beval\s*\("),
    "Unsafe Exec": re.compile(r"\bexec\s*\("),
    "Dangerous Process Execution": re.compile(r"\bsubprocess\.(?:Popen|run|call)\(.*?\bshell\s*=\s*True", re.IGNORECASE)
}

# 4. Weak Hashing (MD5/SHA1 without safety context)
WEAK_HASH_PATTERNS = {
    "Weak Hashing (MD5)": re.compile(r"(?:hashlib\.md5|createHash\(['\"]md5['\"]\))"),
    "Weak Hashing (SHA-1)": re.compile(r"(?:hashlib\.sha1|createHash\(['\"]sha1['\"]\))")
}

# Centralized threshold configuration for deterministic code analysis.
# Each constant has documented reasoning for its chosen value.

# Maximum lines in a single function before flagging as "Long Method".
LONG_METHOD_LOC = 30

# Maximum methods in a class before flagging as "God Class".
GOD_CLASS_METHODS = 10

# Maximum LOC in a class before flagging as "God Class".
GOD_CLASS_LOC = 200

# Maximum LOC in a single file before flagging as "Large File".
LARGE_FILE_LOC = 300

# Maximum control-flow nesting depth before flagging as "Deep Nesting".
DEEP_NESTING_LEVEL = 4

# Numeric literals that are NOT flagged as magic numbers.
MAGIC_NUMBER_EXCEPTIONS = {0, 1, -1, 2, 10, 100}

# Minimum consecutive lines to consider as a duplicate block.
DUPLICATION_BLOCK_SIZE = 6

# Supported file extensions for full analysis.
# Dynamically resolved from the registered analyzers to maintain backward compatibility.
from app.services.analysis.analyzers.registry import AnalyzerRegistry
ANALYZABLE_EXTENSIONS = AnalyzerRegistry.supported_extensions()

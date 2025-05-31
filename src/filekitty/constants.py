from pathlib import Path

# ------------ icons ------------ #
ICON_PATH = str((Path(__file__).parent / "resources/icon/FileKitty-icon.png").resolve())

# ------------ history ------------ #
HISTORY_DIR_NAME = "FileKittyHistory"
STALE_CHECK_INTERVAL_MS = 2500  # Check every 2.5 seconds
HASH_ERROR_SENTINEL = "HASH_ERROR"
HASH_MISSING_SENTINEL = "FILE_MISSING"

# ------------ QSettings keys ------------ #
SETTINGS_DEFAULT_PATH_KEY = "defaultPath"
SETTINGS_HISTORY_PATH_KEY = "historyPath"

SETTINGS_TREE_ENABLED_KEY = "treeEnabled"
SETTINGS_TREE_BASE_KEY = "treeBaseDir"
SETTINGS_TREE_IGNORE_KEY = "treeIgnoreRegex"
SETTINGS_TREE_DEF_BASE_KEY = "treeDefaultBaseDir"
SETTINGS_TREE_DEF_IGNORE_KEY = "treeDefaultIgnoreList"

# ------------ tree defaults ------------ #
TREE_IGNORE_DEFAULT = (
    "__pycache__|.git|.DS_Store|.idea|.ruff_cache|.venv|.pytest_cache|tmp|run_history|"
    "artifacts|__init__.py|.pre-commit-config.yaml|.env|.env.sample|.envrc|CLAUDE.md"
)

TEXT_CHECK_CHUNK_SIZE = 1024

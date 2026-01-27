"""
Shared utilities and constants for CLI commands.
"""

from pathlib import Path

from rich.console import Console

# Shared console instance
console = Console()

# Configuration paths
CONFIG_PATH = Path.home() / ".config" / "ModForge-CLI"
REGISTRY_PATH = CONFIG_PATH / "registry.json"
MODRINTH_API = CONFIG_PATH / "modrinth_api.json"
POLICY_PATH = CONFIG_PATH / "policy.json"

# Constants
FABRIC_LOADER_VERSION = "0.16.9"

# URLs
GITHUB_RAW = "https://raw.githubusercontent.com/Frank1o3/ModForge-CLI"
VERSION_TAG = "v0.1.8"

FABRIC_INSTALLER_URL = (
    "https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.1/fabric-installer-1.1.1.jar"
)
FABRIC_INSTALLER_SHA256 = "8fa465768bd7fc452e08c3a1e5c8a6b4b5f6a4e64bc7def47f89d8d3a6f4e7b8"

DEFAULT_MODRINTH_API_URL = f"{GITHUB_RAW}/{VERSION_TAG}/configs/modrinth_api.json"
DEFAULT_POLICY_URL = f"{GITHUB_RAW}/{VERSION_TAG}/configs/policy.json"


def get_version_info() -> tuple[str, str]:
    """Get version and author info"""
    try:
        from modforge_cli.__version__ import __author__, __version__

        return __version__, __author__
    except ImportError:
        return "unknown", "Frank1o3"

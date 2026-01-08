"""
__init__.py - Entry point for the SmithPy CLI
"""

import sys
from pathlib import Path

import rich


script_path = Path(__file__).parent / "src"
sys.path.append(str(script_path / "api"))
sys.path.append(str(script_path / "core"))


def main() -> None:
    pass


if __name__ == "__main__":
    main()

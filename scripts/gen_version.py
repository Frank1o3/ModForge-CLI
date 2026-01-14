from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
OUT = ROOT / "src/ModForge-Cli/__version__.py"


def main() -> None:
    data = tomllib.loads(PYPROJECT.read_text())
    version = data["project"]["version"]

    OUT.write_text(
        f'''"""
Auto-generated file. DO NOT EDIT.
"""
__version__ = "{version}"
__author__ = "Frank1o3"
'''
    )

    print(f"Generated {OUT.relative_to(ROOT)} ({version})")


if __name__ == "__main__":
    main()

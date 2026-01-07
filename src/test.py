"""
__main__.py - Entry point for the SmithPy CLI
"""

import sys
from pathlib import Path

from styles.banner import print_banner
from styles.console import input_text, input_choice
from core import run

def get_project_root(start: Path) -> Path:
    for parent in start.resolve().parents:
        if parent.name == "src":
            return parent.parent
    raise RuntimeError("Could not locate project root (missing src directory)")

script_path = get_project_root(Path(__file__))
sys.path.append(str(script_path / "api"))
sys.path.append(str(script_path / "core"))

def main() -> None:
    print_banner()  # Show the beautiful banner on startup
    print()
    mods: list[str] = []
    # shaders: list[str] = []
    name = input_text(
        "Enter a modpack name", default="MyModPack", placeholder="e.g., SurvivalPlus"
    )
    loader = input_choice(
        "Select mod loader", ["fabric", "forge", "quilt", "neoforge"], default="fabric"
    )
    version = input_text(
        "What Minecraft version", default="1.21.10", placeholder="e.g., 1.21.10"
    )
    # shader = input_choice(
    #     "Select a shader loader", ["canvas", "iris", "optifine"], default="iris"
    # )

    while True:
        mod = input_text(
            "Enter a mod name (or 'done' to finish)",
            default="sodium",
            placeholder="e.g., sodium",
        )
        if mod.lower() == "done":
            break
        mods.append(mod)

    # while True:
    #     shader_name = input_text(
    #         "Enter a shader name (or 'done' to finish)",
    #         default="Solas Shader",
    #         placeholder="e.g., Solas Shader",
    #     )
    #     if shader_name.lower() == "done":
    #         break
    #     shaders.append(shader_name)

    run(name, loader, version, mods)  # ,shaders)


if __name__ == "__main__":
    main()

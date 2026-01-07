"""
__main__.py - Entry point for the SmithPy CLI
"""

from pathlib import Path

from pprint import pprint
from requests import get

from styles.banner import print_banner
from styles.console import input_text, input_choice
from api import ModrinthAPIConfig

config_path = Path(__file__).parent / "configs" / "modrinth_api.json"

api = ModrinthAPIConfig()


def main() -> None:
    print_banner()  # Show the beautiful banner on startup
    print()
    mods: list[str] = []
    shaders: list[str] = []
    resource_packs: list[str] = []
    name = input_text(
        "Enter a modpack name", default="MyModPack", placeholder="e.g., SurvivalPlus"
    )
    loader = input_choice(
        "Select mod loader", ["fabric", "forge", "quilt", "neoforge"], default="fabric"
    )
    version = input_text(
        "What Minecraft version", default="1.21.10", placeholder="e.g., 1.21.10"
    )
    shader = input_choice(
        "Select a shader loader", ["canvas", "iris", "optifine"], default="iris"
    )

    while True:
        mod = input_text(
            "Enter a mod name (or 'done' to finish)",
            default="sodium",
            placeholder="e.g., sodium",
        )
        if mod.lower() == "done":
            break
        mods.append(mod)

    while True:
        shader_name = input_text(
            "Enter a shader name (or 'done' to finish)",
            default="Solas Shader",
            placeholder="e.g., Solas Shader",
        )
        if shader_name.lower() == "done":
            break
        shaders.append(shader_name)

    while True:
        resource_pack = input_text(
            "Enter a resource pack name (or 'done' to finish)",
            default="faithful",
            placeholder="e.g., faithful",
        )
        if resource_pack.lower() == "done":
            break
        resource_packs.append(resource_pack)

    print(name)
    print(version)
    print(loader)
    print(shader)
    pprint(mods)
    pprint(shaders)
    pprint(resource_packs)

    for mod_name in mods:
        temp_url = api.search(
            mod_name, game_versions=[version], loaders=[loader], project_type="mod"
        )
        res = get(temp_url)
        if res.status_code == 200:
            json = res.json()
            pprint(json)

    for shader_name in shader:
        temp_url = api.search(
            shader_name,
            game_versions=[version],
            loaders=[shader],
            project_type="shaders",
        )
        res = get(temp_url)
        if res.status_code == 200:
            json = res.json()
            pprint(json)

    for resource_pack in resource_packs:
        temp_url = api.search(
            resource_pack,
            game_versions=[version],
            loaders=[shader],
            project_type="resourcepacks",
        )
        res = get(temp_url)
        if res.status_code == 200:
            json = res.json()
            pprint(json)


if __name__ == "__main__":
    main()

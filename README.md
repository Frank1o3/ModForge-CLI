# ModForge-CLI ⛏

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Modrinth API v2](https://img.shields.io/badge/Modrinth-API%20v2-orange)](https://docs.modrinth.com/api-spec)

**ModForge-CLI** is a powerful CLI tool for building and managing custom Minecraft modpacks using the Modrinth API v2.

Search for projects, fetch versions, validate manifests, download mods with hash checks, and generate complete files — all from the terminal.

Ideal for modpack developers, server admins, and automation scripts.

## Terminal Banner

When you run ModForge-CLI, you'll be greeted with this colorful Minecraft-themed banner

## Key Features

- **Modrinth API v2 Integration**: Search projects, list versions, fetch metadata in bulk.
- **Modpack Management**: Read/validate `modrinth.index.json`, build packs from metadata.
- **Validation**: Full JSON Schema checks + optional Pydantic models for strict typing.

## Installation

Requires **Python 3.13+**.

**Recommended (Poetry)**:

```bash
poetry add modforge-cli
```

**Alternative (pip)**:

```bash
pip install modforge-cli
```

## Example

```bash
modforge-cli setup --loader-version 0.18.4 TestPack
cd TestPack
modforge-cli add sodium
modforge-cli add "Fabric API"
modforge-cli add "Cloth Config"
modforge-cli add "ferriteCore"
modforge-cli add "Entity Culling"
modforge-cli add "Mod Menu"
modforge-cli add "Lithium"
modforge-cli add "ImmediatelyFast"
modforge-cli add "yacl"
modforge-cli add "Xaero's minimap"
modforge-cli add "Fabric Language Kotlin"
modforge-cli add "JEI"
modforge-cli add "3D Skin Layers"
modforge-cli add "More Culling"
modforge-cli add "Zoomify"
modforge-cli add "Mouse Tweaks"
modforge-cli add "Sound Physics Remastered"
modforge-cli add "LambDynamicLights"
modforge-cli add "Krypton"
modforge-cli add "AmbientSounds"
modforge-cli add "BadOptimizations"
modforge-cli add "Debugify"
modforge-cli add "Veinminer Enchantment"
modforge-cli add "Packet Fixer"
modforge-cli add "CustomSkinLoader"
modforge-cli add "Cubes Without Borders"
modforge-cli add "Particle Rain"
modforge-cli add "Chunky"
modforge-cli add "Fusion (Connected Textures)"
modforge-cli add "Do a Barrel Roll"
modforge-cli add "Resourcify"
modforge-cli add "Particle Core"
modforge-cli add "Drip Sounds"
modforge-cli add "ScalableLux"
modforge-cli add "Cull Leaves"
modforge-cli add "rrls"
modforge-cli add "ModernFix-mVUS"
modforge-cli add "NoisiumForked"
modforge-cli add "KryptonFNP Patcher"
modforge-cli add "Podium"
modforge-cli add "Iris"
modforge-cli add "first-person-model"
modforge-cli add "Helium"
modforge-cli resolve
modforge-cli build
modforge-cli export
```

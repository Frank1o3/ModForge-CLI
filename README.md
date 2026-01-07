# SmithPy ⛏

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Modrinth API v2](https://img.shields.io/badge/Modrinth-API%20v2-orange)](https://docs.modrinth.com/api-spec)

**SmithPy** is a powerful CLI tool for building and managing custom Minecraft modpacks using the Modrinth API v2.

Search for projects, fetch versions, validate manifests, download mods with hash checks, and generate complete files — all from the terminal.

Ideal for modpack developers, server admins, and automation scripts.

## Terminal Banner

When you run SmithPy, you'll be greeted with this colorful Minecraft-themed banner

## Key Features

- **Modrinth API v2 Integration**: Search projects, list versions, fetch metadata in bulk.
- **Modpack Management**: Read/validate `modrinth.index.json`, build packs from metadata.
- **Secure Downloads**: Async (httpx) with hash verification, retries, and rich progress bars.
- **Validation**: Full JSON Schema checks + optional Pydantic models for strict typing.
- **Developer-Friendly**: Fully typed, modular code with Black/Ruff/Mypy config.

## Installation

Requires **Python 3.13+**.

**Recommended (Poetry)**:

```bash
poetry install
```

**Alternative (pip)**:

```bash
pip install -r requirements.txt
```

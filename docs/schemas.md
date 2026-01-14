---
layout: default
title: Schemas
parent: Home
nav_order: 2
---

# Schemas

ModForge-Cli is built around **schema‑driven configuration**. These schemas define how the CLI interprets policies, resolves dependencies, and interacts with external APIs.

---

## 📜 Policy Schema

**File:** `policy.schema.yml`

Defines:

* Mod inclusion rules
* Conflict resolution
* Sub‑mod expansion
* Conditional dependencies

This schema ensures that modpacks are **predictable, reproducible, and self‑documenting**.

➡️ [View Policy Schema](./schemas/policy.schema.json)

---

## 🔌 Modrinth API Schema

**File:** `modrinth_api.schema.yml`

Defines:

* Supported Modrinth API endpoints
* Request and response shapes
* Version and loader mappings

This allows ModForge-Cli to validate API interactions at runtime and during development.

➡️ [View Modrinth API Schema](./schemas/modrinth_api.schema.json)

---

## 🛠 Why Schemas Matter

Schemas provide:

* Early error detection
* Strong validation guarantees
* IDE auto‑completion
* Long‑term stability

They are a core design principle of ModForge-Cli.

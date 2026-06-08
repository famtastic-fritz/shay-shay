---
id: example-hermes-skill
name: Example Hermes Skill
version: 1.0.0
description: A sample skill in Hermes format for testing YAML frontmatter parsing
permissions:
  - read:files
  - write:memory
tags:
  - test
  - example
entrypoint: dist/index.js
---

# Hermes Skill Format

This is a markdown skill descriptor using YAML frontmatter. The frontmatter block
above contains all the metadata that gets parsed and normalized into a CapabilityManifest.

## Features

- YAML frontmatter with id, name, version, description
- Permissions array for declaring requirements
- Tags for categorization
- Entrypoint path for module resolution

This format is used by the HermesSkillAdapter for round-trip testing.

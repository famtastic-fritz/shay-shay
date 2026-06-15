---
name: github-to-obsidian
description: Autonomously extracts GitHub repositories or documentation and ingests them into the Obsidian vault for permanent research memory.
version: 1.0.0
category: research
---

# GitHub to Obsidian Ingestion

This skill equips you to automatically pull research, code documentation, and architectures from GitHub directly into the user's Obsidian Vault (`~/famtastic/obsidian/03-Research/`).

## When to Use
Trigger this skill whenever you are tasked with:
- "Polling" or "researching" a GitHub repository.
- Gathering data or documentation from a GitHub link provided by the user.
- Analyzing a new codebase where keeping persistent documentation in the Obsidian vault is beneficial.

## Execution Steps

1. **Identify the Target**: Ensure you have a valid GitHub URL (either a repository root like `https://github.com/owner/repo` or a specific file like `https://github.com/owner/repo/blob/main/ARCHITECTURE.md`).
2. **Determine Relevance**: Proactively identify high-value files. If the user just gives you a repo URL, grabbing the README is the best default. If there are specific architecture or setup docs mentioned, target those URLs specifically.
3. **Run the Ingestion Tool**:
   Execute the ingestion Python script via the terminal using your `run_command` tool.
   ```bash
   python3 ~/famtastic/shay-shay/tools/github_obsidian_ingest.py "https://github.com/owner/repo"
   ```
4. **Confirm Success**: Ensure the script outputs `✅ Successfully ingested to...`. The file will automatically receive Obsidian YAML frontmatter and be permanently stored in `~/famtastic/obsidian/03-Research/`.
5. **Report to User**: Inform the user that the GitHub data has been successfully parsed into structured Markdown and permanently ingested into their Obsidian vault for future reference.

## Pitfalls to Avoid
- Do not attempt to use `curl` or `wget` to manually scrape GitHub HTML pages—they will be filled with raw DOM noise. ALWAYS use the `github_obsidian_ingest.py` tool which securely hits the raw API.
- If a repo requires authentication (private repo), the tool might fail. Advise the user if you encounter an error pulling from private endpoints.

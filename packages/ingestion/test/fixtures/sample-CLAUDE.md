# Sample Claude Skill

A simple skill descriptor in Claude format without YAML frontmatter. This tests the fallback
parsing path that extracts metadata from markdown headings and content instead of structured
YAML.

## Description

This is the Claude-format skill descriptor. It relies on markdown heading parsing to extract
the skill name from the H1 and description from the following paragraph. No YAML frontmatter
is present, testing the adapter's ability to handle legacy or simpler formats.

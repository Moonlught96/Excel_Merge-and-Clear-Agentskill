# Bazhuayu Skill Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repackage the existing Bazhuayu Excel cleaning workflow as a complete, portable Agent Skill without changing any established merge, standardization, or cleaning behavior.

**Architecture:** Keep the project-root tools and configuration as the development source, and publish byte-identical copies inside the Skill so the Skill directory can run independently after being copied elsewhere. Keep `SKILL.md` as a concise entrypoint, move detailed policies into focused reference documents, and enforce portability and documentation completeness with automated tests.

**Tech Stack:** Markdown, YAML, Python 3, `unittest`, `openpyxl`.

---

### Task 1: Define the portable Skill contract

**Files:**
- Modify: `tests/test_workflow_docs.py`

- [ ] Add a failing structure test requiring `SKILL.md`, `agents/openai.yaml`, `references/`, `scripts/`, `config/`, and `assets/`.
- [ ] Add failing checks that `SKILL.md` contains responsibilities, triggers, execution steps, output standards, and links to every reference document.
- [ ] Add failing checks that confirmed workflow, header, cleaning, naming, retention, and extension rules remain present across the reference set.
- [ ] Run `python -m unittest tests.test_workflow_docs` and confirm it fails because the new structure does not exist.

### Task 2: Create the standardized Skill documentation

**Files:**
- Modify: `skills/bazhuayu-excel-cleaning/SKILL.md`
- Create: `skills/bazhuayu-excel-cleaning/agents/openai.yaml`
- Create: `skills/bazhuayu-excel-cleaning/references/workflow.md`
- Create: `skills/bazhuayu-excel-cleaning/references/data-contract.md`
- Create: `skills/bazhuayu-excel-cleaning/references/header-standardization.md`
- Create: `skills/bazhuayu-excel-cleaning/references/cleaning-rules.md`
- Create: `skills/bazhuayu-excel-cleaning/references/naming-and-retention.md`
- Create: `skills/bazhuayu-excel-cleaning/references/tool-reference.md`
- Create: `skills/bazhuayu-excel-cleaning/references/extension-policy.md`

- [ ] Replace the oversized entrypoint with a concise progressive-disclosure document.
- [ ] Move every confirmed rule into exactly one focused reference document and preserve all deterministic/no-AI constraints.
- [ ] Add Agent metadata with a clear display name, description, default prompt, and implicit invocation policy.
- [ ] Re-run the documentation tests and fix only missing packaging/documentation behavior.

### Task 3: Bundle automation and reusable assets

**Files:**
- Create: `skills/bazhuayu-excel-cleaning/scripts/*.py`
- Create: `skills/bazhuayu-excel-cleaning/config/*.json`
- Create: `skills/bazhuayu-excel-cleaning/assets/workflow-confirmation-template.md`
- Create: `skills/bazhuayu-excel-cleaning/assets/rule-extension-template.md`
- Create: `tools/sync_skill_bundle.py`

- [ ] Add a failing test that bundled scripts and configuration are byte-identical to the project development source.
- [ ] Add a deterministic sync tool with an explicit allowlist of files.
- [ ] Run the sync tool to publish the scripts and configuration into the Skill.
- [ ] Add reusable workflow and rule-extension templates under `assets/`.
- [ ] Verify the consistency test passes.

### Task 4: Enforce the standard for future Skills

**Files:**
- Modify: `AGENTS.md`
- Modify: `tests/test_workflow_docs.py`

- [ ] Add a failing test for the project-level Agent Skill Packaging Standard.
- [ ] Add the mandatory folder, `SKILL.md`, references, scripts, assets, portability, and validation rules to `AGENTS.md`.
- [ ] Verify the project instructions test passes.

### Task 5: Prove standalone operation

**Files:**
- Modify: `tests/test_workflow_docs.py`

- [ ] Add an isolated test that copies only `skills/bazhuayu-excel-cleaning` into a temporary directory.
- [ ] Generate a representative workbook, run the copied standardization and cleaning scripts, and verify the expected `.xlsx` and `.csv` outputs.
- [ ] Run `python -m unittest discover -s tests` and require a clean pass.
- [ ] Run `python -m compileall tools skills/bazhuayu-excel-cleaning/scripts tests`.
- [ ] Review `git diff --check` and repository status before committing.

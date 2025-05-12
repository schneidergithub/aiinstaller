# 📘 Repository Purpose and Instructions for LLM

## 🚩 Purpose

This repository is designed to facilitate automated synchronization and integration between GitHub and Jira using Project Management as Code (PMaC). It provides a structured, JSON-based single source of truth for project management artifacts such as stories, epics, sprints, and scrum boards.

The goal is to leverage Large Language Models (LLMs) like ChatGPT to analyze, validate, generate, and synchronize Agile project data efficiently.

## 🗂️ Repository Structure

### 📂 `data/`

* Contains structured JSON files:

  * **`project_plan.json`**: Main comprehensive project definition.
  * **`stories.json`**: Individual user stories.
  * **`epics.json`**: High-level thematic groupings.
  * **`sprints.json`**: Time-bound iteration details.
  * **`scrum_board.json`**: Scrum methodology visual setup.
  * **`views.json`**: Visualization support data.
  * **`project_meta.json`**: Metadata about the project setup.

### 📂 `prompts/`

Optimized markdown prompts for AI tools, organized into clear categories:

* **Analysis**: Extract metrics, summarize repo capabilities.
* **Implementation**: Guide the creation of synchronization tools, CLI interfaces, and dashboards.
* **Validation**: Ensure data consistency, schema correctness, and robust testing.

### 📂 `docs/`

Templates and structured reports aiding consistent documentation and clarity.

### ⚙️ Scripts

* **`init_github_board.sh`**: Script for automating GitHub board setup and synchronization.

## 🤖 Intended Use with LLMs

* Use the provided prompts from the `prompts/` directory as structured instructions for AI models.
* Each prompt is optimized to clearly communicate tasks to LLMs for precise, consistent results.

## 🛠️ Workflow for AI-Assisted Development

1. Select relevant prompt(s) from the `prompts/` directory.
2. Provide prompt(s) along with corresponding JSON data files to the LLM.
3. Implement and refine LLM-generated outputs for synchronization, validation, or enhancement.
4. Maintain iterative development by version-controlling important outputs in this repository.

## ✅ Expected Outcomes

* Accurate and efficient synchronization between Jira and GitHub.
* Reduced manual workload for project managers and developers.
* Enhanced project visibility, consistency, and agility through automated processes and AI-driven insights.

---

Use this README to clearly understand the repository's goals and leverage LLMs effectively for automation and project management excellence.

#!/bin/bash

# GitHub Classic Project Setup Script (Stable CLI Support)
# Supports: project creation, issue linking, field setup, and label management
set -e

# Load environment variables from .env file
if [[ -f .env ]]; then
  echo "🔍 Loading environment variables from .env file..."
  source .env
else
  echo "⚠️ .env file not found. Using default values."
fi

# Default values
REPO="${REPO:-schneidergithub/pmac-github-scrum-starter}"
PROJECT_NAME="${PROJECT_NAME:-Scrum Board}"
USER="${USER:-schneidergithub}"
INIT_REPO="${INIT_REPO:-false}"

# Argument parsing
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      USER="${REPO%%/*}"
      shift 2
      ;;
    --project)
      PROJECT_NAME="$2"
      shift 2
      ;;
    --init-repo)
      INIT_REPO=true
      shift
      ;;
    *)
      echo "❌ Unknown argument: $1"
      echo "Usage: $0 [--repo user/repo] [--project 'Project Name'] [--init-repo]"
      exit 1
      ;;
  esac
done

if $INIT_REPO; then
  echo "📦 Initializing local repo and pushing to GitHub..."
  git init
  git add .
  git commit -m "Initial commit"
  gh repo create "$REPO" --public --source=. --remote=origin --push || {
    echo "❌ Failed to create GitHub repo. Is it already created?";
    exit 1;
  }
fi

# Ensure required labels exist
echo "🏷️ Creating required labels (if missing)..."
declare -a REQUIRED_LABELS=(
  "dependencies:FDD835:Dependency management"
  "sync:00B8D9:Sync logic"
  "schema:607D8B:Schema validation"
  "ci:008672:CI/CD pipeline"
  "validation:B39DDB:Validation tasks"
  "testing:00C853:Testing and QA"
  "bug:D73A4A:Bug Report"
  "story:1D76DB:User Story"
  "enhancement:A2EEEF:Feature Request"
  "needs-review:FF9F1C:Ready for Review"
)

for LABEL_DEF in "${REQUIRED_LABELS[@]}"; do
  IFS=':' read -r NAME COLOR DESC <<< "$LABEL_DEF"
  gh label create "$NAME" --color "$COLOR" --description "$DESC" --repo "$REPO" 2>/dev/null ||   gh label edit "$NAME" --color "$COLOR" --description "$DESC" --repo "$REPO"
done

echo "🚀 Creating Classic GitHub Project '$PROJECT_NAME'"
gh project create --title "$PROJECT_NAME" --owner "$USER" --format json > project.json
PROJECT_ID=$(jq -r '.id' project.json)

# Add fields
for FIELD in "Status:single_select" "Story Points:number" "Priority:single_select" "Sprint:text"; do
  IFS=':' read -r NAME TYPE <<< "$FIELD"
  gh project field-create "$PROJECT_ID" --name "$NAME" --data-type "$TYPE"
done

# Create views
gh project view-create "$PROJECT_ID" --title "Kanban Board" --layout board
gh project view-create "$PROJECT_ID" --title "Sprint Table" --layout table

# Link issues to the project
ISSUE_NUMBERS=$(gh issue list --repo "$REPO" --json number --jq '.[].number')
for ISSUE in $ISSUE_NUMBERS; do
  echo "🔗 Adding issue #$ISSUE to project..."
  gh project item-add "$PROJECT_ID" --issue "$REPO#$ISSUE"
done

echo "✅ Classic project setup complete: https://github.com/$REPO/projects"

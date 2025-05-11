#!/bin/bash

# Unified GitHub Project Setup Script (Beta or Classic)
# Supports: project creation, repo initialization, issue linking, field setup
set -e

# Load environment variables from .env file
if [[ -f .env ]]; then
  echo "🔍 Loading environment variables from .env file..."
  source .env
else
  echo "⚠️ .env file not found. Using default values."
fi

# Default values (in case .env is missing or incomplete)
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
# Optional GitHub repo init from local directory
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

# Detect if gh-projects is available (Beta support)
use_beta=false
if gh help projects &>/dev/null && gh projects --help | grep -q 'create'; then
    use_beta=true
fi

echo "🔍 Detected Projects API: $([[ "$use_beta" == true ]] && echo 'Beta' || echo 'Classic')"

# ========== GH PROJECTS BETA ========== #
if $use_beta; then
  echo "🚀 Creating Beta project '$PROJECT_NAME'"
  PROJECT_JSON=$(gh projects create --title "$PROJECT_NAME" --user "$USER" --format json)
  PROJECT_ID=$(echo "$PROJECT_JSON" | jq -r '.id')

  [[ -z "$PROJECT_ID" ]] && { echo "❌ Failed to create Beta project"; exit 1; }

  # Add fields
  for FIELD in "Status:SINGLE_SELECT" "Story Points:NUMBER" "Priority:SINGLE_SELECT" "Sprint:TEXT"; do
    IFS=':' read -r NAME TYPE <<< "$FIELD"
    gh projects fields-add --project-id "$PROJECT_ID" --name "$NAME" --data-type "$TYPE"
  done

  STATUS_FIELD_ID=$(gh projects fields-list --project-id "$PROJECT_ID" --format json | jq -r '.[] | select(.name == "Status") | .id')

  for OPTION in "Backlog" "Selected for Development" "In Progress" "In Review" "Done"; do
    gh projects fields-options-add --project-id "$PROJECT_ID" --field-id "$STATUS_FIELD_ID" --name "$OPTION"
  done

  # Views
  gh projects views-add --project-id "$PROJECT_ID" --name "Kanban Board" --layout BOARD
  gh projects views-add --project-id "$PROJECT_ID" --name "Sprint Table" --layout TABLE

  # Labels
  declare -a LABELS=("bug:D73A4A:Bug Report" "story:1D76DB:User Story" "enhancement:A2EEEF:Feature Request" "needs-review:FF9F1C:Ready for Review")
  for LABEL_DEF in "${LABELS[@]}"; do
    IFS=':' read -r NAME COLOR DESC <<< "$LABEL_DEF"
    gh label create "$NAME" --color "$COLOR" --description "$DESC" --repo "$REPO" || \
    gh label edit "$NAME" --color "$COLOR" --description "$DESC" --repo "$REPO"
  done

  # Link issues + apply status
  ISSUE_NUMBERS=$(gh issue list --repo "$REPO" --json number --jq '.[].number')
  declare -A LABEL_TO_STATUS=(["bug"]="In Progress" ["story"]="Selected for Development" ["enhancement"]="Backlog" ["needs-review"]="In Review")

  for ISSUE in $ISSUE_NUMBERS; do
    echo "🔗 Linking issue #$ISSUE..."
    gh projects items-add --project-id "$PROJECT_ID" --issue "$REPO#$ISSUE"
    ITEM_ID=$(gh projects items-list --project-id "$PROJECT_ID" --format json | jq -r ".[] | select(.content.url | contains(\"$ISSUE\")) | .id")
    [[ -z "$ITEM_ID" ]] && { echo "⚠️ Could not find item for issue $ISSUE"; continue; }

    LABELS=$(gh issue view "$ISSUE" --repo "$REPO" --json labels --jq '.labels[].name')
    for LABEL in $LABELS; do
      if [[ -n "${LABEL_TO_STATUS[$LABEL]}" ]]; then
        STATUS_OPTION="${LABEL_TO_STATUS[$LABEL]}"
        OPTION_ID=$(gh projects fields-options-list --project-id "$PROJECT_ID" --field-id "$STATUS_FIELD_ID" --format json | jq -r ".[] | select(.name == \"$STATUS_OPTION\") | .id")
        gh projects fields-update --project-id "$PROJECT_ID" --item-id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$OPTION_ID"
        echo "   → Set status to $STATUS_OPTION"
        break
      fi
    done
  done

  echo "🎉 Beta project setup complete: https://github.com/users/$USER/projects"

# ========== GH CLASSIC PROJECTS ========== #
else
  echo "🚀 Creating Classic project '$PROJECT_NAME'"
  gh project create --title "$PROJECT_NAME" --format json > project.json
  PROJECT_ID=$(jq -r '.id' project.json)

  for FIELD in "Status:single_select" "Story Points:number" "Priority:single_select" "Sprint:text"; do
    IFS=':' read -r NAME TYPE <<< "$FIELD"
    gh project field-create "$PROJECT_ID" --name "$NAME" --data-type "$TYPE"
  done

  gh project view-create "$PROJECT_ID" --title "Kanban Board" --layout board
  gh project view-create "$PROJECT_ID" --title "Sprint Table" --layout table

  for LABEL in "needs-review:FF9F1C:Ready for Review" "story:1D76DB:User Story" "bug:D73A4A:Bug Report" "enhancement:A2EEEF:Feature Request"; do
    IFS=':' read -r NAME COLOR DESC <<< "$LABEL"
    gh label create "$NAME" --color "$COLOR" --description "$DESC" --repo "$REPO"
  done

  ISSUE_NUMBERS=$(gh issue list --repo "$REPO" --json number --jq '.[].number')
  for ISSUE in $ISSUE_NUMBERS; do
    gh project item-add "$PROJECT_ID" --issue "$REPO#$ISSUE"
  done

  echo "🎉 Classic project setup complete: https://github.com/$REPO/projects"
fi
echo "✅ Project setup complete!"
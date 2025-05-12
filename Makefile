
# Makefile to automate PMAC GitHub Scrum Board setup

include .env
export $(shell sed 's/=.*//' .env)

all: create-fields create-issues init-board

create-fields:
	@echo "🚀 Creating GitHub Beta Project fields via GraphQL..."
	python3 graphql_create_fields.py

create-issues:
	@echo "📄 Running Python script to create issues from stories.json..."
	python3 create_issues_from_json.py

init-board:
	@echo "🚀 Initializing GitHub Scrum board..."
	bash init_github_board.sh --repo $(REPO) --project "$(PROJECT_NAME)"

clean:
	@echo "🧹 Cleaning generated files..."
	rm -f project.json

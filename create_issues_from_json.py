import json
import subprocess
import os

STORIES_PATH = os.getenv("STORIES_PATH", "data/stories.json")
REPO = os.getenv("REPO", "schneidergithub/aiinstaller")

# Get existing issue titles
print("📋 Fetching existing GitHub issues...")
existing_titles = subprocess.run(
    ["gh", "issue", "list", "--repo", REPO, "--json", "title", "--jq", ".[].title"],
    capture_output=True, text=True
).stdout.splitlines()

with open(STORIES_PATH, "r") as f:
    stories = json.load(f)

for story in stories:
    title = story.get("summary", "")
    if title in existing_titles:
        print(f"⏩ Skipping existing issue: {title}")
        continue

    body = story.get("description", "")
    labels = story.get("labels", [])
    label_args = []
    for label in labels:
        label_args.extend(["--label", label])

    print(f"📌 Creating issue: {title}")
    subprocess.run(["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body] + label_args)

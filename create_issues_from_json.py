import json
import subprocess
import os

STORIES_PATH = os.getenv("STORIES_PATH", "data/stories.json")

with open(STORIES_PATH, "r") as f:
    stories = json.load(f)

for story in stories:
    title = story.get("summary", "")
    body = story.get("description", "")
    labels = story.get("labels", [])
    label_args = []
    for label in labels:
        label_args.extend(["--label", label])

    print(f"📌 Creating issue: {title}")
    subprocess.run(["gh", "issue", "create", "--title", title, "--body", body] + label_args)

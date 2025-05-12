import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print(f"GITHUB_TOKEN: {os.getenv('GITHUB_TOKEN')}")
print(f"GITHUB_PROJECT_ID: {os.getenv('GITHUB_PROJECT_ID')}")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PROJECT_ID = os.getenv("GITHUB_PROJECT_ID")  # e.g., PVT_xxxxx

if not GITHUB_TOKEN or not PROJECT_ID:
    print("❌ Missing GITHUB_TOKEN or GITHUB_PROJECT_ID in environment.")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json"
}


def get_existing_field_names():
    query = f'''
    query {{
      node(id: "{PROJECT_ID}") {{
        ... on ProjectV2 {{
          fields(first: 100) {{
            nodes {{
              ... on ProjectV2FieldCommon {{
                name
              }}
            }}
          }}
        }}
      }}
    }}
    '''
    response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=HEADERS)
    data = response.json()
    if "errors" in data:
        print("❌ Failed to list existing fields:", data["errors"])
        return set()
    return {field['name'] for field in data['data']['node']['fields']['nodes']}

existing_fields = get_existing_field_names()

FIELDS = [
    {"name": "Status", "dataType": "SINGLE_SELECT", "options": [
        {"name": "Backlog", "description": "To be worked on", "color": "GRAY"},
        {"name": "Selected for Development", "description": "Planned for sprint", "color": "BLUE"},
        {"name": "In Progress", "description": "Actively being worked on", "color": "YELLOW"},
        {"name": "In Review", "description": "Under code review", "color": "PURPLE"},
        {"name": "Done", "description": "Work is completed", "color": "GREEN"}
    ]},
    {"name": "Sprint", "dataType": "TEXT"},
    {"name": "Story Points", "dataType": "NUMBER"},
    {"name": "Priority", "dataType": "SINGLE_SELECT", "options": [
        {"name": "Low", "description": "Low priority task", "color": "GRAY"},
        {"name": "Medium", "description": "Moderate importance", "color": "YELLOW"},
        {"name": "High", "description": "Must be completed soon", "color": "RED"}
    ]}
]

for field in FIELDS:
    if field["name"] in existing_fields:
        print(f"⏭️ Field '{field['name']}' already exists. Skipping.")
        continue

    if field["dataType"] == "SINGLE_SELECT":
        options_block = ", ".join(
            [f'{{name: "{opt["name"]}", description: "{opt["description"]}", color: {opt["color"]}}}' for opt in field["options"]]
        )
        query = f'''
        mutation {{
          createProjectV2Field(input: {{
            projectId: "{PROJECT_ID}",
            name: "{field['name']}",
            dataType: {field["dataType"]},
            singleSelectOptions: [{options_block}]
          }}) {{
            clientMutationId
          }}
        }}
        '''
    else:
        query = f'''
        mutation {{
          createProjectV2Field(input: {{
            projectId: "{PROJECT_ID}",
            name: "{field['name']}",
            dataType: {field["dataType"]}
          }}) {{
            clientMutationId
          }}
        }}
        '''

    response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=HEADERS)
    result = response.json()

    if "errors" in result:
        print(f"❌ Error creating field '{field['name']}': {result['errors']}")
    else:
        print(f"✅ Created field '{field['name']}'")

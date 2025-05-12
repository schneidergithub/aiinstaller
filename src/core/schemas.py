"""
JSON schema definitions for validating PMaC data files.

These schemas define the expected structure and data types for the
various JSON files used as the source of truth in the system.
"""

from typing import Dict, Any

# Schema for epics.json
EPIC_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "title", "description", "stories"],
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "stories": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }
}

# Schema for stories.json
STORY_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "summary", "description", "epic_id", "story_points", "status"],
        "properties": {
            "id": {"type": "string"},
            "epic_id": {"type": "string"},
            "summary": {"type": "string"},
            "description": {"type": "string"},
            "story_points": {"type": "integer", "minimum": 0},
            "labels": {
                "type": "array",
                "items": {"type": "string"}
            },
            "status": {"type": "string", "enum": ["To Do", "In Progress", "Review", "Done"]}
        }
    }
}

# Schema for sprints.json
SPRINT_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["name", "start_date", "end_date", "stories"],
        "properties": {
            "name": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "stories": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }
}

# Schema for scrum_board.json
BOARD_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["board"],
    "properties": {
        "board": {
            "type": "object",
            "required": ["type", "name", "columns", "initial_assignments"],
            "properties": {
                "type": {"type": "string", "enum": ["scrum", "kanban"]},
                "name": {"type": "string"},
                "columns": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "initial_assignments": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }
}

# Schema for views.json
VIEWS_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["type", "name", "columns"],
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "columns": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    }
}

# Schema for project_meta.json
PROJECT_META_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["project_key", "name", "description"],
    "properties": {
        "project_key": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"}
    }
}

# Schema for project_plan.json (comprehensive)
PROJECT_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["project", "epics", "stories", "sprints", "views"],
    "properties": {
        "project": PROJECT_META_SCHEMA,
        "epics": EPIC_SCHEMA,
        "stories": STORY_SCHEMA,
        "sprints": SPRINT_SCHEMA,
        "views": VIEWS_SCHEMA
    }
}

# Map of file names to their schemas
SCHEMA_MAP: Dict[str, Dict[str, Any]] = {
    "epics.json": EPIC_SCHEMA,
    "stories.json": STORY_SCHEMA,
    "sprints.json": SPRINT_SCHEMA,
    "scrum_board.json": BOARD_SCHEMA,
    "views.json": VIEWS_SCHEMA,
    "project_meta.json": PROJECT_META_SCHEMA,
    "project_plan.json": PROJECT_PLAN_SCHEMA
}

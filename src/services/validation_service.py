"""
JSON Schema Validation Service.

This module provides validation for the JSON data files against their schemas.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import jsonschema

from src.core.schemas import SCHEMA_MAP

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class ValidationService:
    """Service for validating JSON data files."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize the validation service.
        
        Args:
            data_dir: Directory containing JSON data files.
        """
        self.data_dir = Path(data_dir)
    
    def _load_json_file(self, filename: str) -> Any:
        """Load a JSON file from the data directory.
        
        Args:
            filename: Name of the JSON file.
            
        Returns:
            Parsed JSON data.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        file_path = self.data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "r") as f:
            return json.load(f)
    
    def validate_file(self, filename: str) -> Tuple[bool, List[str]]:
        """Validate a JSON file against its schema.
        
        Args:
            filename: Name of the JSON file.
            
        Returns:
            Tuple of (success, error_messages).
        """
        if filename not in SCHEMA_MAP:
            return False, [f"No schema defined for {filename}"]
        
        schema = SCHEMA_MAP[filename]
        
        try:
            data = self._load_json_file(filename)
        except FileNotFoundError:
            return False, [f"File not found: {filename}"]
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON in {filename}: {str(e)}"]
        
        # Validate against schema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(data))
        
        if errors:
            error_messages = [
                f"{error.path}: {error.message}" if error.path else error.message
                for error in errors
            ]
            return False, error_messages
        
        return True, []
    
    def validate_all_files(self) -> Dict[str, Any]:
        """Validate all JSON files against their schemas.
        
        Returns:
            Validation results.
        """
        results = {}
        all_valid = True
        
        for filename in SCHEMA_MAP.keys():
            valid, errors = self.validate_file(filename)
            results[filename] = {
                "valid": valid,
                "errors": errors
            }
            
            if not valid:
                all_valid = False
        
        return {
            "valid": all_valid,
            "results": results
        }
    
    def validate_relationships(self) -> Tuple[bool, List[str]]:
        """Validate relationships between files.
        
        Returns:
            Tuple of (success, error_messages).
        """
        error_messages = []
        
        try:
            # Load all data
            stories = self._load_json_file("stories.json")
            epics = self._load_json_file("epics.json")
            sprints = self._load_json_file("sprints.json")
            board = self._load_json_file("scrum_board.json")
            
            # Check if all story IDs in epics exist
            story_ids = {story["id"] for story in stories}
            for epic in epics:
                for story_id in epic["stories"]:
                    if story_id not in story_ids:
                        error_messages.append(f"Epic {epic['id']} references non-existent story {story_id}")
            
            # Check if all epic IDs in stories exist
            epic_ids = {epic["id"] for epic in epics}
            for story in stories:
                if story["epic_id"] not in epic_ids:
                    error_messages.append(f"Story {story['id']} references non-existent epic {story['epic_id']}")
            
            # Check if all story IDs in sprints exist
            for sprint in sprints:
                for story_id in sprint["stories"]:
                    if story_id not in story_ids:
                        error_messages.append(f"Sprint {sprint['name']} references non-existent story {story_id}")
            
            # Check if all column names in board initial assignments are valid
            board_columns = set(board["board"]["columns"])
            for column, assigned_stories in board["board"]["initial_assignments"].items():
                if column not in board_columns:
                    error_messages.append(f"Board initial assignment references non-existent column {column}")
                
                # Check if all story IDs in board initial assignments exist
                for story_id in assigned_stories:
                    if story_id not in story_ids:
                        error_messages.append(f"Board initial assignment for column {column} references non-existent story {story_id}")
        
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            error_messages.append(f"Error validating relationships: {str(e)}")
        
        return len(error_messages) == 0, error_messages
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all data (schemas and relationships).
        
        Returns:
            Validation results.
        """
        # Validate schemas
        schema_validation = self.validate_all_files()
        
        # Validate relationships only if all schemas are valid
        relationship_valid = False
        relationship_errors = []
        
        if schema_validation["valid"]:
            relationship_valid, relationship_errors = self.validate_relationships()
        
        return {
            "valid": schema_validation["valid"] and relationship_valid,
            "schema_validation": schema_validation,
            "relationship_validation": {
                "valid": relationship_valid,
                "errors": relationship_errors
            }
        }

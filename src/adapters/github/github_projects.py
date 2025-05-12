"""
GitHub Projects Adapter.

This module handles the creation and configuration of GitHub projects,
and the association of issues with projects.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from src.core.models import Board, Story
from src.adapters.github.client import GitHubClient

logger = logging.getLogger(__name__)


class GitHubProjectsAdapter:
    """Adapter for GitHub projects operations."""
    
    def __init__(self, github_client: GitHubClient):
        """Initialize the GitHub projects adapter.
        
        Args:
            github_client: GitHub client instance.
        """
        self.client = github_client
    
    def find_existing_project(self, name: str, owner: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find an existing project by name.
        
        Args:
            name: Project name.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            Project data if found, None otherwise.
        """
        if not owner:
            owner = self.client.config.repo.split("/")[0]
        
        try:
            projects = self.client.list_projects(owner)
            
            for project in projects:
                # Match by title/name
                if project.get("title") == name or project.get("name") == name:
                    logger.debug(f"Found existing project: {name} (#{project.get('number')})")
                    return project
            
            logger.debug(f"No existing project found with name: {name}")
            return None
        except Exception as e:
            logger.error(f"Error finding project {name}: {str(e)}")
            return None
    
    def create_project(
        self,
        name: str,
        owner: Optional[str] = None,
        dry_run: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Create a GitHub project if it doesn't exist.
        
        Args:
            name: Project name.
            owner: Project owner (defaults to repo owner).
            dry_run: If True, don't actually create the project.
            
        Returns:
            Tuple of (project_data, is_new).
        """
        if not owner:
            owner = self.client.config.repo.split("/")[0]
        
        # Check if project already exists
        existing_project = self.find_existing_project(name, owner)
        if existing_project:
            logger.info(f"Project already exists: {name} (#{existing_project.get('number')})")
            return existing_project, False
        
        if dry_run:
            logger.info(f"Would create project: {name}")
            return None, True
        
        # Create the project
        try:
            logger.info(f"Creating project: {name}")
            project = self.client.create_project(name, owner)
            logger.info(f"Created project: {name} (#{project.get('number')})")
            return project, True
        except Exception as e:
            logger.error(f"Failed to create project {name}: {str(e)}")
            return None, False
    
    def add_issue_to_project(
        self,
        project_number: str,
        issue_number: str,
        owner: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """Add an issue to a project.
        
        Args:
            project_number: Project number.
            issue_number: Issue number.
            owner: Project owner (defaults to repo owner).
            dry_run: If True, don't actually add the issue.
            
        Returns:
            True if successful.
        """
        if not owner:
            owner = self.client.config.repo.split("/")[0]
        
        if dry_run:
            logger.info(f"Would add issue #{issue_number} to project #{project_number}")
            return True
        
        try:
            logger.debug(f"Adding issue #{issue_number} to project #{project_number}")
            self.client.add_issue_to_project(project_number, issue_number, owner)
            logger.debug(f"Added issue #{issue_number} to project #{project_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to add issue #{issue_number} to project #{project_number}: {str(e)}")
            return False
    
    def create_board_from_model(
        self,
        board: Board,
        issues_map: Dict[str, str],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Create a GitHub project board from a Board model.
        
        Args:
            board: Board model.
            issues_map: Mapping from story ID to issue number.
            dry_run: If True, don't actually create the board.
            
        Returns:
            Summary of the operation.
        """
        # Create the project
        project, is_new = self.create_project(board.name, dry_run=dry_run)
        
        if not project and not dry_run:
            return {
                "success": False,
                "message": "Failed to create project",
                "is_new": is_new,
                "dry_run": dry_run
            }
        
        # Add issues to the project
        added_issues = []
        failed_issues = []
        
        if not dry_run and project:
            project_number = project.get("number")
            
            # Process each column and its initial assignments
            for column_name, story_ids in board.initial_assignments.items():
                for story_id in story_ids:
                    if story_id in issues_map:
                        issue_number = issues_map[story_id]
                        success = self.add_issue_to_project(project_number, issue_number, dry_run=dry_run)
                        
                        if success:
                            added_issues.append({
                                "story_id": story_id,
                                "issue_number": issue_number,
                                "column": column_name
                            })
                        else:
                            failed_issues.append({
                                "story_id": story_id,
                                "issue_number": issue_number,
                                "column": column_name
                            })
        
        # Prepare summary
        summary = {
            "success": True,
            "project_name": board.name,
            "project_number": project.get("number") if project else None,
            "is_new": is_new,
            "added_issues": len(added_issues),
            "failed_issues": len(failed_issues),
            "added_issues_details": added_issues,
            "failed_issues_details": failed_issues,
            "dry_run": dry_run
        }
        
        logger.info(
            f"Board creation summary: project {'would be' if dry_run else 'was'} "
            f"{'created' if is_new else 'reused'}, {len(added_issues)} issues added, "
            f"{len(failed_issues)} failed"
        )
        
        return summary

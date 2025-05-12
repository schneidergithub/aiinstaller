"""
GitHub Issues Adapter.

This module handles the conversion between domain models and GitHub issues,
and provides operations for creating and updating issues.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from src.core.models import Story, Epic
from src.adapters.github.client import GitHubClient

logger = logging.getLogger(__name__)


class GitHubIssuesAdapter:
    """Adapter for GitHub issues operations."""
    
    def __init__(self, github_client: GitHubClient):
        """Initialize the GitHub issues adapter.
        
        Args:
            github_client: GitHub client instance.
        """
        self.client = github_client
    
    def find_existing_issue(self, story: Story) -> Optional[Dict[str, Any]]:
        """Find an existing issue for a story.
        
        Args:
            story: Story model.
            
        Returns:
            Issue data if found, None otherwise.
        """
        issues = self.client.list_issues(state="all")
        
        # First, try to find by ID in labels
        for issue in issues:
            labels = [label["name"] for label in issue["labels"]]
            if story.id in labels:
                logger.debug(f"Found existing issue for story {story.id} by ID label: #{issue['number']}")
                return issue
        
        # Then, try to find by title match
        for issue in issues:
            if issue["title"] == story.summary:
                logger.debug(f"Found existing issue for story {story.id} by title: #{issue['number']}")
                return issue
        
        return None
    
    def story_to_issue_payload(self, story: Story, epic: Optional[Epic] = None) -> Dict[str, Any]:
        """Convert a story to an issue creation payload.
        
        Args:
            story: Story model.
            epic: Optional epic for the story.
            
        Returns:
            Issue creation payload.
        """
        labels = list(story.labels)
        
        # Add story ID as label
        labels.append(story.id)
        
        # Add epic as label if available
        if story.epic_id:
            labels.append(f"epic:{story.epic_id}")
        
        # Add story points as label
        if story.story_points > 0:
            labels.append(f"points:{story.story_points}")
        
        # Create issue body with metadata
        body = f"{story.description}\n\n"
        body += f"## Metadata\n"
        body += f"- **ID:** {story.id}\n"
        body += f"- **Epic:** {story.epic_id}\n"
        if epic:
            body += f"- **Epic Title:** {epic.title}\n"
        body += f"- **Story Points:** {story.story_points}\n"
        body += f"- **Status:** {story.status}\n"
        
        # Add labels section
        if story.labels:
            body += "\n## Labels\n"
            for label in story.labels:
                body += f"- {label}\n"
        
        return {
            "title": story.summary,
            "body": body,
            "labels": labels
        }
    
    def ensure_labels_exist(self, stories: List[Story], epics: List[Epic]) -> None:
        """Ensure all required labels exist in the repository.
        
        Args:
            stories: List of stories.
            epics: List of epics.
        """
        # Collect all required labels
        required_labels = []
        
        # Add labels for story IDs
        for story in stories:
            required_labels.append({
                "name": story.id,
                "color": "FEF2C0",
                "description": f"Story ID: {story.id}"
            })
        
        # Add labels for epics
        for epic in epics:
            required_labels.append({
                "name": f"epic:{epic.id}",
                "color": "0366D6",
                "description": epic.title
            })
        
        # Add labels for story points
        for points in range(1, 11):
            required_labels.append({
                "name": f"points:{points}",
                "color": "C2E0C6",
                "description": f"{points} story points"
            })
        
        # Add labels from stories
        unique_labels = set()
        for story in stories:
            for label in story.labels:
                unique_labels.add(label)
        
        for label in unique_labels:
            required_labels.append({
                "name": label,
                "color": "D4C5F9",
                "description": f"Tag: {label}"
            })
        
        # Create all labels
        for label_data in required_labels:
            try:
                self.client.create_label(
                    name=label_data["name"],
                    color=label_data["color"],
                    description=label_data["description"]
                )
                logger.debug(f"Created/updated label: {label_data['name']}")
            except Exception as e:
                logger.warning(f"Failed to create/update label {label_data['name']}: {str(e)}")
    
    def create_or_update_issue(
        self,
        story: Story,
        epic: Optional[Epic] = None,
        dry_run: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Create or update an issue for a story.
        
        Args:
            story: Story model.
            epic: Optional epic for the story.
            dry_run: If True, don't actually create/update the issue.
            
        Returns:
            Tuple of (issue_data, is_new).
        """
        # Check if issue already exists
        existing_issue = self.find_existing_issue(story)
        if existing_issue:
            logger.info(f"Issue already exists for story {story.id}: #{existing_issue['number']}")
            return existing_issue, False
        
        # Prepare issue payload
        issue_payload = self.story_to_issue_payload(story, epic)
        
        if dry_run:
            logger.info(f"Would create issue: {issue_payload['title']}")
            return None, True
        
        # Create the issue
        try:
            logger.info(f"Creating issue for story {story.id}: {issue_payload['title']}")
            issue = self.client.create_issue(
                title=issue_payload["title"],
                body=issue_payload["body"],
                labels=issue_payload["labels"]
            )
            logger.info(f"Created issue #{issue['number']} for story {story.id}")
            return issue, True
        except Exception as e:
            logger.error(f"Failed to create issue for story {story.id}: {str(e)}")
            return None, False
    
    def sync_stories_to_issues(
        self,
        stories: List[Story],
        epics: List[Epic],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Sync stories to GitHub issues.
        
        Args:
            stories: List of stories to sync.
            epics: List of epics.
            dry_run: If True, don't actually create/update issues.
            
        Returns:
            Summary of the sync operation.
        """
        if not dry_run:
            # Ensure all required labels exist
            self.ensure_labels_exist(stories, epics)
        
        # Create a map of epic_id to Epic for quick lookup
        epic_map = {epic.id: epic for epic in epics}
        
        # Track sync results
        created_issues = []
        existing_issues = []
        failed_issues = []
        
        # Process each story
        for story in stories:
            epic = epic_map.get(story.epic_id)
            
            try:
                issue, is_new = self.create_or_update_issue(story, epic, dry_run)
                
                if is_new and issue:
                    created_issues.append({
                        "story_id": story.id,
                        "issue_number": issue["number"],
                        "title": issue["title"]
                    })
                elif not is_new and issue:
                    existing_issues.append({
                        "story_id": story.id,
                        "issue_number": issue["number"],
                        "title": issue["title"]
                    })
            except Exception as e:
                logger.error(f"Error syncing story {story.id}: {str(e)}")
                failed_issues.append({
                    "story_id": story.id,
                    "error": str(e)
                })
        
        # Prepare summary
        summary = {
            "created": len(created_issues),
            "existing": len(existing_issues),
            "failed": len(failed_issues),
            "total": len(stories),
            "created_issues": created_issues,
            "existing_issues": existing_issues,
            "failed_issues": failed_issues,
            "dry_run": dry_run
        }
        
        logger.info(f"Sync summary: {summary['created']} created, {summary['existing']} existing, {summary['failed']} failed")
        return summary

"""
GitHub API Client Adapter.

This module provides a clean, flexible interface to interact with GitHub's API,
supporting both GitHub CLI and REST API approaches with comprehensive error handling.
It abstracts the details of HTTP requests, authentication, and response parsing.
"""

import json
import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast
import requests

logger = logging.getLogger(__name__)


class GitHubAPIMode(Enum):
    """Enum for GitHub API access modes."""
    CLI = "cli"  # Using GitHub CLI (gh)
    REST = "rest"  # Using REST API directly


@dataclass
class GitHubConfig:
    """Configuration for GitHub API access."""
    repo: str  # Format: username/repo
    token: Optional[str] = None  # GitHub personal access token
    api_url: str = "https://api.github.com"  # GitHub API base URL
    mode: GitHubAPIMode = GitHubAPIMode.CLI  # API access mode
    timeout: int = 30  # Request timeout in seconds
    verify_ssl: bool = True  # Verify SSL certificates
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.repo or '/' not in self.repo:
            raise ValueError("Invalid repository format. Expected 'username/repo'.")
        
        if self.mode == GitHubAPIMode.REST and not self.token:
            raise ValueError("GitHub token is required for REST API mode.")


class GitHubClientError(Exception):
    """Base exception for GitHub client errors."""
    pass


class GitHubAuthError(GitHubClientError):
    """Exception for authentication errors."""
    pass


class GitHubAPIError(GitHubClientError):
    """Exception for API errors with status code and message."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response: Optional[Dict[str, Any]] = None):
        """Initialize with message, status code, and response."""
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class GitHubRateLimitError(GitHubAPIError):
    """Exception for rate limit errors."""
    
    def __init__(self, message: str, status_code: int = 429, 
                 reset_time: Optional[int] = None):
        """Initialize with message, status code, and reset time."""
        self.reset_time = reset_time
        super().__init__(message, status_code)


class GitHubImplementationBase(ABC):
    """Base class for GitHub API implementations."""
    
    def __init__(self, config: GitHubConfig):
        """Initialize with configuration."""
        self.config = config
    
    @abstractmethod
    def check_auth(self) -> bool:
        """Check if the client is authenticated.
        
        Returns:
            True if authenticated, False otherwise.
            
        Raises:
            GitHubAuthError: If authentication check fails.
        """
        pass
    
    @abstractmethod
    def get_repo_info(self) -> Dict[str, Any]:
        """Get repository information.
        
        Returns:
            Repository information.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def list_issues(self, state: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """List repository issues.
        
        Args:
            state: Issue state ("open", "closed", "all").
            limit: Maximum number of issues to return.
            
        Returns:
            List of issues.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new issue.
        
        Args:
            title: Issue title.
            body: Issue body.
            labels: Issue labels.
            assignees: Issue assignees.
            milestone: Issue milestone number.
            
        Returns:
            Created issue data.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def get_issue(self, issue_number: Union[str, int]) -> Dict[str, Any]:
        """Get issue details.
        
        Args:
            issue_number: Issue number.
            
        Returns:
            Issue details.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def create_label(self, name: str, color: str, description: str = "") -> Dict[str, Any]:
        """Create or update a label.
        
        Args:
            name: Label name.
            color: Label color (hex code without #).
            description: Label description.
            
        Returns:
            Label details.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def list_projects(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects.
        
        Args:
            owner: Project owner (defaults to repo owner).
            
        Returns:
            List of projects.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def create_project(self, title: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            title: Project title.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            Created project data.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass
    
    @abstractmethod
    def add_issue_to_project(
        self,
        project_number: Union[str, int],
        issue_number: Union[str, int],
        owner: Optional[str] = None
    ) -> bool:
        """Add an issue to a project.
        
        Args:
            project_number: Project number.
            issue_number: Issue number.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            True if successful.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        pass


class GitHubCLIImplementation(GitHubImplementationBase):
    """GitHub API implementation using GitHub CLI."""
    
    def check_auth(self) -> bool:
        """Check if the GitHub CLI is authenticated.
        
        Returns:
            True if authenticated.
            
        Raises:
            GitHubAuthError: If authentication check fails.
        """
        try:
            self._run_cli_command(["auth", "status"])
            return True
        except GitHubClientError as e:
            logger.error(f"GitHub CLI authentication failed: {str(e)}")
            raise GitHubAuthError("GitHub CLI not authenticated. Run 'gh auth login' first.")
    
    def _run_cli_command(
        self, 
        args: List[str], 
        check_error: bool = True,
        input_data: Optional[str] = None
    ) -> str:
        """Run a GitHub CLI command.
        
        Args:
            args: Command arguments for GitHub CLI.
            check_error: Whether to check for errors in the response.
            input_data: Optional input data for the command.
            
        Returns:
            Command output as string.
            
        Raises:
            GitHubClientError: If the command fails.
        """
        cmd = ["gh"] + args
        logger.debug(f"Running GitHub CLI command: {' '.join(cmd)}")
        
        # Handle input data if provided
        stdin = None
        temp_file = None
        
        if input_data:
            temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            temp_file.write(input_data)
            temp_file.close()
            stdin = open(temp_file.name, 'r')
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                stdin=stdin
            )
            
            # Clean up temp file if used
            if stdin:
                stdin.close()
                os.unlink(temp_file.name)
            
            if check_error and result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                
                # Handle rate limit errors
                if "API rate limit exceeded" in error_msg:
                    raise GitHubRateLimitError(f"GitHub API rate limit exceeded: {error_msg}")
                
                logger.error(f"GitHub CLI command failed: {error_msg}")
                raise GitHubClientError(f"GitHub CLI command failed: {error_msg}")
            
            return result.stdout.strip()
            
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to run GitHub CLI command: {str(e)}")
            raise GitHubClientError(f"Failed to run GitHub CLI command: {str(e)}")
        finally:
            # Ensure cleanup if an exception occurs
            if stdin and not stdin.closed:
                stdin.close()
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    def get_repo_info(self) -> Dict[str, Any]:
        """Get repository information using GitHub CLI.
        
        Returns:
            Repository information.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        output = self._run_cli_command([
            "repo", "view", self.config.repo, 
            "--json", "name,owner,description,url,isPrivate,defaultBranch"
        ])
        return json.loads(output)
    
    def list_issues(self, state: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """List repository issues using GitHub CLI.
        
        Args:
            state: Issue state ("open", "closed", "all").
            limit: Maximum number of issues to return.
            
        Returns:
            List of issues.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        output = self._run_cli_command([
            "issue", "list",
            "--repo", self.config.repo,
            "--state", state,
            "--limit", str(limit),
            "--json", "number,title,state,labels,assignees,url,author,createdAt,updatedAt,body"
        ])
        
        # Handle empty output (no issues)
        if not output.strip():
            return []
        
        return json.loads(output)
    
    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new issue using GitHub CLI.
        
        Args:
            title: Issue title.
            body: Issue body.
            labels: Issue labels.
            assignees: Issue assignees.
            milestone: Issue milestone number.
            
        Returns:
            Created issue data.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        cmd = ["issue", "create", "--repo", self.config.repo, "--title", title, "--body", body]
        
        if labels:
            for label in labels:
                cmd.extend(["--label", label])
        
        if assignees:
            for assignee in assignees:
                cmd.extend(["--assignee", assignee])
        
        if milestone:
            cmd.extend(["--milestone", str(milestone)])
        
        output = self._run_cli_command(cmd)
        
        # Extract issue number from URL
        # Example output: https://github.com/user/repo/issues/123
        issue_url = output.strip()
        try:
            issue_number = issue_url.split("/")[-1]
            
            # Fetch the created issue details
            return self.get_issue(issue_number)
        except (IndexError, ValueError) as e:
            logger.error(f"Failed to extract issue number from URL: {issue_url}")
            raise GitHubClientError(f"Failed to extract issue number from URL: {issue_url}")
    
    def get_issue(self, issue_number: Union[str, int]) -> Dict[str, Any]:
        """Get issue details using GitHub CLI.
        
        Args:
            issue_number: Issue number.
            
        Returns:
            Issue details.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        output = self._run_cli_command([
            "issue", "view", str(issue_number),
            "--repo", self.config.repo,
            "--json", "number,title,state,body,labels,assignees,url,author,createdAt,updatedAt,comments,reactions"
        ])
        return json.loads(output)
    
    def create_label(self, name: str, color: str, description: str = "") -> Dict[str, Any]:
        """Create or update a label using GitHub CLI.
        
        Args:
            name: Label name.
            color: Label color (hex code without #).
            description: Label description.
            
        Returns:
            Label details.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        try:
            # Try to create the label
            self._run_cli_command([
                "label", "create", name,
                "--repo", self.config.repo,
                "--color", color,
                "--description", description
            ], check_error=False)
        except GitHubClientError as e:
            if "already exists" in str(e):
                # Update the label if it already exists
                self._run_cli_command([
                    "label", "edit", name,
                    "--repo", self.config.repo,
                    "--color", color,
                    "--description", description
                ])
            else:
                raise
        
        # Return label details
        return {"name": name, "color": color, "description": description}
    
    def list_projects(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects using GitHub CLI.
        
        Args:
            owner: Project owner (defaults to repo owner).
            
        Returns:
            List of projects.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        if not owner:
            owner = self.config.repo.split("/")[0]
        
        try:
            # Try to get projects in JSON format first
            output = self._run_cli_command(["project", "list", "--owner", owner, "--format", "json"])
            return json.loads(output)
        except GitHubClientError as e:
            # If JSON format fails, parse the text output
            if "no projects found" in str(e).lower():
                return []
            
            # Try with non-JSON format and parse manually
            try:
                output = self._run_cli_command(["project", "list", "--owner", owner])
                
                # Parse the output
                projects = []
                lines = output.strip().split("\n")
                
                # Skip header row
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 2:
                        project_number = parts[0]
                        # Title might contain spaces
                        title = " ".join(parts[1:-1]) if len(parts) > 2 else parts[1]
                        
                        projects.append({
                            "number": project_number,
                            "title": title,
                            "owner": owner
                        })
                
                return projects
            except Exception as parse_error:
                logger.error(f"Failed to parse projects: {str(parse_error)}")
                return []
    
    def create_project(self, title: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project using GitHub CLI.
        
        Args:
            title: Project title.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            Created project data.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        if not owner:
            owner = self.config.repo.split("/")[0]
        
        output = self._run_cli_command(["project", "create", "--title", title, "--owner", owner])
        
        # Try to extract project number from various output formats
        project_number = None
        
        # Format 1: "Created project 1"
        # Format 2: "Created project #1"
        # Format 3: "https://github.com/users/username/projects/1"
        
        import re
        
        if "Created project" in output:
            match = re.search(r'Created project [#]?(\d+)', output)
            if match:
                project_number = match.group(1)
        elif "github.com" in output:
            match = re.search(r'github\.com/[^/]+/projects/(\d+)', output)
            if match:
                project_number = match.group(1)
        
        if not project_number:
            logger.warning(f"Could not extract project number from output: {output}")
        
        return {
            "number": project_number,
            "title": title,
            "owner": owner,
            "url": output.strip() if "github.com" in output else f"https://github.com/users/{owner}/projects/{project_number}" if project_number else None
        }
    
    def add_issue_to_project(
        self,
        project_number: Union[str, int],
        issue_number: Union[str, int],
        owner: Optional[str] = None
    ) -> bool:
        """Add an issue to a project using GitHub CLI.
        
        Args:
            project_number: Project number.
            issue_number: Issue number.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            True if successful.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        if not owner:
            owner = self.config.repo.split("/")[0]
        
        self._run_cli_command([
            "project", "item-add", str(project_number),
            "--owner", owner,
            "--url", f"https://github.com/{self.config.repo}/issues/{issue_number}"
        ])
        
        return True


class GitHubRESTImplementation(GitHubImplementationBase):
    """GitHub API implementation using REST API."""
    
    def __init__(self, config: GitHubConfig):
        """Initialize with configuration.
        
        Args:
            config: GitHub configuration.
            
        Raises:
            ValueError: If token is not provided.
        """
        super().__init__(config)
        
        if not config.token:
            raise ValueError("GitHub token is required for REST API mode.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/vnd.github.v4+json"
        }
        
        response = self._request(
            "POST", 
            "/graphql", 
            data={"query": query, "variables": variables},
            headers=headers
        )
        
        try:
            project_id = response.get("data", {}).get("user", {}).get("projectV2", {}).get("id")
            
            if not project_id:
                raise GitHubClientError(f"Project with number {project_number} not found for {owner}")
            
            # Now get the issue node ID
            issue_query = """
            query($owner: String!, $repo: String!, $number: Int!) {
              repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                  id
                }
              }
            }
            """
            
            issue_variables = {
                "owner": self.config.repo.split("/")[0],
                "repo": self.config.repo.split("/")[1],
                "number": int(issue_number)
            }
            
            issue_response = self._request(
                "POST",
                "/graphql",
                data={"query": issue_query, "variables": issue_variables},
                headers=headers
            )
            
            issue_id = issue_response.get("data", {}).get("repository", {}).get("issue", {}).get("id")
            
            if not issue_id:
                raise GitHubClientError(f"Issue with number {issue_number} not found")
            
            # Add the issue to the project
            mutation = """
            mutation($input: AddProjectV2ItemByIdInput!) {
              addProjectV2ItemById(input: $input) {
                item {
                  id
                }
              }
            }
            """
            
            add_variables = {
                "input": {
                    "projectId": project_id,
                    "contentId": issue_id
                }
            }
            
            add_response = self._request(
                "POST",
                "/graphql",
                data={"query": mutation, "variables": add_variables},
                headers=headers
            )
            
            # Check if it worked
            if add_response.get("data", {}).get("addProjectV2ItemById", {}).get("item", {}).get("id"):
                return True
            
            # If we get here, something went wrong
            logger.error(f"Failed to add issue to project. Response: {add_response}")
            return False
            
        except (KeyError, AttributeError, GitHubAPIError) as e:
            logger.error(f"Failed to add issue to project: {str(e)}")
            raise GitHubClientError(f"Failed to add issue to project: {str(e)}")


class GitHubClient:
    """Client for interacting with GitHub API.
    
    This client provides a unified interface to GitHub API operations,
    supporting both GitHub CLI and REST API implementations.
    """
    
    def __init__(self, config: GitHubConfig):
        """Initialize the GitHub client.
        
        Args:
            config: Configuration for GitHub API access.
            
        Raises:
            GitHubClientError: If initialization fails.
        """
        self.config = config
        
        # Choose implementation based on configuration
        if config.mode == GitHubAPIMode.CLI:
            self._impl = GitHubCLIImplementation(config)
        else:
            self._impl = GitHubRESTImplementation(config)
        
        # Verify authentication
        self._verify_auth()
    
    def _verify_auth(self) -> None:
        """Verify authentication with the API.
        
        Raises:
            GitHubAuthError: If authentication fails.
        """
        try:
            self._impl.check_auth()
            logger.info(f"Successfully authenticated with GitHub API using {self.config.mode.value} mode")
        except Exception as e:
            logger.error(f"GitHub authentication failed: {str(e)}")
            raise GitHubAuthError(f"GitHub authentication failed: {str(e)}")
    
    def get_repo_info(self) -> Dict[str, Any]:
        """Get repository information.
        
        Returns:
            Repository information.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.get_repo_info()
    
    def list_issues(self, state: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """List repository issues.
        
        Args:
            state: Issue state ("open", "closed", "all").
            limit: Maximum number of issues to return.
            
        Returns:
            List of issues.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.list_issues(state, limit)
    
    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new issue.
        
        Args:
            title: Issue title.
            body: Issue body.
            labels: Issue labels.
            assignees: Issue assignees.
            milestone: Issue milestone number.
            
        Returns:
            Created issue data.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.create_issue(title, body, labels, assignees, milestone)
    
    def get_issue(self, issue_number: Union[str, int]) -> Dict[str, Any]:
        """Get issue details.
        
        Args:
            issue_number: Issue number.
            
        Returns:
            Issue details.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.get_issue(issue_number)
    
    def create_label(self, name: str, color: str, description: str = "") -> Dict[str, Any]:
        """Create or update a label.
        
        Args:
            name: Label name.
            color: Label color (hex code without #).
            description: Label description.
            
        Returns:
            Label details.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.create_label(name, color, description)
    
    def list_projects(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects.
        
        Args:
            owner: Project owner (defaults to repo owner).
            
        Returns:
            List of projects.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.list_projects(owner)
    
    def create_project(self, title: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            title: Project title.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            Created project data.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.create_project(title, owner)
    
    def add_issue_to_project(
        self,
        project_number: Union[str, int],
        issue_number: Union[str, int],
        owner: Optional[str] = None
    ) -> bool:
        """Add an issue to a project.
        
        Args:
            project_number: Project number.
            issue_number: Issue number.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            True if successful.
            
        Raises:
            GitHubClientError: If the request fails.
        """
        return self._impl.add_issue_to_project(project_number, issue_number, owner)"token {config.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PMaC-Sync-Tool/1.0"
        })
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a request to the GitHub API.
        
        Args:
            method: HTTP method ("GET", "POST", etc.).
            endpoint: API endpoint.
            params: Query parameters.
            data: Request body.
            headers: Additional headers.
            
        Returns:
            Response data.
            
        Raises:
            GitHubAPIError: If the request fails.
            GitHubRateLimitError: If rate limit is exceeded.
        """
        url = f"{self.config.api_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl
            )
            
            # Check for rate limit
            if response.status_code == 429:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                raise GitHubRateLimitError(
                    message="GitHub API rate limit exceeded",
                    reset_time=reset_time
                )
            
            # Check for other errors
            response.raise_for_status()
            
            # Return JSON response for non-empty responses
            if response.text.strip():
                return response.json()
            return {}
            
        except requests.RequestException as e:
            status_code = e.response.status_code if hasattr(e, 'response') else None
            response_data = {}
            
            if hasattr(e, 'response') and e.response.text:
                try:
                    response_data = e.response.json()
                except json.JSONDecodeError:
                    response_data = {"message": e.response.text}
            
            message = response_data.get("message", str(e))
            
            logger.error(f"GitHub API error: {message} (Status: {status_code})")
            raise GitHubAPIError(message=message, status_code=status_code, response=response_data)
    
    def check_auth(self) -> bool:
        """Check if the REST API client is authenticated.
        
        Returns:
            True if authenticated.
            
        Raises:
            GitHubAuthError: If authentication check fails.
        """
        try:
            self._request("GET", "/user")
            return True
        except GitHubAPIError as e:
            logger.error(f"GitHub REST API authentication failed: {str(e)}")
            raise GitHubAuthError(f"GitHub REST API authentication failed: {str(e)}")
    
    def get_repo_info(self) -> Dict[str, Any]:
        """Get repository information using REST API.
        
        Returns:
            Repository information.
            
        Raises:
            GitHubAPIError: If the request fails.
        """
        return self._request("GET", f"/repos/{self.config.repo}")
    
    def list_issues(self, state: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """List repository issues using REST API.
        
        Args:
            state: Issue state ("open", "closed", "all").
            limit: Maximum number of issues to return.
            
        Returns:
            List of issues.
            
        Raises:
            GitHubAPIError: If the request fails.
        """
        params = {
            "state": state,
            "per_page": min(limit, 100)  # GitHub API max per page is 100
        }
        
        issues = []
        page = 1
        
        while len(issues) < limit:
            params["page"] = page
            page_issues = self._request("GET", f"/repos/{self.config.repo}/issues", params=params)
            
            if not page_issues:
                break
            
            issues.extend(page_issues)
            page += 1
            
            if len(page_issues) < params["per_page"]:
                break
        
        return issues[:limit]
    
    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new issue using REST API.
        
        Args:
            title: Issue title.
            body: Issue body.
            labels: Issue labels.
            assignees: Issue assignees.
            milestone: Issue milestone number.
            
        Returns:
            Created issue data.
            
        Raises:
            GitHubAPIError: If the request fails.
        """
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        
        if assignees:
            data["assignees"] = assignees
        
        if milestone:
            data["milestone"] = milestone
        
        return self._request("POST", f"/repos/{self.config.repo}/issues", data=data)
    
    def get_issue(self, issue_number: Union[str, int]) -> Dict[str, Any]:
        """Get issue details using REST API.
        
        Args:
            issue_number: Issue number.
            
        Returns:
            Issue details.
            
        Raises:
            GitHubAPIError: If the request fails.
        """
        return self._request("GET", f"/repos/{self.config.repo}/issues/{issue_number}")
    
    def create_label(self, name: str, color: str, description: str = "") -> Dict[str, Any]:
        """Create or update a label using REST API.
        
        Args:
            name: Label name.
            color: Label color (hex code without #).
            description: Label description.
            
        Returns:
            Label details.
            
        Raises:
            GitHubAPIError: If the request fails.
        """
        data = {
            "name": name,
            "color": color,
            "description": description
        }
        
        try:
            # Try to create the label
            return self._request("POST", f"/repos/{self.config.repo}/labels", data=data)
        except GitHubAPIError as e:
            if e.status_code == 422:  # Unprocessable Entity - label already exists
                # Update the label if it already exists
                return self._request("PATCH", f"/repos/{self.config.repo}/labels/{name}", data=data)
            raise
    
    def list_projects(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """List projects using REST API.
        
        Args:
            owner: Project owner (defaults to repo owner).
            
        Returns:
            List of projects.
            
        Raises:
            GitHubAPIError: If the request fails.
            
        Note:
            This uses the GraphQL API since the REST API for Projects is deprecated.
        """
        if not owner:
            owner = self.config.repo.split("/")[0]
        
        # Use GraphQL for projects API
        query = """
        query($owner: String!) {
          user(login: $owner) {
            projectsV2(first: 100) {
              nodes {
                id
                number
                title
                url
                closed
              }
            }
          }
        }
        """
        
        variables = {"owner": owner}
        
        # Use different headers for GraphQL
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/vnd.github.v4+json"
        }
        
        response = self._request(
            "POST", 
            "/graphql", 
            data={"query": query, "variables": variables},
            headers=headers
        )
        
        try:
            projects_data = response.get("data", {}).get("user", {}).get("projectsV2", {}).get("nodes", [])
            
            # Convert the GraphQL format to match the CLI format
            return [
                {
                    "number": project.get("number"),
                    "title": project.get("title"),
                    "url": project.get("url"),
                    "closed": project.get("closed", False),
                    "owner": owner
                }
                for project in projects_data
                if not project.get("closed", False)  # Filter out closed projects
            ]
        except (KeyError, AttributeError) as e:
            logger.error(f"Failed to parse projects response: {str(e)}")
            return []
    
    def create_project(self, title: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project using REST API.
        
        Args:
            title: Project title.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            Created project data.
            
        Raises:
            GitHubAPIError: If the request fails.
            
        Note:
            This uses the GraphQL API since the REST API for Projects is deprecated.
        """
        if not owner:
            owner = self.config.repo.split("/")[0]
        
        # Use GraphQL for projects API
        mutation = """
        mutation($input: CreateProjectV2Input!) {
          createProjectV2(input: $input) {
            projectV2 {
              id
              number
              title
              url
            }
          }
        }
        """
        
        variables = {
            "input": {
                "ownerId": owner,
                "title": title,
                "repositoryId": self.config.repo
            }
        }
        
        # Use different headers for GraphQL
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/vnd.github.v4+json"
        }
        
        response = self._request(
            "POST", 
            "/graphql", 
            data={"query": mutation, "variables": variables},
            headers=headers
        )
        
        try:
            project_data = response.get("data", {}).get("createProjectV2", {}).get("projectV2", {})
            
            return {
                "number": project_data.get("number"),
                "title": title,
                "url": project_data.get("url"),
                "owner": owner
            }
        except (KeyError, AttributeError) as e:
            logger.error(f"Failed to parse project creation response: {str(e)}")
            raise GitHubClientError(f"Failed to create project: {str(e)}")
    
    def add_issue_to_project(
        self,
        project_number: Union[str, int],
        issue_number: Union[str, int],
        owner: Optional[str] = None
    ) -> bool:
        """Add an issue to a project using REST API.
        
        Args:
            project_number: Project number.
            issue_number: Issue number.
            owner: Project owner (defaults to repo owner).
            
        Returns:
            True if successful.
            
        Raises:
            GitHubAPIError: If the request fails.
            
        Note:
            This uses the GraphQL API since the REST API for Projects is deprecated.
        """
        if not owner:
            owner = self.config.repo.split("/")[0]
        
        # First, get the project ID
        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """
        
        variables = {
            "owner": owner,
            "number": int(project_number)
        }
        
        # Use different headers for GraphQL
        headers = {
            "Authorization": f
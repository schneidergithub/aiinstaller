# GitHub Client Module

This module provides a robust, flexible interface for interacting with the GitHub API, supporting both the GitHub CLI and REST API approaches.

## Key Features

- **Dual Implementation**: Supports both GitHub CLI and REST API modes
- **Comprehensive Error Handling**: Specific exception types for different error scenarios
- **Rate Limit Handling**: Detection and appropriate errors for rate limit issues
- **GraphQL Support**: Uses GraphQL for advanced operations like project management
- **Utility Methods**: Convenient helper methods for common operations
- **Thorough Documentation**: Complete docstrings and type annotations

## Architecture

The module follows the **Strategy Pattern** allowing different implementations of the GitHub API interface:

```
GitHubClient
   │
   ├── GitHubImplementationBase (Abstract)
   │      │
   ├──────┼─── GitHubCLIImplementation
   │      │
   └──────┴─── GitHubRESTImplementation
```

This design allows:
- Seamless switching between CLI and REST implementations
- Adding new implementations in the future (e.g., direct GraphQL)
- Consistent interface regardless of the underlying implementation
- Better testability through dependency injection

## Usage Examples

### Basic Configuration

```python
from src.adapters.github.client import GitHubClient, GitHubConfig, GitHubAPIMode

# Configure for GitHub CLI
config = GitHubConfig(
    repo="username/repo",
    mode=GitHubAPIMode.CLI
)

# Or configure for REST API
config = GitHubConfig(
    repo="username/repo",
    token="your-github-token",
    mode=GitHubAPIMode.REST
)

# Create the client
client = GitHubClient(config)
```

### Working with Issues

```python
# List open issues
issues = client.list_issues(state="open", limit=10)

# Create a new issue
issue = client.create_issue(
    title="My Issue Title",
    body="Issue description goes here",
    labels=["bug", "priority:high"]
)

# Get issue details
issue_details = client.get_issue(issue["number"])
```

### Working with Projects

```python
# List projects
projects = client.list_projects()

# Create a new project
project = client.create_project("My Project Board")

# Add an issue to a project
client.add_issue_to_project(
    project_number=project["number"],
    issue_number=issue["number"]
)
```

### Using Utility Methods

```python
# Find or create a project
project, is_new = client.find_or_create_project("Sprint Board")

# Ensure labels exist
labels = [
    {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
    {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"}
]
client.ensure_labels_exist(labels)

# Find issues by label
bugs = client.find_issue_by_label("bug")
```

## Error Handling

The module provides specific exception types:

```python
try:
    client.create_issue(...)
except GitHubAuthError as e:
    print(f"Authentication error: {e}")
except GitHubRateLimitError as e:
    print(f"Rate limit exceeded. Resets at: {e.reset_time}")
except GitHubAPIError as e:
    print(f"API error (Status: {e.status_code}): {e}")
except GitHubClientError as e:
    print(f"General error: {e}")
```

## Design Decisions

1. **Strategy Pattern**: Allows swapping implementations without changing the client interface
2. **GitHub CLI Priority**: Uses GitHub CLI by default for authentication simplicity
3. **REST API Fallback**: Provides REST API implementation for environments without CLI
4. **GraphQL for Projects**: Uses GraphQL API for project operations due to REST API deprecation
5. **Comprehensive Error Types**: Specific exceptions for different error scenarios
6. **Utility Methods**: Common operations as convenience methods

## Dependencies

- `requests`: For REST API HTTP communication
- `json`: For JSON parsing and serialization
- `subprocess`: For GitHub CLI command execution
- `logging`: For consistent logging
- `tempfile`: For handling temporary files with CLI input

## Testing

This module can be tested using:
- Unit tests with mocked responses
- Integration tests with GitHub API (requires token or CLI auth)
- Fake GitHub API server for local testing

## Future Enhancements

- Pagination support for listing operations
- Webhook event handling
- Caching support for frequent requests
- Async API support
- Expanded GraphQL capabilities

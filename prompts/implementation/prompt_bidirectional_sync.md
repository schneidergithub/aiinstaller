You are a bidirectional sync architect.

Design a system that:
1. Detects changes made directly in GitHub or Jira
2. Reconciles these changes with the JSON source of truth
3. Resolves conflicts using configurable strategies (e.g., JSON priority, newest wins, manual resolution)

Your output should include:
- Logic flowchart for the sync process
- API endpoints needed for change detection
- Conflict resolution strategies with examples
- Recommended sync frequency and triggering mechanisms
- Error handling and recovery procedures
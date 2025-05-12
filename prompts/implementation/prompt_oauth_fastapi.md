# 🔐 OAuth 2.0 (3LO) FastAPI Setup

You are an expert in OAuth 2.0 (3LO) for Atlassian. Generate a FastAPI app that:

1. Initiates the OAuth authorization flow to Jira.
2. Handles the redirect from Atlassian with the authorization code.
3. Exchanges the code for access and refresh tokens.
4. Calls the `accessible-resources` endpoint to retrieve the `cloudid`.
5. Stores access, refresh tokens, and cloud ID securely.
6. Exposes a `/refresh` endpoint to rotate tokens.
7. Uses environment variables (.env) for configuration.

# Adding Private Repositories to Poetry Projects

This guide provides comprehensive instructions on how to configure private repositories in Poetry for your Nautobot application development environment, including Docker, Invoke, and local development setups.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Poetry Configuration Methods](#poetry-configuration-methods)
4. [Docker Setup](#docker-setup)
5. [Invoke Tasks Configuration](#invoke-tasks-configuration)
6. [Credentials Management](#credentials-management)
7. [Troubleshooting](#troubleshooting)
8. [Update netnam-cms-core](#updating-netnam-cms-core-from-the-private-repository)
9. [Reference: netnam-cms-core Package Setup](#reference-netnam-cms-core-package-setup)

## Overview

Private repositories in Poetry are used when you have dependencies that are not published on PyPI (Python Package Index). These can include:

- **Private GitLab/GitHub repositories** - Private company packages
- **Internal package repositories** - Private PyPI-compatible indexes
- **Git-based dependencies** - Direct git repositories with SSH or HTTPS authentication

In the nautobot-app-device-onboarding project, the `netnam-cms-core` package is configured as a private Git repository dependency. This guide walks through how to properly configure and manage such dependencies.

## Prerequisites

Before beginning, ensure you have:

- **Poetry** installed (version 1.2 or later)
  ```bash
  # Install Poetry
  curl -sSL https://install.python-poetry.org | python3 -
  
  # Verify installation
  poetry --version
  ```

- **Docker** and **Docker Compose** installed for containerized development
- **Git** configured with credentials for accessing private repositories
- **Invoke** installed for task automation
- Access credentials to your private repository:
  - Git username/token
  - SSH key (optional, for SSH-based authentication)
  - API token (for PyPI-compatible repositories)

## Poetry Configuration Methods

Poetry supports multiple methods for configuring private repositories. Choose the method that best fits your use case.

### Configuring Named Private Repository Sources

```bash
# Add a private PyPI-compatible repository
poetry config repositories.git-netnam-cms-core https://tsd-repo.netnam.vn/netnam-automation/netnam-cms-core.git

# Set credentials for the repository
poetry config http-basic.git-netnam-cms-core username access_token

# Add netnam-cms-core to  `pyproject.toml`
poetry add git+https://tsd-repo.netnam.vn/netnam-automation/netnam-cms-core.git
```


## Docker Setup

When running in Docker, credentials must be passed through build arguments or environment variables since the container doesn't have access to your local Git credentials.

### Setup 1: Using Build Arguments

#### 1.1 Dockerfile Configuration

The `development/Dockerfile` in this project includes support for GitLab credentials:

```dockerfile
# Accept GitLab credentials as build arguments
ARG GITLAB_USERNAME
ARG GITLAB_TOKEN
ARG GITLAB_REPOSITORY

# Configure Git credentials for private packages
RUN git config --global credential.helper store && \
    echo "https://${GITLAB_USERNAME}:${GITLAB_TOKEN}@${GITLAB_REPOSITORY}" > ~/.git-credentials

# Install dependencies with poetry
RUN poetry install --extras all --with dev
```

#### 1.2 Docker Compose Configuration

Update `development/docker-compose.base.yml` to pass build arguments:

```yaml
services:
  nautobot:
    build:
      context: ..
      dockerfile: development/Dockerfile
      args:
        NAUTOBOT_VER: "${NAUTOBOT_VER}"
        PYTHON_VER: "${PYTHON_VER}"
        GITLAB_USERNAME: "${GITLAB_USERNAME}"
        GITLAB_TOKEN: "${GITLAB_TOKEN}"
        GITLAB_REPOSITORY: "${GITLAB_REPOSITORY}"
```

#### 1.3 Setting Environment Variables

Create or update `development/creds.env`:

```bash
# GitLab Credentials for private packages
GITLAB_USERNAME=your-gitlab-username
GITLAB_TOKEN=your-gitlab-api-token
GITLAB_REPOSITORY=tsd-repo.netnam.vn
```

**Example with netnam-cms-core:**

```bash
GITLAB_USERNAME=deploy-bot
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxx
GITLAB_REPOSITORY=tsd-repo.netnam.vn
```

## Invoke Tasks Configuration

The `tasks.py` file contains Invoke tasks that automate Docker and development operations. Here's how to properly configure private repository credentials with Invoke.

### Setup 1: Reading Credentials from `creds.env`

The `docker_compose()` helper in `tasks.py` automatically reads credentials from the `creds.env` file:

```python
def docker_compose(context, command, **kwargs):
    """Helper function for running docker compose with credentials."""
    _ensure_creds_env_file(context)
    
    # Load credentials from creds.env for docker build args
    creds_file = os.path.join(context.nautobot_device_onboarding.compose_dir, "creds.env")
    gitlab_username = ""
    gitlab_token = ""
    gitlab_repository = ""
    
    if os.path.exists(creds_file):
        with open(creds_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITLAB_USERNAME="):
                    gitlab_username = line.split("=", 1)[1].strip('\'"')
                elif line.startswith("GITLAB_TOKEN="):
                    gitlab_token = line.split("=", 1)[1].strip('\'"')
                elif line.startswith("GITLAB_REPOSITORY="):
                    gitlab_repository = line.split("=", 1)[1].strip('\'"')
    
    build_env = {
        "COMPOSE_HTTP_TIMEOUT": context.nautobot_device_onboarding.compose_http_timeout,
        "NAUTOBOT_VER": context.nautobot_device_onboarding.nautobot_ver,
        "PYTHON_VER": context.nautobot_device_onboarding.python_ver,
        "GITLAB_USERNAME": gitlab_username,
        "GITLAB_TOKEN": gitlab_token,
        "GITLAB_REPOSITORY": gitlab_repository,
        **kwargs.pop("env", {}),
    }
    # ... rest of docker compose setup
```

## Credentials Management

### Best Practices

1. **Never commit credentials** to version control
2. **Use `.gitignore`** to exclude credential files:
   ```
   # .gitignore
   creds.env
   development/creds.env
   .env
   .env.local
   ~/.git-credentials
   ~/.config/poetry/auth.toml
   ```

3. **Use API tokens** instead of passwords for Git platforms
4. **Rotate tokens regularly** for security
5. **Use different tokens** for different environments (dev, CI, production)
6. **Document credential sources** for your team

### Creating API Tokens

#### GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Create new token with:
   - **Scopes**: `repo` (full control)
   - **Name**: e.g., "Poetry Dev Bot"
   - **Expiration**: Set appropriate expiration date
3. Copy the token
4. Use in credentials:
   ```
   GIT_USERNAME=your-username
   GIT_PASSWORD=ghp_xxxxxxxxxxxxxxxxxx
   ```

## Troubleshooting

### Issue: "Authentication failed" in Docker build

**Cause**: Credentials not passed to Docker build.

**Solution**:
1. Check `creds.env` file exists with credentials
2. Verify build arguments in `Dockerfile`:
   ```bash
   docker compose build --no-cache nautobot
   ```
3. Check credentials are exported:
   ```bash
   echo $GITLAB_USERNAME
   echo $GITLAB_TOKEN
   ```

### Issue: "poetry.lock conflicts after adding private repo"

**Cause**: Poetry resolver having issues with private package dependencies.

**Solution**:
```bash
# Remove lock file and regenerate
rm poetry.lock

# Install with verbose output
poetry install -vv

# Or update specific package
poetry update netnam-cms-core
```

### Issue: Docker build fails but works locally

**Cause**: Different environments or missing credentials in Docker.

**Solution**:
1. Run same Poetry command locally first:
   ```bash
   poetry install -vv
   ```
2. Check if it's a Docker-specific issue:
   ```bash
   docker compose exec nautobot poetry install -vv
   ```
3. Verify Docker build args:
   ```bash
   docker compose build --build-arg GITLAB_USERNAME=... nautobot
   ```

### Issue: "Cannot locate credentials" in Invoke tasks

**Cause**: `creds.env` file missing or not in expected location.

**Solution**:
```bash
# Copy example credentials file
cp development/creds.example.env development/creds.env

# Edit with your credentials
nano development/creds.env

# Verify Invoke can find it
invoke verify-credentials
```

## Updating `netnam-cms-core` from the Private Repository

#### 1. In the `netnam-cms-core` Repository
- Open `pyproject.toml` and increment the version number.
- Commit the change:
    ```bash
    git commit -am "Bump netnam-cms-core version"
    ```
- Push the update to the remote repository:
    ```bash
    git push
    ```

#### 2. In Your Current Project
- Update the package reference:
    ```bash
    poetry update netnam-cms-core
    ```
- Regenerate the lock file:
    ```bash
    poetry lock
    ```
- Install updated dependencies:
    ```bash
    poetry install
    ```
- Rebuild the project environment:
    ```bash
    invoke build
    ```


## Reference: netnam-cms-core Package Setup

This project uses `netnam-cms-core` as a private Git dependency. Here's the exact setup used:

### Current Configuration

#### `pyproject.toml`

```toml
[tool.poetry.dependencies]
# ... other dependencies ...

#netnam-cms-core
netnam-cms-core = {git = "https://tsd-repo.netnam.vn/netnam-automation/netnam-cms-core.git"}
```

**Repository Details**:
- **URL**: `https://tsd-repo.netnam.vn/netnam-automation/netnam-cms-core.git`
- **Type**: Private GitLab repository
- **Access**: HTTPS with credentials or SSH
- **Authentication**: GitLab personal access token

### Docker Setup for netnam-cms-core

#### `development/Dockerfile`

The Dockerfile includes specific steps for netnam-cms-core:

```dockerfile
# Accept GitLab credentials as build arguments
ARG GITLAB_USERNAME
ARG GITLAB_TOKEN
ARG GITLAB_REPOSITORY

# Configure Git credentials for private packages
RUN git config --global credential.helper store && \
    echo "https://${GITLAB_USERNAME}:${GITLAB_TOKEN}@${GITLAB_REPOSITORY}" > ~/.git-credentials

# Install the app with all dependencies
RUN poetry install --extras all --with dev
```

#### `development/creds.env` (Example)

```bash
# GitLab Credentials for netnam-cms-core
GITLAB_USERNAME=deploy-bot
GITLAB_TOKEN=glpat-xyz123abc...
GITLAB_REPOSITORY=tsd-repo.netnam.vn
```

### Tasks Configuration

The `tasks.py` automatically handles credentials:

```python
# Extracted from the docker_compose helper function
creds_file = os.path.join(context.nautobot_device_onboarding.compose_dir, "creds.env")
gitlab_username = ""
gitlab_token = ""
gitlab_repository = ""

if os.path.exists(creds_file):
    with open(creds_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GITLAB_USERNAME="):
                gitlab_username = line.split("=", 1)[1].strip('\'"')
            elif line.startswith("GITLAB_TOKEN="):
                gitlab_token = line.split("=", 1)[1].strip('\'"')
            elif line.startswith("GITLAB_REPOSITORY="):
                gitlab_repository = line.split("=", 1)[1].strip('\'"')

build_env = {
    "GITLAB_USERNAME": gitlab_username,
    "GITLAB_TOKEN": gitlab_token,
    "GITLAB_REPOSITORY": gitlab_repository,
    # ... other env vars
}
```


## Additional Resources

- [Poetry Documentation - Dependency Specification](https://python-poetry.org/docs/dependency-specification/)
- [Poetry Documentation - Repositories](https://python-poetry.org/docs/repositories/)
- [Poetry Documentation - Authentication](https://python-poetry.org/docs/authentication/)
- [Git Documentation - Credentials](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)
- [GitHub - Creating Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitLab - Personal Access Tokens](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)

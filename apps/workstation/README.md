# Workstation Containers

Life and dev containers for your daily working environment.

## Overview

This compose app defines two containers following a trust gradient model:

| Container | Zone     | Trust Level | Purpose |
|-----------|----------|-------------|---------|
| **life**  | operator | supervised  | LLM tooling + workflows (you're watching) |
| **dev**   | builder  | full        | Development for system changes |

## Trust Gradient

```
agent < life < dev
```

- **agent**: Restricted zone (not defined here) - limited /workspace access
- **life**: Operator zone - supervised LLM tooling, read-only agent access
- **dev**: Builder zone - full access, can modify system capabilities

## Deployment

```bash
# Configure vmctl to use this app directory
vmctl config --app-dir /opt/apps/workstation

# Deploy the containers
vmctl deploy

# Or deploy directly
vmctl deploy --app-dir /opt/apps/workstation
```

## Services

### life (port 8080)

Operator environment for supervised LLM work:
- code-server web IDE
- Claude Code CLI
- Python, Node.js, gcloud
- Read-only access to agent outputs

### dev (port 8081)

Builder environment for development:
- code-server web IDE
- Claude Code CLI
- Full development toolchain
- Docker CLI (host socket optional)
- Read/write access to agent area

## Volumes

```
/workspace          → /mnt/home/user/workspace (shared)
/agent/state        → /mnt/home/user/agent-data/state
/agent/outbox       → /mnt/home/user/agent-data/outbox
/agent/repo         → /mnt/home/user/agent-data/repo
```

## Management

```bash
# Check container status
vmctl ps

# View logs
vmctl logs         # All services
vmctl logs life    # Life container only
vmctl logs dev     # Dev container only

# Restart services
vmctl restart
vmctl restart life
vmctl restart dev
```

## Customization

### Init Scripts

Place init scripts in your workspace:
- `/workspace/.life/init.sh` - Runs on life container start
- `/workspace/.dev/init.sh` - Runs on dev container start

### Docker Socket (dev only)

To enable Docker commands in the dev container, add to compose.yml:

```yaml
dev:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

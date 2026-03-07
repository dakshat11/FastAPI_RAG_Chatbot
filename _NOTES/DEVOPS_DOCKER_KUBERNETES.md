# Docker, Docker Compose & Kubernetes — DevOps Documentation
### In the context of the RAG Voice Bot — `E:\Fastapi_voicebot`

---

## Table of Contents

1. [What Problem Docker Solves](#1-what-problem-docker-solves)
2. [Core Docker Concepts](#2-core-docker-concepts)
3. [Dockerfile — Building Your Image](#3-dockerfile)
4. [Docker Compose — Running Multiple Containers](#4-docker-compose)
5. [Dockerfile vs Docker Compose — When to Use Which](#5-dockerfile-vs-docker-compose)
6. [Docker Compose Workflow — Step by Step](#6-docker-compose-workflow)
7. [Key Docker Commands You Must Know](#7-key-docker-commands)
8. [What Docker Compose Gives You](#8-what-docker-compose-gives-you)
9. [Linux and Server Management Essentials](#9-linux-and-server-management)
10. [How This App Would Be Deployed — Overview](#10-deployment-overview)
11. [From Docker Compose to Kubernetes](#11-from-docker-compose-to-kubernetes)
12. [Kubernetes Core Concepts](#12-kubernetes-core-concepts)
13. [AKS — Azure Kubernetes Service](#13-aks)
14. [Interview Topics to Know](#14-interview-topics)

---

## 1. What Problem Docker Solves

Without Docker, deploying this voice bot means:
- Installing Python 3.12 on the server
- Installing all packages from `pyproject.toml`
- Setting environment variables
- Making sure the server's OS matches your dev machine

If it works on your laptop but not the server — "it works on my machine" — the cause is always a difference in environment. Docker eliminates this by packaging the application and its entire environment (OS, Python version, packages, config) into one unit called a **container**.

```
WITHOUT DOCKER                    WITH DOCKER
──────────────                    ───────────
Your laptop:                      Your laptop:
  Python 3.12 ✅                    Container:
  Package A v1.2 ✅                   Python 3.12
  Package B v3.0 ✅                   Package A v1.2
                                      Package B v3.0
Server:
  Python 3.11 ❌                  Server:
  Package A v1.0 ❌                 Same container ✅
  Package B missing ❌
```

The container runs identically on your laptop, a colleague's machine, a test server, and a production cloud — because it carries its environment with it.

---

## 2. Core Docker Concepts

### Image
A read-only blueprint. The recipe for a container. Built from a `Dockerfile`.
Think of it like a class definition in Python.

### Container
A running instance of an image. You can run 10 containers from one image simultaneously.
Think of it like an object instantiated from a class.

### Dockerfile
A text file with instructions to build an image. Step by step — start from a base OS,
install packages, copy code, set startup command.

### Docker Compose
A tool for defining and running **multiple containers together**. Your voice bot needs
the FastAPI app AND a PostgreSQL database AND (in future) a Redis cache — Compose
starts all of them with one command and wires them together.

### Volume
A way to persist data outside the container. Containers are ephemeral — when they
stop, their internal filesystem resets. A volume mounts a persistent storage location
into the container. Your `chatbot.db` (or PostgreSQL data) lives in a volume so it
survives container restarts.

### Network
Docker Compose creates a private network for your containers. The `api` container
reaches the `postgres` container by hostname `postgres` — no IP addresses needed.
Nothing outside the network can see these internal hostnames.

### Registry
A storage service for Docker images. Docker Hub is the public registry. Azure Container
Registry (ACR) is the private registry you use with AKS. You push images to a registry
and pull them on servers.

---

## 3. Dockerfile

The Dockerfile describes how to build your application's image.
Every line creates a new layer. Docker caches layers — if a line hasn't changed,
it reuses the cached result (fast rebuilds).

### This project's Dockerfile explained line by line

```dockerfile
# ── Stage 1: Builder ─────────────────────────────────────────────
# A separate stage just to install dependencies.
# Why? faiss-cpu and psycopg need build tools (gcc) to compile.
# We don't want gcc in the final image — it bloats the size and
# increases the attack surface.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install uv

# Copy dependency manifest BEFORE the application code.
# Key insight: Docker caches each layer. If only your code changes
# (not pyproject.toml), this layer is cached and packages are NOT
# reinstalled. This makes rebuilds fast — seconds instead of minutes.
COPY ../pyproject.toml ./

# Install all packages into a venv inside the image
RUN uv venv .venv && uv sync --no-dev

# ── Stage 2: Runtime ─────────────────────────────────────────────
# Start fresh from a clean slim image.
# Copy ONLY the installed venv from the builder — no gcc, no build tools.
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY .. .

# Put the venv's Python first in PATH so it's used by default
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### Why `--host 0.0.0.0` matters
By default uvicorn listens on `127.0.0.1` (localhost only). Inside a container,
`127.0.0.1` means "inside this container only" — nothing outside can reach it.
`0.0.0.0` means "accept connections from any network interface" — Docker's port
mapping can then forward traffic from your host machine into the container.

### Why multi-stage builds
Single stage:
```
python:3.12-slim base  → add build tools → install packages → copy code
Final image size: ~800MB (includes gcc, headers, build tools)
```
Multi-stage:
```
builder stage: install packages (gcc used here, stays in this stage)
runtime stage: copy only the .venv — no build tools travel forward
Final image size: ~200MB
```

---

## 4. Docker Compose

Docker Compose manages multiple containers as a single application.
Your voice bot in production needs:

```
┌─────────────────────────────────────────────────┐
│              Docker Compose                      │
│                                                  │
│  ┌──────────────┐      ┌──────────────────────┐  │
│  │  api         │─────▶│  postgres            │  │
│  │  FastAPI app │      │  PostgreSQL 16        │  │
│  │  port 8000   │      │  port 5432 (internal) │  │
│  └──────────────┘      └──────────────────────┘  │
│                                                  │
│  Shared network: voicebot_network                │
│  Volumes: postgres_data (persistent DB files)    │
└─────────────────────────────────────────────────┘
```

### `docker-compose.yml` for this project

```yaml
services:

  postgres:
    image: postgres:16-alpine        # official PostgreSQL image, alpine = smaller
    container_name: voicebot_postgres
    environment:
      POSTGRES_USER: voicebot_user
      POSTGRES_PASSWORD: strongpassword
      POSTGRES_DB: voicebot
    volumes:
      - postgres_data:/var/lib/postgresql/data   # persist DB files
    ports:
      - "5432:5432"        # expose to host for debugging (remove in production)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U voicebot_user -d voicebot"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: voicebot_api
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      # Override DATABASE_URL to use the postgres service by hostname
      # "postgres" here is the service name above — Docker resolves it
      - DATABASE_URL=postgresql://voicebot_user:strongpassword@postgres:5432/voicebot
    depends_on:
      postgres:
        condition: service_healthy    # wait until postgres passes health check
    restart: unless-stopped

volumes:
  postgres_data:     # named volume — Docker manages this, survives container removal
```

### Key things happening here

**`depends_on` with `condition: service_healthy`**
The `api` container will not start until `postgres` passes its health check.
Without this, the API starts, tries to connect to PostgreSQL, PostgreSQL isn't
ready yet, and you get a connection error at startup.

**Service name as hostname**
The `api` container connects to PostgreSQL using the hostname `postgres`
(the service name). Docker's internal DNS resolves `postgres` to the
PostgreSQL container's IP automatically. You never deal with IP addresses.

**Named volume `postgres_data`**
`docker compose down` removes containers but NOT named volumes.
`docker compose down -v` removes containers AND volumes (deletes all data).
This separation protects production data from accidental deletion.

**`env_file: .env`**
Your API keys are never baked into the image. The `.env` file is read at
runtime and injected as environment variables. The image itself contains no secrets.

---

## 5. Dockerfile vs Docker Compose — When to Use Which

This is a common interview question. The answer is always: **both, for different purposes.**

| | Dockerfile | Docker Compose |
|---|---|---|
| What it does | Builds ONE image | Runs MULTIPLE containers together |
| Scope | Single service | Entire application stack |
| Output | An image | Running containers |
| Used for | `docker build` | `docker compose up` |
| Analogy | Recipe for one dish | Full restaurant menu service |

**Rule of thumb:**
- You always need a `Dockerfile` for your custom application code
- You need `Docker Compose` when your application has more than one component
  (app + database, app + cache, app + message queue)
- In production Kubernetes replaces Compose — but Compose is still used for local dev

**For this project specifically:**
- `Dockerfile` — builds the FastAPI voice bot image
- `docker-compose.yml` — starts the FastAPI app AND PostgreSQL together,
  wires them with the right environment variables and network

---

## 6. Docker Compose Workflow — Step by Step

```
Developer runs: docker compose up --build
                        │
                        ▼
        1. Docker reads docker-compose.yml
                        │
                        ▼
        2. Builds images that have a `build:` section
           (runs the Dockerfile for the `api` service)
                        │
                        ▼
        3. Pulls images that have an `image:` section
           (downloads postgres:16-alpine from Docker Hub)
                        │
                        ▼
        4. Creates the private network (voicebot_network)
                        │
                        ▼
        5. Creates named volumes (postgres_data)
                        │
                        ▼
        6. Starts containers in dependency order
           postgres starts first (api depends_on postgres)
                        │
                        ▼
        7. postgres health check runs every 10s
           pg_isready checks if PostgreSQL accepts connections
                        │
                        ▼
        8. Once postgres is healthy, api container starts
           FastAPI app runs, connects to postgres by hostname
                        │
                        ▼
        9. Both containers running, sharing the network
           API available at http://localhost:8000
           Swagger UI at http://localhost:8000/docs
```

### What happens on code change
```bash
# Change a Python file, then:
docker compose up --build

# Docker rebuilds only the api image (Dockerfile runs again)
# postgres image is unchanged — not rebuilt, not restarted
# Only the api container is recreated
```

### What happens on `docker compose down`
```
Containers stopped and removed ✅
Network removed ✅
Named volumes PRESERVED ✅  ← postgres_data survives, your data is safe
Images preserved ✅          ← no need to rebuild next time
```

---

## 7. Key Docker Commands You Must Know

```bash
# ── BUILD ────────────────────────────────────────────────
# Build an image from Dockerfile in current directory
docker build -t voicebot:latest .

# Build and tag with a registry path (for pushing to ACR)
docker build -t myregistry.azurecr.io/voicebot:v1.0 .

# ── RUN ──────────────────────────────────────────────────
# Run a container from an image
docker run -p 8000:8000 voicebot:latest

# Run with env file
docker run -p 8000:8000 --env-file .env voicebot:latest

# Run in detached mode (background)
docker run -d -p 8000:8000 voicebot:latest

# ── COMPOSE ──────────────────────────────────────────────
# Start all services, rebuild images
docker compose up --build

# Start in background
docker compose up -d

# Stop and remove containers (keep volumes)
docker compose down

# Stop, remove containers AND volumes (deletes all data)
docker compose down -v

# View logs for all services
docker compose logs -f

# View logs for one service
docker compose logs -f api

# Restart one service without rebuilding
docker compose restart api

# ── INSPECT ──────────────────────────────────────────────
# List running containers
docker ps

# List all containers including stopped
docker ps -a

# List images
docker images

# Inspect container resource usage
docker stats

# Shell into a running container (like SSH into it)
docker exec -it voicebot_api bash

# ── CLEAN UP ─────────────────────────────────────────────
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove everything unused (containers, images, networks, cache)
docker system prune -a
```

> **Important — `docker exec -it <container> bash`**
> This gives you a shell inside a running container. Essential for debugging.
> You can inspect files, check environment variables, run Python, ping other
> services. This is your main debugging tool in production.

---

## 8. What Docker Compose Gives You

### For development
- **One command setup** — `docker compose up` and the entire stack is running.
  A new developer clones the repo and has a working environment in minutes.
- **Environment parity** — everyone on the team runs the exact same versions
  of every dependency.
- **Isolated environments** — your voice bot's PostgreSQL doesn't conflict with
  another project's PostgreSQL running on the same machine.

### For this project specifically
- PostgreSQL runs in a container — no manual install, no version conflicts
- The API connects to PostgreSQL using the service hostname `postgres` — works
  identically on every developer's machine
- API keys stay in `.env` — never baked into images

### What it does NOT give you (why Kubernetes comes next)
- **No automatic scaling** — if your voice bot gets 1000 simultaneous users,
  Compose can't automatically spin up more API containers
- **No self-healing** — if the API container crashes, Compose won't restart it
  on a different machine
- **Single machine only** — Compose runs on one server. If that server goes down,
  everything goes down.
- **No rolling updates** — deploying a new version takes the app offline momentarily

---

## 9. Linux and Server Management Essentials

When your containers run on a Linux server (which they will in production),
these are the commands and concepts you need.

### File system
```bash
ls -la               # list files with permissions
pwd                  # print current directory
cd /app              # change directory
cat filename         # print file contents
tail -f app.log      # follow a log file in real time (most useful)
grep "ERROR" app.log # search for errors in logs
find / -name "*.env" # find files by name
chmod 600 .env       # set file permissions (owner read/write only)
```

### Process management
```bash
ps aux               # list all running processes
ps aux | grep uvicorn  # find your server process
kill -9 <PID>        # force kill a process by its ID
top                  # real-time process monitor (like Task Manager)
htop                 # better version of top (install separately)
```

### Network
```bash
curl http://localhost:8000/health    # test an endpoint from the server
netstat -tlnp                        # list what's listening on which port
ss -tlnp                             # modern replacement for netstat
ping postgres                        # test connectivity between containers
```

### Docker on Linux servers
```bash
systemctl status docker        # check if Docker daemon is running
systemctl start docker         # start Docker
systemctl enable docker        # start Docker automatically on reboot
journalctl -u docker -f        # view Docker daemon logs
```

### Environment and secrets
```bash
printenv                       # print all environment variables
echo $DATABASE_URL             # print one variable
export MY_VAR=value            # set a variable for this session
```

> **Key security rule on Linux servers:**
> `.env` files must have `chmod 600 .env` — readable only by the owner.
> Never `chmod 777` (world-readable) a file containing API keys.

---

## 10. Deployment Overview

### Current state (development)
```
Your laptop
└── docker compose up
    ├── api container (FastAPI)
    └── postgres container (PostgreSQL)
```

### Next step (single server / staging)
```
Linux VM (Azure VM, AWS EC2, DigitalOcean Droplet)
└── docker compose up -d
    ├── api container
    ├── postgres container
    └── nginx container (reverse proxy, SSL termination)

Users → nginx (port 443, HTTPS) → api (port 8000, internal)
```

### Production step (Kubernetes / AKS)
```
Azure Kubernetes Service (AKS)
├── Node pool (multiple Linux VMs managed by Azure)
│   ├── Node 1
│   │   ├── api Pod (replica 1)
│   │   └── api Pod (replica 2)
│   └── Node 2
│       ├── api Pod (replica 3)
│       └── postgres Pod
├── Azure Load Balancer (distributes traffic across api pods)
├── Azure Container Registry (stores your Docker images)
└── Azure Database for PostgreSQL (managed, outside the cluster)

Users → Load Balancer → any api Pod → Azure PostgreSQL
```

---

## 11. From Docker Compose to Kubernetes

### What stays the same
- Your Docker image (built from the same Dockerfile)
- Environment variables (moved to Kubernetes Secrets/ConfigMaps)
- The application code — untouched

### What changes
- `docker-compose.yml` is replaced by Kubernetes YAML manifests
- Container management moves from Compose to Kubernetes
- Scaling is automatic, not manual

### The conceptual mapping

| Docker Compose | Kubernetes equivalent |
|---|---|
| `service` | `Deployment` + `Service` |
| `image` | image pulled from ACR |
| `ports` | `Service` of type LoadBalancer |
| `environment` | `ConfigMap` (non-secret) / `Secret` (API keys) |
| `volumes` | `PersistentVolumeClaim` |
| `depends_on` | `initContainers` or liveness probes |
| `restart: unless-stopped` | Built into Deployments by default |
| `docker compose up --scale api=3` | `replicas: 3` in Deployment spec |

---

## 12. Kubernetes Core Concepts

### Pod
The smallest unit in Kubernetes. One or more containers that run together on the
same node and share a network. In practice, one Pod = one container for most apps.
Pods are ephemeral — they get created and destroyed constantly. Never store state in a Pod.

### Deployment
Manages a set of identical Pods. You tell it "I want 3 replicas of the api container."
It creates 3 Pods and continuously ensures 3 are always running. If one crashes,
it creates a replacement automatically. This is self-healing.

```yaml
# Deployment for the voice bot api
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voicebot-api
spec:
  replicas: 3                # run 3 copies simultaneously
  selector:
    matchLabels:
      app: voicebot-api
  template:
    metadata:
      labels:
        app: voicebot-api
    spec:
      containers:
      - name: api
        image: myregistry.azurecr.io/voicebot:v1.0
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:       # read from Kubernetes Secret, not hardcoded
              name: voicebot-secrets
              key: openai-api-key
```

### Service
Pods have random IP addresses that change when they're replaced.
A Service gives a stable hostname and IP that always routes to healthy Pods.
It's the internal load balancer within the cluster.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: voicebot-api-service
spec:
  selector:
    app: voicebot-api          # route to all pods with this label
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer           # creates an Azure Load Balancer with a public IP
```

### ConfigMap
Non-sensitive configuration stored in Kubernetes.
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: voicebot-config
data:
  MODEL_NAME: "gpt-4o-mini"
  PINECONE_INDEX_NAME: "voicebot"
```

### Secret
Sensitive configuration (API keys, passwords) stored encrypted in Kubernetes.
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: voicebot-secrets
type: Opaque
data:
  openai-api-key: <base64-encoded-key>
  pinecone-api-key: <base64-encoded-key>
```

> **Important:** Never put secrets in `ConfigMap`. Never hardcode secrets in
> Deployment YAML. Always use `Secret` with `secretKeyRef`.

### Ingress
The external entry point for HTTP/HTTPS traffic. Routes requests to the right
Service based on the hostname or path. Also handles SSL termination.

```yaml
# Route voicebot.yourdomain.com to the api service
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: voicebot-ingress
spec:
  rules:
  - host: voicebot.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: voicebot-api-service
            port:
              number: 80
```

### PersistentVolumeClaim (PVC)
Requests persistent storage for a Pod. For PostgreSQL data that must survive
Pod restarts. In AKS, this provisions an Azure Disk automatically.

### Namespace
Logical isolation within a cluster. Separate dev, staging, and production
environments in the same cluster:
```
cluster
├── namespace: dev
│   └── voicebot-api (3 replicas)
├── namespace: staging
│   └── voicebot-api (1 replica)
└── namespace: production
    └── voicebot-api (5 replicas)
```

---

## 13. AKS — Azure Kubernetes Service

AKS is Microsoft Azure's managed Kubernetes service. "Managed" means Azure handles
the Kubernetes control plane (the brain of the cluster) — you only manage the
worker nodes (the machines running your containers).

### AKS deployment workflow for this project

```
Step 1 — Build and push image
──────────────────────────────
docker build -t myregistry.azurecr.io/voicebot:v1.0 .
docker push myregistry.azurecr.io/voicebot:v1.0

  Your laptop builds the image
  Pushes to Azure Container Registry (ACR)
  AKS pulls from ACR when deploying Pods


Step 2 — Create AKS cluster
─────────────────────────────
az aks create \
  --resource-group myResourceGroup \
  --name voicebotCluster \
  --node-count 2 \
  --generate-ssh-keys

  Azure provisions 2 Linux VMs as worker nodes
  Kubernetes control plane is managed by Azure (free)
  You get a kubectl config to talk to the cluster


Step 3 — Connect kubectl to AKS
────────────────────────────────
az aks get-credentials --resource-group myResourceGroup --name voicebotCluster
kubectl get nodes    # verify you can see your 2 nodes


Step 4 — Apply manifests
──────────────────────────
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

  Kubernetes reads the YAML files
  Creates Pods, Services, Ingress as specified
  Pulls image from ACR
  Starts your containers


Step 5 — Verify
────────────────
kubectl get pods                      # see your running pods
kubectl get services                  # see the public IP
kubectl logs <pod-name>               # see app logs
kubectl describe pod <pod-name>       # debug a failing pod
```

### How AKS orchestrates the containers

```
You run: kubectl apply -f deployment.yaml (replicas: 3)
                    │
                    ▼
         Kubernetes Scheduler decides
         which node each Pod goes on
         (based on available CPU/RAM)
                    │
              ┌─────┴─────┐
              ▼           ▼
           Node 1       Node 2
         ┌───────┐     ┌───────┐
         │ Pod 1 │     │ Pod 2 │
         │ Pod 3 │     └───────┘
         └───────┘

Azure Load Balancer distributes
incoming requests across all 3 Pods
```

**Self-healing in action:**
```
Pod 2 crashes
      │
      ▼
Kubernetes detects: "I want 3 replicas, I only have 2"
      │
      ▼
Kubernetes creates a new Pod on Node 2 automatically
      │
      ▼
Back to 3 replicas — user never noticed the crash
```

**Rolling update (zero downtime deployment):**
```
You push new image version v1.1 and run:
kubectl set image deployment/voicebot-api api=myregistry.azurecr.io/voicebot:v1.1

Kubernetes replaces Pods one at a time:
  - Kill Pod 1 (v1.0)
  - Start Pod 1 (v1.1) — wait until healthy
  - Kill Pod 2 (v1.0)
  - Start Pod 2 (v1.1) — wait until healthy
  - Kill Pod 3 (v1.0)
  - Start Pod 3 (v1.1)

At no point are all Pods down simultaneously.
Users never see downtime.
```

### Key AKS-specific things

**Azure Container Registry (ACR)**
Private Docker registry. Your images live here. AKS pulls from ACR using
a managed identity — no credentials needed in the manifest.

**Managed PostgreSQL (Azure Database for PostgreSQL)**
In production, don't run PostgreSQL inside Kubernetes as a Pod.
Use Azure's managed PostgreSQL service instead. It's outside the cluster,
handles backups, failover, and scaling automatically. Your app just uses
the `DATABASE_URL` connection string.

**Horizontal Pod Autoscaler (HPA)**
Automatically increases/decreases replicas based on CPU usage:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: voicebot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: voicebot-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70   # scale up when CPU > 70%
```

---

## 14. Interview Topics to Know

### Docker questions

**Q: What is the difference between an image and a container?**
An image is a read-only blueprint built from a Dockerfile. A container is a
running instance of an image. Multiple containers can run from one image simultaneously.

**Q: What is a multi-stage build and why use it?**
A Dockerfile with multiple `FROM` statements. Each stage can copy artifacts from
previous stages. Used to separate build environment (needs gcc, compilers) from
runtime environment (needs only the compiled output). Results in smaller, more
secure final images.

**Q: How do you persist data in Docker?**
Named volumes (`volumes: postgres_data:`) or bind mounts. Named volumes are managed
by Docker and survive `docker compose down`. Bind mounts link a host directory
directly into the container.

**Q: How do you pass secrets to a container?**
Never bake them into the image. Use `env_file: .env` in Compose for development.
Use Kubernetes Secrets in production, injected as environment variables or mounted
as files.

**Q: What does `depends_on` do and what doesn't it do?**
It controls container start ORDER — postgres starts before api. It does NOT wait
for the service inside the container to be ready. Use `condition: service_healthy`
with a `healthcheck` to wait for actual readiness.

### Kubernetes questions

**Q: What is the difference between a Pod and a Deployment?**
A Pod is one running instance. A Deployment manages a desired number of Pod replicas
and ensures that many are always running. You never create Pods directly in production
— always through a Deployment.

**Q: What is a Service in Kubernetes?**
A stable network endpoint that routes traffic to Pods. Pods have ephemeral IPs that
change — a Service provides a permanent hostname/IP that always routes to healthy Pods.

**Q: How does Kubernetes do zero-downtime deployments?**
Rolling updates — replaces Pods one at a time, waiting for the new one to be healthy
before killing the old one. At no point are all Pods unavailable simultaneously.

**Q: What is the difference between ConfigMap and Secret?**
ConfigMap is for non-sensitive config (model names, index names). Secret is for
sensitive data (API keys, passwords) — stored encrypted in etcd. Both are injected
into Pods as environment variables or files.

**Q: What is AKS?**
Azure Kubernetes Service — a managed Kubernetes offering where Azure handles the
control plane (API server, scheduler, etcd). You manage only the worker nodes and
your application manifests. Reduces operational overhead significantly.

---

*This document covers the DevOps layer of `E:\Fastapi_voicebot`.*
*The progression is: local dev → Docker Compose → single server → AKS.*
*Each step adds reliability, scalability, and automation.*

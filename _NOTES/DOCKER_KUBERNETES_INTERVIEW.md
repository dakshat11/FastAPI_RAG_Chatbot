# Docker & Kubernetes — Interview Q&A
### Focused on what actually gets asked — in context of the RAG Voice Bot project

---

## Docker Questions

---

**Q: What is Docker and why do we use it?**

Docker packages your application and its entire environment (Python version, packages,
OS libraries) into a container. The container runs identically on your laptop, a
colleague's machine, and a production server. It solves "it works on my machine" —
the most common deployment problem.

---

**Q: What is the difference between an image and a container?**

An image is a read-only blueprint — like a class definition. A container is a running
instance of that image — like an object. You can run 10 containers from one image
simultaneously. When a container stops, the image is untouched.

---

**Q: What is a Dockerfile?**

A text file with step-by-step instructions to build an image. Every line is a layer.
Docker caches layers — if your code changes but `pyproject.toml` doesn't, packages
are NOT reinstalled. This is why you always copy the dependency file before copying
your code:

```dockerfile
COPY ../pyproject.toml ./   # copied first, cached separately
RUN uv sync              # only reruns if pyproject.toml changed
COPY .. .                 # code copied last
```

---

**Q: What is a multi-stage build?**

A Dockerfile with two `FROM` statements. First stage installs packages (needs build
tools like gcc). Second stage copies only the installed packages — no gcc, no build
tools in the final image. Result: smaller and more secure image.

```dockerfile
FROM python:3.12-slim AS builder   # stage 1 — build
RUN uv sync

FROM python:3.12-slim AS runtime   # stage 2 — run
COPY --from=builder /app/.venv .   # only copy the output, not the build tools
```

---

**Q: What is Docker Compose and when do you use it?**

Docker Compose runs multiple containers together as one application. You use it when
your app needs more than one service — in this project: FastAPI + PostgreSQL. One
`docker-compose.yml` defines both, and `docker compose up` starts everything with one
command.

---

**Q: Do you need to run the Dockerfile separately before docker compose?**

No. `docker compose up --build` builds the image AND starts the containers in one
command. You only run `docker build` separately when you want to push an image to a
registry (like Azure Container Registry) without starting containers.

---

**Q: What does `depends_on` do — and what doesn't it do?**

It controls start ORDER — postgres starts before the api. It does NOT wait for the
service inside to be ready. PostgreSQL takes a few seconds to fully initialise after
the container starts. Without a health check, the API starts, tries to connect,
PostgreSQL isn't ready yet, and crashes. The fix:

```yaml
depends_on:
  postgres:
    condition: service_healthy   # waits for health check to pass, not just container start
```

---

**Q: What is a volume and why do you need it?**

Containers are ephemeral — their filesystem resets when they stop. A volume is
persistent storage outside the container. PostgreSQL data goes in a volume so it
survives container restarts and `docker compose down`. Named volumes are NOT deleted
by `docker compose down` — only by `docker compose down -v`.

---

**Q: How do you pass secrets to a container? What NOT to do?**

Never bake secrets into the image. Use `env_file: .env` in Compose — the `.env` file
is read at runtime and injected as environment variables. The image itself contains no
secrets and can be shared safely. In production Kubernetes, use Kubernetes Secrets
instead of `.env` files.

---

**Q: What does `--host 0.0.0.0` mean in the uvicorn command?**

By default uvicorn listens on `127.0.0.1` — inside a container that means "only inside
this container." Nothing from outside can reach it. `0.0.0.0` means "accept connections
from any network interface" — Docker's port mapping can then forward traffic from the
host machine into the container.

---

**Q: What is the difference between Dockerfile and Docker Compose?**

| Dockerfile | Docker Compose |
|---|---|
| Builds ONE image | Runs MULTIPLE containers |
| Single service | Entire app stack |
| `docker build` | `docker compose up` |
| The recipe | The full meal service |

You always need both for a real application.

---

**Q: What happens to data when a container is removed?**

Any data written inside the container's filesystem is lost when the container is
removed. This is why PostgreSQL data must be stored in a named volume — the volume
lives outside the container and persists across restarts, recreations, and
`docker compose down`. Only `docker compose down -v` removes volumes.

---

**Q: What is a Docker network?**

Docker Compose creates a private network for all services defined in the compose file.
Containers on this network reach each other by service name as hostname — the `api`
container connects to PostgreSQL using `postgres` as the hostname (the service name),
not an IP address. Nothing outside the network sees these internal hostnames.

---

**Q: Key Docker commands you must know**

```bash
docker compose up --build        # build images + start all containers
docker compose up -d             # start in background (detached)
docker compose down              # stop + remove containers (keep volumes)
docker compose down -v           # stop + remove containers AND volumes
docker compose logs -f api       # follow logs for the api service
docker exec -it voicebot_api bash  # shell into a running container (main debug tool)
docker ps                        # list running containers
docker images                    # list local images
docker system prune -a           # clean up everything unused
```

---

## Kubernetes Questions

---

**Q: Why Kubernetes after Docker Compose?**

Docker Compose runs on one machine. If that machine goes down, everything goes down.
It cannot automatically scale when traffic spikes and cannot restart containers on a
different machine if one crashes. Kubernetes solves all three: multi-machine,
auto-scaling, self-healing.

---

**Q: What is a Pod?**

The smallest unit in Kubernetes. One running container (usually). Pods are ephemeral —
they get created and destroyed constantly. Never store data in a Pod's filesystem.
Each Pod gets its own IP but that IP changes when the Pod is replaced — this is why
you need a Service in front of Pods.

---

**Q: What is a Deployment?**

Manages a set of identical Pods. You declare "I want 3 replicas." It creates 3 Pods.
If one crashes, it creates a replacement automatically. This is self-healing. You
never create Pods directly in production — always through a Deployment.

```yaml
spec:
  replicas: 3        # always keep 3 pods running
  template:
    spec:
      containers:
      - name: api
        image: myregistry.azurecr.io/voicebot:v1.0
```

---

**Q: What is a Service in Kubernetes?**

A stable hostname and IP that always routes to healthy Pods. Since Pod IPs change
every time a Pod is replaced, a Service gives a permanent address. It is the internal
load balancer. A Service of type `LoadBalancer` creates a public IP (Azure Load
Balancer in AKS) so users can reach your app from the internet.

---

**Q: What is the difference between ConfigMap and Secret?**

ConfigMap stores non-sensitive config (model names, index names). Secret stores
sensitive data (API keys, passwords) — stored encrypted in Kubernetes. Both get
injected into Pods as environment variables. Never put API keys in ConfigMap.

```yaml
# ConfigMap — non-sensitive
data:
  MODEL_NAME: "gpt-4o-mini"
  PINECONE_INDEX_NAME: "voicebot"

# Secret — sensitive (base64 encoded values)
data:
  openai-api-key: <base64-encoded-value>
  pinecone-api-key: <base64-encoded-value>
```

---

**Q: How does Kubernetes do zero-downtime deployments?**

Rolling updates — replaces Pods one at a time. Kills Pod 1 (old version), starts
Pod 1 (new version), waits for it to be healthy, then moves to Pod 2. At no point
are all Pods down. Users never see downtime. This is the default behaviour when you
update a Deployment's image.

```
Before:  Pod1 v1  Pod2 v1  Pod3 v1
Step 1:  Pod1 v2  Pod2 v1  Pod3 v1   (Pod1 replaced, health checked)
Step 2:  Pod1 v2  Pod2 v2  Pod3 v1   (Pod2 replaced, health checked)
Step 3:  Pod1 v2  Pod2 v2  Pod3 v2   (done, zero downtime)
```

---

**Q: What is AKS?**

Azure Kubernetes Service — Microsoft Azure's managed Kubernetes. "Managed" means
Azure runs the Kubernetes control plane (the brain of the cluster). You manage only
the worker nodes (VMs running your containers) and your application YAML files.
You interact with it using `kubectl`.

---

**Q: What is the workflow to deploy this voice bot to AKS?**

```
1. docker build -t myregistry.azurecr.io/voicebot:v1.0 .
   docker push myregistry.azurecr.io/voicebot:v1.0
   → image stored in Azure Container Registry

2. az aks create --name voicebotCluster --node-count 2
   → Azure provisions Linux VMs as worker nodes

3. az aks get-credentials --name voicebotCluster
   → connects your kubectl to the cluster

4. kubectl apply -f k8s/
   → Kubernetes reads YAML files, creates Pods, Services, Secrets

5. kubectl get services
   → get the public IP assigned by Azure Load Balancer
```

---

**Q: What replaces docker-compose.yml in Kubernetes?**

YAML manifest files — one per resource type:

| Docker Compose | Kubernetes |
|---|---|
| `service` with `build` | `Deployment` |
| `ports` | `Service` (type: LoadBalancer) |
| `environment` (non-secret) | `ConfigMap` |
| `environment` (secrets) | `Secret` |
| `volumes` | `PersistentVolumeClaim` |
| `restart: unless-stopped` | Built into Deployments by default |
| `depends_on` | Readiness probes / initContainers |

---

**Q: What is a Horizontal Pod Autoscaler (HPA)?**

Automatically increases or decreases the number of Pods based on CPU or memory usage.
You define min replicas, max replicas, and a threshold. Kubernetes handles the rest —
no manual intervention needed when traffic spikes.

```yaml
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70   # scale up when CPU > 70%
```

---

**Q: What is Azure Container Registry (ACR)?**

A private Docker image registry hosted on Azure. Your Docker images are pushed here
and AKS pulls from here when creating Pods. Unlike Docker Hub (public), ACR is
private — only your team and your AKS cluster can access it. AKS connects to ACR
using a managed identity — no credentials needed in your YAML files.

---

**Q: What is self-healing in Kubernetes?**

When a Pod crashes, the Deployment controller detects that the actual number of
running Pods (2) is less than the desired number (3) and automatically creates a
replacement Pod on a healthy node. This happens without any manual action. The user
experiences at most a brief blip while the replacement Pod starts.

---

**Q: In production, should PostgreSQL run inside Kubernetes as a Pod?**

No — for the voice bot or any production app, use a managed database outside the
cluster (Azure Database for PostgreSQL). Running a database inside Kubernetes as a
Pod requires careful handling of PersistentVolumeClaims, backup strategies, and
failover — all of which Azure's managed service handles automatically. Your app
just uses the `DATABASE_URL` connection string regardless.

---

## The One Paragraph That Ties It All Together

When an interviewer asks "how would this voice bot be deployed?" — say this:

*"The app is containerised using Docker with a multi-stage Dockerfile that keeps the
image small. Docker Compose is used locally to run the FastAPI app and PostgreSQL
together. For production, the image is pushed to Azure Container Registry. AKS runs
the app as a Deployment with multiple Pod replicas behind an Azure Load Balancer —
giving us automatic self-healing if a Pod crashes and rolling updates for zero-downtime
deployments. PostgreSQL moves to Azure's managed database service so data persists
outside the cluster. API keys are stored in Kubernetes Secrets, never in the image."*

That one answer covers Docker, Compose, AKS, scaling, secrets, and persistence.

---

*File: `E:\Fastapi_voicebot\DOCKER_KUBERNETES_INTERVIEW.md`*

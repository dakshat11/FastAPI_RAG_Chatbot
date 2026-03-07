# From Local Docker Compose to Production (AKS)
### How your voice bot goes from your laptop to a real server

---

## Where You Are Now

Everything runs locally on your Windows machine:

```
Your Laptop (Windows)
└── Docker Desktop
    ├── voicebot_api container   (FastAPI on port 8000)
    └── voicebot_postgres container (PostgreSQL on port 5432)
```

`docker compose up --build` starts both. You hit `http://localhost:8000`.
This is fine for development. For production you need:
- A real server (not your laptop)
- The server to keep running 24/7
- The app to handle many users at once
- No downtime when you deploy a new version
- Automatic recovery if something crashes

---

## The Journey — 3 Stages

```
Stage 1: Local (now)          Stage 2: Single Server         Stage 3: AKS (production)
────────────────────          ──────────────────────         ──────────────────────────
Your laptop                   One Linux VM on Azure           Kubernetes cluster on Azure
docker compose up             docker compose up -d            kubectl apply -f k8s/
Works for 1 developer         Works for small traffic         Works for real production
```

---

## Stage 2 — Moving to a Single Linux Server

### What is a Linux server in this context?

It is a virtual machine (VM) running on a cloud provider like Azure.
Azure calls it an "Azure VM". It is just a computer in Azure's data center
running Ubuntu Linux 24.04. It has an IP address, it's always on,
and you connect to it via SSH (Secure Shell) from your laptop.

### What changes from local to a single server

**On your laptop — build and push the image:**
```bash
# 1. Log in to Azure Container Registry (ACR)
az acr login --name myvoicebotregistry

# 2. Build the image with the registry path as the tag
docker build -t myvoicebotregistry.azurecr.io/voicebot:v1.0 .

# 3. Push the image to ACR
docker push myvoicebotregistry.azurecr.io/voicebot:v1.0
```

Why push to ACR? The Linux server cannot build the image itself — it has no
code, no pyproject.toml, nothing. You build on your laptop and push to a
registry. The server then pulls the ready-made image.

**On the Linux server — pull and run:**
```bash
# Connect to the server from your laptop
ssh azureuser@<server-public-ip>

# Now you are inside the Linux server
# Pull your docker-compose.yml and .env onto the server
# (via git clone or scp)

# Log in to ACR from the server
az acr login --name myvoicebotregistry

# Pull the image
docker pull myvoicebotregistry.azurecr.io/voicebot:v1.0

# Start everything
docker compose up -d
```

`-d` means detached — containers run in the background even after you
close the SSH session.

### What the single server setup looks like

```
Azure VM (Ubuntu 24.04)
Public IP: 20.10.5.123
├── Docker Engine (Linux version, not Docker Desktop)
├── docker compose up -d
│   ├── voicebot_api container
│   │   └── uvicorn running on port 8000
│   ├── voicebot_postgres container
│   │   └── PostgreSQL on port 5432 (internal only)
│   └── nginx container (new — explained below)
│       └── listens on port 443 (HTTPS) → forwards to port 8000
└── .env file (stored on the server, NOT in git)

Users → https://yourdomain.com → nginx (443) → api (8000)
```

### Why nginx is added in front

Your FastAPI app runs on port 8000 over plain HTTP.
You cannot expose port 8000 directly to users because:
- Users expect HTTPS (port 443), not HTTP
- SSL certificates must be handled somewhere
- Port 8000 looks unprofessional

Nginx sits in front and does three things:
- Listens on port 443 with an SSL certificate
- Forwards (proxies) requests to the FastAPI container on port 8000
- Can serve static files and handle rate limiting

```yaml
# Add this to docker-compose.yml for single server
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./certs:/etc/nginx/certs      # SSL certificate files
  depends_on:
    - api
```

### How Docker and Linux work together on the server

Docker on Linux is not Docker Desktop — it is the Docker Engine running as
a Linux system service. The relationship:

```
Linux OS (Ubuntu 24.04)
└── systemd (Linux process manager)
    └── docker.service (Docker Engine, managed by systemd)
        └── containers (your api, postgres, nginx)
```

Key difference from Windows: on Linux, Docker runs natively inside the OS
with no virtualisation layer. This makes it faster and more efficient than
Docker Desktop on Windows.

```bash
# On the Linux server — manage Docker as a system service
sudo systemctl status docker       # is Docker running?
sudo systemctl start docker        # start it
sudo systemctl enable docker       # make it start automatically on reboot

# If the server reboots, Docker starts automatically,
# but containers do NOT restart unless you set restart: unless-stopped
# in docker-compose.yml — which is why that setting matters
```

### What `restart: unless-stopped` does on a Linux server

```yaml
services:
  api:
    restart: unless-stopped    # if container crashes, Docker restarts it automatically
  postgres:
    restart: unless-stopped    # same for postgres
```

On a Linux server that reboots (OS update, power cycle), Docker starts
automatically (via systemd). The `restart: unless-stopped` policy then
starts all your containers automatically. The server comes back online
with everything running — no manual intervention.

---

## Stage 3 — Moving to AKS (Production)

### Why you need Kubernetes at this point

The single server has one critical problem: it is ONE machine.
- If that VM crashes, the app is down
- If traffic spikes, you cannot automatically add more capacity
- Deploying a new version requires a brief outage

AKS (Azure Kubernetes Service) solves all three.

### What changes from single server to AKS

The Docker image stays exactly the same. What changes:

| Single Server | AKS |
|---|---|
| One Linux VM | Multiple Linux VMs (nodes) managed by Azure |
| `docker compose up` | `kubectl apply -f k8s/` |
| `docker-compose.yml` | Kubernetes YAML manifests |
| Manual scaling | Automatic scaling (HPA) |
| Manual recovery | Automatic self-healing |
| Brief downtime on deploy | Zero downtime (rolling update) |
| `.env` file on server | Kubernetes Secrets |
| nginx container | Kubernetes Ingress + cert-manager |
| PostgreSQL container | Azure Database for PostgreSQL (managed) |

---

## How Linux and Kubernetes Work Together

This is the part most people don't visualise. Here is exactly what happens:

### The physical reality of an AKS cluster

```
AKS Cluster (managed by Azure)
├── Control Plane (Azure manages this — you never touch it)
│   ├── API Server   — receives your kubectl commands
│   ├── Scheduler    — decides which node to place each Pod on
│   └── etcd         — database storing all cluster state
│
└── Node Pool (Linux VMs YOU pay for)
    ├── Node 1 (Ubuntu Linux VM — Standard_D2s_v3, 2 CPU, 8GB RAM)
    │   ├── kubelet      — agent that talks to the control plane
    │   ├── Docker/containerd  — runs the containers
    │   ├── Pod: voicebot-api-1
    │   └── Pod: voicebot-api-2
    │
    └── Node 2 (Ubuntu Linux VM — Standard_D2s_v3, 2 CPU, 8GB RAM)
        ├── kubelet
        ├── containerd
        ├── Pod: voicebot-api-3
        └── Pod: voicebot-postgres-1
```

Each Node is just a Linux VM running Ubuntu. Kubernetes installs an agent
called `kubelet` on each node. This agent continuously asks the control plane
"what should be running on me?" and ensures those containers are running.

### What happens when you run `kubectl apply`

```
You run: kubectl apply -f k8s/deployment.yaml
              │
              ▼
         kubectl sends the YAML to the AKS API Server over HTTPS
              │
              ▼
         API Server stores the desired state in etcd:
         "I want 3 replicas of voicebot:v1.0"
              │
              ▼
         Scheduler looks at Node 1 and Node 2
         Decides: put 2 Pods on Node 1, 1 Pod on Node 2
              │
              ▼
         kubelet on Node 1 receives: "start 2 containers"
         kubelet on Node 2 receives: "start 1 container"
              │
              ▼
         containerd on each node pulls image from ACR
         Starts the containers
              │
              ▼
         3 Pods running, load balancer distributes traffic
```

### How self-healing works (Linux + Kubernetes together)

```
Pod on Node 2 crashes (uvicorn process dies)
              │
              ▼
         containerd on Node 2 detects the process exited
              │
              ▼
         kubelet on Node 2 reports to control plane:
         "I only have 0 Pods running, desired is 1"
              │
              ▼
         Kubernetes controller: "desired=3, actual=2 — fix it"
              │
              ▼
         Scheduler picks a node (Node 1 or Node 2)
              │
              ▼
         New Pod starts — back to 3 replicas
         Total time: ~10-30 seconds
         User impact: near zero (2 other Pods handled traffic)
```

### How a Node failure is handled

```
Node 2 (the entire Linux VM) goes down
              │
              ▼
         kubelet on Node 2 stops sending heartbeats to control plane
              │
              ▼
         After 5 minutes: control plane marks Node 2 as NotReady
              │
              ▼
         All Pods that were on Node 2 are rescheduled to Node 1
              │
              ▼
         Node 1 now runs all 3 Pods
         (assuming it has enough CPU/RAM)
```

This is why you need at least 2 nodes — one node going down does not
take the app offline.

---

## The Complete Production Architecture

```
                        Internet
                           │
                           ▼
                  Azure Load Balancer
                  (public IP address)
                           │
                           ▼
                  AKS Ingress Controller
                  (nginx inside Kubernetes)
                  (handles HTTPS/SSL)
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Pod 1         Pod 2         Pod 3
        (Node 1)       (Node 1)      (Node 2)
        FastAPI        FastAPI        FastAPI
           │                │                │
           └────────────────┴────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   Azure Database              Pinecone (cloud)
   for PostgreSQL              vector store
   (managed, outside           (already cloud,
    the cluster)                no change needed)
              │
       Conversation
       history persists
       here
```

Everything your app talks to outside the cluster (PostgreSQL, Pinecone,
OpenAI API, Pinecone) remains the same. Only the compute layer (where
the FastAPI app runs) moves from one Docker container to Kubernetes Pods.

---

## What You Actually Do — Step by Step

### One-time setup (first deployment)

```bash
# 1. Create Azure resources
az group create --name voicebot-rg --location eastus
az acr create --name voicebotregistry --resource-group voicebot-rg --sku Basic
az aks create --name voicebot-cluster --resource-group voicebot-rg --node-count 2
az aks get-credentials --name voicebot-cluster --resource-group voicebot-rg

# 2. Link AKS to ACR (so AKS can pull images)
az aks update --name voicebot-cluster --resource-group voicebot-rg \
  --attach-acr voicebotregistry

# 3. Build and push your image
az acr login --name voicebotregistry
docker build -t voicebotregistry.azurecr.io/voicebot:v1.0 .
docker push voicebotregistry.azurecr.io/voicebot:v1.0

# 4. Create secrets in Kubernetes (your API keys)
kubectl create secret generic voicebot-secrets \
  --from-literal=openai-api-key=sk-... \
  --from-literal=pinecone-api-key=pcsk_...

# 5. Deploy everything
kubectl apply -f k8s/
kubectl get pods    # watch them come up
kubectl get service # get the public IP
```

### Every subsequent deployment (new code version)

```bash
# 1. Build and push new version
docker build -t voicebotregistry.azurecr.io/voicebot:v1.1 .
docker push voicebotregistry.azurecr.io/voicebot:v1.1

# 2. Update the Deployment (rolling update starts automatically)
kubectl set image deployment/voicebot-api api=voicebotregistry.azurecr.io/voicebot:v1.1

# 3. Watch the rollout
kubectl rollout status deployment/voicebot-api
```

Zero downtime. Pods replaced one at a time.

---

## Key Things to Know for Interview

**Q: What is a Linux node in AKS?**
A Linux VM (Ubuntu) managed by Azure. Kubernetes installs `kubelet` on it.
Your containers run on these nodes. You do not SSH into them directly —
Kubernetes manages them.

**Q: How does Docker relate to Kubernetes?**
Kubernetes uses Docker (or containerd) to actually run containers on each node.
Kubernetes is the orchestrator — it decides what runs where. Docker/containerd
is the runtime — it does the actual container execution. Kubernetes without
Docker would have no way to run containers. Docker without Kubernetes means
you manage everything manually on one machine.

**Q: What is containerd?**
The container runtime inside each Kubernetes node. It replaced Docker as the
default runtime in modern Kubernetes. It pulls images and runs containers.
You never interact with it directly — kubelet talks to it.

**Q: What is kubelet?**
An agent that runs on every Linux node in the cluster. It receives instructions
from the Kubernetes control plane ("run this container") and uses containerd
to execute them. It also monitors containers and reports their health back.

**Q: What is the control plane and who manages it in AKS?**
The brain of Kubernetes — API server, scheduler, etcd. In AKS, Azure manages
it for free. You do not pay for it, you cannot SSH into it, you do not maintain
it. You only manage the worker nodes (Linux VMs) and your application YAML.

**Q: Why is PostgreSQL moved outside the cluster in production?**
Running a database inside Kubernetes as a Pod is complex — you need to manage
PersistentVolumes, backup jobs, failover, replication. Azure Database for
PostgreSQL does all of this automatically. The app just uses the connection
string. The containers in the cluster remain stateless — easy to replace,
scale, and update.

**Q: If a node goes down, what happens to its containers?**
Kubernetes detects the node as NotReady (after ~5 minutes of no heartbeat).
All Pods from that node are rescheduled onto remaining healthy nodes.
This is why `minReplicas: 2` and having at least 2 nodes matters —
a single node failure should not take the app offline.

---

*The progression: Local Docker Compose → Single Linux VM → AKS*
*The image never changes. The environment around it gets more capable.*

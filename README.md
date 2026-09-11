# PulseFlow Telemetry API

A containerized telemetry ingestion service running on Azure Kubernetes Service (AKS), automated with Terraform and monitored via the Prometheus Operator and Grafana.

## Overview

PulseFlow is a containerized telemetry ingestion service built to demonstrate a complete cloud-native deployment workflow. The project focuses on provisioning Azure infrastructure with Terraform, deploying and updating workloads on AKS, automating delivery through GitHub Actions, and monitoring application and cluster health with Prometheus and Grafana.

## Architecture

The service exposes an HTTP endpoint backed by an internal Redis cache. Cloud infrastructure is provisioned through Terraform, with Kubernetes handling pod scheduling and service exposure via an Azure Load Balancer.

```mermaid
graph TD
    %% Define Styles
    classDef git fill:#f05032,stroke:#333,stroke-width:1px,color:#fff;
    classDef cicd fill:#2088FF,stroke:#333,stroke-width:1px,color:#fff;
    classDef net fill:#0078D4,stroke:#333,stroke-width:1px,color:#fff;
    classDef registry fill:#0078D4,stroke:#333,stroke-width:1px,color:#fff;
    classDef app fill:#008080,stroke:#333,stroke-width:1px,color:#fff;
    classDef data fill:#DC382D,stroke:#333,stroke-width:1px,color:#fff;
    classDef mon fill:#E6522C,stroke:#333,stroke-width:1px,color:#fff;
    classDef vis fill:#F47A20,stroke:#333,stroke-width:1px,color:#fff;

    %% CI/CD Flow
    Push["Git Push to main"]:::git --> Actions["GitHub Actions CI/CD<br>(Lint, Build, Push)"]:::cicd
    Actions --> ACR["Azure Container Registry<br>(Container Images)"]:::registry
    ACR -.->|Image pulled during deployment| PodApp

    %% Traffic Flow
    Traffic["External Traffic"]:::net --> LB["Azure LoadBalancer<br>(Public IP)"]:::net

    %% Default Namespace Cluster
    subgraph AKS_Default ["AKS Cluster: default namespace"]
        LB --> PodApp["PulseFlow Pod (FastAPI + Web UI)<br>Port 8000: / (UI), /api, /metrics"]:::app
        PodApp -->|Writes state / events| PodRedis["Redis Pod<br>(In-Memory Data Store)"]:::data
    end

    %% Monitoring Namespace Cluster
    subgraph AKS_Monitoring ["AKS Cluster: monitoring namespace"]
        Prom["Prometheus Operator<br>(Target Discovery: ServiceMonitor)"]:::mon -->|Feeds metrics| Grafana["Grafana Visualizations<br>& Dashboards"]:::vis
    end

    %% Cross-Namespace Scrape Link
    PodApp -.->|Scraped every 15s| Prom
```

## Key Implementation Details

* **Automated CI/CD Pipeline (GitHub Actions):** Every push to `main` triggers automated linting, container builds pushed to Azure Container Registry (ACR) via short-lived credentials, and rolling updates designed to maintain application availability.

* **Interactive Frontend UI:** The FastAPI application serves a web interface that allows users to trigger real-time telemetry events and interactively visualize Redis state updates directly from the browser.

* **Azure Managed Identity for ACR Authentication:** AKS node pools authenticate with ACR using the cluster’s managed Kubelet identity assigned to the Azure `AcrPull` role. No static container registry passwords or `imagePullSecrets` are stored in Kubernetes manifests.

* **Declarative Metrics Scraping:** Observability is configured using `kube-prometheus-stack` and a Kubernetes `ServiceMonitor` resource, allowing Prometheus to discover and scrape the application's metrics endpoint through its Kubernetes Service.

* **Workload Resource Management:** Deployments define CPU and memory requests and limits to provide Kubernetes with resource requirements and constrain excessive container resource consumption.

* **Infrastructure as Code (IaC):** Core cloud resources—Resource Group, Virtual Network, Subnets, AKS cluster, and ACR—are fully declared and managed via modular Terraform configurations.

## Tech Stack

* **Cloud:** Microsoft Azure (AKS, Azure Container Registry, Virtual Networks, Managed Identity)

* **CI/CD:** GitHub Actions

* **Infrastructure as Code:** Terraform

* **Container & Orchestration:** Docker, Kubernetes (Deployments, Services, ServiceMonitors)

* **Application & Web:** Python 3.11, FastAPI, HTML/Tailwind CSS frontend, Redis

* **Observability:** Prometheus Operator, Grafana, Helm (`kube-prometheus-stack`)

## Project Structure

```text
├── .github/
│   └── workflows/
│       └── deploy.yaml             # GitHub Actions CI/CD pipeline
├── terraform/                      # Azure infrastructure manifests
│   ├── main.tf                     # AKS, ACR, and networking configuration
│   ├── variables.tf                # Cluster parameters and resource sizing
│   └── outputs.tf                  # Control plane endpoints and identity details
├── k8s/                            # Kubernetes manifests
│   ├── pulseflow-deployment.yaml   # Workload definition & LoadBalancer service
│   ├── redis-deployment.yaml       # Internal Redis service
│   └── pulseflow-servicemonitor.yaml # Prometheus Operator scrape target
├── app/                            # Application & Frontend source
│   ├── main.py                     # FastAPI routes, UI rendering, & metrics
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                  # Container build instructions
├── visuals                         # Dashboard and cluster verification
└── README.md
```

### CI/CD Workflow
The automated deployment pipeline defined in .github/workflows/deploy.yaml executes the following sequence:

- Lint & Code Quality: Tests and lints Python code.

- Build & Push: Uses Docker Buildx to build and tag images with Git commit SHA and pushes to ACR.

- Cluster Context Configuration: Logs into Azure via Service Principal credentials stored safely in GitHub Secrets.

### Declarative Deploy: Applies updated Kubernetes manifests and executes a rolling restart:

```
kubectl set image deployment/pulseflow-telemetry pulseflow-telemetry=${{ env.ACR_LOGIN_SERVER }}/pulseflow-telemetry:${{ github.sha }}
kubectl rollout status deployment/pulseflow-telemetry
```

## Deployment Workflow

### Provision the Cloud Infrastructure

```
cd terraform
terraform init
terraform plan
terraform apply
```

Pull the cluster credentials locally:

```
az aks get-credentials --resource-group pulseflow-rg --name pulseflow-aks --overwrite-existing
```

### Build and Push the Application Image
For manual deployments, the application image can be built directly in Azure Container Registry:

```bash
az acr build --registry pulseflowreg001 --image pulseflow-telemetry:latest ../app
```

### Deploy the Observability Stack
Install the Prometheus and Grafana operator stack via Helm:

```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Deploy Workloads and Target Monitors

```
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/pulseflow-deployment.yaml
kubectl apply -f k8s/pulseflow-servicemonitor.yaml
```

## Verification & Metrics

### Verify Pod Status:

```
kubectl get pods -A
```

### Generate Traffic:

```
APP_IP=$(kubectl get svc pulseflow-loadbalancer -o jsonpath='{.status.loadBalancer.ingress[0].ip}')


for i in {1..30}; do curl -s -o /dev/null -w "%{http_code} " http://$APP_IP/; sleep 0.5; done
```

### Inspect Metrics in Grafana:
Forward the Grafana service port locally:

```
kubectl port-forward --namespace monitoring svc/monitoring-grafana 3000:80
```

Retrieve the generated admin password:

```
kubectl get secret --namespace monitoring monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
```

- Access http://localhost:3000

- Review application metrics (such as http_requests_total) and node/pod resource usage under the pre-configured Kubernetes compute dashboards.

## Visual Verification

### Application Frontend UI
The web dashboard running live on the public Azure LoadBalancer IP:

Before:
![Application UI](visuals/Application_Frontend_UI_1.png)

After:
![Application UI](visuals/Application_Frontend_UI_2.png)

### Live Application Telemetry in Grafana
Real-time request metrics captured and visualized during simulated traffic spikes:

![Traffic Monitoring](visuals/Application_Telemetry_Grafana_1.png)


![Traffic Monitoring](visuals/Application_Telemetry_Grafana_2.png)

### Kubernetes Cluster & Pod Health
Workloads and monitoring pods healthy and operational on AKS:

![Pod Health](visuals/Monitoring_pods_1.png)


![Pod Health](visuals/Monitoring_pods_2.png)

### What This Project Demonstrates
- Infrastructure provisioning with Terraform
- Container image creation and registry management with Docker and ACR
- Kubernetes workload deployment and service exposure on AKS
- CI/CD automation with GitHub Actions
- Azure Managed Identity for registry authentication
- Kubernetes resource management
- Application metrics instrumentation and scraping
- Monitoring and visualization with Prometheus and Grafana
- Helm-based deployment of Kubernetes observability tooling

### Key Architecture Decisions

- Terraform: Used to make Azure infrastructure reproducible and version-controlled.

- AKS: Provides managed Kubernetes orchestration for the application workloads.

- ACR: Provides a private container registry integrated with Azure.

- Managed Identity: Avoids storing static ACR credentials in Kubernetes.

- Prometheus/Grafana: Provides application and Kubernetes observability.

- Redis: Provides internal application state storage without exposing Redis publicly.

## Teardown
To cleanly release public IP allocations and deprovision resources:

```
kubectl delete svc pulseflow-loadbalancer

cd terraform
terraform destroy -auto-approve
```

# Kubernetes Deployment Guide

This guide explains how to deploy Contract Manager to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (1.25+)
- `kubectl` configured to access your cluster
- nginx ingress controller installed
- PostgreSQL database (external or in-cluster)
- Redis (external or in-cluster)

## Docker Images

Images are built automatically via GitHub Actions and pushed to GitHub Container Registry:

```
ghcr.io/OWNER/contract-manager/backend:main
ghcr.io/OWNER/contract-manager/frontend:main
```

Replace `OWNER` with your GitHub username or organization.

### Image Tags

- `main` - Latest from main branch
- `v1.0.0` - Semantic version tags
- `sha-abc1234` - Specific commit SHA

## Quick Start

### 1. Update Configuration

Edit the manifests to match your environment:

```bash
# Replace image references
sed -i 's/OWNER/your-github-username/g' k8s/*.yaml

# Update hostname
sed -i 's/contract-manager.example.com/your-domain.com/g' k8s/*.yaml
```

### 2. Configure Secrets

Edit `k8s/secrets.yaml` with your actual values:

```yaml
stringData:
  DJANGO_SECRET_KEY: "your-secure-random-key"
  DATABASE_URL: "postgres://user:pass@your-db-host:5432/contract_manager"
  REDIS_URL: "redis://your-redis-host:6379/0"
```

**Generate a secure secret key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 3. Deploy

```bash
# Create namespace and base resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Run database migrations
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/django-migrate -n contract-manager --timeout=120s

# Deploy applications
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
```

### 4. Verify Deployment

```bash
# Check pods are running
kubectl get pods -n contract-manager

# Check services
kubectl get svc -n contract-manager

# Check ingress
kubectl get ingress -n contract-manager

# View logs
kubectl logs -l app=backend -n contract-manager
kubectl logs -l app=frontend -n contract-manager
```

## Database Setup

### Option A: External PostgreSQL (Recommended for production)

Use a managed database service (AWS RDS, GCP Cloud SQL, etc.) and update the `DATABASE_URL` in secrets.

### Option B: In-cluster PostgreSQL

Deploy PostgreSQL in the cluster (not recommended for production):

```yaml
# postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: contract-manager
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          env:
            - name: POSTGRES_DB
              value: contract_manager
            - name: POSTGRES_USER
              value: contract_manager
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: contract-manager-secrets
                  key: POSTGRES_PASSWORD
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: contract-manager
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
```

## TLS/HTTPS Setup

### Using cert-manager

1. Install cert-manager:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml
```

2. Create a ClusterIssuer:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

3. Uncomment TLS section in `ingress.yaml`

## Updating the Application

```bash
# Update to a new version
kubectl set image deployment/backend backend=ghcr.io/OWNER/contract-manager/backend:v1.1.0 -n contract-manager
kubectl set image deployment/frontend frontend=ghcr.io/OWNER/contract-manager/frontend:v1.1.0 -n contract-manager

# Run migrations if needed
kubectl delete job django-migrate -n contract-manager --ignore-not-found
kubectl apply -f k8s/migration-job.yaml
```

## Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=4 -n contract-manager

# Scale frontend
kubectl scale deployment frontend --replicas=4 -n contract-manager
```

## Troubleshooting

### Check pod status
```bash
kubectl describe pod -l app=backend -n contract-manager
```

### View logs
```bash
kubectl logs -l app=backend -n contract-manager --tail=100 -f
```

### Shell into a pod
```bash
kubectl exec -it deployment/backend -n contract-manager -- /bin/bash
```

### Test database connection
```bash
kubectl exec -it deployment/backend -n contract-manager -- python manage.py dbshell
```

## Environment Variables Reference

### Backend

| Variable | Description | Required |
|----------|-------------|----------|
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `DATABASE_URL` | PostgreSQL connection URL | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `DJANGO_DEBUG` | Enable debug mode | No (default: false) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | Yes |
| `HUBSPOT_API_KEY` | HubSpot API key for sync | No |

### Frontend

The frontend is built with the API URL baked in. To change it, rebuild the image with:

```bash
docker build --build-arg VITE_API_URL=https://api.example.com/graphql -f Dockerfile.prod .
```

# Apache Airflow on Kubernetes — Docker Desktop
**Helm Chart 1.18.0 · Airflow 2.9.2 · LocalExecutor**

---

## Prerequisites

Before starting, make sure you have the following installed:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Kubernetes enabled
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm 3](https://helm.sh/docs/intro/install/)

**Enable Kubernetes in Docker Desktop:**
> Docker Desktop → Settings → Kubernetes → Enable Kubernetes → Apply & Restart

**Share your DAGs folder with Docker Desktop:**
> Docker Desktop → Settings → Resources → File Sharing → Add your project drive (e.g. `C:\`)

---

## Step 1 — Add the Airflow Helm Repository

```powershell
helm repo add apache-airflow https://airflow.apache.org
helm repo update
```

---

## Step 2 — Create the Airflow Namespace

```powershell
kubectl create namespace airflow
```

---

## Step 3 — Deploy PostgreSQL

```powershell
kubectl apply -n airflow -f - <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
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
          image: postgres:15
          env:
            - name: POSTGRES_USER
              value: airflow
            - name: POSTGRES_PASSWORD
              value: airflow
            - name: POSTGRES_DB
              value: airflow
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
EOF
```

Wait for it to be ready:
```powershell
kubectl get pods -n airflow -w
# Wait until postgres-0 shows 1/1 Running
```

---

## Step 4 — Deploy Airflow

```powershell
helm upgrade --install airflow apache-airflow/airflow `
  --namespace airflow `
  -f values.yaml `
  --timeout 10m
```

> ⚠ Run this from the root `Kubernetes-deployment/` folder, not from `k8s/`

---

## Step 5 — Wait for All Pods to Be Ready

```powershell
kubectl get pods -n airflow -w
```

**Expected healthy state:**

| Pod | Ready | Status |
|-----|-------|--------|
| `airflow-scheduler-0` | 2/2 | Running |
| `airflow-triggerer-0` | 2/2 | Running |
| `airflow-webserver-XXXX` | 1/1 | Running |
| `postgres-0` | 1/1 | Running |

This typically takes **5–8 minutes** on first launch.

---

## Step 6 — Access the Airflow UI

Start port forwarding (keep this terminal open):
```powershell
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow
```

Open your browser:
```
http://localhost:8080
```

**Login credentials:**
- Username: `admin`
- Password: `admin123`

---

## Step 7 — Add DAGs

Simply drop `.py` DAG files into your local `dags/` folder:
```
Kubernetes-deployment/dags/your_dag.py
```

The scheduler picks up new files automatically within **60 seconds** (configured via `dag_dir_list_interval`).

Verify DAGs are mounted inside the pod:
```powershell
kubectl exec -n airflow airflow-scheduler-0 -- ls /opt/airflow/dags
```

---

## Step 8 — Trigger a DAG

1. Go to `http://localhost:8080`
2. Find your DAG in the list (e.g. `hello_world`)
3. Toggle the switch on the left to **unpause** it
4. Click the ▶ **Play** button → **Trigger DAG**
5. Watch the tasks turn green in the Graph view

---

## Daily Workflow (After Initial Setup)

Each time you restart your machine:

```powershell
# 1. Start port forwarding
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow

# 2. Open the UI
# http://localhost:8080
```

That's it — Kubernetes keeps Airflow running as long as Docker Desktop is open.

---

## Useful Commands

### Check pod status
```powershell
kubectl get pods -n airflow
```

### View scheduler logs
```powershell
kubectl logs -n airflow airflow-scheduler-0 -c scheduler --tail=50
```

### View webserver logs
```powershell
kubectl logs -n airflow airflow-webserver-<id> --tail=50
```

### Restart a stuck pod
```powershell
# Scheduler
kubectl delete pod -n airflow airflow-scheduler-0
# Kubernetes recreates it automatically
```

### Apply values.yaml changes
```powershell
helm upgrade airflow apache-airflow/airflow `
  --namespace airflow `
  -f values.yaml `
  --timeout 10m
```

### Fix stuck Helm upgrade
```powershell
helm rollback airflow -n airflow
# Then retry the upgrade
```

### Clear stuck/zombie DAG runs
```powershell
kubectl exec -n airflow airflow-scheduler-0 -- airflow dags clear <dag_id> --yes
```

### Check node memory
```powershell
kubectl describe node | Select-String -Pattern "memory|Capacity|Allocatable"
```

## Troubleshooting Quick Reference

| Symptom | Command to diagnose | Fix |
|---|---|---|
| DAGs missing from UI | `kubectl exec ... -- ls /opt/airflow/dags` | Check hostPath in values.yaml |
| Scheduler at 1/2 | `kubectl describe pod airflow-scheduler-0` | Check for OOMKilled, increase memory |
| Helm stuck | `helm history airflow -n airflow` | Run `helm rollback airflow -n airflow` |
| Webserver crash loop | `kubectl logs airflow-webserver-... --previous` | Check gunicorn timeout in config |
| Path mangling in Git Bash | Error mentions `C:/Program Files/Git/opt/...` | Use PowerShell instead |
| Tasks never finish | Check scheduler logs for "zombie" | `airflow dags clear <dag_id> --yes` |

> 📄 For detailed debugging strategies, see `airflow_debug_guide.pdf`

---

## Resource Configuration Summary

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---|---|---|---|
| Scheduler | 200m | 1000m | 512Mi | 1500Mi |
| Webserver | 200m | 1000m | 512Mi | 1500Mi |
| Triggerer | 100m | 500m | 256Mi | 512Mi |
| Log Groomer | 50m | 100m | 64Mi | 128Mi |

> Docker Desktop should have at least **6GB RAM** allocated under Settings → Resources → Memory.
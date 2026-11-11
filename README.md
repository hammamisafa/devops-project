# DevOps API

API REST FastAPI, conteneurisée avec Docker, testée et sécurisée par un pipeline CI/CD GitHub Actions, observable (métriques, logs, traces) et déployée sur Kubernetes (kind).

## Architecture

```
Développeur → GitHub (issues, PR, review)
                 │
                 ▼
          GitHub Actions
   tests → SAST (Bandit) → build + scan Trivy → DAST (ZAP) → publication Docker Hub
                 │
                 ▼
   Image Docker  ──►  docker compose (API + Prometheus + Grafana)
                 └──►  Kubernetes (kind) : Deployment x2 + Service
```

## Structure du projet

```
app/main.py                 API FastAPI (métriques, logs JSON, tracing)
tests/test_api.py           Tests pytest
Dockerfile                  Image de l'API (utilisateur non-root, HEALTHCHECK)
docker-compose.yml          API + Prometheus + Grafana
observability/              Configuration Prometheus, dashboard Grafana
k8s/                        Manifests Kubernetes (Deployment, Service)
.github/workflows/ci.yml    Pipeline CI/CD
```

## Prérequis

- Python 3.12
- Docker Desktop
- kind et kubectl (pour Kubernetes)

## Lancer en local

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

L'API est disponible sur http://127.0.0.1:8000, la documentation Swagger sur http://127.0.0.1:8000/docs.

## Tests

```cmd
python -m pytest -v
```

## Docker

Image publiée sur Docker Hub :

```cmd
docker pull safahammami/devops-api:latest
docker run -d -p 8000:8000 --name devops-api safahammami/devops-api:latest
```

Construire l'image localement :

```cmd
docker build -t devops-api:latest .
docker run -d -p 8000:8000 --name devops-api devops-api:latest
```

### Stack complète avec docker compose

```cmd
docker compose up --build -d
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |

Dans Grafana, ajouter la data source Prometheus avec l'URL `http://prometheus:9090`, puis importer `observability/grafana-dashboard.json`.

Arrêter la stack : `docker compose down`.

## Exemples d'API

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | État du service |
| GET | `/items` | Liste des items |
| POST | `/items` | Création d'un item |
| GET | `/items/{id}` | Lecture d'un item |
| DELETE | `/items/{id}` | Suppression d'un item |
| GET | `/metrics` | Métriques Prometheus |

```cmd
curl http://localhost:8000/health
curl -X POST http://localhost:8000/items -H "Content-Type: application/json" -d "{\"name\": \"Livre\", \"price\": 12.5}"
curl http://localhost:8000/items
curl http://localhost:8000/items/1
curl -X DELETE http://localhost:8000/items/1
```

## Observabilité

- **Métriques** : `/metrics` (nombre de requêtes, temps de réponse) collectées par Prometheus, visualisées dans Grafana.
- **Logs** : une ligne JSON par requête (méthode, chemin, statut, durée, `trace_id`) : `docker logs devops-api`.
- **Tracing** : OpenTelemetry, un span par requête affiché sur la sortie standard ; le `trace_id` du log permet de relier log et trace.

## CI/CD

Le pipeline `.github/workflows/ci.yml` s'exécute à chaque push et Pull Request :

1. **Tests pytest**
2. **SAST (Bandit)** : analyse statique du code
3. **Build et scan de l'image** : construction Docker, scan Trivy, test de `/health`
4. **DAST (OWASP ZAP)** : scan dynamique de l'API en fonctionnement
5. **Publication sur Docker Hub** : uniquement sur `main`, si tous les contrôles passent

Les rapports Bandit, Trivy et ZAP sont conservés comme artefacts de chaque exécution.

## Kubernetes (kind)

```cmd
kind create cluster --name devops
docker build -t devops-api:latest .
kind load docker-image devops-api:latest --name devops
kubectl apply -f k8s/
kubectl get pods
kubectl port-forward svc/devops-api 8080:80
```

L'API est alors accessible sur http://localhost:8080/health. Le Deployment utilise 2 réplicas, des probes de readiness et de liveness sur `/health`, et des limites de ressources.

Supprimer le cluster : `kind delete cluster --name devops`.

## Workflow Git

Une issue par tâche, une branche par issue (`feature/...`), une Pull Request relue par un second compte avant fusion dans `main`.
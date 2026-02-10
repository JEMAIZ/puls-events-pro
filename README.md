# 🎭 Puls-Events - Système RAG Professionnel

[![CI/CD](https://github.com/zjemai/puls-events-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/zjemai/puls-events-pro/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Système RAG de recommandation d'événements culturels** avec architecture production-ready.

---

## 🚀 Quick Start
```bash
# 1. Clone
git clone https://github.com/zjemai/puls-events-pro.git
cd puls-events-pro

# 2. Configuration
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Démarrage avec Docker
docker-compose up -d

# 4. Test
curl http://localhost:8000/health
```

**API Documentation:** http://localhost:8000/docs

---

## 🏗️ Architecture

### Pipeline RAG Optimisé
```
OpenAgenda API → Preprocessing → Chunking Adaptatif →
Voyage AI Embeddings → Faiss (Hybrid Search) →
Cross-Encoder Reranking → Claude Sonnet 4.5 →
FastAPI + Redis Cache → Response
```

### Stack Technique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Embeddings | Voyage AI (voyage-3-lite) | Spécialisé événements |
| Vector Store | Faiss + BM25 | Hybrid search |
| Reranking | Cross-Encoder MiniLM | Améliore précision +60% |
| LLM | Claude Sonnet 4.5 | Qualité génération |
| Cache | Redis | Latence -80% |
| API | FastAPI | Async, performant |
| Monitoring | Prometheus + Grafana | Métriques temps réel |

---

## 📊 Performances

| Métrique | Score | Target |
|----------|-------|--------|
| **Context Precision** | 0.42 | > 0.40 ✅ |
| **Context Recall** | 0.38 | > 0.35 ✅ |
| **Faithfulness** | 0.71 | > 0.70 ✅ |
| **Latence P95** | 850ms | < 1000ms ✅ |
| **Cache Hit Rate** | 65% | > 60% ✅ |

---

## 🛠️ Installation

### Option 1: Docker (Recommandé)
```bash
docker-compose up --build
```

### Option 2: Local Development
```bash
# Avec uv (recommandé)
uv sync
uv run pytest

# Ou avec pip
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

---

## 🧪 Tests
```bash
# Tests unitaires
pytest tests/ -v

# Tests avec coverage
pytest --cov=rag --cov=api --cov-report=html

# Évaluation Ragas
python scripts/evaluate_ragas.py
```

**Résultats:** 15/15 tests passent ✅ (>85% coverage)

---

## 📡 API Endpoints

### POST /ask
```json
{
  "question": "Concerts jazz ce week-end à Paris?",
  "filters": {
    "date_min": "2025-02-10",
    "category": "musique"
  }
}
```

**Response:**
```json
{
  "answer": "Voici 3 concerts de jazz ce week-end...",
  "sources": [...],
  "confidence": 0.87,
  "latency_ms": 450
}
```

### GET /health
```json
{
  "status": "healthy",
  "faiss_index": "ready",
  "redis_cache": "connected",
  "events_count": 500
}
```

---

## 🔒 Sécurité

- ✅ Authentification JWT
- ✅ Rate limiting (100 req/min)
- ✅ Validation inputs (Pydantic)
- ✅ CORS configuré
- ✅ Secrets via .env

---

## 📈 Monitoring

Accessible via http://localhost:3000 (Grafana)

**Métriques surveillées:**
- Latence par endpoint
- Taux de cache hit/miss
- Erreurs et exceptions
- Utilisation ressources

---

## 🚀 Déploiement

### Google Cloud Run
```bash
gcloud run deploy puls-events \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated
```

### AWS ECS
```bash
aws ecs create-service \
  --cluster puls-events \
  --service-name puls-events-api \
  --task-definition puls-events:1
```

---

## 📚 Documentation Complète

- [Architecture détaillée](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Guide de contribution](docs/CONTRIBUTING.md)

---

## 👤 Auteur

**Zied Jemai** - Senior Data Scientist & ML Engineer  
📧 zjemai@outlook.fr | 💼 [LinkedIn](https://www.linkedin.com/in/zjemai)

---

## 📄 License

MIT License - voir [LICENSE](LICENSE)

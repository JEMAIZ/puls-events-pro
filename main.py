"""
FastAPI application for Puls-Events RAG system.
Production-ready with authentication, caching, and monitoring.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
import time
import logging
from datetime import datetime, timedelta
import redis
import json
import hashlib
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from rag.rag_orchestrator import RAGOrchestrator
from rag.vector_store import VectorStore

# =======================
# CONFIGURATION
# =======================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Puls-Events RAG API",
    description="Système RAG professionnel pour événements culturels",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Redis cache
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    CACHE_ENABLED = True
    logger.info("✅ Redis cache connected")
except:
    CACHE_ENABLED = False
    logger.warning("⚠️ Redis cache unavailable, running without cache")

# Prometheus metrics
query_counter = Counter('queries_total', 'Total queries received')
query_latency = Histogram('query_latency_seconds', 'Query latency')
cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')

# Initialize RAG
try:
    rag = RAGOrchestrator()
    vector_store = VectorStore()
    logger.info("✅ RAG system initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize RAG: {e}")
    rag = None
    vector_store = None

# =======================
# MODELS
# =======================

class QueryFilters(BaseModel):
    """Filtres optionnels pour la recherche"""
    date_min: Optional[str] = Field(None, description="Date minimum (YYYY-MM-DD)")
    date_max: Optional[str] = Field(None, description="Date maximum (YYYY-MM-DD)")
    category: Optional[str] = Field(None, description="Catégorie événement")
    location: Optional[str] = Field(None, description="Lieu géographique")
    
    @validator('date_min', 'date_max')
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Format de date invalide. Utilisez YYYY-MM-DD")
        return v

class QueryRequest(BaseModel):
    """Requête utilisateur"""
    question: str = Field(..., min_length=3, max_length=500, description="Question utilisateur")
    filters: Optional[QueryFilters] = None
    max_results: int = Field(3, ge=1, le=10, description="Nombre de résultats max")
    
    class Config:
        schema_extra = {
            "example": {
                "question": "Quels concerts de jazz ce week-end à Paris?",
                "filters": {
                    "date_min": "2025-02-10",
                    "category": "musique"
                },
                "max_results": 3
            }
        }

class Source(BaseModel):
    """Source d'information"""
    title: str
    date: str
    location: str
    url: Optional[str] = None
    relevance_score: float

class QueryResponse(BaseModel):
    """Réponse du système"""
    answer: str
    sources: List[Source]
    confidence: float = Field(..., ge=0.0, le=1.0)
    latency_ms: int
    cached: bool = False

class HealthResponse(BaseModel):
    """État du système"""
    status: str
    faiss_index: str
    redis_cache: str
    events_count: int
    uptime_seconds: float

# =======================
# SECURITY
# =======================

async def verify_token(authorization: str = Header(None)):
    """Vérification du token JWT (simplifié)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # TODO: Implémenter vérification JWT complète
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    # Exemple basique - à remplacer par vraie validation JWT
    if token != "demo-token-12345":  # À remplacer par validation JWT
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token

# =======================
# UTILS
# =======================

def get_cache_key(question: str, filters: Optional[QueryFilters]) -> str:
    """Génère une clé de cache unique"""
    data = f"{question}_{filters.dict() if filters else ''}"
    return hashlib.md5(data.encode()).hexdigest()

def get_from_cache(key: str) -> Optional[Dict]:
    """Récupère depuis le cache"""
    if not CACHE_ENABLED:
        return None
    try:
        cached = redis_client.get(key)
        if cached:
            cache_hits.inc()
            return json.loads(cached)
        cache_misses.inc()
        return None
    except Exception as e:
        logger.error(f"Cache error: {e}")
        return None

def set_cache(key: str, value: Dict, ttl: int = 3600):
    """Sauvegarde dans le cache"""
    if not CACHE_ENABLED:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.error(f"Cache write error: {e}")

# =======================
# ENDPOINTS
# =======================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint racine"""
    return {
        "name": "Puls-Events RAG API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Vérification de santé du système"""
    start_time = getattr(app.state, 'start_time', time.time())
    
    return HealthResponse(
        status="healthy" if rag else "degraded",
        faiss_index="ready" if vector_store and vector_store.index else "not_loaded",
        redis_cache="connected" if CACHE_ENABLED else "disabled",
        events_count=vector_store.get_total_chunks() if vector_store else 0,
        uptime_seconds=time.time() - start_time
    )

@app.post("/ask", response_model=QueryResponse, tags=["RAG"])
async def ask_question(
    request: QueryRequest,
    token: str = Depends(verify_token)
):
    """
    Poser une question sur les événements culturels.
    
    Nécessite authentification via header: Authorization: Bearer <token>
    """
    if not rag:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    query_counter.inc()
    start_time = time.time()
    
    # Check cache
    cache_key = get_cache_key(request.question, request.filters)
    cached_response = get_from_cache(cache_key)
    
    if cached_response:
        logger.info(f"✅ Cache hit for: {request.question[:50]}...")
        return QueryResponse(**cached_response, cached=True)
    
    try:
        # Query RAG system
        with query_latency.time():
            result = rag.query(
                question=request.question,
                filters=request.filters.dict() if request.filters else None,
                top_k=request.max_results
            )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        response = QueryResponse(
            answer=result['answer'],
            sources=[
                Source(
                    title=src['title'],
                    date=src.get('date', 'N/A'),
                    location=src.get('location', 'N/A'),
                    url=src.get('url'),
                    relevance_score=src.get('score', 0.0)
                )
                for src in result['sources']
            ],
            confidence=result.get('confidence', 0.0),
            latency_ms=latency_ms,
            cached=False
        )
        
        # Cache la réponse
        set_cache(cache_key, response.dict(exclude={'cached'}))
        
        logger.info(f"✅ Query processed in {latency_ms}ms: {request.question[:50]}...")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Métriques Prometheus"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/rebuild-index", tags=["Admin"])
async def rebuild_index(token: str = Depends(verify_token)):
    """
    Reconstruit l'index Faiss (admin seulement).
    
    ⚠️ Opération longue, peut prendre plusieurs minutes.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    try:
        logger.info("🔄 Starting index rebuild...")
        vector_store.rebuild_index()
        logger.info("✅ Index rebuild completed")
        return {"status": "success", "message": "Index rebuilt successfully"}
    except Exception as e:
        logger.error(f"❌ Index rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =======================
# STARTUP / SHUTDOWN
# =======================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    app.state.start_time = time.time()
    logger.info("🚀 Puls-Events API starting...")
    logger.info(f"📊 Cache: {'enabled' if CACHE_ENABLED else 'disabled'}")
    logger.info(f"🤖 RAG: {'ready' if rag else 'unavailable'}")

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("👋 Puls-Events API shutting down...")
    if CACHE_ENABLED:
        redis_client.close()

# =======================
# ERROR HANDLERS
# =======================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestion des erreurs HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestion des erreurs générales"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

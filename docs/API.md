# API Reference

Cette documentation décrit l'API REST du RAG Agent IA.

## Base URL

- **Production**: `https://agent-ia-augment.onrender.com/api/v1`
- **Development**: `http://localhost:8000/api/v1`

## Authentication

L'API utilise des clés API pour l'authentification. Incluez votre clé dans le header:

```
X-API-Key: votre_cle_api
```

### Obtenir une clé API

1. Créez un compte sur le frontend
2. Allez dans **Clés API** > **Créer une clé**
3. Copiez la clé générée (elle ne sera plus visible)

---

## Endpoints

### Health & Status

#### GET /health

Vérifie l'état de l'API.

**Response 200**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "api": true,
    "mistral": true,
    "supabase": true,
    "redis": true
  }
}
```

---

### Query (Chat/RAG)

#### POST /query

Envoie une requête au système RAG.

**Headers**

- `X-API-Key`: Votre clé API (required)

**Body**

```json
{
  "question": "Comment utiliser l'API?",
  "context": "optional context",
  "model": "mistral-large-latest",
  "max_tokens": 4096,
  "temperature": 0.7
}
```

**Response 200**

```json
{
  "answer": "Voici comment utiliser l'API...",
  "sources": [
    {
      "content": "Extrait du document...",
      "source_id": "doc:123",
      "similarity": 0.92
    }
  ],
  "tokens_used": 150,
  "model_used": "mistral-large-latest"
}
```

#### POST /query/stream

Requête avec réponse en streaming (SSE).

**Headers**

- `X-API-Key`: Votre clé API
- `Accept`: text/event-stream

**Body** (même que /query)

**Response** (Server-Sent Events)

```
data: {"content": "Voici", "done": false}
data: {"content": " comment", "done": false}
data: {"content": "...", "done": true, "sources": [...]}
```

---

### API Keys Management

#### GET /keys

Liste vos clés API.

**Response 200**

```json
{
  "keys": [
    {
      "id": "uuid",
      "name": "Production Key",
      "key_prefix": "sk_live_abc...",
      "scopes": ["query", "ingest"],
      "rate_limit": 1000,
      "created_at": "2024-01-01T00:00:00Z",
      "last_used_at": "2024-01-15T12:00:00Z"
    }
  ]
}
```

#### POST /keys

Crée une nouvelle clé API.

**Body**

```json
{
  "name": "My API Key",
  "scopes": ["query", "ingest"],
  "rate_limit": 100
}
```

**Response 201**

```json
{
  "id": "uuid",
  "name": "My API Key",
  "key": "sk_live_xxxxxxxxxxxxx",
  "message": "Conservez cette clé, elle ne sera plus visible"
}
```

#### DELETE /keys/{key_id}

Révoque une clé API.

---

### Document Ingestion

#### POST /jobs/ingest

Ingère un document texte.

**Body**

```json
{
  "content": "Contenu du document à ingérer...",
  "source_filename": "document.txt",
  "source_type": "text"
}
```

**Response 202**

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job créé. Utilisez GET /jobs/{job_id} pour suivre."
}
```

#### POST /jobs/async/github

Ingère un repository GitHub (async via Redis Queue).

**Body**

```json
{
  "repo_url": "https://github.com/user/repo",
  "branch": "main"
}
```

**Response 202**

```json
{
  "job_id": "rq-job-id",
  "status": "queued",
  "queue": "ingestion"
}
```

#### GET /jobs/{job_id}

Récupère le statut d'un job.

**Response 200**

```json
{
  "id": "uuid",
  "status": "processing",
  "progress": 45,
  "chunks_total": 100,
  "chunks_processed": 45,
  "source_filename": "document.txt"
}
```

#### GET /jobs/async/{job_id}

Récupère le statut d'un job RQ (async).

**Response 200**

```json
{
  "job_id": "rq-job-id",
  "status": "running",
  "progress": 65,
  "message": "Génération des embeddings..."
}
```

---

### Analytics & Usage

#### GET /usage

Récupère les statistiques d'utilisation.

**Response 200**

```json
{
  "period": "month",
  "queries_count": 1500,
  "tokens_used": 250000,
  "documents_ingested": 25,
  "cost_estimate_usd": 12.5
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request body",
  "errors": [{ "field": "question", "message": "Field required" }]
}
```

### 401 Unauthorized

```json
{
  "detail": "Missing or invalid API key"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions",
  "required_scope": "ingest"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

Headers:

- `X-RateLimit-Limit`: 100
- `X-RateLimit-Remaining`: 0
- `X-RateLimit-Reset`: 60

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- **Free tier**: 100 requêtes/minute
- **Pro tier**: 1000 requêtes/minute
- **Enterprise**: Illimité

Les headers de rate limit sont inclus dans chaque réponse.

---

## SDKs & Examples

### Python

```python
import requests

API_KEY = "sk_live_xxx"
BASE_URL = "https://agent-ia-augment.onrender.com/api/v1"

response = requests.post(
    f"{BASE_URL}/query",
    headers={"X-API-Key": API_KEY},
    json={"question": "Comment fonctionne le RAG?"}
)

print(response.json()["answer"])
```

### JavaScript/TypeScript

```typescript
const response = await fetch(
  "https://agent-ia-augment.onrender.com/api/v1/query",
  {
    method: "POST",
    headers: {
      "X-API-Key": "sk_live_xxx",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question: "Comment fonctionne le RAG?" }),
  }
);

const data = await response.json();
console.log(data.answer);
```

### cURL

```bash
curl -X POST "https://agent-ia-augment.onrender.com/api/v1/query" \
  -H "X-API-Key: sk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{"question": "Comment fonctionne le RAG?"}'
```

---

## Changelog

### v0.1.0 (2024-01)

- Initial release
- Query endpoint with RAG
- Document ingestion
- API key management
- Rate limiting

### v0.2.0 (Coming Soon)

- Streaming responses
- Async job processing
- Multi-provider LLM support

"""
Help Chat API
=============

Endpoint dédié au chatbot d'aide FAQ.
Utilise Mistral AI avec un prompt système spécialisé.
Pas d'authentification requise - rate limiting par IP.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal

from src.config.logging_config import get_logger
from src.providers.llm import get_llm_provider

router = APIRouter(prefix="/help", tags=["Help"])
logger = get_logger(__name__)

# Rate limiting simple en mémoire (production: utiliser Redis)
_request_counts: dict[str, list[float]] = {}
RATE_LIMIT_REQUESTS = 15
RATE_LIMIT_WINDOW = 60  # secondes


# ==================== Models ====================

class ChatMessage(BaseModel):
    """Message dans l'historique de conversation."""
    role: Literal["user", "assistant"]
    content: str


class HelpChatRequest(BaseModel):
    """Requête de chat pour l'aide."""
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)


class HelpChatResponse(BaseModel):
    """Réponse du chatbot d'aide."""
    response: str
    suggestions: list[str] = []


# ==================== Prompt Système ====================

HELP_SYSTEM_PROMPT = """Tu es l'assistant d'aide de RAG Agentia, un SaaS de création d'agents IA personnalisés.

PRODUIT:
- Playground: Tester l'agent IA en direct avec des questions
- Dashboard: Voir les statistiques (requêtes, tokens, latence)
- Documents: Uploader des PDFs ou repos GitHub pour enrichir la base de connaissances
- Clés API: Créer des clés pour intégrer l'agent dans des applications
- Docs: Documentation technique de l'API

TARIFS:
- Plan Free: 100 requêtes/mois, 1 agent, 5 documents
- Plan Pro (39,99€/mois): 10 000 requêtes/mois, 3 agents, 100 documents, support prioritaire

RÈGLES:
1. Adapte toi à la langue de l'utilisateur, mais restes en français si tu ne sais pas
2. Sois concis et direct (max 3-4 phrases sauf si explication technique nécessaire)
3. Si tu ne sais pas, dis "Je ne peux pas répondre à cette question. Contactez support@rag-agentia.com"
4. Ne donne JAMAIS d'informations techniques sensibles (clés, tokens, configs internes)
5. Pour les bugs, suggère de contacter le support avec les détails de l'erreur

GUIDE RAPIDE:
- Créer une clé API: Menu "Clés API" > "Nouvelle clé" > Choisir les permissions
- Ajouter un document: Menu "Documents" > "Ajouter" > Uploader PDF ou coller URL GitHub
- Tester l'agent: Menu "Playground" > Poser une question dans le chat
- Voir les stats: Menu "Dashboard" > Graphiques d'utilisation"""


QUICK_SUGGESTIONS = [
    "Comment créer une clé API ?",
    "Comment ajouter un document ?",
    "Quels sont les tarifs ?",
    "Contact support",
]


# ==================== Rate Limiting ====================

def check_rate_limit(client_ip: str) -> bool:
    """
    Vérifie si l'IP a dépassé la limite de requêtes.
    
    Returns:
        True si autorisé, False si rate limited.
    """
    import time
    now = time.time()
    
    if client_ip not in _request_counts:
        _request_counts[client_ip] = []
    
    # Nettoyer les anciennes requêtes
    _request_counts[client_ip] = [
        ts for ts in _request_counts[client_ip] 
        if now - ts < RATE_LIMIT_WINDOW
    ]
    
    if len(_request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    _request_counts[client_ip].append(now)
    return True


# ==================== Routes ====================

@router.post("/chat", response_model=HelpChatResponse)
async def help_chat(
    request: Request,
    body: HelpChatRequest,
) -> HelpChatResponse:
    """
    Chat avec l'assistant d'aide.
    
    - Pas d'authentification requise
    - Rate limit: 15 req/min par IP
    - Contexte: 10 derniers messages maximum
    """
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de requêtes. Réessayez dans quelques secondes."
        )
    
    try:
        # Utiliser le provider Mistral
        llm_provider = get_llm_provider("mistral")
        
        # Construire messages sans le system (passé séparément)
        chat_messages = []
        for msg in body.history[-10:]:
            chat_messages.append({"role": msg.role, "content": msg.content})
        chat_messages.append({"role": "user", "content": body.message})
        
        # generate() retourne LLMResponse, pas str
        llm_response = await llm_provider.generate(
            messages=chat_messages,
            system_prompt=HELP_SYSTEM_PROMPT,
        )
        
        response_text = llm_response.content
        
        logger.info(
            "Help chat response generated",
            message_length=len(body.message),
            response_length=len(response_text),
            tokens_used=llm_response.tokens_input + llm_response.tokens_output,
            client_ip=client_ip,
        )
        
        return HelpChatResponse(
            response=response_text,
            suggestions=QUICK_SUGGESTIONS,
        )
        
    except Exception as e:
        logger.error("Help chat error", error=str(e))
        # Fallback gracieux
        return HelpChatResponse(
            response="Désolé, je rencontre un problème technique. Contactez support@rag-agentia.com pour assistance.",
            suggestions=QUICK_SUGGESTIONS,
        )


@router.get("/suggestions")
async def get_suggestions() -> dict:
    """Retourne les suggestions rapides."""
    return {"suggestions": QUICK_SUGGESTIONS}

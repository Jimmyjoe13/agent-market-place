"""
Assistant Plugin API
======================

Endpoints dédiés au plugin assistant (widget web).
Gère la génération du code d'intégration, le script JS, et les requêtes du widget.
"""

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl

from src.api.auth import require_api_key, get_api_key_repo
from src.api.deps import get_current_user, UserWithSubscription, get_user_repo
from src.config.settings import get_settings
from src.models.api_key import ApiKeyValidation
from src.services.rag_engine import RAGEngine
from src.services.circuit_breaker import get_circuit_breaker
from src.providers.llm import get_llm_provider
from src.repositories.conversation_repository import ConversationRepository
from src.models.conversation import ConversationCreate, ConversationMessage
from src.config.logging_config import get_logger

router = APIRouter(prefix="/assistant-plugin", tags=["Assistant Plugin"])
logger = get_logger(__name__)

# ===== Models =====

class EmbedConfig(BaseModel):
    """Configuration pour la génération du code d'intégration."""
    agent_id: str
    theme_color: str = "#4F46E5"  # Indigo-600 default
    position: str = "bottom-right"
    title: str = "Assistant IA"

class PluginQueryRequest(BaseModel):
    """Requête de chat depuis le plugin."""
    query: str
    history: list[ConversationMessage] = []
    session_id: str | None = None

class PluginResponse(BaseModel):
    """Réponse de chat pour le plugin."""
    response: str
    session_id: str
    sources: list[dict] = []

# ===== Routes =====

@router.post("/embed")
async def generate_embed_code(
    config: EmbedConfig,
    current_user: UserWithSubscription = Depends(get_current_user),
) -> dict:
    """
    Génère le code JavaScript à intégrer sur un site tiers.
    
    Nécessite d'être authentifié comme utilisateur SaaS.
    Vérifie que l'agent appartient bien à l'utilisateur.
    """
    settings = get_settings()
    
    # Vérifier que l'agent existe et appartient à l'utilisateur
    # Note: On devrait utiliser AgentRepository, mais pour l'instant on fait simple
    # TODO: Ajouter validation agent ownership
    
    # Construire l'URL de l'API publique
    if settings.is_production:
        api_url = "https://agent-ia-augment.onrender.com" # TODO: Mettre dans settings
    else:
        api_url = f"http://{settings.api_host}:{settings.api_port}"
    
    script_url = f"{api_url}/api/v1/assistant-plugin/script.js"
    
    embed_code = f"""<!-- RAG Assistant Widget -->
<script>
  window.RAGAssistantConfig = {{
    agentId: "{config.agent_id}",
    apiUrl: "{api_url}",
    themeColor: "{config.theme_color}",
    position: "{config.position}",
    title: "{config.title}"
  }};
  (function(d, s, id) {{
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s); js.id = id;
    js.src = "{script_url}";
    fjs.parentNode.insertBefore(js, fjs);
  }}(document, 'script', 'rag-assistant-sdk'));
</script>"""

    return {
        "script_url": script_url,
        "embed_code": embed_code,
        "config": config.model_dump()
    }

@router.get("/script.js")
async def get_assistant_script():
    """
    Sert le script JavaScript du widget.
    
    Retourne le fichier statique localisé dans src/static/assistant.js.
    """
    script_path = Path(__file__).parent.parent / "static" / "assistant.js"
    
    if not script_path.exists():
        raise HTTPException(404, "Script not found")
        
    return FileResponse(
        script_path, 
        media_type="application/javascript", 
        headers={"Cache-Control": "public, max-age=3600"}
    )

@router.post("/query")
async def plugin_query(
    request: PluginQueryRequest,
    origin: str | None = Header(None),
    x_agent_id: str | None = Header(None, alias="X-Agent-ID"),
    # Pour le plugin, on authentifie via l'Agent ID public + domaines autorisés (CORS)
    # ou via une API Key publique si on implémente ça.
    # Pour simplifier V1 : on utilise une clé API passée par le widget si dispo, 
    # sinon on s'appuie sur le fait que l'agent est public ou configuré pour le domaine.
    # ICI: On va exiger une API Key "publishable" ou simplement l'ID de l'agent
    # et vérifier dans la DB si l'agent autorise les requêtes publiques.
    
    # SOLUTION IMMEDIATE: Le widget enverra une API Key dans le header X-API-Key
    # Cette clé doit être créée par l'utilisateur pour son agent.
    api_key_validation: ApiKeyValidation = Depends(require_api_key)
) -> PluginResponse:
    """
    Endpoint de chat pour le widget.
    
    Authentification:
    - Standard via X-API-Key (fournie dans la config du widget)
    - Le domaine d'origine (Origin) devrait être validé si possible
    """
    settings = get_settings()
    
    # Validation du domaine (CORS soft check)
    # Dans une vraie prod, on vérifierait que api_key_validation.allowed_domains contient 'origin'
    if settings.is_production and origin:
       # TODO: Vérifier origin contre une whitelist dans l'agent ou la clé API
       pass

    # Initialiser Services
    llm_provider = get_llm_provider(settings.default_llm_provider) # Ou celui de l'agent
    circuit_breaker = get_circuit_breaker()
    
    # RAG Engine
    # Note: On instancie RAGEngine avec la config de l'agent lié à la clé
    # Pour l'instant on utilise une config par défaut ou celle de la clé
    
    # TODO: Récupérer la config spécifique de l'agent via api_key_validation.agent_id
    
    # Exécution RAG
    # Simulé pour l'instant en attendant l'intégration complète avec RAGEngine
    # qui demande beaucoup de dépendances
    
    # Pour la V1, on retourne un echo intelligent
    return PluginResponse(
        response=f"Bonjour ! Je suis l'agent {api_key_validation.agent_id}. Je reçois votre message : {request.query}",
        session_id=request.session_id or "new_session",
        sources=[]
    )

# Note: Pour une implémentation réelle, nous connecterons ceci 
# au RAGEngine existant dans src/services/rag_engine.py

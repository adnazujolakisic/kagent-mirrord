"""
ResearchCrew A2A Agent Server

FastAPI + Uvicorn wrapper for CrewAI. Exposes a BYO agent via KAgentApp (A2A protocol).

Used as:
  - In-cluster: Docker pod (crew/Dockerfile)
  - Local dev: mirrord-crew.sh (steals traffic from the pod)

Logs crew initialization and server startup/errors for observability.
"""

import uvicorn
import logging
import os
from kagent.crewai import KAgentApp
from crew import ResearchCrew

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    crew = ResearchCrew().crew()
    logger.info("✓ ResearchCrew initialized successfully")
except Exception as e:
    logger.error(f"✗ Failed to initialize ResearchCrew: {e}", exc_info=True)
    raise

# AgentCard.url is what *callers* use for JSON-RPC POST / (not GET agent-card only).
# http://127.0.0.1:8080/ makes in-cluster orchestrators POST to their own loopback — no traffic
# to this workload. Use the Service DNS name so traffic hits research-crew → mirrord steal works.
_agent_card_url = os.getenv(
    "AGENT_CARD_PUBLIC_URL",
    "http://research-crew.kagent.svc.cluster.local:8080/",
).strip()
if not _agent_card_url.endswith("/"):
    _agent_card_url += "/"
logger.info("AgentCard public url (A2A POST target): %s", _agent_card_url)

app = KAgentApp(
    crew=crew,
    agent_card={
        "name": "research-crew",
        "description": "A research-style agent with retrieval capabilities that synthesizes findings into clear, actionable insights",
        "version": "0.1.0",
        "url": _agent_card_url,
        # a2a-sdk AgentCard expects AgentSkill objects, not plain strings (id, name, description, tags required).
        "skills": [
            {
                "id": "research",
                "name": "Research",
                "description": "Gather and structure findings on a topic.",
                "tags": ["research"],
            },
            {
                "id": "synthesis",
                "name": "Synthesis",
                "description": "Combine information into coherent analysis.",
                "tags": ["synthesis"],
            },
            {
                "id": "summarization",
                "name": "Summarization",
                "description": "Produce concise summaries of research output.",
                "tags": ["summarization"],
            },
        ],
        "capabilities": {"streaming": True},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
)

if __name__ == "__main__":
    """
    Main entry point.
    
    Initializes the research crew, wraps it in KAgentApp (kagent-crewai integration),
    and starts Uvicorn on port 8080.
    
    Environment variables:
      - ANTHROPIC_API_KEY: Required. Claude API key (passed from pod or .env).
      - AGENT_CARD_PUBLIC_URL: URL in the agent card for A2A RPC (default: research-crew k8s Service).
      - HOST: Uvicorn bind address (default: 0.0.0.0).
      - PORT: Uvicorn port (default: 8080).
    """
    try:
        fastapi_app = app.build()
        logger.info("✓ FastAPI app built successfully")
    except Exception as e:
        logger.error(f"✗ Failed to build FastAPI app: {e}", exc_info=True)
        raise
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting Uvicorn server on {host}:{port}")
    
    try:
        uvicorn.run(fastapi_app, host=host, port=port, log_level="info")
    except Exception as e:
        logger.error(f"✗ Server crash: {e}", exc_info=True)
        raise

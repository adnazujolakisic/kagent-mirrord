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

app = KAgentApp(
    crew=crew,
    agent_card={
        "name": "research-crew",
        "description": "A research-style agent with retrieval capabilities that synthesizes findings into clear, actionable insights",
        "version": "0.1.0",
        "url": "http://127.0.0.1:8080/",
        "skills": ["research", "synthesis", "summarization"],
        "capabilities": {"streaming": True, "tools": True},
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

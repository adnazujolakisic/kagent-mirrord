import uvicorn
from kagent.crewai import KAgentApp
from crew import ResearchCrew

app = KAgentApp(
    crew=ResearchCrew().crew(),
    agent_card={
        "name": "research-crew",
        "description": "A research agent that searches the web and summarizes findings",
        "version": "0.1.0",
        "capabilities": {"streaming": True},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    },
)

if __name__ == "__main__":
    fastapi_app = app.build()
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8080)

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool
import json

"""
ResearchCrew: A CrewAI-based multi-agent crew for research synthesis.

This module implements a lightweight research crew with two agents:
  1. Researcher: Gathers facts using the retrieve_context tool
  2. Summarizer: Distills findings into concise summaries

Used by crew/main.py to handle A2A requests from kagent orchestrator.
Edit this file to demo live agent substitution (no rebuild, no redeploy).
"""

# ANTHROPIC_API_KEY in the environment — explicit Anthropic provider (bare model strings
# in CrewAI 1.6 default to OpenAI). Haiku keeps RPM down (orchestrator uses Haiku too in claude-model-config).
_CREW_LLM = LLM(model="claude-haiku-4-5", provider="anthropic")


# ===== Mock Retrieval Tool =====
# Demonstrates dynamic tool injection: add a capability to the agent without rebuilding the pod.
# In a real scenario, this would call a vector DB, S3, or web search API.
@tool
def retrieve_context(query: str) -> str:
    """
    Retrieve relevant context or documents for a given query.
    
    This is a mock implementation for demo purposes. In production, this would
    query a real knowledge base, vector DB, or web search API.
    
    Args:
        query: The search query or topic
        
    Returns:
        A JSON string with relevant facts and sources
    """
    # Mock knowledge base
    knowledge_base = {
        "kagent": {
            "facts": [
                "kagent is an open-source orchestration framework for multi-agent AI systems",
                "It supports declarative and BYO (Bring Your Own) agent patterns",
                "Agents communicate via A2A (Agent-to-Agent) HTTP protocol with agent cards",
                "kagent integrates with CrewAI, LangChain, and other agent frameworks"
            ],
            "sources": ["https://kagent.dev", "kagent handbook", "community examples"]
        },
        "mirrord": {
            "facts": [
                "mirrord is a tool by Metalbear that intercepts and duplicates traffic to remote targets",
                "It supports 'steal' mode: redirect traffic from cluster to local process",
                "Useful for rapid iteration on Kubernetes workloads without rebuilds",
                "Works at the network layer via eBPF on Linux, or interceptor on macOS"
            ],
            "sources": ["https://mirrord.dev", "mirrord docs", "engineering blog"]
        },
        "a2a": {
            "facts": [
                "A2A (Agent-to-Agent) is a protocol for agents to communicate over HTTP",
                "Uses agent card (/.well-known/agent-card.json) for discovery",
                "Allows composition of agents without tight coupling",
                "Foundation for multi-agent orchestration in kagent"
            ],
            "sources": ["kagent spec", "A2A RFC", "protocol docs"]
        }
    }
    
    # Simple keyword match against mock knowledge base
    query_lower = query.lower()
    results = {}
    
    for topic, data in knowledge_base.items():
        if topic in query_lower or any(topic in fact for fact in data["facts"]):
            results[topic] = data
    
    if not results:
        # If no exact match, return all facts as fallback
        results = knowledge_base
    
    return json.dumps(results, indent=2)


class ResearchCrew:
    """
    Instantiates and configures a CrewAI-based research crew.
    
    The crew consists of:
      - Researcher: Uses retrieve_context tool to gather facts
      - Summarizer: Distills findings into 1-2 sentences
    
    Configured for token efficiency (Haiku, sub-200-word output).
    
    Usage:
        crew_obj = ResearchCrew()
        crew = crew_obj.crew()
        result = crew.kickoff(inputs={"input": "What is kagent?"})
    
    Demo: Edit agent definitions below and restart mirrord-crew.sh to see
    changes instantly in the live orchestrator call chain (zero rebuild).
    """
    
    def crew(self) -> Crew:
        """
        Instantiate the research crew.
        
        Returns:
            Crew: A CrewAI Crew instance with researcher and summarizer agents,
                  configured for sequential task execution.
        """
        researcher = Agent(
            role="Research Analyst",
            goal="Find concise, relevant facts using the retrieve_context tool. Keep response under 200 words.",
            backstory="""You are efficient and concise. Use retrieve_context to gather facts.
            Synthesize into 2-3 clear points. No fluff. Token efficiency matters.""",
            tools=[retrieve_context],
            verbose=True,
            llm=_CREW_LLM,
        )

        summarizer = Agent(
            role="Concise Summarizer",
            goal="Create a 1-2 sentence summary. Be brutally brief.",
            backstory="""You distill findings into one or two clear sentences.
            No elaboration. No fluff. Clarity over completeness.""",
            tools=[],
            verbose=True,
            llm=_CREW_LLM,
        )

        research_task = Task(
            description="Research the topic: {input}. Use retrieve_context. Keep it brief (under 200 words).",
            expected_output="2-3 key facts with sources. Concise.",
            agent=researcher,
        )

        summary_task = Task(
            description="Summarize the research into ONE sentence. That's it.",
            expected_output="A single, clear sentence capturing the essence.",
            agent=summarizer,
            context=[research_task],
        )

        return Crew(
            agents=[researcher, summarizer],
            tasks=[research_task, summary_task],
            process=Process.sequential,
            verbose=True,
        )


# ---
# DEMO MOMENT: Live Agent Substitution Examples
# ===============================================
#
# Example 1: Replace the researcher with one that ALWAYS uses retrieval:
#
# researcher = Agent(
#     role="Senior Research Analyst",
#     goal="ALWAYS retrieve context first, then synthesize",
#     backstory="""You are thorough. Always call retrieve_context before making claims.""",
#     tools=[retrieve_context],
#     verbose=True,
#     llm=_CREW_LLM,
# )
#
# Example 2: Replace the summarizer to be sarcastic:
#
# summarizer = Agent(
#     role="Sarcastic Summarizer",
#     goal="Respond in exactly one sarcastic sentence. Never more.",
#     backstory="You are deeply unimpressed by everything.",
#     tools=[],
#     verbose=True,
#     llm=_CREW_LLM,
# )
#
# HOW TO DEMO:
# 1. Edit the crew definition above (swap in one of these agents)
# 2. Restart ./scripts/mirrord-crew.sh (Ctrl+C, then re-run)
# 3. Run: kagent invoke --agent orchestrator --task "Research what kagent is"
# 4. See the behavior change — same cluster, same pods, different agent logic.
# 5. No docker build. No kubectl rollout. That's runtime agent substitution.
# ---

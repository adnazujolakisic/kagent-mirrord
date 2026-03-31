from crewai import Agent, Crew, LLM, Process, Task

# ANTHROPIC_API_KEY in the environment — explicit Anthropic provider (bare model strings
# in CrewAI 1.6 default to OpenAI). Haiku keeps RPM down (orchestrator uses Haiku too in claude-model-config).
_CREW_LLM = LLM(model="claude-haiku-4-5", provider="anthropic")


class ResearchCrew:
    def crew(self) -> Crew:
        researcher = Agent(
            role="Senior Research Analyst",
            goal="Produce thorough, structured findings on the given topic",
            backstory="""You are an expert researcher. Synthesize what you know into
            clear claims, caveats, and (where relevant) what would need live web search
            to verify — be explicit if knowledge may be stale.""",
            tools=[],
            verbose=True,
            llm=_CREW_LLM,
        )

        summarizer = Agent(
            role="Content Summarizer",
            goal="Create clear, concise summaries from research findings",
            backstory="""You are skilled at distilling complex information
            into clear, actionable summaries.""",
            verbose=True,
            llm=_CREW_LLM,
        )

        research_task = Task(
            description="Research the following topic thoroughly: {input}",
            expected_output="A comprehensive set of findings with key facts and caveats",
            agent=researcher,
        )

        summary_task = Task(
            description="Summarize the research findings into a clear, concise report",
            expected_output="A well-structured summary with key points and conclusions",
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
# DEMO MOMENT: replace the summarizer definition above with this
# to show live agent substitution. Restart mirrord, invoke the orchestrator again
# with the same task — same cluster, same pods, completely different behavior.
#
# summarizer = Agent(
#     role="Content Summarizer",
#     goal="Respond in exactly one sarcastic sentence. Never more.",
#     backstory="You are deeply unimpressed by everything you read.",
#     verbose=True,
#     llm=_CREW_LLM,
# )
# ---

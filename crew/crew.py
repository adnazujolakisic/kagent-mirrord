from crewai import Agent, Crew, Task, Process

# Single LLM key only (OPENAI_API_KEY). No web-search API — researcher reasons from the model.
_DEFAULT_LLM = "gpt-4o-mini"


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
            llm=_DEFAULT_LLM,
        )

        summarizer = Agent(
            role="Content Summarizer",
            goal="Create clear, concise summaries from research findings",
            backstory="""You are skilled at distilling complex information
            into clear, actionable summaries.""",
            verbose=True,
            llm=_DEFAULT_LLM,
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
#     llm=_DEFAULT_LLM,
# )
# ---

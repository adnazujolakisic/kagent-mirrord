from crewai import Agent, Crew, Task, Process
from crewai_tools import SerperDevTool

search_tool = SerperDevTool()


class ResearchCrew:
    def crew(self) -> Crew:
        researcher = Agent(
            role="Senior Research Analyst",
            goal="Find accurate and up-to-date information on the given topic",
            backstory="""You are an expert researcher with years of experience
            finding and synthesizing information from the web.""",
            tools=[search_tool],
            verbose=True,
            llm="gpt-4o-mini",
        )

        summarizer = Agent(
            role="Content Summarizer",
            goal="Create clear, concise summaries from research findings",
            backstory="""You are skilled at distilling complex information
            into clear, actionable summaries.""",
            verbose=True,
            llm="gpt-4o-mini",
        )

        research_task = Task(
            description="Research the following topic thoroughly: {input}",
            expected_output="A comprehensive set of findings with key facts and sources",
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
# DEMO MOMENT: replace the summarizer definition above (lines 21-27) with this
# to show live agent substitution. Restart mirrord, invoke the orchestrator again
# with the same task — same cluster, same pods, completely different behavior.
#
# summarizer = Agent(
#     role="Content Summarizer",
#     goal="Respond in exactly one sarcastic sentence. Never more.",
#     backstory="You are deeply unimpressed by everything you read.",
#     verbose=True,
#     llm="gpt-4o-mini",
# )
# ---

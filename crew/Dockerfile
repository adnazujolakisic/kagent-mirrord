FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system crewai anthropic kagent-crewai uvicorn

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]

def foundation_capabilities() -> list[dict[str, str]]:
    return [
        {"name": "FastAPI API", "status": "ready"},
        {"name": "React console", "status": "ready"},
        {"name": "PostgreSQL data layer", "status": "planned"},
        {"name": "Playwright browser worker", "status": "planned"},
        {"name": "LangGraph workflows", "status": "planned"},
    ]



"""
FILE CONTRACT: deps.py

Goal: Central place for FastAPI dependencies.
Requirements:
- For now, stub DB session dependency (yield None).
- Add docstring explaining placeholder role (will be expanded in Phase 3 for Postgres).
"""

def get_db():
    """
    Placeholder for a database session dependency.
    In Phase 3, this will yield a real Postgres session for use in routes.
    For now, yields None to satisfy dependency injection signatures.
    """
    yield None

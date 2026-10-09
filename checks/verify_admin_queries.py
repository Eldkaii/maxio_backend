"""Compile dashboard queries for PostgreSQL without any database connection.

Run directly, never through the project's destructive pytest fixtures.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from datetime import date, datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.orm import Query, Session
from sqlalchemy.dialects import postgresql
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "before_cursor_execute")
def reject_sql(*args, **kwargs):
    raise AssertionError("Database execution is prohibited in this check")


from src.services.admin_dashboard_service import dashboard_metrics, list_entities, entity_detail
from src.services.league_service import create_league
from src.models import Player, Match, League, AchievementDefinition
from src.routers.user_router import admin_dashboard, admin_entities, admin_entity
from fastapi import HTTPException

compiled = []


class CompileOnlyQuery(Query):
    def all(self):
        compiled.append(str(self.statement.compile(dialect=postgresql.dialect())))
        return []

    def count(self):
        self.all()
        return 0

    def __iter__(self):
        return iter(self.all())


class CompileOnlySession(Session):
    def get(self, model, ident, **kwargs):
        samples = {
            Player: Player(id=1, name="Example", is_bot=False, elo=1000, cant_partidos=0),
            Match: Match(id=1, date=datetime(2026, 1, 1), max_players=10, is_draw=True),
            League: League(id=1, name="League", start_date=date(2026, 1, 1), end_date=date(2027, 1, 1)),
            AchievementDefinition: AchievementDefinition(id=1, name="Award", key="award", conditions={}),
        }
        return samples[model]


db = CompileOnlySession(query_cls=CompileOnlyQuery)  # deliberately unbound
for days in (7, 30, 365):
    result = dashboard_metrics(db, days)
    assert len(result["dates"]) == days
    assert all(len(s["values"]) == days and not any(s["values"]) for c in result["charts"] for s in c["series"])
for kind in ("players", "matches", "leagues", "awards"):
    for term in ("", "name_%", "123"):
        assert list_entities(db, kind, term)["items"] == []
    assert entity_detail(db, kind, 1)["id"] == 1
for endpoint, args in ((admin_dashboard, {}), (admin_entities, {"kind": "players"}), (admin_entity, {"kind": "players", "entity_id": 1})):
    try:
        endpoint(**args, current_user=SimpleNamespace(is_admin=False), db=db)
        raise AssertionError("Non-admin accepted")
    except HTTPException as error:
        assert error.status_code == 403

# Exercise league creation by the bootstrap administrator (no player profile).
fake = MagicMock()
fake.query.return_value.filter.return_value.all.return_value = []
with patch("src.services.league_service.get_league_or_404", return_value="created"):
    result = create_league(fake, SimpleNamespace(is_admin=True, player=None), "Admin league", start_date=date(2026, 1, 1), end_date=date(2027, 1, 1))
    assert result == "created"
    created = fake.add.call_args_list[0].args[0]
    assert isinstance(created, League) and created.owner_player_id is None
    assert fake.add.call_count == 1  # no phantom league member for admin
print(f"OK: {len(compiled)} PostgreSQL query compilations; empty series; admin guards; admin league creation. No database execution.")

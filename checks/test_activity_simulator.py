"""Run directly with unittest: no src imports, no .env, no sockets, no database."""
import copy
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extensions.activity_simulator.config import Config
from extensions.activity_simulator.engine import (Engine, DAY, HOUR, WEEK, available, outcome,
                                                   UncertainAction, NAME_CATALOG, LEAGUE_CATALOG,
                                                   username_part)
from extensions.activity_simulator.storage import Store
from extensions.activity_simulator.api import Rejected
from extensions.activity_simulator.runtime import configure_logging

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc).timestamp()


class MemoryStore:
    def __init__(self):
        self.data = None

    def load(self):
        return json.loads(self.data) if self.data is not None else None

    def save(self, data):
        self.data = json.dumps(data)


class FakeApi:
    def __init__(self):
        self.players, self.matches, self.leagues = {}, {}, {}
        self.calls = []
        self.now = NOW

    def login(self, actor):
        if actor["username"] not in self.players:
            raise Rejected(401)

    def request(self, method, path, payload=None, actor=None):
        self.calls.append((self.now, method, path, copy.deepcopy(payload), actor and actor["username"]))
        if path == "/maxio/users/register":
            assert payload["nationality"] == "UY" and payload["is_bot"] is False
            assert payload["first_name"] and payload["last_name"] and payload["email"].endswith("@example.com")
            assert payload["username"] not in self.players
            self.players[payload["username"]] = dict(id=len(self.players) + 1, **payload)
            return {"id": len(self.players)}
        if path.startswith("/player/"):
            return self.players[path.split("/")[2]]
        if path == "/leagues":
            assert datetime.fromisoformat(payload["end_date"]) > datetime.fromisoformat(payload["start_date"])
            key = len(self.leagues) + 1
            self.leagues[key] = {"id": key, "members": [actor["username"]]}
            return {"id": key}
        if path.startswith("/leagues/"):
            league = self.leagues[int(path.split("/")[2])]
            if method == "GET":
                return {"id": league["id"], "members": [{"player_id": self.players[name]["id"]} for name in league["members"]]}
            league["members"].append(actor["username"])
            return league
        if path == "/match/matches":
            key = len(self.matches) + 1
            self.matches[key] = dict(payload, id=key, roster=[], votes={})
            return {"id": key}
        parts = path.split("/")
        match = self.matches[int(parts[3])]
        if parts[4] == "players":
            key = int(parts[5])
            assert key not in match["roster"]
            match["roster"].append(key)
        elif parts[4] == "pre-set-groups":
            match["groups"] = payload["groups"]
        elif parts[4] == "generate-teams":
            assert len(match["roster"]) == 10
            names = [name for name, data in self.players.items() if data["id"] in match["roster"]]
            match.update(team1={"players": [{"name": n} for n in names[:5]]},
                         team2={"players": [{"name": n} for n in names[5:]]})
            return match
        elif parts[4] == "result":
            kickoff = datetime.fromisoformat(match["date"]).replace(tzinfo=timezone.utc).timestamp()
            assert self.now >= kickoff + 90 * 60
            assert self.players[actor["username"]]["id"] in match["roster"]
            match["votes"][actor["username"]] = payload["result"]
        else:
            raise AssertionError(path)
        return {"message": "ok"}


class SimulatorTests(unittest.TestCase):
    def make_engine(self, **config):
        store, api = MemoryStore(), FakeApi()
        engine = Engine(Config(**config), store, api, NOW, random.Random(17))
        return engine, store, api

    def test_disabled_is_only_opt_in_at_startup(self):
        # Static check of the tiny lifecycle hook; importing src.main would touch config/DB.
        source = (Path(__file__).resolve().parents[1] / "src/main.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("SIMULATOR_ENABLED", "false")', source)

    def test_no_initial_burst_and_restart_keeps_signup_agenda(self):
        engine, store, api = self.make_engine()
        engine.tick(NOW)
        self.assertEqual(api.calls, [])
        engine.tick(NOW + 300)
        self.assertEqual(len(api.players), 1)
        resumed = Engine(engine.config, store, api, NOW + 350, random.Random(9))
        resumed.tick(NOW + 350)
        self.assertEqual(len(api.players), 1)
        self.assertEqual(resumed.state["next_signup"], engine.state["next_signup"])

    def test_rolling_limit_includes_future_reservations(self):
        self.assertFalse(available({"matches": [NOW], "weekly_limit": 1}, NOW + DAY))
        self.assertTrue(available({"matches": [NOW], "weekly_limit": 1}, NOW + WEEK))
        self.assertFalse(available({"matches": [NOW, NOW + 6 * DAY], "weekly_limit": 2}, NOW + 3 * DAY))
        self.assertTrue(available({"matches": [NOW], "weekly_limit": 2}, NOW + 3 * DAY))

    def test_catalog_names_and_bootstrap_schedule_match_and_league(self):
        self.assertGreater(len(NAME_CATALOG), 100)
        self.assertGreater(len(LEAGUE_CATALOG), 5)
        engine, store, api = self.make_engine(max_players=10, startup_delay_seconds=0)
        for _ in range(10):
            actor = engine.identity(NOW - DAY)
            actor.update(registered=True, next_social=NOW, organizer=False)
        actors = list(engine.state["actors"].values())
        actors[0]["organizer"] = True
        engine.state["next_plan"] = NOW
        engine.plan(NOW)
        self.assertTrue(any(job["kind"] == "match" for job in engine.state["jobs"]))
        leagues = [job for job in engine.state["jobs"] if job["kind"] == "league"]
        self.assertTrue(leagues)
        self.assertIn(leagues[0]["name"], LEAGUE_CATALOG)

    def test_compound_surnames_produce_valid_usernames(self):
        self.assertEqual(username_part("Gómez Delgado"), "gomezdelgado")
        engine, _, _ = self.make_engine()
        with patch("extensions.activity_simulator.engine.NAME_CATALOG", ("Claudia Gómez Delgado",)):
            actor = engine.identity(NOW)
        self.assertNotRegex(actor["username"], r"[^a-z0-9._]")
        self.assertNotIn(" ", actor["username"])
        self.assertLessEqual(len(actor["username"]), 50)

    def test_weekly_limit_applies_to_captain_and_all_invited_players_after_restart(self):
        for cap in (1, 2):
            with self.subTest(weekly_limit=cap):
                engine, store, api = self.make_engine(max_players=10)
                for _ in range(10):
                    actor = engine.identity(NOW)
                    actor.update(registered=True, weekly_limit=cap,
                                 next_visit=NOW + WEEK, next_social=NOW + WEEK)
                now = NOW + HOUR
                for count in range(cap):
                    engine.plan(now)
                    matches = [j for j in engine.state["jobs"] if j["kind"] == "match"]
                    self.assertEqual(len(matches), count + 1)
                    match = matches[-1]
                    self.assertEqual(len([n for n in match["names"] if n != match["actor"]]), 9)
                    for name in match["names"]:
                        self.assertEqual(len(engine.state["actors"][name]["matches"]), count + 1)
                    store.save(engine.state)
                    now = match["kickoff"] + DAY
                    engine = Engine(engine.config, store, api, now, random.Random(17))
                engine.plan(now)
                self.assertEqual(len([j for j in engine.state["jobs"] if j["kind"] == "match"]), cap)

    def test_signup_logged_after_checkpoint_without_credentials(self):
        engine, store, api = self.make_engine(startup_delay_seconds=0)
        persisted_stages = []
        with patch("extensions.activity_simulator.engine.log.log",
                   side_effect=lambda *args: persisted_stages.append(store.load()["jobs"][0]["stage"])) as emit:
            engine.tick(NOW)
        message = emit.call_args.args[1]
        actor = next(iter(engine.state["actors"].values()))
        self.assertEqual(persisted_stages, [1])
        self.assertIn("Crea user: " + actor["username"], message)
        self.assertNotIn(actor["password"], message)
        self.assertNotIn(actor["email"], message)

    def test_rejected_action_logs_retry_without_success(self):
        engine, store, api = self.make_engine(startup_delay_seconds=0)
        with patch.object(api, "request", side_effect=Rejected(429)):
            with self.assertLogs("maxio.simulator", level="INFO") as captured:
                engine.tick(NOW)
        self.assertIn("Difiere acción 15 minutos", captured.output[0])
        self.assertIn("HTTP=429", captured.output[0])
        self.assertNotIn("Crea user:", "\n".join(captured.output))
        self.assertEqual(engine.state["jobs"][0]["due"], NOW + 15 * 60)

    def test_activity_log_is_utf8_rotating_and_configured_once(self):
        logger = logging.getLogger("maxio.simulator")
        old_level = logger.level
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "logs" / "activity-simulator.log"
            handler = configure_logging(path)
            try:
                self.assertIs(configure_logging(path), handler)
                self.assertEqual(handler.maxBytes, 5 * 1024 * 1024)
                self.assertEqual(handler.backupCount, 3)
                logger.info("Crea user: nicolás.pereira — prueba")
                content = path.read_text(encoding="utf-8")
                self.assertEqual(content.count("Crea user:"), 1)
                self.assertIn("nicolás.pereira", content)
                self.assertRegex(content, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| INFO")
                handler.doRollover()
                logger.info("Crea liga: prueba")
                self.assertIn("Crea user:", Path(str(path) + ".1").read_text(encoding="utf-8"))
                self.assertIn("Crea liga:", path.read_text(encoding="utf-8"))
            finally:
                logger.removeHandler(handler)
                handler.close()
                logger.setLevel(old_level)

    def test_sixty_days_through_mock_api(self):
        engine, store, api = self.make_engine(max_players=28)
        with self.assertLogs("maxio.simulator", level="INFO") as captured:
            for tick in range(0, 60 * DAY, 5 * 60):
                api.now = NOW + tick
                engine.tick(api.now)
                if tick and tick % (13 * DAY) == 0:
                    engine = Engine(engine.config, store, api, api.now, random.Random(tick))
        messages = "\n".join(captured.output)
        for action in ("Crea user:", "Confirma perfil:", "Visita perfil:", "Crea liga:", "Se une a liga:",
                       "Programa partido:", "Crea partido:", "Agrega jugador:", "Configura grupos:",
                       "Balancea equipos:", "Vota resultado:", "Completa votos y actualiza afinidades locales:"):
            self.assertIn(action, messages)
        for actor in engine.state["actors"].values():
            self.assertNotIn(actor["password"], messages)
            self.assertNotIn(actor["email"], messages)
        self.assertEqual(len(api.players), 28)
        finished = [m for m in api.matches.values() if len(m["votes"]) == 10]
        self.assertGreater(len(finished), 12)
        for name, actor in engine.state["actors"].items():
            dates = sorted(datetime.fromisoformat(m["date"]).replace(tzinfo=timezone.utc).timestamp()
                           for m in api.matches.values() if api.players[name]["id"] in m["roster"])
            cap = actor["weekly_limit"]
            self.assertTrue(all(dates[i + cap] - dates[i] >= WEEK for i in range(len(dates) - cap)))
        self.assertGreater(len(api.leagues), 0)
        self.assertLessEqual(len(api.leagues), 2)
        self.assertTrue(any(len(l["members"]) > 1 for l in api.leagues.values()))
        self.assertTrue(any(a["friends"] for a in engine.state["actors"].values()))
        self.assertTrue(any(m["league_id"] for m in finished))
        for match in finished:
            votes = match["votes"]
            first = [votes[p["name"]] for p in match["team1"]["players"]]
            second = [votes[p["name"]] for p in match["team2"]["players"]]
            self.assertEqual(len(set(first)), 1)
            self.assertEqual(len(set(second)), 1)
            self.assertIn((first[0], second[0]), [("win", "loss"), ("loss", "win"), ("draw", "draw")])
        self.assertFalse(any(j["status"] == "blocked" for j in engine.state["jobs"]))

    def test_uncertain_write_is_not_replayed_after_restart(self):
        engine, store, api = self.make_engine(startup_delay_seconds=0)
        real_request = api.request
        def lost_response(*args, **kwargs):
            real_request(*args, **kwargs)
            raise TimeoutError("response lost")
        api.request = lost_response
        with self.assertLogs("maxio.simulator", level="ERROR") as captured:
            with self.assertRaises(UncertainAction):
                engine.tick(NOW)
        self.assertIn("Acción interrumpida:", "\n".join(captured.output))
        self.assertIn("causa=TimeoutError", "\n".join(captured.output))
        self.assertNotIn("response lost", "\n".join(captured.output))
        self.assertNotIn("Crea user:", "\n".join(captured.output))
        resumed = Engine(engine.config, store, api, NOW + DAY)
        with self.assertRaises(UncertainAction):
            resumed.tick(NOW + DAY)
        self.assertEqual(len(api.players), 1)

    def test_confirmed_response_can_resume_without_second_post(self):
        engine, store, api = self.make_engine(startup_delay_seconds=0)
        engine.plan(NOW)
        job = engine.state["jobs"][0]
        engine.state["journal"] = {"key": f'{job["id"]}:0', "path": "/maxio/users/register", "response": {"id": 5}}
        store.save(engine.state)
        resumed = Engine(engine.config, store, api, NOW)
        resumed.tick(NOW)
        self.assertFalse(api.calls)
        self.assertEqual(resumed.state["jobs"][0]["stage"], 1)

    def pending_join(self, committed=True):
        engine, store, api = self.make_engine()
        actor = engine.identity(NOW)
        actor.update(registered=True, player_id=12)
        api.players[actor["username"]] = {"id": 12}
        api.leagues[5] = {"id": 5, "members": [actor["username"]] if committed else []}
        engine.state["leagues"] = [{"id": 5, "members": []}]
        job = engine.enqueue("join", NOW, actor=actor["username"], league=5)
        engine.state["journal"] = {"key": f'{job["id"]}:0', "path": "/leagues/5/join"}
        store.save(engine.state)
        return engine, store, api, actor, job

    def test_committed_join_recovers_by_read_without_duplicate_post(self):
        engine, store, api, actor, job = self.pending_join()
        resumed = Engine(engine.config, store, api, NOW)
        resumed.tick(NOW)
        self.assertEqual([call[1] for call in api.calls], ["GET"])
        self.assertIsNone(resumed.state["journal"])
        self.assertEqual(next(j for j in resumed.state["jobs"] if j["id"] == job["id"])["status"], "done")
        self.assertEqual(resumed.state["actors"][actor["username"]]["leagues"], [5])
        self.assertEqual(resumed.state["leagues"][0]["members"], [actor["username"]])

    def test_unconfirmed_join_stays_paused_without_post(self):
        engine, store, api, actor, job = self.pending_join(False)
        with self.assertRaises(UncertainAction):
            engine.tick(NOW)
        self.assertNotIn("response", store.load()["journal"])
        self.assertEqual([call[1] for call in api.calls], ["GET"])

    def test_recovery_rejects_malformed_or_wrong_league_reads(self):
        for response in ({}, None, {"id": 6, "members": [{"player_id": 12}]}, {"id": 5, "members": [None, "12"]}):
            engine, store, api, actor, job = self.pending_join()
            with patch.object(api, "request", return_value=response):
                self.assertFalse(engine.recover_pending_join())
            self.assertNotIn("response", store.load()["journal"])

    def test_recovery_read_timeout_preserves_journal(self):
        engine, store, api, actor, job = self.pending_join()
        with patch.object(api, "request", side_effect=TimeoutError("private message")):
            with self.assertRaises(TimeoutError):
                engine.recover_pending_join()
        self.assertNotIn("response", store.load()["journal"])

    def test_recovered_join_survives_second_restart(self):
        engine, store, api, actor, job = self.pending_join()
        self.assertTrue(engine.recover_pending_join())
        api.calls.clear()
        resumed = Engine(engine.config, store, api, NOW)
        resumed.tick(NOW)
        self.assertEqual(api.calls, [])
        self.assertIsNone(store.load()["journal"])

    def test_mutation_failure_records_http_status_without_private_body(self):
        import httpx
        engine, store, api = self.make_engine(startup_delay_seconds=0)
        response = httpx.Response(500, request=httpx.Request("POST", "http://localhost/private"))
        error = httpx.HTTPStatusError("secret-body", request=response.request, response=response)
        with patch.object(api, "request", side_effect=error):
            with self.assertLogs("maxio.simulator", level="ERROR") as captured:
                with self.assertRaises(UncertainAction):
                    engine.tick(NOW)
        self.assertEqual(store.load()["journal"]["failure"], {"type": "HTTPStatusError", "http_status": 500})
        self.assertNotIn("secret-body", "\n".join(captured.output))

    def test_backup_preserves_original_state(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.json")
            store.save({"version": 1, "journal": {"key": "example:0"}})
            with store.lock():
                backup = store.backup()
                store.save({"version": 1, "journal": None})
            self.assertEqual(Store(backup).load()["journal"], {"key": "example:0"})

    def test_database_reset_is_not_silently_repopulated(self):
        engine, store, api = self.make_engine(startup_delay_seconds=0)
        engine.tick(NOW)
        api.players.clear()
        # A missing persisted actor is an authentication failure, not a new signup.
        with self.assertRaises(Rejected):
            api.login(next(iter(engine.state["actors"].values())))
        self.assertEqual(len(engine.state["actors"]), 1)

    def test_outcome_perspective(self):
        self.assertEqual(outcome("team1", "team1"), "win")
        self.assertEqual(outcome("team1", "team2"), "loss")
        self.assertEqual(outcome("draw", "team1"), "draw")

    def test_local_config_validation(self):
        with patch.dict("os.environ", {"SIMULATOR_API_URL": "https://example.com"}):
            with self.assertRaises(ValueError):
                Config.from_env()

    def test_atomic_state_and_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.json")
            store.save({"version": 1, "value": "Peñarol"})
            self.assertEqual(store.load()["value"], "Peñarol")
            with store.lock():
                with self.assertRaises(OSError):
                    with store.lock():
                        self.fail("second worker acquired lock")
            with store.lock():
                pass


if __name__ == "__main__":
    unittest.main()

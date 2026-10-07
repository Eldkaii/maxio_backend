"""A durable agenda driven by wall-clock time. Importing this has no side effects."""
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import random
import secrets
import sys
import unicodedata
import uuid

from .api import Rejected

log = logging.getLogger("maxio.simulator")
HOUR = 3600
DAY = 24 * HOUR
WEEK = 7 * DAY
UY = timezone(timedelta(hours=-3))
FIRST = ("Santiago", "Mateo", "Nicolás", "Bruno", "Diego", "Federico", "Gonzalo", "Facundo",
         "Martín", "Joaquín", "Agustín", "Ignacio", "Lucía", "Camila", "Valentina", "Sofía",
         "Florencia", "Victoria", "Paula", "Carolina", "Emiliano", "Rodrigo", "Pablo", "Natalia")
LAST = ("Pereira", "Rodríguez", "González", "Fernández", "Silva", "Martínez", "López", "Suárez",
        "Acosta", "Cabrera", "Bentancur", "Olivera", "Viera", "Sosa", "Ramos", "Castro", "Duarte")
NEIGHBORHOODS = ("Cordón", "La Comercial", "Prado", "Unión", "Malvín", "La Blanqueada", "Aguada", "Goes")
BOOTSTRAP_MIN = 10


def _catalog_lines(filename, fallback):
    candidates = []
    configured = __import__("os").getenv("SIMULATOR_" + filename.upper().replace(".", "_"))
    if configured:
        candidates.append(Path(configured))
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "simulator-data" / filename)
    candidates.append(Path(__file__).resolve().parents[2] / "src" / filename)
    for path in candidates:
        try:
            values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, UnicodeError):
            continue
        if values:
            return tuple(dict.fromkeys(values))
    return tuple(fallback)


NAME_CATALOG = _catalog_lines("1000_nombres_apellidos_espana_latinoamerica.txt", ())
LEAGUE_CATALOG = _catalog_lines("ligas_nombres.txt", NEIGHBORHOODS)


class UncertainAction(Exception):
    """A mutation may have committed; never blindly issue it a second time."""


def slug(value):
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def username_part(value):
    """Return one safe username component, without whitespace or punctuation."""
    return "".join(character for character in slug(value) if character.isalnum())


def available(actor, date):
    """Count all participation/reservations, regardless of who created the match."""
    dates = sorted([d for d in actor["matches"] if abs(d - date) < WEEK] + [date])
    cap = actor["weekly_limit"]
    return all(dates[i + cap] - dates[i] >= WEEK for i in range(len(dates) - cap))


def outcome(winner, team):
    return "draw" if winner == "draw" else "win" if winner == team else "loss"


class Engine:
    def __init__(self, config, store, api, now, rng=None):
        self.config, self.store, self.api = config, store, api
        self.rng = rng or random.Random()
        self.events = []
        self.state = store.load() or {
            "version": 1, "api_url": config.api_url, "actors": {}, "jobs": [], "leagues": [],
            "next_signup": now + config.startup_delay_seconds, "next_plan": now + HOUR,
            "journal": None,
        }
        if self.state["api_url"] != config.api_url:
            raise ValueError("El estado pertenece a otra API; usá otro SIMULATOR_STATE_PATH")
        self.store.save(self.state)

    def event(self, job, message, *args, level=logging.INFO):
        # Only emit after the corresponding state checkpoint succeeds. Never log
        # request/response bodies or actor dictionaries (they contain credentials).
        self.events.append((level, f'{message % args} | acción={job["id"]}:{job["stage"]}'))

    def flush_events(self):
        for level, message in self.events:
            log.log(level, message)
        self.events.clear()

    def later(self, now, low, high):
        return now + self.rng.uniform(low, high)

    def enqueue(self, kind, due, **data):
        job = dict(id=uuid.uuid4().hex, kind=kind, due=due, stage=0, status="pending", **data)
        self.state["jobs"].append(job)
        return job

    def mutation(self, job, path, payload, actor=None):
        key = f'{job["id"]}:{job["stage"]}'
        journal = self.state["journal"]
        if journal:
            if journal["key"] != key or "response" not in journal:
                raise UncertainAction("Acción sin confirmación; revisar el diario antes de continuar")
            return journal["response"]
        # Login and read-only failures happen before journaling a possible mutation.
        if actor:
            self.api.login(actor)
        self.state["journal"] = {"key": key, "path": path}
        self.store.save(self.state)
        try:
            response = self.api.request("POST", path, payload, actor)
        except Rejected:
            self.state["journal"] = None
            self.store.save(self.state)
            raise
        except Exception as error:
            raise UncertainAction("Respuesta de escritura incierta; simulador pausado") from error
        self.state["journal"]["response"] = response
        self.store.save(self.state)
        return response

    def identity(self, now):
        if NAME_CATALOG:
            full_name = self.rng.choice(NAME_CATALOG)
            parts = full_name.split()
            first, last = parts[0], " ".join(parts[1:]) or self.rng.choice(LAST)
        else:
            first, last = self.rng.choice(FIRST), self.rng.choice(LAST)
        first_slug, last_slug = username_part(first), username_part(last)
        username_options = (f"{first_slug}.{last_slug}",
                            f"{first_slug[:max(3, min(8, len(first_slug)))]}{last_slug}",
                            f"{first_slug}_{last_slug}")
        username = self.rng.choice(username_options)
        if self.rng.random() < .45:
            username += str(self.rng.randint(7, 999))
        while username in self.state["actors"]:
            username = f'{first_slug}.{last_slug}{self.rng.randint(10, 999999)}'
        actor = dict(username=username, first_name=first, last_name=last, nationality="UY",
                     email=f'{username}.{uuid.uuid4().hex[:8]}@example.com',
                     password=secrets.token_urlsafe(24), registered=False, created=now,
                     weekly_limit=self.rng.choice([1, 2]), matches=[], friends={}, leagues=[],
                     organizer=self.rng.random() < .25, founded=False,
                     next_visit=now + DAY, next_social=now + self.rng.uniform(6, 12) * HOUR,
                     stats={key: self.rng.randint(35, 80) for key in ("tiro", "ritmo", "fisico", "defensa")})
        actor["stats"]["aura"] = self.rng.randint(3, 8)
        self.state["actors"][username] = actor
        self.enqueue("signup", now, actor=username)
        return actor

    def plan(self, now):
        actors = self.state["actors"]
        if len(actors) < BOOTSTRAP_MIN:
            self.state["next_signup"] = min(self.state["next_signup"], now + 30 * 60)
        if now >= self.state["next_signup"] and len(actors) < self.config.max_players:
            self.identity(now)
            # During bootstrap, add the first ten accounts at a human-looking
            # pace of roughly 10–30 minutes. Once there is a real population,
            # return to the configured slower cadence.
            if len(actors) < BOOTSTRAP_MIN:
                self.state["next_signup"] = self.later(now, 10 * 60, 30 * 60)
            else:
                self.state["next_signup"] = self.later(now, self.config.signup_min_hours * HOUR,
                                                      self.config.signup_max_hours * HOUR)
        if now < self.state["next_plan"]:
            return
        self.state["next_plan"] = self.later(now, HOUR, 2 * HOUR)
        registered = [a for a in actors.values() if a["registered"]]
        for actor in registered:
            if now >= actor["next_visit"]:
                self.enqueue("visit", now, actor=actor["username"])
                actor["next_visit"] = self.later(now, DAY, 3 * DAY)
            if len(registered) >= BOOTSTRAP_MIN and now < actor["next_social"]:
                # Do not wait days to unlock the first social loop after the
                # population becomes large enough to support leagues.
                actor["next_social"] = min(actor["next_social"], now + self.rng.uniform(30, 90) * 60)
            if now < actor["next_social"]:
                continue
            actor["next_social"] = self.later(now, 2 * DAY, 5 * DAY)
            # Only a small fraction become organizers, once each, after a week.
            founders = sum(a["founded"] for a in actors.values())
            if len(registered) >= BOOTSTRAP_MIN and not any(a["organizer"] for a in registered):
                actor["organizer"] = True
            if (actor["organizer"] and not actor["founded"] and now - actor["created"] >= 6 * HOUR
                    and len(registered) >= BOOTSTRAP_MIN and founders < max(1, len(registered) // 10)):
                actor["founded"] = True
                name = self.rng.choice(LEAGUE_CATALOG)
                if any(l.get("name") == name for l in self.state["leagues"]):
                    name = f"{name} {self.rng.randint(2, 99)}"
                self.enqueue("league", self.later(now, 30 * 60, 90 * 60), actor=actor["username"], name=name)
            others = [l for l in self.state["leagues"] if l["id"] not in actor["leagues"]]
            if others and len(actor["leagues"]) < 3 and self.rng.random() < .65:
                league = max(others, key=lambda l: sum(actor["friends"].get(n, 0) for n in l["members"]))
                if not any(j["kind"] == "join" and j.get("actor") == actor["username"]
                           and j["status"] == "pending" for j in self.state["jobs"]):
                    self.enqueue("join", self.later(now, 30 * 60, 6 * HOUR), actor=actor["username"], league=league["id"])
        # Schedule a real future evening, with enough lead time for the call-up.
        local = datetime.fromtimestamp(now, UY)
        date = local.replace(hour=self.rng.randint(18, 22), minute=self.rng.choice([0, 30]), second=0, microsecond=0)
        if date.timestamp() < now + 3 * HOUR:
            date += timedelta(days=1)
        kickoff = date.timestamp()
        eligible = [a for a in registered if available(a, kickoff) and not any(d > now for d in a["matches"])]
        if len(eligible) < 10:
            return
        self.rng.shuffle(eligible)
        captain = min(eligible, key=lambda a: max(a["matches"], default=0))
        others = [a for a in eligible if a is not captain]
        others.sort(key=lambda a: captain["friends"].get(a["username"], 0) + self.rng.uniform(0, 3), reverse=True)
        selected = [captain] + others[:9]
        names = [a["username"] for a in selected]
        candidates = [l for l in self.state["leagues"] if captain["username"] in l["members"]]
        league_id = self.rng.choice(candidates)["id"] if candidates and self.rng.random() < .8 else None
        groups = []
        if self.rng.random() < .7:
            size = self.rng.choice([2, 3, 4])
            groups = [names[:size]]
        job = self.enqueue("match", now, actor=captain["username"], names=names, kickoff=kickoff,
                     league=league_id, groups=groups, winner=self.rng.choices(["team1", "team2", "draw"], [45, 40, 15])[0])
        for actor in selected:
            actor["matches"] = [d for d in actor["matches"] if d > now - WEEK] + [kickoff]
        self.event(job, "Programa partido: organizador=%s, fecha=%s, reserva cupo para=%s",
                   captain["username"], date.isoformat(), ", ".join(names))

    def step(self, job, now):
        actor = self.state["actors"][job["actor"]]
        kind, stage = job["kind"], job["stage"]
        if kind == "signup":
            if stage == 0:
                payload = {k: actor[k] for k in ("username", "password", "first_name", "last_name", "nationality", "email", "stats")}
                self.mutation(job, "/maxio/users/register", dict(payload, is_bot=False))
                self.event(job, "Crea user: %s (%s %s), nacionalidad=UY, límite=%s partidos/7 días",
                           actor["username"], actor["first_name"], actor["last_name"], actor["weekly_limit"])
            else:
                profile = self.api.request("GET", f'/player/{actor["username"]}', actor=actor)
                actor.update(player_id=profile["id"], registered=True)
                job["status"] = "done"
                self.event(job, "Confirma perfil: %s, jugador=%s", actor["username"], actor["player_id"])
        elif kind == "visit":
            self.api.request("GET", f'/player/{actor["username"]}/profile', actor=actor)
            job["status"] = "done"
            self.event(job, "Visita perfil: %s", actor["username"])
        elif kind == "league":
            result = self.mutation(job, "/leagues", {"name": job["name"], "is_public": True}, actor)
            self.state["leagues"].append({"id": result["id"], "name": job["name"], "members": [actor["username"]]})
            actor["leagues"].append(result["id"])
            job["status"] = "done"
            self.event(job, "Crea liga: %s, liga=%s, nombre=%s", actor["username"], result["id"], job["name"])
        elif kind == "join":
            self.mutation(job, f'/leagues/{job["league"]}/join', {}, actor)
            actor["leagues"].append(job["league"])
            next(l for l in self.state["leagues"] if l["id"] == job["league"])["members"].append(actor["username"])
            job["status"] = "done"
            self.event(job, "Se une a liga: %s, liga=%s", actor["username"], job["league"])
        elif kind == "match":
            self.match_step(job, now, actor)
        job["stage"] += 1
        if job["due"] <= now:
            job["due"] = self.later(now, 2 * 60, 8 * 60)

    def match_step(self, job, now, actor):
        stage = job["stage"]
        if stage == 0:
            if now > job["kickoff"] - 2 * HOUR and not self.state["journal"]:
                job["status"] = "cancelled"
                for name in job["names"]:
                    self.state["actors"][name]["matches"].remove(job["kickoff"])
                self.event(job, "Cancela planificación: %s, fecha demasiado próxima; libera los cupos",
                           actor["username"], level=logging.WARNING)
                return
            result = self.mutation(job, "/match/matches", {
                "date": datetime.fromtimestamp(job["kickoff"], timezone.utc).replace(tzinfo=None).isoformat(),
                "max_players": 10, "league_id": job["league"],
            }, actor)
            job["match_id"] = result["id"]
            self.event(job, "Crea partido: %s, partido=%s, liga=%s", actor["username"], result["id"], job["league"])
        elif 1 <= stage <= 10:
            participant = self.state["actors"][job["names"][stage - 1]]
            self.mutation(job, f'/match/matches/{job["match_id"]}/players/{participant["player_id"]}', {}, actor)
            self.event(job, "Agrega jugador: %s, partido=%s, convocado por=%s",
                       participant["username"], job["match_id"], actor["username"])
        elif stage == 11:
            self.mutation(job, f'/match/matches/{job["match_id"]}/pre-set-groups', {"groups": job["groups"]}, actor)
            self.event(job, "Configura grupos: %s, partido=%s, grupos=%s",
                       actor["username"], job["match_id"], job["groups"])
        elif stage == 12:
            result = self.mutation(job, f'/match/matches/{job["match_id"]}/generate-teams', {}, actor)
            job["teams"] = {p.get("name", p.get("username")): team for team in ("team1", "team2") for p in result[team]["players"]}
            if set(job["teams"]) != set(job["names"]):
                raise ValueError("Plantel inesperado; se detiene este partido")
            job["due"] = max(now + 120, self.later(job["kickoff"], 90 * 60, 150 * 60))
            self.event(job, "Balancea equipos: %s, partido=%s", actor["username"], job["match_id"])
        else:
            if now > job["kickoff"] + 23 * HOUR and not self.state["journal"]:
                job["status"], job["error"] = "blocked", "Votación vencida tras inactividad; revisar cierre del partido"
                self.event(job, "Bloquea votación: partido=%s, plazo vencido", job["match_id"], level=logging.WARNING)
                return
            name = job["names"][stage - 13]
            participant = self.state["actors"][name]
            self.mutation(job, f'/match/matches/{job["match_id"]}/result',
                          {"result": outcome(job["winner"], job["teams"][name])}, participant)
            vote = outcome(job["winner"], job["teams"][name])
            self.event(job, "Vota resultado: %s, partido=%s, voto=%s", name, job["match_id"],
                       {"win": "victoria", "loss": "derrota", "draw": "empate"}[vote])
            if stage == 22:
                job["status"] = "done"
                for name in job["names"]:
                    friends = self.state["actors"][name]["friends"]
                    for other in job["names"]:
                        if name != other:
                            friends[other] = friends.get(other, 0) + 1
                self.event(job, "Completa votos y actualiza afinidades locales: partido=%s", job["match_id"])

    def tick(self, now):
        self.events.clear()
        journal = self.state["journal"]
        if journal and "response" not in journal:
            raise UncertainAction("Hay una escritura sin confirmación en el diario")
        if journal:
            job = next(j for j in self.state["jobs"] if journal["key"] == f'{j["id"]}:{j["stage"]}')
        else:
            self.plan(now)
            self.store.save(self.state)
            self.flush_events()
            due = [j for j in self.state["jobs"] if j["status"] == "pending" and j["due"] <= now]
            if not due:
                return
            job = min(due, key=lambda j: j["due"])
        try:
            self.step(job, now)
        except Rejected as error:
            if error.status in {401, 429}:
                job["due"] = now + 15 * 60
            else:
                job["status"], job["error"] = "blocked", str(error)
            self.event(job, "%s: tipo=%s, jugador=%s, partido=%s, liga=%s, HTTP=%s",
                       "Difiere acción 15 minutos" if error.status in {401, 429} else "Bloquea acción",
                       job["kind"], job["actor"], job.get("match_id"), job.get("league"), error.status,
                       level=logging.WARNING)
        except Exception:
            log.error("Acción interrumpida: tipo=%s, jugador=%s, acción=%s:%s; revisar estado antes de reintentar",
                      job["kind"], job["actor"], job["id"], job["stage"])
            raise
        # Saving result effects and clearing the journal is a single atomic checkpoint.
        self.state["journal"] = None
        self.store.save(self.state)
        self.flush_events()

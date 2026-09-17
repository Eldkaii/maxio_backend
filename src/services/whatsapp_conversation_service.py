"""Flujos de Max_io adaptados a mensajes y botones de WhatsApp."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any

from fastapi import HTTPException

from src.database import SessionLocal
from src.models.match import Match, MatchPlayer
from src.models.player import Player
from src.schemas.match_schema import MatchCreate
from src.schemas.player_schema import PlayerStatsUpdate
from src.schemas.user_schema import UserCreate
from src.services.auth_service import authenticate_user
from src.services.match_service import (
    assign_player_to_match,
    create_match,
    generate_match_card,
    generate_teams_for_match,
    set_pre_set_player_groups_for_match,
)
from src.services.player_service import (
    build_full_player_profile, generate_player_card, save_player_photo, update_player_stats,
)
from src.services.user_service import create_user
from src.services.whatsapp_identity_service import (
    get_or_create_identity, get_or_create_session, link_identity_to_user, unlink_identity_from_user,
)
from src.utils.logger_config import app_logger as logger


class WhatsAppConversationService:
    EVALUATION_STATS = ("aura", "tiro", "ritmo", "fisico", "defensa")
    EVALUATION_DELTAS = (-15, -7, 0, 7, 15)
    EVALUATION_LABELS = {
        "aura": "Aura", "tiro": "Tiro", "ritmo": "Ritmo", "fisico": "Físico", "defensa": "Defensa",
    }

    def __init__(self, sender: Any) -> None:
        self.sender = sender

    async def process(self, wa_id, profile_name, message_id, message_type, text=None, media=None) -> None:
        db = SessionLocal()
        try:
            identity = get_or_create_identity(db, wa_id, profile_name)
            session = get_or_create_session(db, identity)
            if identity.user_id and session.state in {
                "login_username", "login_password", "register_username", "register_email", "register_password",
            }:
                self._reset_session(db, session)
            if message_id and session.last_inbound_message_id == message_id:
                return

            command = (text or "").strip()
            if command.casefold() in {"hola", "inicio", "start", "menu", "menú"}:
                self._reset_session(db, session)
                await self._send_home(identity)
            elif command.casefold() in {"salir", "logout"}:
                unlink_identity_from_user(db, identity)
                self._reset_session(db, session)
                await self.sender.send_text(wa_id, "Tu cuenta fue desvinculada de WhatsApp.")
                await self._send_home(identity)
            elif message_type == "image" and session.state == "awaiting_profile_photo":
                await self._save_profile_photo(db, identity, session, media or {})
            else:
                await self._advance(db, identity, session, command)

            session.last_inbound_message_id = message_id
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("WhatsApp: error al procesar el flujo del usuario")
            await self.sender.send_text(wa_id, "No pude completar esa acción. Escribí INICIO para volver al menú.")
        finally:
            db.close()

    async def _send_home(self, identity) -> None:
        if identity.user_id:
            await self._send_main_menu(identity.wa_id)
            return
        await self.sender.send_buttons(identity.wa_id, "Bienvenido a Max_io. ¿Cómo querés continuar?", [
            ("auth_login", "Ingresar"), ("auth_register", "Registrarme"),
        ])

    async def _send_main_menu(self, wa_id: str) -> None:
        await self.sender.send_buttons(wa_id, "¿Qué querés hacer?", [
            ("menu_profile", "Ver jugador"),
            ("menu_match", "Crear partido"),
            ("menu_more", "Más opciones"),
        ])

    async def _advance(self, db, identity, session, command: str) -> None:
        actions = {
            "auth_login": ("login_username", "Ingresá tu username:"),
            "auth_register": ("register_username", "Elegí un username:"),
        }
        if command in actions:
            state, prompt = actions[command]
            self._set_state(db, session, state)
            await self.sender.send_text(identity.wa_id, prompt)
            return
        if command == "menu_profile" and identity.user_id:
            self._set_state(db, session, "profile_username")
            await self.sender.send_buttons(identity.wa_id, "Elegí una opción o enviá el username de otro jugador.", [("profile_me", "Mi jugador")])
            return
        if command == "profile_me" and identity.user_id:
            await self._send_profile(db, identity.wa_id, identity.user.username)
            self._reset_session(db, session)
            return
        if command == "menu_photo" and identity.user_id:
            self._set_state(db, session, "awaiting_profile_photo")
            await self.sender.send_text(identity.wa_id, "Enviame la imagen que querés usar como foto de perfil.")
            return
        if command == "menu_more" and identity.user_id:
            await self.sender.send_buttons(identity.wa_id, "¿Qué querés hacer?", [
                ("menu_photo", "Cambiar foto"),
                ("menu_evaluate_last", "Evaluar partido"),
                ("menu_home", "Volver"),
            ])
            return
        if command == "menu_home" and identity.user_id:
            self._reset_session(db, session)
            await self._send_main_menu(identity.wa_id)
            return
        if command == "menu_evaluate_last" and identity.user_id:
            await self._start_last_match_evaluation(db, identity, session)
            return
        if command.casefold() in {"eval_cancel", "cancelar"} and session.state == "evaluating_last_match":
            self._reset_session(db, session)
            await self.sender.send_text(identity.wa_id, "Evaluación cancelada.")
            await self._send_main_menu(identity.wa_id)
            return
        if session.state == "evaluating_last_match":
            await self._save_evaluation_form(db, identity, session, command)
            return
        if command == "menu_match" and identity.user_id:
            self._set_state(db, session, "match_date_option")
            await self.sender.send_buttons(identity.wa_id, "¿Cuándo se juega el partido?", [
                ("match_now", "Ahora"),
                ("match_schedule", "Agregar fecha y hora"),
            ])
            return
        if command == "match_now" and session.state == "match_date_option":
            self._set_state(db, session, "match_team_size", {"date": datetime.utcnow().isoformat()})
            await self._ask_for_match_team_size(identity.wa_id)
            return
        if command == "match_schedule" and session.state == "match_date_option":
            self._set_state(db, session, "match_datetime")
            await self.sender.send_text(
                identity.wa_id,
                "Ingresá la fecha y hora del partido en formato DD/MM/AAAA HH:MM. Ejemplo: 25/12/2026 20:30.",
            )
            return
        if command == "obsolete_menu_match" and identity.user_id:
            self._set_state(db, session, "match_players", {"players": []})
            await self.sender.send_text(identity.wa_id, "Escribí los usernames de los jugadores, separados por comas. Mínimo dos jugadores.")
            return
        if command == "match_cancel":
            self._reset_session(db, session)
            await self.sender.send_text(identity.wa_id, "Creación de partido cancelada.")
            await self._send_main_menu(identity.wa_id)
            return
        if command == "match_confirm" and session.state == "match_confirm":
            await self._create_match(db, identity, session)
            return

        if command.startswith("match_team_size_") and session.state == "match_team_size":
            try:
                team_size = int(command.removeprefix("match_team_size_"))
            except ValueError:
                team_size = 0
            if not 1 <= team_size <= 10:
                await self.sender.send_text(identity.wa_id, "Eleg\u00ed un tama\u00f1o de equipo v\u00e1lido.")
                return
            data = dict(session.data or {})
            data["team_size"] = team_size
            self._set_state(db, session, "match_players", data)
            await self._ask_for_match_players(identity.wa_id, db, identity)
            return

        if session.state == "login_username":
            self._set_state(db, session, "login_password", {"username": self._normalize_username(command)})
            await self.sender.send_text(identity.wa_id, "Ingresá tu contraseña:")
        elif session.state == "login_password":
            await self._login(db, identity, session, command)
        elif session.state == "register_username":
            self._set_state(db, session, "register_email", {"username": self._normalize_username(command)})
            await self.sender.send_text(identity.wa_id, "Ingresá tu email:")
        elif session.state == "register_email":
            data = dict(session.data or {})
            data["email"] = command
            self._set_state(db, session, "register_password", data)
            await self.sender.send_text(identity.wa_id, "Elegí una contraseña (mínimo 6 caracteres):")
        elif session.state == "register_password":
            await self._register(db, identity, session, command)
        elif session.state == "profile_username":
            await self._send_profile(db, identity.wa_id, self._normalize_username(command))
            self._reset_session(db, session)
        elif session.state == "match_players":
            await self._prepare_match(db, identity, session, command)
        elif session.state == "match_datetime":
            match_date = self._parse_match_datetime(command)
            if not match_date:
                await self.sender.send_text(
                    identity.wa_id,
                    "No pude interpretar la fecha. Usá el formato DD/MM/AAAA HH:MM, por ejemplo 25/12/2026 20:30.",
                )
                return
            self._set_state(db, session, "match_team_size", {"date": match_date.isoformat()})
            await self._ask_for_match_team_size(identity.wa_id)
        else:
            await self._send_home(identity)

    async def _start_last_match_evaluation(self, db, identity, session) -> None:
        evaluator = identity.user.player if identity.user else None
        if not evaluator:
            await self.sender.send_text(identity.wa_id, "Tu usuario no tiene un jugador asociado.")
            return

        match = (
            db.query(Match)
            .join(MatchPlayer)
            .filter(
                MatchPlayer.player_id == evaluator.id,
                Match.date <= datetime.utcnow() - timedelta(hours=1),
            )
            .order_by(Match.date.desc())
            .first()
        )

        if not match:
            await self.sender.send_text(identity.wa_id, "No encontré un partido finalizado para evaluar.")
            return

        target_ids = [player.id for player in match.players if player.id != evaluator.id]
        if not target_ids:
            await self.sender.send_text(identity.wa_id, "No hay otros jugadores para evaluar en tu último partido.")
            return

        self._set_state(db, session, "evaluating_last_match", {
            "match_id": match.id,
            "target_ids": target_ids,
            "target_index": 0,
            "stat_index": 0,
            "scores": {},
        })
        await self._send_evaluation_form(db, identity, session)

    async def _send_evaluation_form(self, db, identity, session) -> None:
        data = session.data or {}
        target = db.get(Player, data["target_ids"][data["target_index"]])
        if not target:
            raise ValueError("No se encontró el jugador a evaluar.")
        await self.sender.send_text(
            identity.wa_id,
            "Evaluando a {player}.\n\nRespondé con cinco valores del 1 al 5, separados por comas, en este orden:\n"
            "Aura, Tiro, Ritmo, Físico, Defensa.\n\nEjemplo: 3,4,2,5,4\n\n"
            "1 Muy bajo (-15) · 2 Bajo (-7) · 3 Normal · 4 Bueno (+7) · 5 Excelente (+15)\n\n"
            "Escribí CANCELAR para volver al menú.".format(player=target.name),
        )

    async def _save_evaluation_form(self, db, identity, session, command: str) -> None:
        scores = self._parse_evaluation_scores(command)
        if scores is None:
            await self.sender.send_text(
                identity.wa_id,
                "Usá cinco valores del 1 al 5 separados por comas. Ejemplo: 3,4,2,5,4.",
            )
            return

        data = dict(session.data or {})
        target = db.get(Player, data["target_ids"][data["target_index"]])
        if not target:
            raise ValueError("No se encontró el jugador a evaluar.")
        stats = {
            stat_name: max(0, min(100, getattr(target, stat_name) + self.EVALUATION_DELTAS[score - 1]))
            for stat_name, score in zip(self.EVALUATION_STATS, scores)
        }
        update_player_stats(target.name, identity.user.username, PlayerStatsUpdate(**stats), db)

        data["target_index"] += 1
        if data["target_index"] >= len(data["target_ids"]):
            self._reset_session(db, session)
            await self.sender.send_text(identity.wa_id, "Terminaste de evaluar tu último partido.")
            await self._send_main_menu(identity.wa_id)
            return

        self._set_state(db, session, "evaluating_last_match", data)
        await self._send_evaluation_form(db, identity, session)

    async def _send_evaluation_question(self, db, identity, session) -> None:
        data = session.data or {}
        target = db.get(Player, data["target_ids"][data["target_index"]])
        stat = self.EVALUATION_STATS[data["stat_index"]]
        if not target:
            raise ValueError("No se encontró el jugador a evaluar.")
        await self.sender.send_list(
            identity.wa_id,
            "Evaluando a {player} ({current}/{total})\n\n{label}: {value:.1f}".format(
                player=target.name,
                current=data["stat_index"] + 1,
                total=len(self.EVALUATION_STATS),
                label=self.EVALUATION_LABELS[stat],
                value=getattr(target, stat),
            ),
            "Puntuar",
            [
                ("eval_score_0", "Muy bajo", "-15 puntos"),
                ("eval_score_1", "Bajo", "-7 puntos"),
                ("eval_score_2", "Normal", "Sin cambios"),
                ("eval_score_3", "Bueno", "+7 puntos"),
                ("eval_score_4", "Excelente", "+15 puntos"),
                ("eval_cancel", "Cancelar", "Volver al menú"),
            ],
        )

    async def _save_evaluation_score(self, db, identity, session, command: str) -> None:
        try:
            score = int(command.removeprefix("eval_score_"))
            if score not in range(len(self.EVALUATION_DELTAS)):
                raise ValueError
        except ValueError:
            await self.sender.send_text(identity.wa_id, "Esa puntuación no es válida.")
            return

        data = dict(session.data or {})
        stat = self.EVALUATION_STATS[data["stat_index"]]
        scores = dict(data.get("scores") or {})
        scores[stat] = score
        data["scores"] = scores
        data["stat_index"] += 1

        if data["stat_index"] < len(self.EVALUATION_STATS):
            self._set_state(db, session, "evaluating_last_match", data)
            await self._send_evaluation_question(db, identity, session)
            return

        target = db.get(Player, data["target_ids"][data["target_index"]])
        if not target:
            raise ValueError("No se encontró el jugador a evaluar.")
        stats = {
            stat_name: max(0, min(100, getattr(target, stat_name) + self.EVALUATION_DELTAS[scores[stat_name]]))
            for stat_name in self.EVALUATION_STATS
        }
        update_player_stats(target.name, identity.user.username, PlayerStatsUpdate(**stats), db)
        await self.sender.send_text(identity.wa_id, f"Evaluación de {target.name} registrada.")

        data["target_index"] += 1
        data["stat_index"] = 0
        data["scores"] = {}
        if data["target_index"] >= len(data["target_ids"]):
            self._reset_session(db, session)
            await self.sender.send_text(identity.wa_id, "Terminaste de evaluar tu último partido.")
            await self._send_main_menu(identity.wa_id)
            return

        self._set_state(db, session, "evaluating_last_match", data)
        await self._send_evaluation_question(db, identity, session)

    async def _login(self, db, identity, session, password: str) -> None:
        try:
            user = authenticate_user(db, session.data.get("username", ""), password)
            link_identity_to_user(db, identity, user)
        except (HTTPException, ValueError):
            self._set_state(db, session, "login_username")
            await self.sender.send_text(identity.wa_id, "Usuario o contraseña incorrectos. Ingresá tu username nuevamente:")
            return
        self._reset_session(db, session)
        await self.sender.send_text(identity.wa_id, f"Bienvenido, {user.username}.")
        await self._send_main_menu(identity.wa_id)

    async def _register(self, db, identity, session, password: str) -> None:
        data = session.data or {}
        try:
            user = create_user(UserCreate(username=data.get("username", ""), email=data.get("email", ""), password=password, is_bot=False), db)
            link_identity_to_user(db, identity, user)
        except Exception as exc:
            self._set_state(db, session, "register_username")
            await self.sender.send_text(identity.wa_id, f"No pude crear la cuenta: {exc}. Ingresá un username para reintentar.")
            return
        self._reset_session(db, session)
        await self.sender.send_text(identity.wa_id, f"Usuario creado. Bienvenido, {user.username}.")
        await self._send_main_menu(identity.wa_id)

    async def _send_profile(self, db, wa_id: str, username: str) -> None:
        try:
            profile = build_full_player_profile(db, username)
            card = generate_player_card(username, db)
            await self.sender.send_image(wa_id, card.getvalue(), f"Carta de {profile['name']}", "player_card.png")
            stats, summary = profile["stats"], profile["matches_summary"]
            await self.sender.send_text(wa_id, "{name}\n\nPartidos: {played} | Ganados: {won} | Winrate: {winrate}%\nTiro: {tiro} | Ritmo: {ritmo} | Físico: {fisico}\nDefensa: {defensa} | Aura: {aura} | ELO: {elo}".format(name=profile["name"], played=summary["played"], won=summary["won"], winrate=summary["winrate"], **stats))
        except ValueError:
            await self.sender.send_text(wa_id, f"No encontré al jugador '{username}'.")

    async def _save_profile_photo(self, db, identity, session, media: dict[str, Any]) -> None:
        if not identity.user_id or not media.get("id"):
            await self.sender.send_text(identity.wa_id, "No pude leer esa imagen. Enviá una imagen válida.")
            return
        image_bytes, mime_type = await self.sender.download_media(media["id"])
        if not mime_type.startswith("image/") or len(image_bytes) > 5 * 1024 * 1024:
            await self.sender.send_text(identity.wa_id, "La imagen debe ser válida y pesar como máximo 5 MB.")
            return
        extension = mime_type.split("/", maxsplit=1)[-1].replace("jpeg", "jpg")
        save_player_photo(identity.user.username, image_bytes, f"profile.{extension}", db)
        self._reset_session(db, session)
        await self.sender.send_text(identity.wa_id, "Foto de perfil actualizada.")
        await self._send_main_menu(identity.wa_id)

    async def _prepare_match(self, db, identity, session, command: str) -> None:
        usernames, groups = self._parse_match_players(command)
        if len(usernames) < 2:
            await self.sender.send_text(identity.wa_id, "Necesito al menos dos usernames separados por comas.")
            return
        team_size = int((session.data or {}).get("team_size", 5))
        if len(usernames) > team_size * 2:
            await self.sender.send_text(identity.wa_id, f"El tamaño elegido admite hasta {team_size * 2} jugadores reales.")
            return
        players = db.query(Player).filter(Player.name.in_(usernames)).all()
        found = {player.name for player in players}
        missing = [name for name in usernames if name not in found]
        if missing:
            await self.sender.send_text(identity.wa_id, "No encontré: " + ", ".join(missing) + ". Corregí la lista completa.")
            return
        data = dict(session.data or {})
        data["players"] = usernames
        data["groups"] = groups
        self._set_state(db, session, "match_confirm", data)
        match_date = datetime.fromisoformat(data.get("date", datetime.utcnow().isoformat()))
        await self.sender.send_text(
            identity.wa_id,
            f"Fecha y hora: {match_date.strftime('%d/%m/%Y %H:%M')}",
        )
        await self.sender.send_buttons(identity.wa_id, "Crearé el partido con:\n- " + "\n- ".join(usernames), [("match_confirm", "Confirmar"), ("match_cancel", "Cancelar")])

    async def _create_match(self, db, identity, session) -> None:
        data = session.data or {}
        usernames = data.get("players", [])
        players = db.query(Player).filter(Player.name.in_(usernames)).all()
        if len(players) != len(usernames):
            self._reset_session(db, session)
            await self.sender.send_text(identity.wa_id, "Un jugador ya no existe. Volvé a iniciar la creación.")
            return
        try:
            match_date = datetime.fromisoformat(data.get("date", datetime.utcnow().isoformat()))
            team_size = int(data.get("team_size", 5))
            match = create_match(MatchCreate(date=match_date, max_players=team_size * 2), db)
            for player in players:
                if not assign_player_to_match(db, match, player):
                    raise ValueError(f"No se pudo agregar a {player.name}.")
            groups_by_name = {player.name: player for player in players}
            groups = [
                [groups_by_name[name] for name in group]
                for group in data.get("groups", [])
            ]
            if groups:
                set_pre_set_player_groups_for_match(match, groups, db)
            match = generate_teams_for_match(match.id, db)
        except Exception as exc:
            db.rollback()
            self._reset_session(db, session)
            await self.sender.send_text(identity.wa_id, f"No pude crear el partido: {exc}")
            return
        self._reset_session(db, session)
        team1 = ", ".join(player.name for player in match.team1.players)
        team2 = ", ".join(player.name for player in match.team2.players)
        await self.sender.send_text(identity.wa_id, f"Partido #{match.id} creado ({team_size} por equipo).\n\nEquipo 1: {team1}\nEquipo 2: {team2}")
        try:
            card = generate_match_card(match.id, db)
            await self.sender.send_image(identity.wa_id, card.getvalue(), "Resumen visual del partido", "match_card.png")
        except Exception:
            logger.exception("WhatsApp: no se pudo enviar la carta visual del partido %s", match.id)
            await self.sender.send_text(identity.wa_id, "El partido fue creado, pero no pude generar su imagen.")
        await self._send_main_menu(identity.wa_id)

    @staticmethod
    def _set_state(db, session, state: str, data: dict[str, Any] | None = None) -> None:
        session.state, session.data = state, data or {}
        db.commit()

    @staticmethod
    def _reset_session(db, session) -> None:
        session.state, session.data = "idle", {}
        db.commit()

    @staticmethod
    def _parse_match_datetime(value: str) -> datetime | None:
        """Interpreta la fecha ingresada en el formato de WhatsApp."""
        try:
            return datetime.strptime(value.strip(), "%d/%m/%Y %H:%M")
        except ValueError:
            return None

    @staticmethod
    def _parse_evaluation_scores(value: str) -> list[int] | None:
        try:
            scores = [int(item.strip()) for item in value.replace(";", ",").split(",")]
        except ValueError:
            return None
        if len(scores) != len(WhatsAppConversationService.EVALUATION_STATS) or any(
            score not in range(1, 6) for score in scores
        ):
            return None
        return scores

    @staticmethod
    def _normalize_username(value: str) -> str:
        return value.strip().lower()

    @staticmethod
    def _parse_match_players(value: str) -> tuple[list[str], list[list[str]]]:
        groups = []
        for group_text in re.findall(r"\[([^\]]+)\]", value):
            group = [WhatsAppConversationService._normalize_username(name) for name in group_text.replace(";", ",").split(",") if name.strip()]
            if len(group) >= 2:
                groups.append(group)
        remaining = re.sub(r"\[[^\]]+\]", "", value)
        names = [WhatsAppConversationService._normalize_username(name) for name in remaining.replace(";", ",").split(",") if name.strip()]
        for group in groups:
            names.extend(group)
        return list(dict.fromkeys(names)), groups

    async def _ask_for_match_team_size(self, wa_id: str) -> None:
        await self.sender.send_list(
            wa_id,
            "¿Cuántos jugadores querés por equipo? El sistema balanceará sólo a los reales y completará los lugares restantes con bots.",
            "Elegir tamaño",
            [(f"match_team_size_{size}", f"{size} por equipo", f"Hasta {size * 2} jugadores reales") for size in range(2, 11)],
        )

    async def _ask_for_match_players(self, wa_id: str, db=None, identity=None) -> None:
        if db is not None and identity and identity.user and identity.user.player:
            recommendations = identity.user.player.top_teammates(db, limit=5, exclude_bots=True)
            names = [player.name for player, _ in recommendations]
            if names:
                await self.sender.send_text(wa_id, "Sugeridos por historial: " + ", ".join(names))
        await self.sender.send_text(
            wa_id,
            "Escribí usernames separados por comas. Para mantener jugadores juntos usá corchetes: ana,[juan,pedro],lucas.",
        )

# test/utils_common_methods.py

from datetime import datetime
from typing import List, Dict, Tuple, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import  Session

from src.models import Team, Player, Match
from src.models.player import PlayerRelation
from src.services import player_service
from src.services.match_service import assign_team_to_match
import random

from src.utils.logger_config import test_logger as logger

class TestUtils:

    # ─────────────────────────────
    # USER/PLAYER ENDPOINTS
    # ─────────────────────────────


    def create_player(self, client: TestClient, username: str,is_bot: bool = False,stats: Optional[Dict[str, int]] = None) -> int:
        payload = {
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass",
            "is_bot": is_bot,
        }
        if stats:
            payload["stats"] = stats

        res = client.post("/maxio/users/register", json=payload)
        assert res.status_code == 200, f"Error creando player '{username}': {res.text}"
        return res.json()["id"]

    def create_players(self, client: TestClient, usernames: List[str]) -> List[int]:
        return [self.create_player(client, username) for username in usernames]

    # ─────────────────────────────
    # PLAYER ENDPOINTS
    # ─────────────────────────────

    # def get_player(self, client: TestClient, username: str) -> Dict:
    #     res = client.get(f"/player/{username}")
    #     assert res.status_code == 200, f"No se pudo obtener al jugador '{username}': {res.text}"
    #     return res.json()

    def get_player(self, client: TestClient, username: str) -> Dict:
        res = client.get(f"/player/{username}")
        assert res.status_code == 200, f"No se pudo obtener al jugador '{username}': {res.text}"
        data = res.json()
        logger.info(f"Player obtenido para '{username}': {data}")
        return data

    def update_player_stats(self, client: TestClient, target_username: str, evaluator_username: str, stats: Dict):
        res = client.put(f"/players/{target_username}/stats", params={"evaluator_username": evaluator_username}, json=stats)
        assert res.status_code == 200, f"No se pudieron actualizar los stats de '{target_username}': {res.text}"
        return res.json()

    def get_top_teammates(self, client: TestClient, username: str, limit: int = 5, exclude_bots: bool = False) -> List[Dict]:
        res = client.get(f"/players/{username}/top_teammates", params={"limit": limit, "exclude_bots": exclude_bots})
        assert res.status_code == 200, f"Error obteniendo top teammates de '{username}': {res.text}"
        return res.json()

    def get_top_allies(self, client: TestClient, username: str, limit: int = 3, exclude_bots: bool = False) -> List[Dict]:
        res = client.get(f"/players/{username}/top_allies", params={"limit": limit, "exclude_bots": exclude_bots})
        assert res.status_code == 200, f"Error obteniendo top allies de '{username}': {res.text}"
        return res.json()

    def get_top_opponents(self, client: TestClient, username: str, limit: int = 3, exclude_bots: bool = False) -> List[Dict]:
        res = client.get(f"/players/{username}/top_opponents", params={"limit": limit, "exclude_bots": exclude_bots})
        assert res.status_code == 200, f"Error obteniendo top opponents de '{username}': {res.text}"
        return res.json()

    def seed_players_and_relations(
        self,
        client: TestClient,
        db_session: Session,
        player_data: List[Tuple[str, bool]],  # (username, is_bot)
        relations: Optional[List[Tuple[str, str, int, int]]] = None  # (username1, username2, games_together, games_apart)
    ) -> List[int]:
        """
        Crea jugadores y relaciones entre ellos.

        Args:
            client: Cliente de pruebas HTTP.
            db_session: Sesión de la base de datos.
            player_data: Lista de tuplas (nombre, is_bot).
            relations: Lista de relaciones entre jugadores. Cada ítem es una tupla:
                       (nombre1, nombre2, games_together, games_apart)

        Returns:
            Lista de IDs de los jugadores creados (en el mismo orden que player_data).
        """
        player_ids = []
        name_to_id = {}

        # Crear jugadores usando la API
        for name, is_bot in player_data:
            player_id = self.create_player(client, name,is_bot)
            player_ids.append(player_id)
            name_to_id[name] = player_id

        db_session.commit()

        # Actualizar la bandera is_bot en la base
        for name, is_bot in player_data:
            if is_bot:
                player = db_session.get(Player, name_to_id[name])
                if player is None:
                    raise ValueError(f"No se encontró el jugador con id {name_to_id[name]} para {name}")

                player.is_bot = True

        db_session.commit()

        # Crear relaciones usando player_service
        if relations:
            for name1, name2, games_together, games_apart in relations:
                id1 = name_to_id[name1]
                id2 = name_to_id[name2]

                # Llamar a player_service.add_player_relation tantas veces como sea necesario
                for _ in range(games_together):
                    player_service.add_player_relation(id1, id2, together=True, db=db_session)

                for _ in range(games_apart):
                    player_service.add_player_relation(id1, id2, together=False, db=db_session)

        return player_ids

    # ─────────────────────────────
    # TEAMS ENDPOINTS
    # ─────────────────────────────
    def create_team(self, db_session: Session, player_ids: List[int], name: Optional[str] = None, match_id: Optional[int] = None) -> int:
        # Obtener instancias Player desde DB
        players = db_session.query(Player).filter(Player.id.in_(player_ids)).all()
        assert len(players) == len(player_ids), "Error: algunos player_ids no existen en la DB"

        team = Team(name=name, match_id=match_id, players=players)
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        return team.id

    def get_team_by_id(self, db_session: Session, team_id: int):
        from src.models import Team
        return db_session.query(Team).get(team_id)


    # ─────────────────────────────
    # MATCH ENDPOINTS
    # ─────────────────────────────

    def create_match(self, client: TestClient, max_players: int = 10) -> int:
        res = client.post("/match/matches", json={
            "fecha": datetime.utcnow().isoformat(),
            "max_players": max_players
        })
        assert res.status_code == 200, f"Error creando match: {res.text}"
        return res.json()["id"]

    def get_match_by_id(self, db_session: Session, match_id: int):
        from src.models import Match
        return db_session.query(Match).get(match_id)

    def assign_player_to_match(self, client: TestClient, match_id: int, player_id: int):
        res = client.post(f"/match/matches/{match_id}/players/{player_id}")
        assert res.status_code == 200, f"Error asignando player {player_id} a match {match_id}: {res.text}"

    def assign_players_to_match(self, client: TestClient, match_id: int, player_ids: List[int]):
        for pid in player_ids:
            self.assign_player_to_match(client, match_id, pid)

    def assign_team_to_match(self, client: TestClient, team_id: int, match_id: int):
        res = client.post(f"/match/matches/{match_id}/teams/{team_id}")
        assert res.status_code == 200, f"Error asignando team {team_id} al match {match_id}: {res.text}"

    def setup_match_teams_players(
            self,
            client: TestClient,
            db_session: Session
    ) -> Tuple[Match, Team, Team, List[Player], List[Player]]:
        # Crear usuarios en el sistema vía HTTP (esto genera registros en la base)
        usernames_team1 = [f"PlayerA{i}" for i in range(5)]
        usernames_team2 = [f"PlayerB{i}" for i in range(5)]

        ids_team1 = self.create_players(client, usernames_team1)
        ids_team2 = self.create_players(client, usernames_team2)

        # Crear match
        match_id = self.create_match(client)
        match = db_session.query(Match).get(match_id)

        # Asignar jugadores al match vía endpoints
        self.assign_players_to_match(client, match_id, ids_team1 + ids_team2)

        # Obtener instancias Player desde la base (para pasar a assign_team_to_match)
        players_team1 = db_session.query(Player).filter(Player.id.in_(ids_team1)).all()
        players_team2 = db_session.query(Player).filter(Player.id.in_(ids_team2)).all()

        # Crear equipos directamente desde backend, usando objetos persistidos
        team1 = Team(players=players_team1)
        team2 = Team(players=players_team2)
        db_session.add_all([team1, team2])
        db_session.commit()

        # Asignar equipos al match
        assign_team_to_match(team1, match, db_session)
        assign_team_to_match(team2, match, db_session)

        return match, team1, team2, players_team1, players_team2


    def assign_players_randomly(
        self,
        client,
        db_session: Session,
        match_id: int,
        player_ids: List[int]
    ):
        """
        Asigna players a un match usando 3 posibles variantes de forma aleatoria:
        1) Todos los players asignados individualmente al match.
        2) Se crea 1 equipo con parte de los players, ese equipo se asigna al match,
           y el resto se asigna individualmente.
        3) Se crean 2 equipos con parte de los players, ambos equipos se asignan al match,
           y el resto se asigna individualmente.
        """

        if not player_ids:
            return  # No hay jugadores para asignar

        match = db_session.query(Match).get(match_id)
        assert match is not None, f"Match {match_id} no existe"

        option = random.choice([1, 2, 3])

        if option == 1:
            # Asignar todos los players individualmente
            self.assign_players_to_match(client=client, match_id=match_id, player_ids=player_ids)
            logger.info(f"[Option 1] Asignados {len(player_ids)} players individualmente al match {match_id}")

        elif option == 2:
            team_size = random.randint(1, int(match.max_players/2))
            team_players = random.sample(player_ids, team_size)
            remaining_players = [pid for pid in player_ids if pid not in team_players]

            team_name = f"Equipo Random 1 - Match {match_id}"
            team_id = self.create_team(db_session, team_players, name=team_name, match_id=None)

            self.assign_team_to_match(client, team_id=team_id, match_id=match_id)
            self.assign_players_to_match(client=client, match_id=match_id, player_ids=remaining_players)

            logger.info(f"[Option 2] Creado equipo {team_id} con {len(team_players)} players y asignado al match {match_id}. Además asignados {len(remaining_players)} players individualmente.")

        else:
            if len(player_ids) < 2:
                self.assign_players_to_match(client=client, match_id=match_id, player_ids=player_ids)
                logger.warning(f"[Option 3 fallback] Pocos players, asignados individualmente.")
                return

            max_team_size = int(match.max_players / 2)
            team1_size = random.randint(1, max_team_size)
            team2_size = random.randint(1, max_team_size)

            team_players_1 = random.sample(player_ids, team1_size)
            remaining_after_team1 = [pid for pid in player_ids if pid not in team_players_1]
            team_players_2 = random.sample(remaining_after_team1, team2_size)
            remaining_players = [pid for pid in player_ids if pid not in team_players_1 and pid not in team_players_2]

            team_id_1 = self.create_team(db_session, team_players_1, name=f"Equipo Random 1 - Match {match_id}", match_id=None)
            team_id_2 = self.create_team(db_session, team_players_2, name=f"Equipo Random 2 - Match {match_id}", match_id=None)

            self.assign_team_to_match(client, team_id=team_id_1, match_id=match_id)
            self.assign_team_to_match(client, team_id=team_id_2, match_id=match_id)
            self.assign_players_to_match(client=client, match_id=match_id, player_ids=remaining_players)

            logger.info(f"[Option 3] Creado equipo {team_id_1} con {len(team_players_1)} players y equipo {team_id_2} con {len(team_players_2)} players. Ambos asignados al match {match_id}. Además asignados {len(remaining_players)} players individualmente.")

    def reset_db_state(self, db_session: Session):
        """
        Borra todos los datos de las tablas principales para dejar la base limpia entre tests.
        """
        # IMPORTANTE: respetar el orden para evitar errores de claves foráneas
        logger = None
        try:
            from src.utils.logger_config import test_logger
            logger = test_logger
        except Exception:
            pass

        models = [PlayerRelation, Match, Team, Player]
        for model in models:
            db_session.query(model).delete()

        db_session.commit()
        if logger:
            logger.info("Base de datos reseteada correctamente.")






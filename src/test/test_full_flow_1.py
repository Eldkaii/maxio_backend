import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.main import app
from src.models import Player, Team, Match, MatchPlayer, TeamEnum
from src.services.team_service import assign_team_players
from src.test.utils_common_methods import TestUtils
from sqlalchemy.orm import Session

from src.services.player_service import get_or_create_relation
from src.test.utils_common_methods import TestUtils
from src.utils.logger_config import test_logger as logger

utils = TestUtils()

client = TestClient(app)

@pytest.mark.nivel("alto")
def test_assign_match_winner_updates_stats_and_relations_correctly(client: TestClient, db_session: Session):
    """1) crear 6 players.
    2) Crear un historial de relaciones (jugaron juntos / separados) entre algunos de ellos.
    3) Crear un team, asignarle 3 jugadores a ese team.
    4) Crear un match
    5) Asignarle ese team al match
    6) Asignarle los otros 3 jugadores libres al match.
    7) Generar los equipos para el match con el balanceador.
    8) Usar la funcion assign_match_winner para indicar cual gano. """

    """
    PASO 1
    """
    # Crear 5 jugadores humanos
    player_ids = []
    for i in range(5):
        username = f"player{i}"
        utils.create_player(client, username=username)
        player = db_session.query(Player).filter_by(name=username).first()
        assert player is not None
        player_ids.append(player.id)

    # Crear 1 jugador bot
    utils.create_player(client, username="bot_player", is_bot=True)
    bot = db_session.query(Player).filter_by(name="bot_player").first()
    assert bot is not None
    player_ids.append(bot.id)

    """
    PASO 2
    """
    # Paso 2: Simular historial de relaciones (el bot no participa)
    get_or_create_relation(player1_id=player_ids[0], player2_id=player_ids[1], db=db_session,
                           new_game_together=True)  # player0 - player1 juntos
    get_or_create_relation(player1_id=player_ids[2], player2_id=player_ids[3], db=db_session,
                           new_game_together=False)  # player2 - player3 en contra
    get_or_create_relation(player1_id=player_ids[1], player2_id=player_ids[4], db=db_session,
                           new_game_together=True)  # player1 - player4 juntos

    for i in range(5):
        username = f"player{i}"
        player = db_session.query(Player).filter_by(name=username).first()
        print(player.name,player.cant_partidos)

    """
    PASO 3
    """

    # Paso 3: Crear un equipo prearmado y asignarle 3 jugadores usando assign_team_players
    team = Team(name="Prearmado 1")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Usamos assign_team_players para asignar los jugadores por IDs
    team = assign_team_players(
        db=db_session,
        team_id=team.id,
        player_ids=player_ids[:3]
    )

    print("Team creado:", [p.name for p in team.players])  # debería dar 3 nombres

    """
    PASO 4
    """

    # Paso 4: Crear el match (por endpoint)
    match_id = utils.create_match(client,6)
    match = db_session.query(Match).get(match_id)
    assert match is not None

    """
    PASO 5
    """
    # Paso 5: Asignar el equipo prearmado al match
    utils.assign_team_to_match(client=client, team_id=team.id, match_id=match.id)

    # Refrescar el objeto Match desde la base
    db_session.refresh(match)
    assert match.team1_id == team.id or match.team2_id == team.id

    for i in range(5):
        username = f"player{i}"
        player = db_session.query(Player).filter_by(name=username).first()
        print(player.name,player.cant_partidos)


    """
    PASO 6
    """
    players_libres = player_ids[3:5]  # player3 y player4
    utils.assign_players_to_match(client=client, match_id=match.id, player_ids=players_libres)

    # Verificamos que ahora el match tiene 5 jugadores asignados (3 del team + 2 libres)
    match_players = db_session.query(MatchPlayer).filter_by(match_id=match.id).all()
    print("Match players después de asignar el team:", match_players)  # debería haber 3

    db_session.expire_all()
    assert len(match_players) == 5

    # Paso 6 (continuación): Llenar con bots el match
    from src.services.match_service import fill_with_bots

    match = fill_with_bots(db=db_session, match=match)

    # Verificamos que hay 6 jugadores en total
    assert len(match.players) == 6
    # Verificamos que el bot está incluido
    assert any(player.is_bot for player in match.players)

    for i in range(5):
        username = f"player{i}"
        player = db_session.query(Player).filter_by(name=username).first()
        print(player.name,player.cant_partidos)


    """
    PASO 7
    """

    # Paso 7: Generar los equipos usando el balanceador
    res = client.post(f"/match/matches/{match.id}/generate-teams")
    assert res.status_code == 200, f"Error generando equipos: {res.text}"

    # Refrescar el match desde la base para ver los cambios
    db_session.refresh(match)

    # Asegurar que ambos equipos han sido asignados
    assert match.team1_id is not None, "team1_id no fue asignado"
    assert match.team2_id is not None, "team2_id no fue asignado"
    assert match.team1_id != match.team2_id, "Ambos teams tienen el mismo ID"

    # Verificar que cada equipo tiene 3 jugadores asignados
    team1 = db_session.query(Team).filter_by(id=match.team1_id).all()
    team2 = db_session.query(Team).filter_by(id=match.team2_id).all()

    assert len(team1[0].players) == 3, f"team1 tiene {len(team1[0].players)} jugadores, se esperaban 3"
    assert len(team2[0].players) == 3, f"team2 tiene {len(team2[0].players)} jugadores, se esperaban 3"

    res = client.post(f"/match/matches/{match.id}/balance-report")

    logger.info("BALANCE GENERADO DE EQUIPOS: /n" , res.json())



    """
   PASO 8
   """
    # Importar la función del servicio
    from src.services.match_service import assign_match_winner

    # Asignamos el equipo ganador arbitrariamente (por ejemplo, el team1)
    winning_team_id = match.team1_id
    winning_team = db_session.query(Team).get(winning_team_id)

    assign_match_winner(match=match, winning_team=winning_team, db=db_session)

    # Volvemos a refrescar el match
    db_session.refresh(match)

    # Verificamos que el equipo ganador quedó registrado
    assert match.winner_team_id == winning_team.id

    # Guardar el enum ganador según match.team1_id
    winning_team_enum = TeamEnum.team1 if winning_team.id == match.team1_id else TeamEnum.team2

    # Validamos que los jugadores tienen sus estadísticas actualizadas
    for player in match.players:
        print(player.name)
        db_session.refresh(player)

        # Obtener la asignación del jugador en el match
        mp = db_session.query(MatchPlayer).filter_by(match_id=match.id, player_id=player.id).first()
        assert mp is not None

        # Cantidad total de partidos debe ser 1 para todos
        assert player.cant_partidos == 1

        if mp.team == winning_team_enum:
            assert player.cant_partidos_ganados == 1
            assert player.recent_results[-1] == 1
        else:
            assert player.cant_partidos_ganados == 0
            assert player.recent_results[-1] == 0


    player1_id = match.players[0].id
    player2_id = match.players[1].id

    relation = get_or_create_relation(player1_id, player2_id, db=db_session)
    assert relation is not None
    assert relation.games_together + relation.games_apart > 0
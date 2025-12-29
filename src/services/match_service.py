from collections import defaultdict
from typing import Optional
from pathlib import Path

from sqlalchemy.orm import Session, joinedload
from src.models.player import Player, PlayerRelation
from src.models.match import Match, MatchPlayer, TeamEnum
from src.models.team import Team
from fastapi import HTTPException, APIRouter
from sqlalchemy import select, insert, func
from typing import List, Tuple
from sqlalchemy import select, update

from src.services.player_service import calculate_elo, update_player_match_history, get_or_create_relation
from src.services.team_service import get_team_relations, get_players_by_team_enum
from src.utils.balance_teams import balance_teams, chemistry_score, team_stats_summary, STAT_NAMES, \
    calculate_balance_score, calculate_stat_diff
from src.utils.build_match_response import build_individual_stats
from src.config import settings


from sqlalchemy.orm import Session
from src.schemas.match_schema import MatchCreate, MatchReportResponse, TeamBalanceReport
from src.utils.logger_config import app_logger as logger


from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os

from src.config import Settings

def create_match(match_data: MatchCreate, db: Session) -> Match:
    new_match = Match(
        date=match_data.date,
        max_players=match_data.max_players
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    logger.info(f"Match creado con ID {new_match.id} y fecha {new_match.date}")
    return new_match

def assign_team_to_match(team, match, db):
    """Requisitos de la función assign_team_to_match(team, match, db):
        Validar cantidad de jugadores:
        La cantidad de jugadores en team.players debe ser menor o igual a match.max_players / 2.

        Validar que el equipo no esté ya asignado:
        No debe haber otro equipo con el mismo team.id asignado ya al match (en match.team1_id o match.team2_id).

        Validar que no haya jugadores repetidos en ambos equipos:
        Si ya hay un equipo asignado, sus jugadores no deben superponerse con los del nuevo equipo.

        Validar que los jugadores del equipo estén asignados al match:

        Obtener los jugadores ya asignados al match (tabla match_players).

        Si algún jugador del equipo no está asignado, agregarlo a la tabla, siempre que no se exceda el máximo permitido (match.max_players).

        Agregar el equipo al match:

        Si no hay equipo en team1_id, asignar ahí el nuevo equipo, o si no, asignarlo a team2_id.

        Guardar todo en la base y confirmar con commit.

        """

    max_players = match.max_players
    team_size = len(team.players)

    # 1. Validar cantidad de jugadores en el equipo
    if team_size > max_players // 2:
        raise HTTPException(
            status_code=400,
            detail=f"El equipo tiene {team_size} jugadores, que excede la mitad del máximo permitido ({max_players // 2})."
        )

    # 2. Validar que el equipo no esté ya asignado
    if match.team1_id == team.id or match.team2_id == team.id:
        raise HTTPException(status_code=400, detail="El equipo ya está asignado a este match.")

    # 3. Validar que no haya jugadores repetidos en ambos equipos
    # Obtener jugadores del equipo ya asignado si existe
    other_team_players_ids = set()
    if match.team1_id and match.team1_id != team.id:
        other_team = db.query(type(team)).get(match.team1_id)
        other_team_players_ids.update(p.id for p in other_team.players)
    if match.team2_id and match.team2_id != team.id:
        other_team = db.query(type(team)).get(match.team2_id)
        other_team_players_ids.update(p.id for p in other_team.players)

    current_team_player_ids = {p.id for p in team.players}
    overlap = current_team_player_ids.intersection(other_team_players_ids)
    if overlap:
        raise HTTPException(
            status_code=400,
            detail=f"Hay jugadores que ya están en otro equipo asignado al match: {overlap}"
        )

    # 4. Validar jugadores ya asignados al match
    assigned_player_ids = {
        row[0] for row in db.execute(
            select(MatchPlayer.player_id).where(MatchPlayer.match_id == match.id)
        )
    }

    # Cantidad actual de jugadores en el match
    current_player_count = len(assigned_player_ids)

    # Jugadores nuevos que hay que agregar al match
    new_players = [p for p in team.players if p.id not in assigned_player_ids]

    # Validar que no exceda el max_players
    if current_player_count + len(new_players) > max_players:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se pueden agregar {len(new_players)} jugadores nuevos; "
                f"excede el máximo permitido de {max_players} en el match."
            )
        )

    # 5. Asignar el equipo al match
    if not match.team1_id:
        match.team1_id = team.id
        team_enum = TeamEnum.team1
    elif not match.team2_id:
        match.team2_id = team.id
        team_enum = TeamEnum.team2
    else:
        raise HTTPException(
            status_code=400,
            detail="El match ya tiene dos equipos asignados."
        )

    # Agregar jugadores nuevos a match_players con el team correcto
    for player in new_players:
        res = assign_player_to_match(db, match,player,team_enum)
        if not res:
            break

    db.commit()
    db.refresh(match)

def assign_player_to_match(db: Session, match: Match, player: Player, team: TeamEnum | None = None) -> bool:
    # Verificar si el jugador ya está en el match
    existing = db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match.id,
            MatchPlayer.player_id == player.id
        )
    ).first()

    if existing:
        return False  # Ya está en el match

    # Verificar si el match está lleno
    current_count = db.scalar(
        select(func.count()).select_from(MatchPlayer).where(MatchPlayer.match_id == match.id)
    )
    if current_count >= match.max_players:
        return False  # Match lleno

    # Insertar en tabla intermedia
    db.execute(
        insert(MatchPlayer).values(
            match_id=match.id,
            player_id=player.id,
            team=team
        )
    )
    db.commit()
    return True

# def generate_teams_for_match(match: Match, db: Session):
#     match_players = db.execute(
#         select(MatchPlayer).where(MatchPlayer.match_id == match.id)
#     ).scalars().all()
#
#     if len(match_players) < 2:
#         raise ValueError("No hay suficientes jugadores para formar equipos")
#
#     existing_teams = db.execute(
#         select(Team).where(Team.match_id == match.id)
#     ).scalars().all()
#
#
#
#     if len(existing_teams) >= 2:
#         raise ValueError("El match ya tiene dos equipos asignados")
#
#     players = [db.get(Player, mp.player_id) for mp in match_players]
#
#     groups = [[p] for p in players]
#
#
#     total_players = len(players)
#     if any(len(group) > total_players // 2 for group in groups):
#         raise ValueError("Un grupo tiene más jugadores que el permitido por equipo")
#
#     set_player_groups_for_match(match, groups,db)
#     team1, team2 = balance_teams(groups)
#
#     # Crear equipos y asignarlos al match
#     team1_entity = Team(name="Team A", players=team1, match_id=match.id)
#     team2_entity = Team(name="Team B", players=team2, match_id=match.id)
#
#     db.add_all([team1_entity, team2_entity])
#     db.commit()
#
#     # Asignar referencias en el objeto match para devolver actualizado
#     match.team1 = team1_entity
#     match.team2 = team2_entity
#
#     db.refresh(match)  # Refrescar para que esté sincronizado con DB
#
#     return match

def generate_teams_for_match(match_id: int, db: Session) -> Match:
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    if not match:
        logger.error(f"Match con id={match_id} no encontrado")
        raise HTTPException(status_code=404, detail="Match no encontrado")

    rows = db.execute(
        select(Player, MatchPlayer.team)
        .join(MatchPlayer, MatchPlayer.player_id == Player.id)
        .where(MatchPlayer.match_id == match.id)
    ).all()

    # logger.info(f"Total rows obtenidas del match {match.id}: {len(rows)}")
    # for i, (player, team) in enumerate(rows):
    #     logger.info(f"Row {i + 1}: Player(id={player.id}, name={player.name}), team={team}")

    if not rows:
        logger.warning(f"No hay jugadores asignados al match {match_id}")
        raise HTTPException(status_code=400, detail="No hay jugadores asignados al match")

    groups_dict = defaultdict(list)
    individual_players = []

    for player, team in rows:
        if team is None:
            #logger.info(f"Jugador sin team: {player.name} (id={player.id}) → agregado a individual_players")
            individual_players.append(player)
        else:
            #logger.info(f"Jugador con team '{team}': {player.name} (id={player.id}) → agregado a groups_dict[{team}]")
            groups_dict[team].append(player)

    input_groups = list(groups_dict.values()) + [[p] for p in individual_players]

    # Loguear cómo quedaron los grupos armados
    # logger.info(f"Total de grupos prearmados (con team): {len(groups_dict)}")
    # for team_key, group in groups_dict.items():
    #     nombres = [p.name for p in group]
    #     logger.info(f"Grupo del team {team_key}: {nombres}")
    #
    # logger.info(f"Total de jugadores individuales: {len(individual_players)}")
    # logger.info(f"input_groups final: {[[p.name for p in g] for g in input_groups]}")

    set_pre_set_player_groups_for_match(match, input_groups,db)

    total_players = sum(len(g) for g in input_groups)

    if total_players < 2:
        logger.error(f"Match {match_id} tiene menos de 2 jugadores")
        raise HTTPException(status_code=400, detail="Se necesitan al menos 2 jugadores para formar equipos")

    if any(len(group) > total_players // 2 for group in input_groups):
        logger.error(f"En match {match_id}, un grupo tiene más jugadores que el permitido por equipo")
        raise HTTPException(
            status_code=400,
            detail=f"Un grupo tiene más jugadores que el permitido por equipo (máximo {total_players // 2})"
        )

    logger.info(f"Match {match_id}: intentando balancear {total_players} jugadores con {len(groups_dict)} grupos")

    team_a, team_b = balance_teams(input_groups)

    if not match.team1:
        team1 = Team(name="Team 1", players=team_a)
        db.add(team1)
        db.commit()
        match.team1 = team1
    else:
        match.team1.players = team_a

    if not match.team2:
        team2 = Team(name="Team 2", players=team_b)
        db.add(team2)
        db.commit()
        match.team2 = team2
    else:
        match.team2.players = team_b

    for player in team_a:
        db.execute(
            update(MatchPlayer)
            .where(
                MatchPlayer.match_id == match.id,
                MatchPlayer.player_id == player.id
            )
            .values(team=TeamEnum.team1)
        )

    for player in team_b:
        db.execute(
            update(MatchPlayer)
            .where(
                MatchPlayer.match_id == match.id,
                MatchPlayer.player_id == player.id
            )
            .values(team=TeamEnum.team2)
        )

    db.commit()

    db.refresh(match)
    match = db.query(Match).options(
        joinedload(Match.team1).joinedload(Team.players),
        joinedload(Match.team2).joinedload(Team.players)
    ).filter(Match.id == match_id).first()

    logger.info(f"Match {match_id} balanceado correctamente")
    return match

def fill_with_bots(db: Session, match: Match) -> Match:
    current_players = match.players
    current_count = len(current_players)
    max_players = match.max_players

    # Si ya está lleno, no hacer nada
    if current_count >= max_players:
        return match

    # Calcular cuántos faltan
    missing = max_players - current_count

    # Buscar bots disponibles que no estén ya en el match
    bot_candidates = db.scalars(
        select(Player)
        .where(Player.is_bot == True)
        .where(Player.id.notin_([p.id for p in current_players]))
        .limit(missing)
    ).all()

    for bot in bot_candidates:
        match.players.append(bot)

    db.commit()
    db.refresh(match)
    return match

def assign_match_winner(match: Match, winning_team: Team, db: Session):
    # Validar que el equipo pertenece al match
    if winning_team.id not in [match.team1_id, match.team2_id]:
        raise ValueError("El equipo no pertenece al match")

    # Guardar el equipo ganador
    match.winner_team_id = winning_team.id
    db.add(match)
    db.commit()
    db.refresh(match)

    # Obtener todos los MatchPlayer
    match_players = db.query(MatchPlayer).filter_by(match_id=match.id).all()

    # Determinar equipo ganador (enum)
    winning_team_enum = TeamEnum.team1 if winning_team.id == match.team1_id else TeamEnum.team2

    # IDs de ganadores y perdedores
    winning_ids = {mp.player_id for mp in match_players if mp.team == winning_team_enum}
    losing_ids = {mp.player_id for mp in match_players if mp.team != winning_team_enum}

    # Actualizar historial de cada jugador
    for player in match.players:
        update_player_match_history(username=player.name, won=player.id in winning_ids, db=db)

    # Actualizar relaciones entre jugadores
    player_list = match.players
    for i, player1 in enumerate(player_list):
        for player2 in player_list[i + 1:]:
            same_team = (
                (player1.id in winning_ids and player2.id in winning_ids) or
                (player1.id in losing_ids and player2.id in losing_ids)
            )
            get_or_create_relation(player1.id, player2.id, db=db, new_game_together=same_team)

def get_match_balance_report(match_id: int, db: Session) -> MatchReportResponse:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise ValueError("Match no encontrado")

    # Obtener jugadores por equipo
    team1_players: list[Player] = get_players_by_team_enum(match_id, TeamEnum.team1, db)
    team2_players: list[Player] = get_players_by_team_enum(match_id, TeamEnum.team2, db)

    # Calcular stats agregadas por equipo
    team1_total = team_stats_summary(team1_players)
    team2_total = team_stats_summary(team2_players)

    #print("match.pre_set_groups:", match.pre_set_groups)

    players_preserved_groups , names_players_preserved_groups = get_player_groups_from_match(match,db)


    # Crear objetos de respuesta por equipo
    team1_report = TeamBalanceReport(
        players=[p.name for p in team1_players],
        total_stats=team1_total,
        individual_stats=build_individual_stats(team1_players),
        chemistry_score=chemistry_score(team1_players),
    )

    team2_report = TeamBalanceReport(
        players=[p.name for p in team2_players],
        total_stats=team2_total,
        individual_stats=build_individual_stats(team2_players),
        chemistry_score=chemistry_score(team2_players),
    )

    # Ensamblar la respuesta completa
    response = MatchReportResponse(
        match_id=match_id,
        teams={
            "team_1": team1_report,
            "team_2": team2_report,
        },
        preserved_groups=names_players_preserved_groups,
        balance_score=calculate_balance_score(team1_players, team2_players),
        stat_diff=calculate_stat_diff(team1_players, team2_players),
        relations_summary={
            "team_1": get_team_relations(team1_players, db),
            "team_2": get_team_relations(team2_players, db),
        },
    )

    return response


def get_player_groups_from_match(match: Match, db: Session) -> Tuple[List[List[Player]], List[List[str]]]:
    """
    Devuelve:
    - Una lista de listas de objetos Player que representan los grupos predefinidos.
    - Una lista de listas de nombres de esos jugadores (en el mismo orden).
    """
    player_groups = []
    player_name_groups = []

    for group_ids in match.pre_set_groups or []:
        if len(group_ids) <= 1:
            continue  # Ignorar grupos de un solo jugador

        players = db.query(Player).filter(Player.id.in_(group_ids)).all()
        players_dict = {p.id: p for p in players}

        ordered_group = [players_dict[pid] for pid in group_ids if pid in players_dict]


        player_groups.append(ordered_group)
        name_group = [p.name for p in ordered_group]
        player_name_groups.append(name_group)

    return player_groups, player_name_groups



def set_pre_set_player_groups_for_match(match: Match, groups: List[List[Player]], db: Session) -> None:
    """
    Recibe una lista de grupos de Player y actualiza el campo pre_set_groups con sus IDs.
    """
    match.pre_set_groups = [[player.id for player in group] for group in groups]
    db.add(match)
    db.commit()



def generate_match_card(match_id: int, db: Session,print_icons:bool = False) -> BytesIO:
    report = get_match_balance_report(match_id, db)

    logger.info(f"REPORTE: {report}")

    template = Image.open(Settings.API_MATCH_TEMPLATE_PATH).convert("RGBA")
    draw = ImageDraw.Draw(template)

    regions = _build_match_layout(draw, template, debug=True)
    location_fonts = Settings.DEFAULT_FONTS_PATH
    fonts = _load_fonts(template.height, location_fonts)

    _draw_match_header(draw, template, report, fonts)

    _draw_team_block(
        draw,
        template,
        regions["team_1"],
        report.teams["team_1"],
        fonts["name"],
        side="left",
        print_icons=True,
    )

    _draw_team_block(
        draw,
        template,
        regions["team_2"],
        report.teams["team_2"],
        fonts,
        side="right",
        print_icons=True,
    )

    _draw_stat_lider(
        draw,
        template,
        regions["icons"],
        report.teams["team_1"],
        report.teams["team_2"],
        debug=False)

    _draw_comparison_star(
        template,
        regions["stats"],
        report,
        fonts,
    )



    _draw_preserved_groups(draw, template, report, fonts)

    buffer = BytesIO()
    template.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ---------- Helpers ----------
def load_match_fonts(size):
    pass

def _draw_match_header(draw, template, report, fonts):
    pass

from PIL import ImageDraw, ImageFont

def _draw_team_block(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    rect: tuple[int, int, int, int],
    team,
    fonts: dict | ImageFont.FreeTypeFont | None = None,
    side: str = "left",
    debug: bool = False,
    print_icons: bool = False,  # <-- nuevo parámetro
) -> None:
    STAT_ORDER = ["tiro", "ritmo", "fisico", "defensa", "aura"]
    STAT_THRESHOLD = 80

    # =====================
    # Cache de iconos
    # =====================
    _ICON_CACHE: dict[str, Image.Image] = {}

    def _get_stat_icon(stat_name: str, size: int) -> Image.Image | None:
        key = f"{stat_name}_{size}"
        if key in _ICON_CACHE:
            return _ICON_CACHE[key]

        path = os.path.join(settings.API_ICONS_MATCH_PATH_FOLDER, f"{stat_name}.png")
        if not os.path.exists(path):
            return None

        icon = Image.open(path).convert("RGBA")
        icon = icon.resize((size, size), Image.LANCZOS)
        _ICON_CACHE[key] = icon
        return icon

    def _truncate_username(name: str, max_len: int = 8) -> str:
        return name if len(name) <= max_len else name[: max_len - 2] + ".."

    x1, y1, x2, y2 = rect
    w = x2 - x1
    h = y2 - y1

    # ─────────────────────────────
    # Fuentes
    # ─────────────────────────────
    if fonts is None:
        title_font = player_font = ImageFont.load_default()
    elif isinstance(fonts, dict):
        title_font = fonts.get("name") or ImageFont.load_default()
        player_font = fonts.get("stats") or ImageFont.load_default()
    else:
        title_font = player_font = fonts

    # ─────────────────────────────
    # Fondo tipo card
    # ─────────────────────────────
    CARD_RADIUS = int(h * 0.06)
    CARD_COLOR = (245, 245, 245, 12)

    overlay = Image.new("RGBA", template.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(rect, CARD_RADIUS, fill=CARD_COLOR)
    template.alpha_composite(overlay)

    # ─────────────────────────────
    # Título
    # ─────────────────────────────
    title_h = int(h * 0.12)
    if side == 'left':
        title = "Equipo Rojo"
    else:
        title = "Equipo Amarrillo"

    draw.text(
        (x1 + w // 2, y1 + title_h // 2),
        title,
        fill=(30, 30, 30),
        font=title_font,
        anchor="mm",
    )

    content_top = y1 + title_h
    # ─────────────────────────────
    # Players
    # ─────────────────────────────
    players = getattr(team, "individual_stats", [])
    if not players:
        return

    # ─────────────────────────────
    # Ordenar players por prioridad de stats (sin repetir)
    # ─────────────────────────────
    PLAYER_ORDER = ["aura", "tiro", "ritmo", "fisico", "defensa"]
    ordered_players = []
    used_names: set[str] = set()

    for stat_name in PLAYER_ORDER:
        best_player = None
        best_value = -1
        for p in players:
            if p.name in used_names:
                continue
            value = p.stats.get(stat_name, 0)
            if value > best_value:
                best_value = value
                best_player = p
        if best_player:
            ordered_players.append(best_player)
            used_names.add(best_player.name)

    # fallback si sobran players
    for p in players:
        if p.name not in used_names:
            ordered_players.append(p)
    players = ordered_players

    # ─────────────────────────────
    # Layout
    # ─────────────────────────────
    available_h = y2 - content_top
    row_h = available_h / len(players)
    is_left = side == "left"
    PADDING_X = int(w * 0.06)
    ICON_TEXT_GAP = 10

    # ─────────────────────────────
    # Precalcular winner por stat
    # ─────────────────────────────
    stat_winners: dict[str, object] = {}
    for stat_name in STAT_ORDER:
        best_player = None
        best_value = STAT_THRESHOLD
        for p in players:
            value = p.stats.get(stat_name, 0)
            if value > best_value:
                best_value = value
                best_player = p
        if best_player:
            stat_winners[stat_name] = best_player

    # ─────────────────────────────
    # Render players
    # ─────────────────────────────
    for i, player_stat in enumerate(players):
        row_top = content_top + i * row_h
        cy = int(row_top + row_h / 2)
        name = _truncate_username(getattr(player_stat, "name", "Unknown"))

        # Stats que le corresponden (máx 2)
        player_icons = []
        if print_icons:
            player_icons = [
                stat_name
                for stat_name, winner in stat_winners.items()
                if winner is player_stat
            ][:2]

        ICON_COUNT = len(player_icons)
        icon_radius = int(row_h * 0.11) + 5
        icon_gap = icon_radius * 2
        icons_width = ICON_COUNT * icon_gap if print_icons else 0

        # ─────────────────────────────
        # Alineación original (con espacio fijo si no hay íconos)
        # ─────────────────────────────
        if is_left:
            text_x = x2 - PADDING_X - icons_width - ICON_TEXT_GAP
            text_anchor = "rm"
            icons_start_x = text_x + ICON_TEXT_GAP + icon_radius
            icon_dir = 1
        else:
            text_x = x1 + PADDING_X + icons_width + ICON_TEXT_GAP
            text_anchor = "lm"
            icons_start_x = text_x - ICON_TEXT_GAP - icon_radius
            icon_dir = -1

        # ─────────────────────────────
        # Texto con sombra
        # ─────────────────────────────
        shadow_offset = 1
        shadow_color = (100, 100, 100)
        draw.text(
            (text_x + shadow_offset, cy + shadow_offset),
            name,
            fill=shadow_color,
            font=player_font,
            anchor=text_anchor,
        )
        draw.text(
            (text_x, cy),
            name,
            fill=(20, 20, 20),
            font=player_font,
            anchor=text_anchor,
        )

        # ─────────────────────────────
        # Íconos
        # ─────────────────────────────
        if print_icons:
            icon_size = icon_radius * 2 + 1
            for idx, stat_name in enumerate(player_icons):
                cx = icons_start_x + icon_dir * idx * icon_gap
                icon = _get_stat_icon(stat_name, icon_size)
                if not icon:
                    continue
                template.paste(
                    icon,
                    (int(cx - icon_size / 2), int(cy - icon_size / 2)),
                    icon,
                )

        # ─────────────────────────────
        # Separador
        # ─────────────────────────────
        if i < len(players) - 1:
            sep_y = int(row_top + row_h)
            center_x = (x1 + x2) // 2
            draw.line(
                [
                    (center_x - int(w * 0.23), sep_y),
                    (center_x + int(w * 0.23), sep_y),
                ],
                fill=(120, 130, 140),
                width=2,
            )

        # ─────────────────────────────
        # Debug
        # ─────────────────────────────
        if debug:
            draw.rectangle(
                (x1, int(row_top), x2, int(row_top + row_h)),
                outline=(180, 180, 180),
                width=1,
            )


def _draw_stat_lider(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    rect: tuple[int, int, int, int],
    team1,
    team2,
    fonts: dict | ImageFont.FreeTypeFont | None = None,
    debug: bool = False,
) -> None:
    """
    Dibuja dentro del rect la comparación de players de ambos equipos.
    Cada línea muestra el icon del stat correspondiente al orden:
    1: aura, 2: tiro, 3: ritmo, 4: fisico, 5: defensa
    alineado a la izquierda si el ganador es team 1 y a la derecha si es team 2.
    """
    PLAYER_ORDER = ["aura", "tiro", "ritmo", "fisico", "defensa"]

    x1, y1, x2, y2 = rect
    w = x2 - x1
    h = y2 - y1

    if fonts is None:
        font = ImageFont.load_default()
    elif isinstance(fonts, dict):
        font = fonts.get("stats") or ImageFont.load_default()
    else:
        font = fonts

    # Reservar espacio para título
    title_h = int(h * 0.12)

    # Cache de íconos
    _ICON_CACHE: dict[str, Image.Image] = {}

    def _get_stat_icon(stat_name: str, size: int) -> Image.Image | None:
        key = f"{stat_name}_{size}"
        if key in _ICON_CACHE:
            return _ICON_CACHE[key]

        path = os.path.join(settings.API_ICONS_MATCH_PATH_FOLDER, f"{stat_name}.png")
        if not os.path.exists(path):
            return None

        icon = Image.open(path).convert("RGBA")
        icon = icon.resize((size, size), Image.LANCZOS)
        _ICON_CACHE[key] = icon
        return icon

    # Ordenar players según prioridad de stats
    def ordenar_players(players):
        ordered = []
        used_names = set()
        for stat_name in PLAYER_ORDER:
            best_player = None
            best_value = -1
            for p in players:
                if p.name in used_names:
                    continue
                value = p.stats.get(stat_name, 0)
                if value > best_value:
                    best_value = value
                    best_player = p
            if best_player:
                ordered.append(best_player)
                used_names.add(best_player.name)
        for p in players:
            if p.name not in used_names:
                ordered.append(p)
        return ordered

    players1 = ordenar_players(getattr(team1, "individual_stats", []))
    players2 = ordenar_players(getattr(team2, "individual_stats", []))

    max_len = min(len(players1), len(players2), len(PLAYER_ORDER))
    row_h = (h - title_h) / max_len
    icon_radius = int(row_h * 0.25)

    for i in range(max_len):
        stat_name = PLAYER_ORDER[i]
        p1 = players1[i]
        p2 = players2[i]

        v1 = p1.stats.get(stat_name, 0)
        v2 = p2.stats.get(stat_name, 0)

        if v1 == v2:
            winner_team = "draw"  # indicamos empate

        else:
            winner_team = "team1" if v1 > v2 else "team2"

        # Coordenadas verticales
        row_top = y1 + title_h + i * row_h
        cy = int(row_top + row_h / 2)

        # Icono del stat correspondiente a la línea
        icon = _get_stat_icon(stat_name, icon_radius * 2)
        if not icon:
            continue

        # Coordenadas horizontal según equipo ganador
        if winner_team == "team1":
            cx = x1 + icon_radius
        elif winner_team == "team2":
            cx = x2 - icon_radius
        else:  # empate
            cx = (x1 + x2) // 2

        template.paste(
            icon,
            (int(cx - icon_radius), int(cy - icon_radius)),
            icon,
        )

        if debug:
            draw.rectangle(
                (x1, int(row_top), x2, int(row_top + row_h)),
                outline=(180, 180, 180),
                width=1,
            )


def _draw_preserved_groups(draw, template, report, fonts):
    pass

def _rect_from_ratios(
    template: Image.Image,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[int, int, int, int]:
    w, h = template.size
    return (
        int(w * x1),
        int(h * y1),
        int(w * x2),
        int(h * y2),
    )


def _build_match_layout(
    draw: ImageDraw.ImageDraw,
    template: Image.Image,
    debug: bool = True,
) -> dict[str, tuple[int, int, int, int]]:
    regions = {}

    regions["header"] = _rect_from_ratios(template, 0.12, 0.14, 0.85, 0.25)
    regions["stats"] = _rect_from_ratios(template, 0.15, 0.26, 0.35, 0.56)
    regions["relations"] = _rect_from_ratios(template, 0.15, 0.56, 0.35, 0.83)
    regions["team_1"] = _rect_from_ratios(template, 0.40, 0.26, 0.60, 0.83)
    regions["icons"] = _rect_from_ratios(template, 0.60, 0.26, 0.65, 0.83)
    regions["team_2"] = _rect_from_ratios(template, 0.65, 0.26, 0.85, 0.83)
    regions["footer"] = _rect_from_ratios(template, 0.12, 0.85, 0.85, 0.98)

    if debug:
        #_draw_region_debug(draw, regions)
        pass

    return regions

def _draw_region_debug(
    draw: ImageDraw.ImageDraw,
    regions: dict[str, tuple[int, int, int, int]],
) -> None:
    COLORS = {
        "header": (0, 200, 255, 255),
        "relations": (255, 200, 0, 255),
        "team_1": (0, 180, 120, 255),
        "icons": (200, 200, 200, 255),
        "team_2": (180, 80, 255, 255),
        "footer": (255, 80, 80, 255),
    }

    for name, rect in regions.items():
        draw.rectangle(
            rect,
            outline=COLORS.get(name, (255, 0, 0, 255)),
            width=2,
        )

def _draw_comparison_star(
    template: Image.Image,
    rect: tuple[int, int, int, int],
    report,
    fonts: dict,
) -> None:



    all_stats = (
            list(report.teams["team_1"].total_stats.values()) +
            list(report.teams["team_2"].total_stats.values())
    )
    max_value = max(all_stats) + 20

    draw_comparison_stats_star(
        template,
        rect,
        stats_a=[
            ("AUR", report.teams["team_1"].total_stats["aura"]),
            ("TIR", report.teams["team_1"].total_stats["tiro"]),
            ("RIT", report.teams["team_1"].total_stats["ritmo"]),
            ("FIS", report.teams["team_1"].total_stats["fisico"]),
            ("DEF", report.teams["team_1"].total_stats["defensa"]),
        ],
        stats_b=[
            ("AUR", report.teams["team_2"].total_stats["aura"]),
            ("TIR", report.teams["team_2"].total_stats["tiro"]),
            ("RIT", report.teams["team_2"].total_stats["ritmo"]),
            ("FIS", report.teams["team_2"].total_stats["fisico"]),
            ("DEF", report.teams["team_2"].total_stats["defensa"]),
        ],
        max_value=max_value,
        colors=((255, 0, 0),  # azul intenso
                (255, 255, 0)) , # naranja fuerte
        font = fonts.get("small") if fonts else None
    )

import math
from PIL import Image, ImageDraw, ImageFont

def draw_comparison_stats_star(
    template: Image.Image,
    rect: tuple[int, int, int, int],
    stats_a: list[tuple[str, float]],
    stats_b: list[tuple[str, float]],
    *,
    max_value: 500,
    colors: tuple[tuple[int, int, int], tuple[int, int, int]],
    font: ImageFont.FreeTypeFont | None = None,
    debug: bool = False,
) -> None:

    assert len(stats_a) == len(stats_b)

    x1, y1, x2, y2 = rect
    w = x2 - x1
    h = y2 - y1

    size = int(min(w, h) * 0.95)
    cx = x1 + w // 2
    cy = y1 + h // 2

    center = (size // 2, size // 2)
    radius = size * 0.45

    if font is None:
        font = ImageFont.load_default()

    labels = [label for label, _ in stats_a]

    def normalize(stats):
        return [
            min(max(v, 0), max_value) / max_value
            for _, v in stats
        ]

    norm_a = normalize(stats_a)
    norm_b = normalize(stats_b)

    # ==========================================================
    # Base radar (grid)
    # ==========================================================
    radar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(radar)

    for f in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = []
        for i in range(len(labels)):
            a = math.radians(90 + i * (360 / len(labels)))
            pts.append((
                center[0] + math.cos(a) * radius * f,
                center[1] - math.sin(a) * radius * f,
            ))
        rdraw.polygon(pts, outline=(0, 0, 0, 120))

    # ==========================================================
    # Helper para dibujar estrella
    # ==========================================================
    def draw_star(norm_values, base_color):
        star = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(star)

        pts = []
        for i, v in enumerate(norm_values):
            a = math.radians(90 + i * (360 / len(labels)))
            pts.append((
                center[0] + math.cos(a) * radius * v,
                center[1] - math.sin(a) * radius * v,
            ))

        fill_color = (*base_color, 90)
        outline_color = (*base_color, 220)

        sdraw.polygon(pts, fill=fill_color)
        sdraw.line(pts + [pts[0]], fill=outline_color, width=2)

        return star, pts

    # ==========================================================
    # Dibujar ambas estrellas
    # ==========================================================
    star_a, pts_a = draw_star(norm_a, colors[0])
    star_b, pts_b = draw_star(norm_b, colors[1])

    combined = Image.alpha_composite(radar, star_a)
    combined = Image.alpha_composite(combined, star_b)

    template.alpha_composite(
        combined,
        (cx - size // 2, cy - size // 2)
    )

    # ==========================================================
    # Labels
    # ==========================================================
    label_r = radius + 14
    draw = ImageDraw.Draw(template)

    for i, label in enumerate(labels):
        a = math.radians(90 + i * (360 / len(labels)))
        lx = cx + math.cos(a) * label_r
        ly = cy - math.sin(a) * label_r

        draw.text(
            (lx, ly),
            label,
            fill=(0, 0, 0, 220),
            font=font,
            anchor="mm",
        )

    if debug:
        draw.rectangle(rect, outline=(255, 0, 0, 255), width=1)

def _load_fonts(
    template_height: int,
    font_dir: str,
    *,
    name_scale: float = 0.05,
    stats_scale: float = 0.05 #0.022
) -> dict:
    """
    Carga las fuentes necesarias para la carta a partir de un directorio.

    El directorio debe contener:
        - name.(ttf|otf)   -> fuente para el nombre
        - stats.(ttf|otf)  -> fuente para stats

    Args:
        template_height: altura del template en píxeles
        font_dir: ruta al directorio de fuentes
        name_scale: proporción de la altura para el nombre
        stats_scale: proporción de la altura para stats

    Returns:
        dict con las fuentes cargadas
    """

    font_dir = Path(font_dir)

    name_size = int(template_height * name_scale)
    stats_size = int(template_height * stats_scale)

    def _find_font(filename_base: str) -> Path:
        for ext in ("ttf", "otf"):
            path = font_dir / f"{filename_base}.{ext}"
            if path.exists():
                return path
        raise FileNotFoundError(
            f"No se encontró {filename_base}.ttf ni {filename_base}.otf en {font_dir}"
        )

    try:
        name_font_path = _find_font("HighVoltage_Rough")
        stats_font_path = _find_font("HighVoltage_Rough")

        return {
            "name": ImageFont.truetype(str(name_font_path), name_size),
            "stats": ImageFont.truetype(str(stats_font_path), stats_size),
        }

    except Exception as e:
        raise RuntimeError(f"Error cargando fuentes desde {font_dir}: {e}")
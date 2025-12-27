# src/models/player.py

from sqlalchemy import Column, Integer, Float,String, ForeignKey, UniqueConstraint, Boolean, or_, case, func, desc
from sqlalchemy.orm import Session, aliased

from sqlalchemy.orm import relationship
from src.database import Base
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY  # Solo si usás PostgreSQL



class PlayerRelation(Base):
    __tablename__ = "player_relations"

    id = Column(Integer, primary_key=True)
    player1_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    player2_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)

    # Nuevos campos:
    games_together = Column(Integer, default=0, nullable=False)   # mismos equipos
    games_apart = Column(Integer, default=0, nullable=False)      # equipos contrarios

    # Para evitar duplicados cruzados (ej: (1,2) y (2,1))
    __table_args__ = (
        UniqueConstraint("player1_id", "player2_id", name="uq_player_relation"),
    )

    player1 = relationship("Player", foreign_keys=[player1_id], back_populates="relations_as_player1")
    player2 = relationship("Player", foreign_keys=[player2_id], back_populates="relations_as_player2")


def update_player_relation(
    db: Session,
    player_a_id: int,
    player_b_id: int,
    played_together: bool
):
    # Ordenamos los IDs para evitar duplicados cruzados
    player1_id, player2_id = sorted([player_a_id, player_b_id])

    relation = db.query(PlayerRelation).filter_by(
        player1_id=player1_id,
        player2_id=player2_id
    ).first()

    if not relation:
        relation = PlayerRelation(
            player1_id=player1_id,
            player2_id=player2_id
        )
        db.add(relation)

    if played_together:
        relation.games_together += 1
    else:
        relation.games_apart += 1

    db.commit()

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cant_partidos = Column(Integer, default=0)
    cant_partidos_ganados = Column(Integer, default=0)
    is_bot = Column(Boolean, default=False)

    # Guardar los últimos 10 resultados como True (victoria) o False (derrota)
    # Esto funciona solo si usás PostgreSQL
    recent_results = Column(PG_ARRAY(Boolean), default=[])

    # ELO general que afecta crecimiento de stats
    elo = Column(Integer, default=1000)  # Conviene arrancar con 1000 como base

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    user = relationship("User", back_populates="player")

    #stats
    tiro = Column(Float,  default=50, nullable=False)
    ritmo = Column(Float, default=50,nullable=False)
    fisico = Column(Float, default=50,nullable=False)
    defensa = Column(Float, default=50,nullable=False)
    aura = Column(Float, default=50,nullable=False)

    photo_path = Column(String, nullable=True)


    # Relaciones desde Player hacia PlayerRelation (sin usar backref ahora)
    relations_as_player1 = relationship(
        "PlayerRelation",
        foreign_keys="[PlayerRelation.player1_id]",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="player1"
    )

    relations_as_player2 = relationship(
        "PlayerRelation",
        foreign_keys="[PlayerRelation.player2_id]",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="player2"
    )

    match_associations = relationship("MatchPlayer", back_populates="player", cascade="all, delete-orphan")
    matches = relationship("Match", secondary="match_players", back_populates="players", overlaps="match_associations")



    @property
    def all_relationships(self):
        return self.relations_as_player1 + self.relations_as_player2

    def parse_recent_results(recent: str) -> list[bool]:
        return [c == "1" for c in recent]

    def serialize_recent_results(results: list[bool]) -> str:
        return ''.join(['1' if r else '0' for r in results])


    def top_teammates(self, db: Session, limit: int = 5, exclude_bots: bool = False):
        relations = db.query(
            case(
                (PlayerRelation.player1_id == self.id, PlayerRelation.player2_id),
                else_=PlayerRelation.player1_id
            ).label("other_id"),
            PlayerRelation.games_together + PlayerRelation.games_apart
        ).filter(
            or_(
                PlayerRelation.player1_id == self.id,
                PlayerRelation.player2_id == self.id
            )
        ).order_by(
            (PlayerRelation.games_together + PlayerRelation.games_apart).desc()
        ).limit(limit * 2).all()  # usamos *2 para poder filtrar después

        result = []
        for other_id, total_games in relations:
            other_player = db.get(Player, other_id)
            if exclude_bots and other_player.is_bot:
                continue
            result.append((other_player, total_games))
            if len(result) >= limit:
                break
        return result

    def top_allies(self, db: Session, limit: int = 3, exclude_bots: bool = False):
        # Definimos "other_id" como el ID del aliado
        other_id = case(
            (PlayerRelation.player1_id == self.id, PlayerRelation.player2_id),
            else_=PlayerRelation.player1_id
        ).label("other_id")

        # Hacemos la consulta con agregación de la suma de games_together
        results = (
            db.query(
                other_id,
                func.sum(PlayerRelation.games_together).label("total_games")
            )
            .filter(
                or_(
                    PlayerRelation.player1_id == self.id,
                    PlayerRelation.player2_id == self.id
                )
            )
            .group_by(other_id)
            .order_by(func.sum(PlayerRelation.games_together).desc())
            .limit(limit)
            .all()
        )

        allies = []
        for ally_id, total_games in results:
            ally = db.get(Player, ally_id)
            if exclude_bots and ally.is_bot:
                continue
            allies.append((ally, total_games))
        return allies

    def top_opponents(self, db: Session, limit: int = 3, exclude_bots: bool = False):
        # Alias para la tabla Player, para que se entienda que es el oponente
        Opponent = aliased(Player)

        # Creamos una subquery que calcula el id del "otro jugador" y los juegos separados
        subquery = db.query(
            case(
                (PlayerRelation.player1_id == self.id, PlayerRelation.player2_id),
                else_=PlayerRelation.player1_id
            ).label("other_id"),
            PlayerRelation.games_apart.label("games")
        ).filter(
            or_(
                PlayerRelation.player1_id == self.id,
                PlayerRelation.player2_id == self.id
            )
        ).subquery()

        # Hacemos join con Player para obtener los datos del oponente
        query = db.query(Opponent, subquery.c.games).join(
            subquery, Opponent.id == subquery.c.other_id
        )

        if exclude_bots:
            query = query.filter(Opponent.is_bot.is_(False))

        query = query.order_by(desc(subquery.c.games)).limit(limit)

        return query.all()  # Devuelve [(Player, games), ...]

    def get_relation_with(self, other_id: int) -> PlayerRelation | None:
        for r in self.all_relationships:
            if (r.player1_id == self.id and r.player2_id == other_id) or \
                    (r.player2_id == self.id and r.player1_id == other_id):
                return r
        return None
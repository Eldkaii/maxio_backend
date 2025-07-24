

# def test_get_team_relations(db_session: Session):
#     # Crear 3 jugadores y relaciones entre ellos
#     alice = Player(name="Alice", ...)
#     bob = Player(name="Bob", ...)
#     charlie = Player(name="Charlie", ...)
#     db_session.add_all([alice, bob, charlie])
#     db_session.commit()
#
#     # Crear relaciones
#     relation1 = PlayerRelation(player_a_id=alice.id, player_b_id=bob.id, games_together=5, games_apart=1)
#     relation2 = PlayerRelation(player_a_id=alice.id, player_b_id=charlie.id, games_together=0, games_apart=2)
#     db_session.add_all([relation1, relation2])
#     db_session.commit()
#
#     result = get_team_relations([alice, bob, charlie], db_session)
#
#     assert ("Alice", "Bob", 5) in result["together"]
#     assert ("Alice", "Charlie", 2) in result["apart"]


# def test_get_players_by_team(db_session: Session):
#     # Crear jugadores
#     alice = Player(name="Alice", ...)
#     bob = Player(name="Bob", ...)
#     db_session.add_all([alice, bob])
#     db_session.commit()
#
#     # Crear un team
#     team = Team(...)
#     db_session.add(team)
#     db_session.commit()
#
#     # Asociar jugadores al team con MatchPlayer
#     mp1 = MatchPlayer(player_id=alice.id, team_id=team.id)
#     mp2 = MatchPlayer(player_id=bob.id, team_id=team.id)
#     db_session.add_all([mp1, mp2])
#     db_session.commit()
#
#     players = get_players_by_team(team.id, db_session)
#
#     assert len(players) == 2
#     assert set(p.name for p in players) == {"Alice", "Bob"}
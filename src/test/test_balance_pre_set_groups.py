from src.utils.balance_teams import balance_teams


class PlayerStub:
    def __init__(self, player_id: int):
        self.id = player_id
        self.tiro = 50
        self.ritmo = 50
        self.fisico = 50
        self.defensa = 50
        self.aura = 5

    def get_relation_with(self, _other_player_id):
        return None


def test_balance_accepts_three_pre_set_pairs_when_bots_can_complete_capacity():
    """Tres duplas caben en un partido 5v5 aunque queden 2 y 4 convocados."""
    players = [PlayerStub(player_id) for player_id in range(1, 7)]
    groups = [players[0:2], players[2:4], players[4:6]]

    team1, team2 = balance_teams(groups, team_capacity=5)

    assert {player.id for player in team1 + team2} == set(range(1, 7))
    assert len(team1) <= 5
    assert len(team2) <= 5
    assert {len(team1), len(team2)} == {2, 4}


def test_balance_rejects_a_group_that_does_not_fit_in_one_team():
    players = [PlayerStub(player_id) for player_id in range(1, 7)]

    try:
        balance_teams([players, [PlayerStub(7)]], team_capacity=5)
    except ValueError as error:
        assert "5 lugares" in str(error)
    else:
        raise AssertionError("Se esperaba que un grupo de seis no fuera aceptado")

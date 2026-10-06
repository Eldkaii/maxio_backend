"""Pure serializer checks. Parse the function without importing config or a database."""
import ast
import unittest
from enum import Enum
from pathlib import Path
from types import SimpleNamespace as Obj


class Side(Enum):
    team1 = 'team1'
    team2 = 'team2'


source = ast.parse((Path(__file__).parents[1] / 'src/services/club_history_service.py').read_text(encoding='utf-8'))
function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'serialize_player_matches')


class RemoveImports(ast.NodeTransformer):
    def visit_ImportFrom(self, node):
        return None


function = RemoveImports().visit(function)
module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
scope = {'TeamEnum': Side, 'MatchResultReply': Obj(match_id=0)}
exec(compile(module, '<isolated serializer>', 'exec'), scope)
serialize = scope['serialize_player_matches']


class Query:
    def __init__(self, replies): self.replies = replies
    def filter(self, *args): return self
    def all(self): return self.replies


class HistorySerialization(unittest.TestCase):
    def result(self, *, winner=None, side=Side.team1, draw=False, bot=False):
        from datetime import datetime
        player = Obj(id=1, user_id=11, name='Jugador', is_bot=bot)
        friend = Obj(id=2, user_id=22, name='Compañero', is_bot=False)
        opponent = Obj(id=3, user_id=None, name='Bot', is_bot=True)
        match = Obj(id=7, date=datetime(2026, 10, 6), is_draw=draw,
                    winner_team_id=winner, team1_id=101, team2_id=102,
                    match_associations=[Obj(player_id=1),
                        Obj(player_id=2, player=friend, team=Side.team1),
                        Obj(player_id=3, player=opponent, team=Side.team2)])
        db = Obj(query=lambda *args: Query([Obj(user_id=11, result='win')]))
        return serialize(db, player, [Obj(match=match, team=side)])[0]

    def test_settled_results(self):
        self.assertEqual(self.result(winner=101)['result'], 'win')
        self.assertEqual(self.result(winner=102)['result'], 'loss')
        self.assertEqual(self.result(draw=True)['result'], 'draw')

    def test_pending_and_unassigned(self):
        self.assertEqual(self.result()['result'], 'pending')
        item = self.result(winner=101, side=None)
        self.assertEqual(item['result'], 'pending')
        self.assertIsNone(item['team'])

    def test_rosters_and_votes(self):
        item = self.result()
        self.assertEqual([p['name'] for p in item['teammates']], ['Jugador', 'Compañero'])
        self.assertEqual(item['opponents'][0]['response'], 'bot')
        self.assertEqual(item['teammates'][1]['response'], 'pending')
        self.assertEqual(item['my_response'], 'win')

    def test_bot_and_empty(self):
        self.assertEqual(self.result(bot=True)['my_response'], 'bot')
        self.assertEqual(serialize(None, None, []), [])


if __name__ == '__main__':
    unittest.main()

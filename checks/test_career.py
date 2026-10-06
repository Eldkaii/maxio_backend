"""Run with `python -m unittest discover -s checks`.

Pure unit checks: never import src.database, settings or pytest fixtures.
"""
import unittest

from src.services.career_service import STAGES, build_career


class CareerTests(unittest.TestCase):
    def test_every_neighborhood_boundary(self):
        for index, (target, title, _, _) in enumerate(STAGES):
            with self.subTest(target=target):
                current = build_career(target, 0)
                self.assertEqual(current["stage"], index)
                self.assertEqual(current["title"], title)
                if index:
                    self.assertEqual(build_career(target - 1, 0)["stage"], index - 1)
                next_goal = current["next_milestone"]
                self.assertEqual(next_goal["target"] if next_goal else None,
                                 STAGES[index + 1][0] if index < 6 else None)

    def test_new_player_and_bot(self):
        new = build_career(None, None)
        self.assertEqual(new["earned_count"], 0)
        self.assertEqual(new["next_milestone"]["progress"], 0)
        self.assertTrue(all(c["peer"] is None for c in new["connections"]))
        self.assertIsNone(build_career(500, 200, is_bot=True))

    def test_wins_do_not_gate_participation(self):
        career = build_career(100, 0)
        self.assertEqual(career["stage"], 6)
        self.assertEqual(career["earned_count"], 6)
        self.assertIsNone(career["next_milestone"])
        self.assertEqual(build_career(100, 50)["earned_count"], 10)

    def test_all_previous_pairs_keep_their_stamps_and_bots_are_excluded(self):
        peers = [dict(id=i, name=f"Human {i}", games_together=5 + i, games_apart=10)
                 for i in range(1, 7)]
        peers.append(dict(id=99, name="Bot", games_together=100, games_apart=100, is_bot=True))
        career = build_career(50, 15, peers)
        pairs = [m for m in career["milestones"] if m["peer"]]
        self.assertEqual({m["peer"] for m in pairs}, {f"Human {i}" for i in range(1, 7)})
        self.assertEqual(career["connections"][0]["peer"], "Human 6")
        self.assertEqual(career["connections"][1]["peer"], "Human 1")
        self.assertEqual(len({m["key"] for m in pairs}), len(pairs))
        self.assertTrue(all(m["progress"] <= m["target"] for m in career["milestones"]))

    def test_social_counts_have_separate_meanings(self):
        career = build_career(25, 1, [dict(id=2, name="Nico", games_together=4, games_apart=5)])
        duo, rival = career["connections"]
        self.assertEqual(duo["title"], "Por construir")
        self.assertEqual(rival["title"], "La revancha")
        self.assertEqual(rival["target"], 10)
        self.assertEqual([m["key"] for m in career["milestones"] if m["peer"]], ["rival-2-5"])


if __name__ == "__main__":
    unittest.main()

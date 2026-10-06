"""Pure display rules: no application startup, database or pytest fixtures."""
import unittest

from src.services.locker_room_service import build_locker_room


class LockerRoomTests(unittest.TestCase):
    def item(self, slot, target, unlocked=False):
        return dict(slot=slot, id="sample", name="Prenda", target=target,
                    unlocked=unlocked, requirement="5 partidos", progress=0)

    def test_starter_gear_and_tattoos_do_not_fill_lockers(self):
        catalog = [self.item("jersey", 0, True), self.item("boots", 0, True),
                   self.item("tattoo", 20, True), self.item("cap", 5)]
        room = build_locker_room(catalog)
        self.assertEqual(len(room["equipment"]), 1)
        self.assertFalse(any(item["unlocked"] for item in room["equipment"]))

    def test_unlock_and_affinity_decisions_are_preserved(self):
        catalog = [self.item("jersey", 10, True), self.item("jersey", 10, False),
                   self.item("shorts", 5, True), self.item("boots", 10, True)]
        catalog[1]["progress"] = 10  # Counter alone cannot override affinity.
        room = build_locker_room(catalog)
        self.assertEqual(room["equipment"], catalog)
        self.assertEqual(sum(item["unlocked"] for item in room["equipment"]), 3)
        room["equipment"][0]["name"] = "Changed"
        self.assertEqual(catalog[0]["name"], "Prenda")

    def test_no_trophy_awards_are_inferred(self):
        self.assertEqual(build_locker_room([]), {"equipment": []})


if __name__ == "__main__":
    unittest.main()

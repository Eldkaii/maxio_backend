"""Read-only locker display. Unlock rules remain in the wardrobe catalog."""


def build_locker_room(catalog):
    # Starter clothing and tattoos are not collectible hanging equipment.
    equipment = [dict(item) for item in catalog
                 if item["target"] > 0 and item["slot"] in {"jersey", "shorts", "boots", "cap"}]
    return {"equipment": equipment}

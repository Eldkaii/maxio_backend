INITIAL_USERS = [
    {
        "username": "masiba",
        "email": "masiba@user.com",
        "password": "123456789",
        "player": {
            "name": "masiba",
            "stats": {
                "tiro": 70,
                "ritmo": 30,
                "fisico": 25,
                "defensa": 73,
                "aura": 50,
            },
        },
    },
    {
        "username": "maxilu",
        "email": "maxilu@user.com",
        "password": "123456789",
        "player": {
            "name": "maxilu",
            "stats": {
                "tiro": 75,
                "ritmo": 60,
                "fisico": 60,
                "defensa": 50,
                "aura": 50,
            },
        },
    },
    {
        "username": "germame",
        "email": "germame@user.com",
        "password": "123456789",
        "player": {
            "name": "germame",
            "stats": {
                "tiro": 90,
                "ritmo": 87,
                "fisico": 80,
                "defensa": 65,
                "aura": 80,
            },
        },
    },
    {
        "username": "nachoro",
        "email": "nachoro@user.com",
        "password": "123456789",
        "player": {
            "name": "nachoro",
            "stats": {
                "tiro": 90,
                "ritmo": 85,
                "fisico": 80,
                "defensa": 75,
                "aura": 65,
            },
        },
    },
    {
        "username": "brunofe",
        "email": "brunofe@user.com",
        "password": "123456789",
        "player": {
            "name": "brunofe",
            "stats": {
                "tiro": 93,
                "ritmo": 70,
                "fisico": 65,
                "defensa": 60,
                "aura": 100,
            },
        },
    },
    {
        "username": "kevicr",
        "email": "kevicr@user.com",
        "password": "123456789",
        "player": {
            "name": "kevicr",
            "stats": {
                "tiro": 89,
                "ritmo": 95,
                "fisico": 85,
                "defensa": 43,
                "aura": 88,
            },
        },
    },
    {
        "username": "clovife",
        "email": "clovife@user.com",
        "password": "123456789",
        "player": {
            "name": "clovife",
            "stats": {
                "tiro": 70,
                "ritmo": 65,
                "fisico": 60,
                "defensa": 70,
                "aura": 65,
            },
        },
    },
    {
        "username": "diegoma",
        "email": "diegoma@user.com",
        "password": "123456789",
        "player": {
            "name": "diegoma",
            "stats": {
                "tiro": 75,
                "ritmo": 40,
                "fisico": 55,
                "defensa": 80,
                "aura": 75,
            },
        },
    },
    {
        "username": "nicolhe",
        "email": "nicolhe@user.com",
        "password": "123456789",
        "player": {
            "name": "nicolhe",
            "stats": {
                "tiro": 90,
                "ritmo": 91,
                "fisico": 89,
                "defensa": 71,
                "aura": 88,
            },
        },
    },
    {
        "username": "santigo",
        "email": "santigo@user.com",
        "password": "123456789",
        "player": {
            "name": "santigo",
            "stats": {
                "tiro": 55,
                "ritmo": 45,
                "fisico": 40,
                "defensa": 67,
                "aura": 60,
            },
        },
    },
    {
        "username": "yaicelp",
        "email": "yaicelp@user.com",
        "password": "123456789",
        "player": {
            "name": "yaicelp",
            "stats": {
                "tiro": 83,
                "ritmo": 85,
                "fisico": 90,
                "defensa": 75,
                "aura": 71,
            },
        },
    },
    {
        "username": "alaynsa",
        "email": "alaynsa@user.com",
        "password": "123456789",
        "player": {
            "name": "alaynsa",
            "stats": {
                "tiro": 69,
                "ritmo": 41,
                "fisico": 35,
                "defensa": 20,
                "aura": 31,
            },
        },
    },
    {
        "username": "emiliom",
        "email": "emiliom@user.com",
        "password": "123456789",
        "player": {
            "name": "emiliom",
            "stats": {
                "tiro": 50,
                "ritmo": 45,
                "fisico": 70,
                "defensa": 85,
                "aura": 50,
            },
        },
    },
    {
        "username": "nestoet",
        "email": "nestoet@user.com",
        "password": "123456789",
        "player": {
            "name": "nestoet",
            "stats": {
                "tiro": 75,
                "ritmo": 85,
                "fisico": 79,
                "defensa": 67,
                "aura": 70,
            },
        },
    },
]


INITIAL_PLAYER_RELATIONS = {
    "masiba": {
        "maxilu": {"together": 7, "apart": 3},
        "germame": {"together": 4, "apart": 6},
        "nachoro": {"together": 5, "apart": 5},
        "kevicr": {"together": 6, "apart": 4},
        "clovife": {"together": 5, "apart": 5},
        "diegoma": {"together": 1, "apart": 9},
        "nicolhe": {"together": 5, "apart": 5},
        "santigo": {"together": 5, "apart": 5},
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 5, "apart": 5},
        "nestoet": {"together": 5, "apart": 5},
    },

    "maxilu": {
        "germame": {"together": 9, "apart": 1},
        "nachoro": {"together": 5, "apart": 5},
        "kevicr": {"together": 1, "apart": 1},
        "clovife": {"together": 1, "apart": 1},
        "diegoma": {"together": 3, "apart": 3},
        "nicolhe": {"together": 1, "apart": 1},
        "santigo": {"together": 5, "apart": 5},
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 4, "apart": 6},
        "nestoet": {"together": 1, "apart": 1},
    },

    "germame": {
        "nachoro": {"together": 5, "apart": 5},
        "kevicr": {"together": 0, "apart": 5},
        "clovife": {"together": 1, "apart": 1},
        "diegoma": {"together": 5, "apart": 5},
        "nicolhe": {"together": 1, "apart": 1},
        "santigo": {"together": 1, "apart": 1},
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 7, "apart": 3},
        "nestoet": {"together": 1, "apart": 1},
    },

    "nachoro": {
        "kevicr": {"together": 1, "apart": 1},
        "clovife": {"together": 1, "apart": 1},
        "diegoma": {"together": 5, "apart": 5},
        "nicolhe": {"together": 1, "apart": 1},
        "santigo": {"together": 1, "apart": 1},
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 0, "apart": 6},
        "nestoet": {"together": 1, "apart": 1},
    },

    "kevicr": {
        "clovife": {"together": 10, "apart": 0},
        "diegoma": {"together": 5, "apart": 5},
        "nicolhe": {"together": 3, "apart": 7},
        "santigo": {"together": 1, "apart": 1},
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 6, "apart": 4},
        "nestoet": {"together": 1, "apart": 1},
    },

    "clovife": {
        "diegoma": {"together": 5, "apart": 5},
        "nicolhe": {"together": 6, "apart": 4},
        "santigo": {"together": 5, "apart": 5},
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 5, "apart": 5},
        "nestoet": {"together": 1, "apart": 1},
    },

    "diegoma": {
        "nicolhe": {"together": 6, "apart": 4},
        "santigo": {"together": 5, "apart": 5},
        "yaicelp": {"together": 5, "apart": 5},
        "alaynsa": {"together": 5, "apart": 5},
        "emiliom": {"together": 8, "apart": 2},
        "nestoet": {"together": 1, "apart": 1},
    },

    "nicolhe": {
        "santigo": {"together": 7, "apart": 3},
        "yaicelp": {"together": 5, "apart": 5},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 8, "apart": 2},
        "nestoet": {"together": 5, "apart": 5},
    },

    "santigo": {
        "yaicelp": {"together": 1, "apart": 1},
        "alaynsa": {"together": 1, "apart": 1},
        "emiliom": {"together": 5, "apart": 5},
        "nestoet": {"together": 1, "apart": 1},
    },

    "yaicelp": {
        "alaynsa": {"together": 10, "apart": 0},
        "emiliom": {"together": 9, "apart": 1},
        "nestoet": {"together": 1, "apart": 1},
    },

    "alaynsa": {
        "emiliom": {"together": 5, "apart": 5},
        "nestoet": {"together": 0, "apart": 1},
    },

    "emiliom": {
        "nestoet": {"together": 10, "apart": 0},
        "brunofe": {"together": 10, "apart": 0},
    },
}

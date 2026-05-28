"""
plants_db.py – Pflanzendatenbank
20 vorkonfigurierte Profile mit Feuchtigkeitsschwellen, Bewässerungsdauer etc.
"""
from config import get_config

PLANTS = [
    # id, name_de, name_en, emoji, min%, max%, ideal%, dauer_s, interval_h, ow_sensitiv, temp_hot_adj, notiz
    (0,  'Benutzerdefiniert', 'Custom',      '🌱', 20,  80,  50, 30, 6,  False, 0,  ''),
    (1,  'Tomate',            'Tomato',      '🍅', 45,  80,  65, 45, 8,  False, 10, 'Viel Wasser, besonders bei Hitze'),
    (2,  'Basilikum',         'Basil',       '🌿', 50,  80,  65, 20, 6,  False, 5,  'Gleichmäßig feucht halten'),
    (3,  'Kaktus',            'Cactus',      '🌵', 5,   30,  15, 10, 72, True,  0,  'Sehr selten gießen'),
    (4,  'Sukkulente',        'Succulent',   '🪴', 10,  35,  20, 10, 48, True,  0,  'Staunässe vermeiden'),
    (5,  'Lavendel',          'Lavender',    '💜', 15,  45,  30, 20, 24, True,  0,  'Trockenheit bevorzugt'),
    (6,  'Rose',              'Rose',        '🌹', 40,  75,  55, 40, 12, False, 5,  'Regelmäßig gießen'),
    (7,  'Erdbeere',          'Strawberry',  '🍓', 50,  80,  65, 35, 8,  False, 5,  'Nie austrocknen lassen'),
    (8,  'Paprika',           'Bell Pepper', '🫑', 45,  75,  60, 40, 10, False, 8,  'Gleichmäßig feucht'),
    (9,  'Minze',             'Mint',        '🌿', 55,  85,  70, 25, 6,  False, 0,  'Immer feucht halten'),
    (10, 'Orchidee',          'Orchid',      '🌸', 30,  50,  40, 15, 48, True,  0,  'Staunässe sehr schädlich'),
    (11, 'Farn',              'Fern',        '🌿', 60,  90,  75, 30, 6,  False, 0,  'Hohe Luftfeuchtigkeit'),
    (12, 'Efeutute',          'Pothos',      '🌿', 30,  60,  45, 20, 12, False, 0,  'Robust, für Anfänger'),
    (13, 'Grünlilie',         'Spider Plant','🌿', 35,  65,  50, 20, 12, False, 0,  'Pflegeleicht'),
    (14, 'Einblatt',          'Peace Lily',  '🤍', 45,  75,  60, 25, 8,  False, 0,  'Hängende Blätter = Durst'),
    (15, 'Aloe Vera',         'Aloe Vera',   '🌵', 10,  30,  20, 15, 48, True,  0,  'Sehr selten gießen'),
    (16, 'Salat',             'Lettuce',     '🥬', 60,  90,  75, 30, 4,  False, 5,  'Immer feucht, schnell trocken'),
    (17, 'Gurke',             'Cucumber',    '🥒', 55,  85,  70, 45, 6,  False, 8,  'Viel Wasser bei Fruchtbildung'),
    (18, 'Sonnenblume',       'Sunflower',   '🌻', 35,  65,  50, 30, 12, False, 5,  'Tiefwurzler, selten gießen'),
    (19, 'Chili',             'Chili',       '🌶️', 40,  70,  55, 30, 10, False, 5,  'Zwischen Gießen trocknen lassen'),
]

# Index-Konstanten für schnellen Zugriff
F_ID, F_NAME_DE, F_NAME_EN, F_EMOJI = 0, 1, 2, 3
F_MIN, F_MAX, F_IDEAL, F_DUR, F_IVL = 4, 5, 6, 7, 8
F_OW_SENS, F_TEMP_ADJ, F_NOTES = 9, 10, 11


def get_plant(idx):
    """Plant-Tupel by Index (0-based). Fallback auf 'Benutzerdefiniert'."""
    if 0 <= idx < len(PLANTS):
        return PLANTS[idx]
    return PLANTS[0]


def as_dict(plant):
    """Tupel → Dict für JSON-Serialisierung."""
    return {
        'id': plant[F_ID], 'name_de': plant[F_NAME_DE], 'name_en': plant[F_NAME_EN],
        'emoji': plant[F_EMOJI], 'min': plant[F_MIN], 'max': plant[F_MAX],
        'ideal': plant[F_IDEAL], 'duration': plant[F_DUR], 'interval': plant[F_IVL],
        'ow_sensitive': plant[F_OW_SENS], 'temp_adj': plant[F_TEMP_ADJ],
        'notes': plant[F_NOTES]
    }


def all_as_list():
    return [as_dict(p) for p in PLANTS]


def get_thresh_adjusted(plant, weather_temp, weather_humidity):
    """Schwellwert basierend auf Wetterdaten anpassen."""
    thresh = plant[F_IDEAL]
    if weather_temp is not None:
        if weather_temp > 28:
            thresh = min(100, thresh + plant[F_TEMP_ADJ])
        elif weather_temp < 8:
            thresh = max(0, thresh - 5)
    return thresh
�

#pragma once
#include <Arduino.h>

// ╔══════════════════════════════════════════════════════════════════╗
// ║  Pflanzendatenbank — plants_db.h                                 ║
// ║  Quellen: RHS, USDA, Plantnet, gärtnerische Fachliteratur        ║
// ║  Werte = Substrat-Feuchtigkeit (kapazitiv, nicht Luftfeucht.)    ║
// ╚══════════════════════════════════════════════════════════════════╝

struct PlantProfile {
  const char*  name_en;
  const char*  name_de;
  uint8_t      moisture_min;         // % — Bewässerung starten ab hier
  uint8_t      moisture_max;         // % — Ziel nach Bewässerung
  uint8_t      moisture_ideal;       // % — Optimalwert für Anzeige
  uint16_t     watering_duration_s;  // Sekunden Pumplaufzeit
  uint16_t     min_interval_h;       // Mindestabstand in Stunden
  bool         overwater_sensitive;  // true = empfindlich gegenüber Staunässe
  float        temp_hot_adjust;      // Schwellwert-Erhöhung bei Hitze (°C über Grenze)
  const char*  emoji;
  const char*  notes_de;
};

// Alle Strings im Flash (PROGMEM) um RAM zu sparen
const PlantProfile PLANT_DATABASE[] PROGMEM = {
  //  name_en            name_de                min  max  ideal  dur   ivl   owSens  hotAdj emoji   notes
  {  "Custom",          "Benutzerdefiniert",    30,  70,  50,   30,    6,   false,  5.0f,  "🌱",  "Eigene Werte — alles manuell einstellbar"                          },
  {  "Tomato",          "Tomate",               45,  80,  65,   45,   12,   false, 10.0f,  "🍅",  "Gleichmäßig feucht halten, Trockenheit vermeiden"                  },
  {  "Basil",           "Basilikum",            50,  80,  65,   20,    8,   false,  8.0f,  "🌿",  "Warmer Standort, feucht aber nicht nass"                           },
  {  "Cactus",          "Kaktus",                5,  30,  15,   10,  168,   true,   0.0f,  "🌵",  "Sehr selten gießen, komplett trocknen lassen"                      },
  {  "Succulent",       "Sukkulente",           10,  35,  20,   10,  120,   true,   0.0f,  "🪴",  "Substrat zwischen Gießen vollständig trocknen"                     },
  {  "Lavender",        "Lavendel",             15,  45,  30,   20,   48,   true,   2.0f,  "💜",  "Trockenheitsresistent, gut drainiertes Substrat"                   },
  {  "Rose",            "Rose",                 40,  75,  60,   40,   24,   false,  8.0f,  "🌹",  "Regelmäßig gießen, Blätter trocken halten"                         },
  {  "Strawberry",      "Erdbeere",             50,  80,  70,   35,   12,   false, 10.0f,  "🍓",  "Viel Wasser besonders beim Fruchten"                               },
  {  "Pepper",          "Paprika",              45,  75,  60,   40,   12,   false,  8.0f,  "🫑",  "Gleichmäßige Wasserversorgung wie Tomate"                          },
  {  "Mint",            "Minze",                55,  85,  70,   25,    8,   false,  5.0f,  "🌿",  "Mag es konstant feucht, verträgt auch kurze Trockenheit"           },
  {  "Orchid",          "Orchidee",             30,  50,  40,   15,   72,   true,   3.0f,  "🌸",  "Keine Staunässe! Wurzeln müssen gut trocknen können"               },
  {  "Fern",            "Farn",                 60,  90,  75,   30,    6,   false,  5.0f,  "🌿",  "Konstant gleichmäßig feucht, hohe Luftfeuchtigkeit ideal"          },
  {  "Pothos",          "Efeutute",             30,  60,  45,   20,   24,   false,  5.0f,  "🌿",  "Tolerant und pflegeleicht, gut für Anfänger"                       },
  {  "Spider Plant",    "Grünlilie",            35,  65,  50,   20,   24,   false,  5.0f,  "🌿",  "Robuste Zimmerpflanze, verträgt auch kurze Trockenheit"            },
  {  "Peace Lily",      "Einblatt",             45,  75,  60,   25,   12,   false,  5.0f,  "🤍",  "Zeigt Durst durch hängende Blätter, reagiert gut auf Gießen"      },
  {  "Aloe Vera",       "Aloe Vera",            10,  30,  20,   15,  168,   true,   0.0f,  "🌵",  "Sehr trockenresistent, Staunässe tötet die Pflanze"                },
  {  "Lettuce",         "Salat",                60,  90,  80,   30,    6,   false, 12.0f,  "🥬",  "Viel Wasser, nie austrocknen lassen"                               },
  {  "Cucumber",        "Gurke",                55,  85,  75,   45,    8,   false, 10.0f,  "🥒",  "Regelmäßig und gleichmäßig gießen"                                 },
  {  "Sunflower",       "Sonnenblume",          35,  65,  50,   30,   24,   false,  8.0f,  "🌻",  "Mäßig gießen, tiefe Wurzeln brauchen gelegentlich viel Wasser"     },
  {  "Chili",           "Chili",                40,  70,  55,   30,   12,   false,  8.0f,  "🌶️",  "Ähnlich Paprika, etwas trockenheitstoleranter"                    },
};

const uint8_t PLANT_DB_COUNT = sizeof(PLANT_DATABASE) / sizeof(PlantProfile);

// Hilfsfunktion: Pflanzenprofil aus Flash lesen
inline PlantProfile getPlantProfile(uint8_t idx) {
  if (idx >= PLANT_DB_COUNT) idx = 0;
  PlantProfile p;
  memcpy_P(&p, &PLANT_DATABASE[idx], sizeof(PlantProfile));
  return p;
}

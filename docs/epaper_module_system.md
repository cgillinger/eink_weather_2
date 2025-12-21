# E-Paper Väderapp - Modulärt Layout-system
## Skärm: Waveshare 4.26" (800×480px) - Designspecifikation

### 🎯 DESIGNPRINCIPER
- **Kvalitet över kvantitet** - Max 5 moduler totalt
- **Hierarkisk information** - Viktigast störst
- **E-ink optimerat** - Tydliga kontraster, stora textstorlekar
- **Flexibel konfiguration** - Moduler kan växlas utan kodändring

---

## 📐 LAYOUT GRID-SYSTEM

### Skärmindelning (800×480px)
```
Margins: 40px på alla sidor
Arbetsutrymme: 720×400px

┌─────────────────────────────────────┐ 800px
│  40px margin                        │
│ ┌─────────────────────────────────┐ │
│ │                                 │ │ 
│ │     ARBETSUTRYMME               │ │ 400px
│ │     720×400px                   │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│  40px margin                        │
└─────────────────────────────────────┘
```

### MODULTYPER OCH STORLEKAR

| Typ    | Bredd × Höjd | Användning                    | Max antal |
|--------|--------------|-------------------------------|-----------|
| **HERO**   | 480×200px    | Huvudtemperatur + väderikon   | 1         |
| **MEDIUM** | 240×200px    | Tryck, Prognos, Luftkvalitet | 2         |
| **SMALL**  | 240×100px    | Soldata, Datum/tid, Status    | 2         |

---

## 🏗️ STANDARDLAYOUTER

### Layout A: FOKUS (Rekommenderad för start)
```
┌─────────────────────┬─────────────┐
│                     │   MEDIUM    │
│      HERO           │   Tryck/    │
│   Temp + Väder      │   Sol       │ 200px
│                     ├─────────────┤
│                     │   MEDIUM    │
├─────────────────────┤   Prognos   │
│  SMALL   │  SMALL   │             │ 100px
│ Datum/Tid│  Status  │             │
└──────────┴──────────┴─────────────┘
  240px      240px      240px
```

### Layout B: KOMPAKT  
```
┌─────────────────────┬─────────────┐
│                     │   MEDIUM    │
│      HERO           │   Prognos   │
│   Temp + Väder      │             │ 200px
│                     ├─────────────┤
│                     │   MEDIUM    │
└─────────────────────┤   Tryck     │ 200px
                      │             │
                      └─────────────┘
```

### Layout C: INFORMATIONSRIK (Max rekommenderat)
```
┌─────────────┬─────────────┬─────────────┐
│             │   MEDIUM    │   MEDIUM    │
│    HERO     │   Tryck     │   Prognos   │ 200px
│ Temp+Väder  │             │             │
├─────────────┼─────────────┼─────────────┤
│   SMALL     │   SMALL     │   SMALL     │ 100px
│   Datum     │   Sol       │   Status    │
└─────────────┴─────────────┴─────────────┘
```

---

## 🧩 LAYOUT A - MODULER OCH DATAPUNKTER

### 📍 HERO-MODUL: `main_weather` (480×200px)
**Datapunkter:**
- 🌡️ **Temperatur**: `22.3°C` (stor text, 72px)
- 🌤️ **Väderikon**: SMHI symbol → SVG/Unicode (64px)  
- 📝 **Väderbeskrivning**: `"Molnigt"` (32px)
- 📊 **Källa**: `"Netatmo"` eller `"SMHI"` (liten text, 18px)

### 📍 MEDIUM-MODUL 1: `barometer_module` (240×200px)
**Standard: Lufttryck**
- 📊 **Tryck**: `1013 hPa` (48px)
- 📈 **Trend**: `↗` pil + `"Stigande"` (24px)
- ⏱️ **Trenddata**: `"3h analys"` (18px)

**Växlingsalternativ: `sun_module`**
- 🌅 **Soluppgång**: `07:32`
- 🌇 **Solnedgång**: `16:18`  
- ⏰ **Återstående ljus**: `8h 46m`

### 📍 MEDIUM-MODUL 2: `tomorrow_forecast` (240×200px)
**Datapunkter:**
- 📅 **Datum**: `"Imorgon"` (24px)
- 🌦️ **Väderikon**: Morgondagens SMHI symbol (48px)
- 🌡️ **Max temp**: `4°C` (36px, prominent)
- 🌡️ **Min temp**: `-1°C` (24px, mindre)
- 🌧️ **Nederbörd**: `"2mm"` (18px, om relevant)

### 📍 SMALL-MODUL 1: `clock_module` (240×100px)
**Datapunkter:**
- 📅 **Datum**: `"Onsdag 23 Juli"` (24px)
- 🕐 **Tid**: `"14:25"` (32px)

### 📍 SMALL-MODUL 2: `status_module` (240×100px)
**Datapunkter:**
- 🔄 **Senaste uppdatering**: `"14:23"` (20px)
- 🌐 **Datakälla**: `"Netatmo + SMHI"` (16px)
- 📶 **Status**: `"●"` grönt för OK (18px)

---

## 🎯 LAYOUT A - SAMMANTAGET

**Total datapunkter: 15** (inom rimlig gräns!)

**Hierarki (viktigast → mindre viktigt):**
1. 🌡️ **Aktuell temperatur** (störst)
2. 🌤️ **Aktuellt väder** (ikon + text)
3. 📊 **Lufttryck + trend** (viktigt för väderutveckling)
4. 🌦️ **Morgondagens väder** (planering)
5. 📅 **Datum/tid** (referens)
6. 🔄 **Systemstatus** (debug)

**Växlingsmöjlighet:**
- `barometer_module` ↔ `sun_module` (samma position)
- Enkelt byte via config: `"medium_1": "barometer_module"` → `"medium_1": "sun_module"`

---

## 🏗️ ARKITEKTUR - FRISTÅENDE LOKAL APP

```
┌─────────────────────────────────────────┐
│           RASPBERRY PI 3B               │
│                                         │
│  ┌─────────────────────────────────────┐│
│  │     E-PAPER VÄDERAPP (Lokal)       ││
│  │                                     ││
│  │  ┌─────────────┐ ┌─────────────────┐││
│  │  │   SMHI      │ │    NETATMO      │││
│  │  │   Client    │ │    Client       │││
│  │  │  (direkt)   │ │   (direkt)      │││
│  │  └─────────────┘ └─────────────────┘││
│  │                                     ││
│  │  ┌─────────────────────────────────┐││
│  │  │       E-PAPER RENDERER          │││
│  │  └─────────────────────────────────┘││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │   E-PAPER DISPLAY   │
    │   Waveshare 4.26"   │
    │     800×480px       │
    └─────────────────────┘
```

**HELT FRISTÅENDE - Inga externa beroenden!**

---

## 💾 LOKAL APPSTRUKTUR

```
~/epaper_weather/
├── main.py              # Huvudapp + E-paper rendering
├── config.json          # Konfiguration (moduler, API-nycklar)
├── modules/
│   ├── __init__.py
│   ├── weather_client.py    # SMHI + Netatmo API-anrop
│   ├── layout_engine.py     # Layout A rendering
│   └── display_driver.py    # E-paper hårdvarukontroll
├── fonts/               # Lokala typsnitt
├── icons/               # Lokala väderikoner (fallback)
└── cache/               # Lokal cache för API-data
```

**DATAKÄLLOR (direktanslutning från Pi):**
- 🌐 **SMHI API**: Direkt från Pi → `opendata.smhi.se`
- 🏠 **Netatmo API**: Direkt från Pi → `api.netatmo.com` 
- 🕐 **Tid/datum**: Lokal systemtid på Pi
- 💾 **Cache**: Lokal fil på Pi (offline-funktion)

---

## 📍 ANVÄNDARVÄNLIG PLATSKONFIGURATION

### config.json - Lätt att ändra plats
```json
{
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686,
    "comment": "Ändra bara koordinaterna för ny plats"
  },
  "api_keys": {
    "netatmo": {
      "client_id": "6848077b1c8bb27c8809e259",
      "client_secret": "WZ1vJos04mu7SlL1QmsMv3cZ1OURHF", 
      "refresh_token": "5c3dd9b22733bf0c008b8f1c|a7be84ead1b2e9ce13a4781fdab434f3",
      "comment": "Tillfälliga credentials - byt när appen är klar"
    }
  },
  "modules": {
    "main_weather": {"enabled": true, "position": "hero"},
    "barometer_module": {"enabled": true, "position": "medium_1"},
    "tomorrow_forecast": {"enabled": true, "position": "medium_2"}, 
    "clock_module": {"enabled": true, "position": "small_1"},
    "status_module": {"enabled": true, "position": "small_2"}
  }
}
```

### 🗺️ POPULÄRA SVENSKA PLATSER (för enkel kopiering)
```bash
# Lägg till i config.json → location:

# Stockholm (nuvarande standard)
"name": "Stockholm", "latitude": 59.3293, "longitude": 18.0686

# Yxlan, Norrtälje skärgård (exempel)  
"name": "Yxlan", "latitude": 59.8481, "longitude": 18.5040

# Göteborg  
"name": "Göteborg", "latitude": 57.7089, "longitude": 11.9746

# Malmö
"name": "Malmö", "latitude": 55.6050, "longitude": 13.0038

# Uppsala
"name": "Uppsala", "latitude": 59.8586, "longitude": 17.6389

# Linköping
"name": "Linköping", "latitude": 58.4108, "longitude": 15.6214

# Örebro
"name": "Örebro", "latitude": 59.2753, "longitude": 15.2134
```

### 🔧 SETUP-KOMMANDO (för framtida användarvänlighet)
```bash
# Eventuell future feature:
python3 main.py --setup-location
# → Frågar användaren om plats och uppdaterar config automatiskt
```

---

## 📋 NÄSTA STEG (när installationen är 100%)

1. **Verifiera E-paper**: `lsmod | grep spi` 
2. **Skapa appstruktur**: Moduler + config
3. **Test basic rendering**: Simpel "Hello World" på E-paper
4. **Implementera Layout A**: Med riktiga väderdata  
5. **Fintuning**: Typsnitt, spacing, användarvänlighet

**Latitude/Longitude hittas lätt på:** `latlong.net` eller Google Maps 🗺️

---

## 🎨 DESIGNRIKTLINJER

### Typografi (E-ink optimerat)
- **HERO Text**: 72px (temperatur), 32px (beskrivning)
- **MEDIUM Text**: 48px (huvudvärde), 24px (beskrivning) 
- **SMALL Text**: 32px (huvudvärde), 18px (beskrivning)
- **Font**: DejaVu Sans (monospace, tydlig på E-ink)

### Färger (Svartvit optimerat)
- **Text**: #000000 (ren svart)
- **Bakgrund**: #FFFFFF (ren vit)
- **Accenter**: #666666 (grå för sekundär info)
- **Ikoner**: Svartvita, stora (min 64px)

### Spacing
- **Modulmarginaler**: 20px mellan moduler
- **Intern padding**: 16px inom moduler
- **Ikonspacing**: 12px mellan ikon och text

---

## 🚫 BEGRÄNSNINGAR & REGLER

### Maximal information per skärm:
- ✅ **1 HERO** + **2 MEDIUM** + **2 SMALL** = Layout C (MAX)
- ⚠️ **Mer än 5 moduler** = Nej, blir rörigt
- ⚠️ **Text under 18px** = Nej, svårläst på E-ink
- ⚠️ **Över 8 datapunkter** = Nej, för mycket information

### Växlingsregler:
- `pressure` ↔ `sun_times` (samma position, medium_1)
- `air_quality` kräver Netatmo (annars dold)
- `datetime` + `status` kan tas bort för renare look

---

## 🔄 IMPLEMENTATION APPROACH

1. **Steg 1**: Bygg Layout A (FOKUS) med fasta moduler
2. **Steg 2**: Implementera config-driven modulväxling  
3. **Steg 3**: Lägg till Layout B & C som alternativ
4. **Steg 4**: Användarvänlig config-editor

**Resultat**: Flexibel, skalbar och användarvänlig E-paper väderapp! 🎯
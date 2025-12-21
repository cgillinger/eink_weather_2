# E-Paper Väderapp - Komplett Projekt med Dynamic Module System
**Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480px)**

## 🏆 Projektöversikt

Avancerad väderstation med E-Paper display som kombinerar lokala Netatmo-sensorer med SMHI väderdata, **SMHI Observations från Observatorielunden** och exakta soltider. Systemet använder ett **Dynamic Module System** med trigger-baserade moduler, högkvalitativa Weather Icons och intelligent rendering pipeline för professionell presentation.

**🚀 NYTT: Villkorsbaserade moduler** som automatiskt aktiveras baserat på väderförhållanden (t.ex. nederbörd-varningar för cykling).  
**🆕 NYTT: SMHI Observations** för exakt "regnar just nu"-logik från station 98230 (Stockholm-Observatoriekullen).  
**🌬️ NYTT: Wind Module** - intelligent vindmodul för cykel-optimerade vindbeslut med automatisk aktivering vid kraftig vind.

## 🔧 Hårdvarukrav

### Huvudkomponenter
- **Raspberry Pi 3B** (eller nyare)
- **Waveshare 4.26" E-Paper HAT** (800×480px, svartvit)
- **SPI aktiverat** (`lsmod | grep spi` ska visa spi-moduler)
- **Internet-anslutning** för API-anrop

### E-Paper Specifikationer
- **Upplösning**: 800×480 pixlar
- **Färger**: 1-bit svartvit (optimerat för E-Paper)
- **Uppdateringstid**: ~10 sekunder per rendering
- **Strömförbrukning**: Mycket låg (E-Paper behåller bild utan ström)

## 📊 Funktionalitet och Datakällor

### Intelligenta Datakällor
**NETATMO** (prioriterat för lokala mätningar):
- 🌡️ **Utomhustemperatur** (från utomhusmodul)
- 📊 **Lufttryck** (från inomhusmodul, mer exakt än SMHI)
- 💨 **Luftfuktighet** (utomhus + inomhus)
- 📈 **3-timmars trycktrend** (meteorologisk standard)

**SMHI PROGNOSER** (för prognoser och väderdata):
- 🌤️ **Aktuellt väder** (27 SMHI-symboler med dag/natt-varianter)
- 🌦️ **Morgondagens prognos** (temperatur + väder)
- 💨 **🌬️ Vind och nederbörd** (inklusive cykel-väder analys + vindmodul)
- 📍 **Exakta geografiska data**

**🆕 SMHI OBSERVATIONS** (för exakt "regnar just nu"):
- 🌧️ **Aktuell nederbörd** (senaste timmen från Observatorielunden)
- 📊 **Station 98230** (Stockholm-Observatoriekullen A)
- ✅ **Kvalitetskoder** (G=Godkänt, Y=Preliminärt, R=Dåligt)
- ⏰ **Timmesdata** (uppdateras varje hel timme)
- 🔄 **Fallback till Arlanda** (station 97390) vid fel

**ipgeolocation.io API** (exakta soltider):
- ☀️ **Soluppgång/solnedgång** (exakt tid för koordinater)
- ⏰ **Dagsljuslängd** (automatisk beräkning)
- 🌅 **Dag/natt-logik** för väderikoner

### 🌬️ Wind Module - Cykel-Optimerad Vinddata

**PROFESSIONELL VINDMODUL** för cykel-optimerade vindbeslut:
- **🎯 Primär data**: Vindstyrka (m/s) + svensk vindbenämning
- **🧭 Sekundär data**: Vindriktning med kardinalpil + kort riktningstext  
- **🚴‍♂️ Cykel-fokuserad design**: Snabb avläsning för "ska jag cykla idag?"-beslut
- **🤖 Intelligent aktivering**: Automatisk växling vid kraftig vind (>10 m/s)

#### Svenska Vindbenämningar (Beaufort-baserat)
| M/S-intervall | Beskrivning | Cykel-användning |
|---------------|-------------|------------------|
| **0-0.2** | **Lugnt** | Perfekt cykelväder |
| **0.3-3.3** | **Svag vind** | Lätt motstånd |
| **3.4-7.9** | **Måttlig vind** | Märkbar men hanterbar |
| **8.0-13.8** | **Frisk vind** | **→ Wind-modul aktiveras** |
| **13.9-24.4** | **Hård vind** | Svårt att cykla |
| **24.5+** | **Storm/Orkan** | Farligt - stanna hemma |

#### Vindriktningar och Ikoner
- **16 kardinalpunkter**: N, NNO, NO, ONO, O, OSO, SO, SSO, S, SSV, SV, VSV, V, VNV, NV, NNV
- **Korta svenska förkortningar**: Optimerat för snabb läsning ("SV" istället för "Sydvästlig vind")
- **40×40px kardinalpil-ikoner**: Custom storlek för optimal E-Paper synlighet
- **Intelligent ikon-fallback**: Robust system med alternativa koder vid ikonfel

### Smart Datakombination med Prioritering
Appen använder **intelligent prioritering** med ny observations-logik:
1. **Netatmo** för lokala mätningar (temperatur, tryck)
2. **🆕 SMHI Observations** för nederbörd (prioriterat över prognoser)
3. **SMHI Prognoser** för väderprognos och meteorologi (fallback för nederbörd)
4. **🌬️ SMHI Prognoser** för vinddata (ws + wd parametrar)
5. **API soltider** för exakt sol-information
6. **Fallback-system** vid API-fel

#### Nederbörd-prioritering:
```
PRIORITERING: SMHI Observations > SMHI Prognoser > Fallback
- observations > 0 → använd observations-värde
- observations = 0 → använd prognos-värde  
- båda saknas → fallback till 0mm/h
```

#### 🌬️ Vinddata-hantering:
```
KÄLLOR: SMHI Prognoser (ws + wd parametrar)
- wind_speed: m/s → svenska vindbenämningar
- wind_direction: grader → kardinalpunkter
- automatisk kvalitetskontroll + fallback
```

## 🔄 Dynamic Module System

### **Revolutionerande arkitektur för villkorsbaserade moduler**

Systemet kan automatiskt växla mellan olika moduler baserat på:
- 🌧️ **Väderförhållanden** (nederbörd aktiverar cykel-väder varningar)
- 🌬️ **Vindförhållanden** (kraftig vind aktiverar wind-modul)
- 👤 **Användarinställningar** (växla mellan barometer/sol-modul)
- ⏰ **Tid/säsong** (UV-index sommartid, mörka månader)
- 🎯 **Trigger-conditions** (anpassningsbara villkor)

### **Trigger-baserade Moduler med SMHI Observations + Wind**

```json
{
  "triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR forecast_precipitation_2h > 0.2",
      "target_section": "bottom_section",
      "activate_group": "precipitation_active",
      "priority": 100,
      "description": "Aktivera nederbörd-modul vid regn eller kommande regn - NU MED OBSERVATIONS!"
    },
    "wind_trigger": {
      "condition": "wind_speed > 10.0",
      "target_section": "medium_right_section", 
      "activate_group": "wind_active",
      "priority": 80,
      "description": "🌬️ NYTT: Aktivera wind-modul vid frisk vind för cykel-beslut"
    }
  }
}
```

### **Module Groups - Intelligent Layout-växling**

```json
{
  "module_groups": {
    "bottom_section": {
      "normal": ["clock_module", "status_module"],
      "precipitation_active": ["precipitation_module"]
    },
    "medium_right_section": {
      "normal": ["barometer_module"],
      "wind_active": ["wind_module"]
    }
  }
}
```

**🎯 INTELLIGENT VÄXLING:**
- **Normal väder**: Barometer-modul visas (trycktrend)
- **Kraftig vind (>10 m/s)**: Wind-modul ersätter barometer automatiskt
- **Regn**: Nederbörd-modul ersätter klocka/status automatiskt
- **Efter väder**: Automatisk återgång till normal layout

### **🛠️ Användarkonfiguration av Triggers**

#### Ändra Trigger-tröskelvärden
```json
{
  "wind_trigger": {
    "condition": "wind_speed > 8.0",    ← Ändra från 10.0 till 8.0 för tidigare aktivering
    "priority": 80
  }
}
```

#### Manuell Modulaktivering
```json
{
  "modules": {
    "wind_module": {
      "enabled": true,               ← Permanent wind-modul
      "coords": {"x": 540, "y": 40}
    },
    "barometer_module": {
      "enabled": false              ← Inaktivera barometer
    }
  }
}
```

#### Hybrid-konfiguration
```json
{
  "wind_trigger": {
    "condition": "wind_speed > 15.0"  ← Endast vid mycket kraftig vind
  },
  "modules": {
    "wind_module": {"enabled": true}, ← MEN även permanent aktiverad
    "barometer_module": {"enabled": false}
  }
}
```

**🎛️ KONFIGURATIONSSTRATEGIER:**
- **Automatisk endast**: Använd triggers, `enabled: false` för moduler
- **Manuell endast**: Inaktivera triggers, använd `enabled: true/false`
- **Hybrid**: Triggers för extremväder + permanent aktivering för favoriter

## 🏗️ Rendering Pipeline och Arkitektur

### **🌬️ Wind Module Renderer-system**

```python
# Modulär renderer-arkitektur
class WindRenderer(ModuleRenderer):
    """
    Cykel-optimerad wind-modul med ren layout
    - M/s primär data (stort, vänsterjusterat)
    - Beskrivning sekundär (radbrytning max 2 rader)  
    - Kardinalpil + riktning tertiär (vänsterlinjerat nederst)
    - Kollisionssäker design utan allmän vindikon
    """
    
    def render(self, x, y, width, height, weather_data, context_data):
        # REN LAYOUT enligt UX-expert feedback:
        # 1. M/s-värde prominent
        # 2. Svensk beskrivning under (radbrytning)
        # 3. Kardinalpil + riktning nederst
        # Ingen allmän vindikon - tar bort visuellt brus
```

### **ModuleFactory Integration**
```python
# Automatisk renderer-registrering
self.renderers = {
    'precipitation_module': PrecipitationRenderer,
    'wind_module': WindRenderer,           # ← NY RENDERER
    'barometer_module': LegacyModuleRenderer
}
```

### **🎨 E-Paper Optimering för Wind Module**
- **Kollisionssäker layout**: Text når aldrig ikoner i högerkolumn
- **40×40px kardinalpil**: Custom storlek för E-Paper synlighet  
- **Radbrytning**: "Måttlig vind" på två rader istället för "Måttlig..."
- **Konstanter för spacing**: Förutsägbar layout utan överlapp
- **1-bit rendering**: Optimerat för svartvit E-Paper kontrast

## 🧪 Test-system och Utveckling

### **🌬️ Wind Module Test-kommandon**
```bash
# Testa vinddata-hämtning
python3 -c "
from modules.weather_client import WeatherClient
import json
with open('config.json', 'r') as f: config = json.load(f)
client = WeatherClient(config)
data = client.get_current_weather()
print(f'Wind: {data.get(\"wind_speed\", 0)} m/s, {data.get(\"wind_direction\", 0)}°')
print(f'Beskrivning: {client.icon_manager.get_wind_description_swedish(data.get(\"wind_speed\", 0))}')
"

# Testa wind-trigger
python3 -c "
import json
with open('config.json', 'r') as f: config = json.load(f)
wind_condition = config['triggers']['wind_trigger']['condition']
print(f'Wind trigger: {wind_condition}')
print('Testa med olika wind_speed värden i weather_data')
"
```

### **Säker Test-data för Wind Module**
```json
{
  "debug": {
    "allow_test_data": true,
    "test_data_wind": {
      "wind_speed": 12.5,
      "wind_direction": 225,
      "description": "Test kraftig sydvästlig vind för wind-modul trigger"
    }
  }
}
```

### **🔄 Backup-system för Wind Module**
```bash
# Automatiska backups vid utveckling
backup/
├── ORIGINAL_wind_20250817_162223/    ← Första backup per session
├── wind_layout_fix_20250817_165040/  ← Layout-ändringar  
└── wind_clean_final_20250817_173022/ ← Slutlig version
```

## 📋 Installation och Konfiguration

### **Snabbinstallation**
```bash
# 1. Klona projekt
git clone [repo] epaper_weather
cd epaper_weather

# 2. Installera beroenden  
pip install pillow requests

# 3. Konfigurera API-nycklar i config.json
# - Netatmo OAuth2 (client_id, client_secret)
# - ipgeolocation.io API-nyckel

# 4. Aktivera SPI för E-Paper
sudo raspi-config # Interface Options > SPI > Enable

# 5. Testa wind-modul
python3 -c "from modules.weather_client import WeatherClient; print('✅ Wind module ready')"
```

### **🌬️ Wind Module Konfiguration**

#### Grundkonfiguration
```json
{
  "modules": {
    "wind_module": {
      "enabled": true,
      "coords": {"x": 540, "y": 40},
      "size": "MEDIUM_1"
    }
  }
}
```

#### Trigger-konfiguration för Automatisk Aktivering
```json
{
  "triggers": {
    "wind_trigger": {
      "condition": "wind_speed > 10.0",
      "target_section": "medium_right_section",
      "activate_group": "wind_active",
      "priority": 80
    }
  },
  "module_groups": {
    "medium_right_section": {
      "normal": ["barometer_module"],
      "wind_active": ["wind_module"]
    }
  }
}
```

#### Avancerad Konfiguration
```json
{
  "wind_trigger": {
    "condition": "wind_speed > 8.0 AND wind_direction >= 180 AND wind_direction <= 270",
    "description": "Aktivera vid västlig-sydlig vind >8 m/s (motvind på vanlig cykelrutt)"
  }
}
```

### **Daemon-installation för Kontinuerlig Drift**
```bash
# Systemd service för wind-modul
sudo systemctl enable epaper-weather
sudo systemctl start epaper-weather

# Kontrollera wind-modul status
sudo systemctl status epaper-weather
tail -f logs/weather_daemon.log | grep -E "(wind|Wind)"
```

## 🔧 API-integration

### **SMHI Wind API**
```python
# Vinddata från SMHI Prognoser
url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"

# Parametrar:
# - ws: vindstyrka (m/s)  
# - wd: vindriktning (grader 0-360)
# - Uppdateras var 6:e timme
# - Prognos upp till 10 dagar
```

### **🆕 SMHI Observations API Integration**

```python
# Endpoint för Observatorielunden (parameter 7 = nederbörd)
url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/98230/period/latest-hour/data.json"

# Prioriteringslogik i weather_client.py
if observations_data and observations_data['precipitation_observed'] > 0:
    combined['precipitation'] = observations_data['precipitation_observed']
    combined['precipitation_source'] = 'smhi_observations'
else:
    combined['precipitation'] = smhi_data.get('precipitation', 0)
    combined['precipitation_source'] = 'smhi_forecast'
```

### **Kritiska filer för backup (uppdaterat med Wind Module)**
- **main_daemon.py**: Daemon + Dynamic Module System + Rendering Pipeline
- **config.json**: Komplett konfiguration + triggers + module groups + **OBSERVATIONS + WIND**
- **modules/weather_client.py**: API-integration + **OBSERVATIONS** + cykel-väder + **WIND** + test-data support
- **modules/renderers/**: Alla renderer-klasser + factory + **wind_renderer.py**
- **modules/icon_manager.py**: **WIND-mappningar** + vindbenämningar + kardinalpunkter
- **tools/test_precipitation_trigger.py**: **🆕 OBSERVATIONS-test** + Prioriteringslogik-test
- **tools/restart.py**: Restart script

### **🆕 Nya beroenden för OBSERVATIONS + WIND**
- **PIL (Pillow)**: Bildbehandling + E-Paper rendering (befintlig)
- **requests**: API-anrop (SMHI, **OBSERVATIONS + WIND**, Netatmo, ipgeolocation.io) (utökad)
- **systemd**: Daemon-hantering för kontinuerlig körning
- **Dynamic imports**: Runtime loading av renderer-klasser (**inklusive WindRenderer**)

### **Utvecklingsverktyg (uppdaterat med Wind Module)**
- **🆕 test_precipitation_trigger.py**: Säker test-data injection för nederbörd MED OBSERVATIONS-stöd
- **🌬️ wind_test_commands**: Test-kommandon för vinddata och triggers
- **restart.py**: Intelligent daemon restart med timeout-hantering
- **screenshot.py**: Debug-screenshots (kompatibel med observations + wind-systemet)
- **backup-system**: Automatisk versionhantering + ORIGINAL-backups **+ wind-versioner**

## 🚀 Framtida Utveckling

### **🌬️ Wind Module Förbättringar**
- **Vindbyar-detection**: Separata ikoner för konstant vs. byig vind
- **Vindkomfort-index**: Kombinera temperatur + vind för "känns som"-temperatur
- **Riktnings-historik**: Visa vindskifte-tendenser
- **Cykel-rutt-integration**: Motvind/medvind-analys för specifika rutter
- **Säsongsanpassning**: Olika tröskelvärden sommartid vs vintertid

### **Trigger-system Förbättringar**
- **Kombinerade triggers**: `"wind_speed > 10 AND temperature < 5"` för vintercykling
- **Tidsberoende triggers**: Olika tröskelvärden beroende på tid på dygnet
- **Användarläges-triggers**: Olika beteende för "cykel-läge" vs "hem-läge"
- **Regional observations**: Automatisk val av närmaste station baserat på koordinater
- **Kvalitets-viktning**: Använd kvalitetskoder för viktning mellan källor
- **Historisk observations**: Trend-analys baserat på observations-historik
- **Real-time varningar**: Push-notiser vid plötsliga observations-förändringar

### **Enkla tillägg med befintlig arkitektur:**
- **Säsongsmoduler**: UV-index sommartid, mörka månader-fokus
- **Användarstyrda moduler**: Manuell växling mellan barometer/sol/**wind**
- **Fler trigger-conditions**: **Vindstyrka (observations)**, extremtemperatur, tidsbaserat
- **Nya renderers**: **WindRenderer (✅ KLAR)**, UVRenderer, AirQualityRenderer

### **Advanced Features:**
- **🆕 Observations-debugging interface**: Visualisera observations vs prognoser
- **🌬️ Wind-debugging interface**: Visualisera vindtriggers och riktningshistorik
- **Trigger debugging interface**: Visualisera aktiva triggers med observations-prioritering
- **Configuration hot-reload**: Ändra triggers utan restart
- **Multi-source triggers**: Komplexa villkor med observations + prognoser + Netatmo + **wind**
- **User preference management**: Web-interface för inställningar

### Tekniska optimeringar
- **Partiell uppdatering**: Endast ändrade moduler (kräver avancerat E-Paper stöd)
- **🆕 Asynkrona observations-anrop**: Parallella calls för snabbare observations-data
- **🌬️ Asynkrona wind-anrop**: Parallell vinddata-hämtning
- **Asynkrona API-anrop**: Parallella calls för snabbare data-hämtning
- **Compressed screenshots**: Mindre filstorlek för backup
- **Hot-swappable renderers**: Runtime loading av nya moduler

## 🏆 Slutresultat

**Avancerad, intelligens väderstation** som kombinerar:
- 🏠 **Lokala sensorer** (Netatmo utomhus/inomhus)
- 🌍 **Meteorologisk data** (SMHI prognoser + cykel-väder analys)
- **🆕 Exakta observations** (SMHI Observatorielunden för "regnar just nu")
- **🌬️ Cykel-optimerad vinddata** (intelligent wind-modul för vindbeslut)
- ⭐ **Exakt astronomi** (API-baserade soltider)  
- 🎨 **Högkvalitativa ikoner** (Weather Icons SVG→PNG + **40×40px wind-ikoner**)
- 📱 **E-Paper optimering** (1-bit, kontrast, cache)
- 🔄 **Dynamic Module System** (trigger-baserade moduler med observations-prioritering **+ wind-triggers**)
- 🧪 **Robust test-system** (säker utveckling med observations + prognos + **wind-testning**)

### **🆕 Revolutionary OBSERVATIONS Features:**
- **🌧️ Exakt nederbörd-medvetenhet**: Verklig nederbörd från Observatorielunden prioriterat över prognoser
- **🎯 Smart prioriteringslogik**: Observations > Prognoser > Fallback med intelligent växling
- **🔄 Trigger-driven layout**: Moduler aktiveras baserat på verkliga observations-förhållanden
- **🏭 Dual-source tracking**: Spårar både observations och prognoser separat
- **🔧 Production-ready**: Daemon + observations-logging + robust felhantering med station-fallback
- **📊 Intelligent caching**: Optimal cache-tider för olika datakällor (observations 15min, prognoser 30min)

### **🌬️ Revolutionary WIND MODULE Features:**
- **🚴‍♂️ Cykel-optimerad design**: Snabb vindstyrka-avläsning för "ska jag cykla?"-beslut
- **🤖 Intelligent aktivering**: Automatisk växling vid kraftig vind (>10 m/s) ersätter barometer
- **🧭 Professionell navigation**: 16 kardinalpunkter med svenska förkortningar + 40×40px ikoner
- **📏 Beaufort-skala integration**: 13 svenska vindbenämningar från "Lugnt" till "Orkan"
- **🎨 Kollisionssäker layout**: Ren UX-design utan visuellt brus, radbrytning för långa texter
- **🔧 Användarkonfigurerbar**: Manuell aktivering eller trigger-baserad automatik
- **🧪 Robust testing**: Komplett test-system för vinddata, triggers och layout-debugging

### **🧪 Advanced Test-capabilities:**
- **Observations vs prognoser**: Testa prioriteringslogik mellan datakällor
- **🌬️ Wind trigger-testning**: Simulera olika vindstyrkor för trigger-debugging
- **Konflikt-scenarion**: Vad händer när observations och prognoser skiljer sig åt
- **Kvalitets-testning**: Simulera dålig observations-data för fallback-testning
- **Threshold-testning**: Precis testning av trigger-tröskelvärden (0.2mm/h för cykel-väder, **10.0m/s för wind**)
- **🌬️ Wind-layout testing**: Testa olika vindstyrkor och riktningar för layout-kvalitet

**Resultat**: Kristallklar, adaptiv väderstation med meteorologisk precision som automatiskt anpassar sig efter **verkliga väderförhållanden från Observatorielunden OCH vindförhållanden** och användarens behov, med komplett test-system för säker utveckling och **professionell cykel-optimerad wind-modul för dagliga vindbeslut**.

## 📚 Teknisk Dokumentation

### **🌬️ Wind Module API Integration**

```python
# SMHI Wind Data Parameters
def parse_smhi_forecast(self, json_data):
    for param in json_data.get('timeSeries', [{}])[0].get('parameters', []):
        if param['name'] == 'ws':  # Vindstyrka
            data['wind_speed'] = param['values'][0]
        elif param['name'] == 'wd':  # Vindriktning  
            data['wind_direction'] = param['values'][0]
    return data

# Wind Description Mapping (13 nivåer)
def get_wind_description_swedish(self, speed_ms):
    if speed_ms < 0.2: return "Lugnt"
    elif speed_ms < 5.4: return "Måttlig vind" 
    elif speed_ms < 10.7: return "Frisk vind"
    elif speed_ms < 17.1: return "Hård vind"
    elif speed_ms < 28.4: return "Storm"
    else: return "Orkan"

# Cardinal Direction Mapping (16 punkter)  
def get_wind_direction_info(self, degrees):
    # Returnerar ("SV", "sw") för 225°
    # Korta svenska förkortningar för cykel-optimering
```

---

## 🎯 Användning och Exempel

### **🌬️ Daglig Wind Module Användning**

**🚴‍♂️ Cykel-scenario:**
1. **Normal morgon**: Barometer-modul visar trycktrend
2. **Kraftig vind (>10 m/s)**: Wind-modul aktiveras automatiskt
3. **Snabb avläsning**: "12.3 m/s Frisk vind" + "NV" kardinalpil
4. **Cykel-beslut**: För kraftigt från nordväst → välj annan rutt eller transport

**⚙️ Konfigurationsexempel:**
```bash
# Permanent wind-modul för cykelentusiast
echo '{"modules": {"wind_module": {"enabled": true}, "barometer_module": {"enabled": false}}}' > custom_wind.json

# Sensitiv trigger för lättare aktivering  
echo '{"triggers": {"wind_trigger": {"condition": "wind_speed > 8.0"}}}' > sensitive_wind.json

# Riktningsspecifik trigger (endast motvind)
echo '{"triggers": {"wind_trigger": {"condition": "wind_speed > 10.0 AND wind_direction >= 270 AND wind_direction <= 90"}}}' > headwind_only.json
```

Detta är nu den **kompletta, produktionsklara väderstationen** med full wind-modul integration! 🌬️🚴‍♂️
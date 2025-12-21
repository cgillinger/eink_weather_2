# 🌬️ Wind Module Gust Enhancement Project
**Utöka Wind Module med vindbyar-stöd för dubbel trigger-logik och förbättrad visning**

## 🎯 Projektmål

**HUVUDMÅL**: Utöka befintlig Wind Module att stödja både medelvind OCH vindbyar för trigger-aktivering och visning.

**SPECIFIKA MÅL**:
1. ✅ **Dubbel trigger-logik**: Aktivera wind-modul om ANTINGEN medelvind ELLER vindbyar överstiger tröskelvärde
2. ✅ **Förbättrad visning**: "10 m/s (15)" format där (15) är byvärdet  
3. ✅ **Bakåtkompatibilitet**: Befintlig konfiguration ska fortsätta fungera
4. ✅ **Robust fallback**: Graceful degradation om vindbyar-data saknas
5. ✅ **Test-system**: Komplett testning av ny funktionalitet

## 🚫 ANTI-MONOLIT Constraint Check

**✅ GODKÄNT PROJEKT**: 
- **Begränsad scope**: Endast Wind Module och related triggers
- **Modulär approach**: Separata ändringar i WeatherClient, TriggerEvaluator, WindRenderer
- **Max 200 rader per fil**: Inga filer kommer överstiga gränsen
- **Single Responsibility**: Varje ändring har ett tydligt ansvar

**ARKITEKTUR-CHECKPOINT vid 100 rader kod**: Utvärdera om uppdelning behövs

## 📋 Förutsättningar och Kunskapsluckor

### ✅ KÄNT (från befintlig kod):
- Wind Module använder SMHI parametrar `ws` (vindstyrka) och `wd` (vindriktning)  
- Trigger-system finns i `main_daemon.py` med condition evaluation
- WindRenderer finns i `modules/renderers/wind_renderer.py`
- WeatherClient hanterar SMHI API-anrop i `modules/weather_client.py`

### ❓ KUNSKAPSLUCKOR (kräver research):
1. **KRITISK**: Vilka SMHI-parametrar finns för vindbyar/gusts?
   - Möjliga namn: `gust`, `wind_gust`, `wg`, `maximum_wind_gust`?
   - Finns detta i prognoser-API:et eller bara observations?
   - Samma tidsupplösning som `ws`?

2. **VIKTIGT**: SMHI API-struktur för vindbyar
   - JSON-format för gust-data
   - Kvalitetskoder och tillgänglighet
   - Fallback-strategier vid saknad data

3. **NICE-TO-HAVE**: Meteorologisk praxis
   - Hur länge mäts vindbyar? (3-sekunder som nämns i docs?)
   - Relation mellan medelvind och byar (typiska ratios)

### 🔍 RESEARCH TASKS (behöver göras först):
```bash
# Task 1: Identifiera SMHI gust-parametrar
python3 -c "
import requests
url = 'https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/18.0686/lat/59.3293/data.json'
resp = requests.get(url)
data = resp.json()
params = set()
for ts in data['timeSeries'][:3]:
    for p in ts['parameters']:
        params.add(p['name'])
print('Tillgängliga parametrar:', sorted(params))
print('Sök efter: gust, wind, wg, maxwind')
"

# Task 2: Undersök SMHI observations för vindbyar
# Kontrollera om vindbyar finns i observations-API:et

# Task 3: Validera befintlig trigger-syntax
# Säkerställ att nya conditions fungerar med befintlig parser
```

## 🏗️ Teknisk Arkitektur

### 📁 Filer som kommer ändras:
```
modules/weather_client.py          # API-integration för gust-data
modules/renderers/wind_renderer.py # Visning av "speed (gust)" format  
main_daemon.py                     # Trigger evaluation för gust conditions
config.json                        # Nya trigger-conditions och konfiguration
tools/test_wind_gust_trigger.py    # NYTT: Test-system för gust triggers
```

### 🔄 Data Flow:
```
1. WeatherClient.parse_smhi_forecast() 
   → Extrahera både 'ws' OCH gust-parameter
   
2. WeatherClient.combine_weather_data()
   → Kombinera wind_speed + wind_gust i samma struktur
   
3. TriggerEvaluator (main_daemon.py)
   → Utvärdera: "wind_speed > 8 OR wind_gust > 8"
   
4. WindRenderer.render()
   → Visa: "10.2 m/s (14.5)" format med båda värdena
```

## 📊 Implementation Plan

### **STEG 1: Research och API-discovery** ⏱️ 30 min
**MÅL**: Identifiera exakta SMHI-parametrar för vindbyar

**ACTIONS**:
```bash
# 1.1 Undersök tillgängliga SMHI-parametrar  
python3 research_smhi_gust_params.py

# 1.2 Testa API-responses för gust-data
curl "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/18.0686/lat/59.3293/data.json" | jq '.timeSeries[0].parameters[] | select(.name | contains("gust") or contains("wind") or contains("wg"))'

# 1.3 Dokumentera findings
echo "Gust parameter: [DISCOVERED_NAME]" >> gust_research.md
```

**DELIVERABLE**: `gust_research.md` med exakta parameter-namn och API-struktur

**BACKUP**: Innan research
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/ORIGINAL_gust_research_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
echo "Starting gust research" > "$BACKUP_DIR/README_backup.txt"
```

---

### **STEG 2: WeatherClient utökning** ⏱️ 45 min  
**MÅL**: Utöka `parse_smhi_forecast()` med gust-data extraction

**BACKUP FÖRE ÄNDRING**:
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M_S)
BACKUP_DIR="backup/weather_client_gust_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp modules/weather_client.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/weather_client.py"
```

**CHANGES**:
```python
# I parse_smhi_forecast() metoden, lägg till:
elif param['name'] == '[DISCOVERED_GUST_PARAM]':  # Vindbyar
    data['wind_gust'] = param['values'][0]
    
# I combine_weather_data() metoden:
if smhi_data and 'wind_gust' in smhi_data:
    combined['wind_gust'] = smhi_data['wind_gust']
    combined['wind_gust_source'] = 'smhi'
else:
    # Fallback: estimera från medelvind (gust ≈ 1.4 × medelvind)
    if 'wind_speed' in combined:
        combined['wind_gust'] = round(combined['wind_speed'] * 1.4, 1)
        combined['wind_gust_source'] = 'estimated'
```

**TESTING**:
```bash
# Testa gust-data extraction
python3 -c "
from modules.weather_client import WeatherClient
import json
with open('config.json', 'r') as f: config = json.load(f)
client = WeatherClient(config)
data = client.get_current_weather()
print(f'Wind: {data.get(\"wind_speed\", 0)} m/s')
print(f'Gust: {data.get(\"wind_gust\", \"N/A\")} m/s')
print(f'Gust source: {data.get(\"wind_gust_source\", \"unknown\")}')
"
```

---

### **STEG 3: Trigger-system utökning** ⏱️ 30 min
**MÅL**: Utöka trigger evaluation med `wind_gust` variabel

**BACKUP**:
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/trigger_gust_$TIMESTAMP"  
mkdir -p "$BACKUP_DIR"
cp main_daemon.py "$BACKUP_DIR/"
cp config.json "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/"
```

**CHANGES**:
```python
# I build_trigger_context() (main_daemon.py):
context.update({
    'wind_speed': weather_data.get('wind_speed', 0),
    'wind_gust': weather_data.get('wind_gust', 0),      # NYTT
    'wind_direction': weather_data.get('wind_direction', 0)
})
```

**CONFIG UPDATES**:
```json
{
  "triggers": {
    "wind_trigger": {
      "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
      "target_section": "medium_right_section", 
      "activate_group": "wind_active",
      "priority": 80,
      "description": "Aktivera vid medelvind >8 m/s ELLER vindbyar >8 m/s"
    }
  }
}
```

**TESTING**:
```bash
# Testa trigger evaluation
python3 -c "
import json
from main_daemon import build_trigger_context
with open('config.json', 'r') as f: config = json.load(f)
# Simulera data med gust > threshold men wind_speed < threshold  
weather_data = {'wind_speed': 7.0, 'wind_gust': 10.5}
context = {'wind_speed': 7.0, 'wind_gust': 10.5}
condition = 'wind_speed > 8.0 OR wind_gust > 8.0'
result = eval(condition, {}, context)  # VARNING: Endast för test
print(f'Trigger result: {result} (ska vara True)')
"
```

---

### **STEG 4: WindRenderer enhancement** ⏱️ 40 min
**MÅL**: Uppdatera visning till "10 m/s (15)" format

**BACKUP**:
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/wind_renderer_gust_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"  
cp modules/renderers/wind_renderer.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/wind_renderer.py"
```

**CHANGES**:
```python
# I WindRenderer.render() metoden:
def format_wind_speed_with_gust(self, wind_speed, wind_gust=None, wind_gust_source=None):
    """Format wind speed with optional gust value"""
    base_speed = f"{wind_speed:.1f} m/s"
    
    if wind_gust and wind_gust > wind_speed:
        if wind_gust_source == 'estimated':
            # Visa estimat diskret
            return f"{base_speed} (~{wind_gust:.0f})"
        else:
            # Visa verklig gust-data
            return f"{base_speed} ({wind_gust:.0f})"
    
    return base_speed

# Använd i render():
wind_speed = weather_data.get('wind_speed', 0)
wind_gust = weather_data.get('wind_gust')
wind_gust_source = weather_data.get('wind_gust_source')

speed_text = self.format_wind_speed_with_gust(wind_speed, wind_gust, wind_gust_source)
```

**LAYOUT CONSIDERATIONS**:
- Kontrollera att längre text (15 tecken istället för 10) passar i wind-modulen
- Testa radbrytning för långa texter
- Säkerställ kollisionsfri layout

---

### **STEG 5: Test-system** ⏱️ 35 min
**MÅL**: Skapa komplett test-system för gust-funktionalitet

**NY FIL**: `tools/test_wind_gust_trigger.py`
```python
#!/usr/bin/env python3
"""
SÄKER TEST-DATA INJECTION FÖR WIND GUST MODULE
Testar både medelvind och vindbyar triggers
"""

import json
import time
from pathlib import Path

def create_wind_gust_test_data():
    """Skapa test-data för gust triggers"""
    test_scenarios = {
        "scenario_1_gust_trigger": {
            "description": "Medelvind under tröskelvärde, gust över",
            "wind_speed": 7.0,    # Under 8.0 tröskelvärde
            "wind_gust": 12.5,    # Över 8.0 tröskelvärde
            "expected_trigger": True
        },
        "scenario_2_both_over": {
            "description": "Både medelvind och gust över tröskelvärde", 
            "wind_speed": 10.2,
            "wind_gust": 15.8,
            "expected_trigger": True
        },
        "scenario_3_no_trigger": {
            "description": "Både medelvind och gust under tröskelvärde",
            "wind_speed": 6.5,
            "wind_gust": 7.8,
            "expected_trigger": False
        }
    }
    
    return test_scenarios

def inject_test_data(scenario_name):
    """Injicera specifikt test-scenario"""
    scenarios = create_wind_gust_test_data()
    
    if scenario_name not in scenarios:
        print(f"❌ Okänt scenario: {scenario_name}")
        return
        
    scenario = scenarios[scenario_name]
    
    test_data = {
        "enabled": True,
        "timeout_hours": 1,
        "timestamp": time.time(),
        "scenario": scenario_name,
        "wind_speed": scenario["wind_speed"],
        "wind_gust": scenario["wind_gust"],
        "wind_direction": 225,  # SW för test
        "description": scenario["description"],
        "expected_trigger": scenario["expected_trigger"]
    }
    
    # Skriv test-data
    test_file = Path("cache/test_wind_gust.json")
    test_file.parent.mkdir(exist_ok=True)
    
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"✅ Injicerat test-scenario: {scenario_name}")
    print(f"📊 Wind: {scenario['wind_speed']} m/s, Gust: {scenario['wind_gust']} m/s")
    print(f"🎯 Förväntat trigger: {scenario['expected_trigger']}")
    
if __name__ == "__main__":
    print("🌬️ WIND GUST TRIGGER TEST")
    scenarios = create_wind_gust_test_data()
    
    print("\nTillgängliga test-scenarios:")
    for i, (name, data) in enumerate(scenarios.items(), 1):
        print(f"{i}. {name}: {data['description']}")
    
    choice = input("\nVälj scenario (1-3): ")
    scenario_names = list(scenarios.keys())
    
    if choice.isdigit() and 1 <= int(choice) <= len(scenario_names):
        inject_test_data(scenario_names[int(choice)-1])
    else:
        print("❌ Ogiltigt val")
```

**TESTING WORKFLOW**:
```bash
# 1. Injicera gust-trigger scenario
python3 tools/test_wind_gust_trigger.py

# 2. Restart daemon för att ladda test-data  
python3 tools/restart.py

# 3. Kontrollera trigger activation i logs
sudo journalctl -u epaper-weather -f | grep -E "(wind|gust|trigger)"

# 4. Ta screenshot för visuell verifiering
python3 screenshot.py --output wind_gust_test

# 5. Rensa test-data
rm cache/test_wind_gust.json && python3 tools/restart.py
```

---

### **STEG 6: Konfiguration och dokumentation** ⏱️ 20 min
**MÅL**: Uppdatera config.json och dokumentation

**CONFIG EXAMPLES**:
```json
{
  "_comment_wind_gust": "=== WIND GUST CONFIGURATION ===",
  "triggers": {
    "wind_trigger": {
      "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
      "description": "Trigger på medelvind ELLER vindbyar över 8 m/s"
    },
    
    "_examples_advanced_gust_triggers": {
      "winter_cycling": {
        "condition": "wind_gust > 12.0 AND temperature < 5.0",
        "description": "Kraftiga vindbyar i kyla - farligt för cykling"
      },
      "gust_differential": {
        "condition": "(wind_gust - wind_speed) > 5.0",
        "description": "Stora skillnader mellan medelvind och byar"
      }
    }
  },
  
  "wind_gust_config": {
    "show_estimated_gust": true,
    "estimation_factor": 1.4,
    "min_gust_display_threshold": 2.0,
    "gust_display_format": "speed (gust)"
  }
}
```

**DOCUMENTATION UPDATE**:
```markdown
## 🌬️ Wind Gust Enhancement

### Nya funktioner:
- **Dubbel trigger**: wind_speed > X OR wind_gust > X  
- **Gust visning**: "10.2 m/s (15)" format
- **Fallback**: Estimat om gust-data saknas
- **Test-system**: Komplett gust-scenario testning

### Nya trigger-variabler:
- `wind_gust`: Vindbyar i m/s (från SMHI eller estimat)
- `wind_gust_source`: 'smhi' eller 'estimated'

### Exempel-triggers:
```json
"wind_speed > 8.0 OR wind_gust > 8.0"     // Antingen medel eller byar
"wind_gust > 15.0"                        // Endast kraftiga byar  
"(wind_gust - wind_speed) > 4.0"          // Stora skillnader
```
```

---

## 🧪 Kvalitetssäkring och Testing

### **KOMPLETT TEST-SUITE**:
```bash
# Test 1: API integration
python3 -c "from modules.weather_client import WeatherClient; client = WeatherClient({}); print('Gust support:', 'wind_gust' in client.get_current_weather())"

# Test 2: Trigger evaluation  
python3 tools/test_wind_gust_trigger.py

# Test 3: Visual rendering
python3 screenshot.py --output gust_test

# Test 4: Fallback behavior (simulera API-fel)
# Testa att estimering fungerar när gust-data saknas

# Test 5: Backwards compatibility
# Säkerställ att befintlig config utan gust fortfarande fungerar
```

### **ROBUSTHET-TESTNING**:
- ✅ Gust-data saknas → Fallback till estimering
- ✅ SMHI API-fel → Graceful degradation  
- ✅ Ogiltiga gust-värden → Validering och fallback
- ✅ Trigger-syntax fel → Säker evaluation med fallback

### **PERFORMANCE-KONTROLL**:
- Ingen betydande overhead från gust-processing
- Cache-effektiv gust-data hantering
- Minimal impact på befintliga moduler

---

## 📈 Success Metrics

### **TEKNIK**:
- ✅ Wind gust-data extraheras från SMHI  
- ✅ Trigger aktiveras på wind_speed OR wind_gust conditions
- ✅ Visning: "10.2 m/s (15)" format implementerat
- ✅ Backup-kompatibel med befintlig funktionalitet
- ✅ <200 rader kod per förändrad fil

### **FUNKTIONALITET**:
- ✅ Trigger aktiveras när wind_gust > threshold även om wind_speed < threshold
- ✅ Visuellt tydlig presentation av både medel och byar
- ✅ Graceful fallback när gust-data saknas
- ✅ Test-system för alla gust-scenarios

### **ANVÄNDARVÄNLIGHET**:
- ✅ Intuitiv visning av vindbyar-information
- ✅ Bakåtkompatibel konfiguration
- ✅ Tydlig dokumentation av nya möjligheter

---

## ⚠️ Risker och Mitigation

### **TEKNISKA RISKER**:

**RISK**: SMHI kanske inte har gust-parametrar i prognoser
- **MITIGATION**: Research-fas identifierar detta tidigt + estimering-fallback
- **PLAN B**: Använd observations-API för gust-data istället

**RISK**: Gust-data kan vara opålitligt/spora
- **MITIGATION**: Kvalitetskontroll + graceful fallback till medelvind

**RISK**: Layout-problem med längre text  
- **MITIGATION**: Testning av extremfall + responsive layout

### **PROJEKT-RISKER**:

**RISK**: Research-fasen tar längre tid än planerat
- **MITIGATION**: Börja med estimering-implementation medan research pågår

**RISK**: Trigger-syntax blir för komplex
- **MITIGATION**: Behåll enkla OR-conditions, undvik komplexa boolean logic

---

## 🚀 Implementation Timeline

**TOTAL TIDSESTIMERING**: ~3.5 timmar

1. **Research** (30 min) → Identifiera SMHI gust-parametrar
2. **WeatherClient** (45 min) → API integration + parsing  
3. **Triggers** (30 min) → Utökad trigger evaluation
4. **WindRenderer** (40 min) → Gust display formatting
5. **Testing** (35 min) → Komplett test-suite
6. **Documentation** (20 min) → Config + docs update

**KRITISK VÄG**: Research → WeatherClient → Triggers
**PARALLELL**: WindRenderer och Testing kan delvis köras parallellt

---

## 📂 Backup och Rollback Plan

### **BACKUP-STRATEGI**:
```bash
# Före varje steg:
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/wind_gust_[STEP]_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp [AFFECTED_FILES] "$BACKUP_DIR/"
```

### **ROLLBACK-SCENARIO**:
Om projektet misslyckas efter Steg 3:
```bash
# Återställ alla filer från ORIGINAL backup
ORIGINAL_BACKUP=$(ls -td backup/ORIGINAL_* | head -1)
cp "$ORIGINAL_BACKUP"/* .
python3 tools/restart.py
echo "✅ Rollback till utgångsläge komplett"
```

---

## 🎯 Framtida Expansioner

Efter grundfunktionaliteten är implementerad:

### **FAS 2 - Avancerad Gust Analytics**:
- Gust-faktor beräkning (gust/medelvind ratio)
- Trendanalys av vindbyar över tid
- Säsongsbaserade gust-tröskelvärden

### **FAS 3 - Meteorologisk Integration**:
- Kombination med trycktrend för storm-förutsägelse  
- Integration med nederbörds-modulen för storm-varningar
- Temperatur-korrigerad vindkomfort

### **FAS 4 - User Experience**:
- Konfigurerbar gust-visning (ON/OFF)
- Anpassade tröskelvärden per användare
- Push-notifikationer vid extrema vindbyar

---

## 🔄 Chat Handoff Instructions

**VIKTIGT**: Varje steg är designat för att färdigställas i en separat chatt. Här är exakta instruktioner för hur du övergår mellan steg.

### **STEG 1 → STEG 2 Handoff**

**VID SLUTET AV STEG 1**, rapportera följande:
```
✅ STEG 1 FÄRDIGT: Research och API-discovery
📊 RESULTAT:
- SMHI gust-parameter: [DISCOVERED_NAME] (t.ex. "gust", "wg", "wind_gust_speed")
- API-struktur: [JSON_FORMAT_EXAMPLE]
- Tillgänglighet: [PROGNOS/OBSERVATIONS/BÅDE]
- Fallback-behov: [JA/NEJ + anledning]

📁 FILER SKAPADE:
- gust_research.md (dokumentation)
- backup/ORIGINAL_gust_research_[TIMESTAMP]/ (säkerhetskopia)

🎯 NÄSTA STEG: WeatherClient utökning
```

**PROMPT FÖR NÄSTA CHATT (STEG 2)**:
```
Jag arbetar med Wind Module Gust Enhancement Project och har slutfört STEG 1 (Research). 

RESULTAT FRÅN STEG 1:
- SMHI gust-parameter: [SÄTT IN DISCOVERED_NAME]
- API-struktur: [SÄTT IN JSON_EXAMPLE] 
- Tillgänglighet: [PROGNOS/OBSERVATIONS/BÅDE]

Nu ska jag genomföra STEG 2: WeatherClient utökning för att extrahera gust-data från SMHI API.

MÅL FÖR DENNA CHATT:
1. Backup av modules/weather_client.py
2. Utöka parse_smhi_forecast() med gust-parameter extraction
3. Uppdatera combine_weather_data() med gust-hantering och fallback
4. Testa gust-data extraction

Ge mig backup-kommando först, sedan implementation av gust-extraction enligt projektet.
```

---

### **STEG 2 → STEG 3 Handoff**

**VID SLUTET AV STEG 2**, rapportera följande:
```
✅ STEG 2 FÄRDIGT: WeatherClient utökning
📊 RESULTAT:
- Gust-extraction implementerat i parse_smhi_forecast()
- Fallback-logik: [ESTIMERING/CACHE/NONE] 
- Test-resultat: wind_speed=[X]m/s, wind_gust=[Y]m/s, source=[SOURCE]

📁 FILER ÄNDRADE:
- modules/weather_client.py (backup: wind_gust_[TIMESTAMP])
- Testning genomförd och godkänd

⚠️ NOTERINGAR:
- [EVENTUELLA PROBLEM ELLER OBSERVATIONER]

🎯 NÄSTA STEG: Trigger-system utökning
```

**PROMPT FÖR NÄSTA CHATT (STEG 3)**:
```
Wind Module Gust Enhancement Project - STEG 2 färdigt.

STATUS:
- WeatherClient ger nu både wind_speed och wind_gust
- Gust-parameter från SMHI: [PARAMETER_NAME]
- Fallback-strategi: [FALLBACK_METHOD]
- Test bekräftat: fungerar

Nu ska jag genomföra STEG 3: Trigger-system utökning för "wind_speed > X OR wind_gust > X" logik.

MÅL FÖR DENNA CHATT:
1. Backup av main_daemon.py och config.json
2. Utöka build_trigger_context() med wind_gust variabel
3. Uppdatera config.json med nya wind_trigger condition
4. Testa trigger evaluation med gust-data

Ge mig backup-kommando och implementation av trigger-utökning.
```

---

### **STEG 3 → STEG 4 Handoff**

**VID SLUTET AV STEG 3**, rapportera följande:
```
✅ STEG 3 FÄRDIGT: Trigger-system utökning
📊 RESULTAT:
- wind_gust variabel tillgänglig i trigger context
- Ny condition: "wind_speed > 8.0 OR wind_gust > 8.0"
- Test-resultat: trigger=[TRUE/FALSE] vid test-värden

📁 FILER ÄNDRADE:
- main_daemon.py (backup: trigger_gust_[TIMESTAMP])
- config.json (backup: trigger_gust_[TIMESTAMP])

✅ TRIGGER-TEST:
- Scenario 1: wind_speed=7, gust=10 → trigger=[RESULT]
- Scenario 2: wind_speed=9, gust=6 → trigger=[RESULT]

🎯 NÄSTA STEG: WindRenderer enhancement
```

**PROMPT FÖR NÄSTA CHATT (STEG 4)**:
```
Wind Module Gust Enhancement Project - STEG 3 färdigt.

STATUS:
- Trigger-system stödjer nu wind_gust variabel
- OR-logik fungerar: wind_speed > X OR wind_gust > X
- Testning bekräftad för trigger activation

Nu ska jag genomföra STEG 4: WindRenderer enhancement för "10 m/s (15)" visningsformat.

MÅL FÖR DENNA CHATT:
1. Backup av modules/renderers/wind_renderer.py
2. Implementera format_wind_speed_with_gust() metod
3. Uppdatera render() för gust-visning 
4. Testa layout och textlängd

Ge mig backup-kommando och implementation av WindRenderer gust-visning.
```

---

### **STEG 4 → STEG 5 Handoff**

**VID SLUTET AV STEG 4**, rapportera följande:
```
✅ STEG 4 FÄRDIGT: WindRenderer enhancement
📊 RESULTAT:
- Gust-visning format: "10.2 m/s (15)" implementerat
- Layout-testning: [FUNKAR/PROBLEM med längre text]
- Estimat-visning: "10 m/s (~14)" för estimated gust

📁 FILER ÄNDRADE:
- modules/renderers/wind_renderer.py (backup: wind_renderer_gust_[TIMESTAMP])

✅ VISUELL TEST:
- Normal visning: wind_speed=8.5, gust=12.3 → "8.5 m/s (12)"
- Estimat: wind_speed=10, estimated_gust=14 → "10.0 m/s (~14)"
- Ingen gust: wind_speed=6.5 → "6.5 m/s"

🎯 NÄSTA STEG: Test-system development
```

**PROMPT FÖR NÄSTA CHATT (STEG 5)**:
```
Wind Module Gust Enhancement Project - STEG 4 färdigt.

STATUS:
- WindRenderer visar nu gust-data i "speed (gust)" format
- Layout fungerar för längre text
- Både real och estimated gust-värden hanteras

Nu ska jag genomföra STEG 5: Test-system development för komplett gust-scenario testning.

MÅL FÖR DENNA CHATT:
1. Skapa tools/test_wind_gust_trigger.py
2. Implementera test-scenarios för gust triggers
3. Testa trigger activation med olika gust-kombinationer
4. Verifiera visuell presentation med screenshot

Ge mig implementation av test-systemet enligt projektspecifikationen.
```

---

### **STEG 5 → STEG 6 Handoff**

**VID SLUTET AV STEG 5**, rapportera följande:
```
✅ STEG 5 FÄRDIGT: Test-system development
📊 RESULTAT:
- test_wind_gust_trigger.py skapad med 3 scenarios
- Test-scenarios: gust_only, both_over, no_trigger
- Trigger-testning: [RESULTAT för varje scenario]
- Screenshot-verifiering: [VISUELLT RESULTAT]

📁 FILER SKAPADE:
- tools/test_wind_gust_trigger.py
- cache/test_wind_gust.json (test-data)
- screenshots/wind_gust_test.png (visuell verifiering)

✅ TEST-RESULTAT:
- Scenario 1 (wind=7, gust=12): trigger=[RESULT], visning=[TEXT]
- Scenario 2 (wind=10, gust=16): trigger=[RESULT], visning=[TEXT]  
- Scenario 3 (wind=6, gust=7): trigger=[RESULT], visning=[TEXT]

🎯 NÄSTA STEG: Konfiguration och dokumentation
```

**PROMPT FÖR NÄSTA CHATT (STEG 6)**:
```
Wind Module Gust Enhancement Project - STEG 5 färdigt.

STATUS:
- Komplett test-system implementerat och verifierat
- Alla gust-scenarios testade framgångsrikt
- Visuell presentation bekräftad

Nu ska jag genomföra STEG 6: Final konfiguration och dokumentation.

MÅL FÖR DENNA CHATT:
1. Uppdatera config.json med fullständig gust-konfiguration
2. Skapa exempel-triggers för avancerade use-cases
3. Uppdatera README/dokumentation med gust-funktionalitet
4. Slutlig verifiering av hela projektet

Ge mig implementation av final config-uppdateringar och dokumentation.
```

---

### **STEG 6 → PROJEKT SLUTFÖRT**

**VID SLUTET AV STEG 6**, rapportera följande:
```
🎉 PROJEKT SLUTFÖRT: Wind Module Gust Enhancement

📊 SLUTRESULTAT:
- ✅ Dubbel trigger-logik: wind_speed > X OR wind_gust > X
- ✅ Gust-visning: "10.2 m/s (15)" format
- ✅ Robust fallback vid saknad gust-data
- ✅ Bakåtkompatibilitet bibehållen
- ✅ Komplett test-system

📁 FILER FÖRÄNDRADE:
- modules/weather_client.py (gust extraction)
- main_daemon.py (trigger context)
- modules/renderers/wind_renderer.py (gust display)
- config.json (nya triggers)
- tools/test_wind_gust_trigger.py (test system)

📈 FUNKTIONALITETER:
- SMHI gust-parameter: [FINAL_PARAMETER_NAME]
- Trigger aktiveras vid: medelvind >8 m/s ELLER vindbyar >8 m/s
- Fallback-strategi: [FINAL_FALLBACK_METHOD]
- Test-coverage: 100% för alla gust-scenarios

🚀 DEPLOYMENT-REDO:
Alla ändringar är implementerade, testade och dokumenterade.
Systemet är redo för production-användning.

📋 BACKUP-STATUS:
Alla backup-filer sparade i backup/-katalogen för eventuell rollback.
```

---

## 📋 Handoff Checklist

**FÖR VARJE STEG-ÖVERGÅNG:**

### ✅ Obligatoriska element i handoff:
1. **Status-sammanfattning** av genomfört steg
2. **Resultat-rapportering** med konkreta värden
3. **Fil-status** (ändrade/skapade filer + backup-locations)
4. **Test-resultat** eller verifiering av funktionalitet
5. **Problemrapportering** om något oväntat inträffade

### ✅ Obligatoriska element i nästa prompt:
1. **Projektnamn** och steg-nummer
2. **Status från föregående steg** (kopierat från handoff)
3. **Specifika mål** för aktuellt steg
4. **Tydlig första åtgärd** (oftast backup-kommando)
5. **Referens till projektdokumentation** vid behov

### ✅ Säkerhet och kontinuitet:
- Varje steg börjar med backup
- Alla kritiska värden överförs mellan chattar
- Test-verifiering innan handoff
- Rollback-information vid problem

**🎯 DENNA STRUKTUR SÄKERSTÄLLER**:
- Inget steg blir beroende av tidigare chat-minne
- Varje chatt har all information som behövs
- Robust felhantering och backup-strategi
- Kontinuerlig projektprogress utan informationsförlust

---

**🎖️ PROJEKTRESULTAT**: En robust, utökad Wind Module med intelligent gust-hantering som förbättrar användarens förståelse av vindförhållanden för bättre dagliga beslut.**
# 🧪 Precipitation Module Test System

**E-Paper Weather Daemon - Säker test-data injection för nederbörd-modul**

## 📋 Översikt

Detta system möjliggör säker testning av precipitation module's trigger-funktionalitet genom att injicera test-data i `weather_client.py` innan rendering. Detta är nödvändigt eftersom triggers aktiveras korrekt baserat på conditions, men rendering får `precipitation: 0.0` från API:er (eftersom det inte regnar naturligt under testning).

## 🏗️ Arkitektur

### **Komponenter som modifierats:**

1. **`modules/weather_client.py`** - Säker test-data injection
2. **`config.json`** - Debug-konfiguration för test-aktivering  
3. **`test_precipitation_trigger.py`** - Test-script för data-injection

### **Säkerhetsdesign:**

- ✅ **Config-driven säkerhet** - Kräver explicit `debug.allow_test_data = true`
- ✅ **Automatisk timeout** - Test-data rensas efter konfigurerad tid (default: 1h)
- ✅ **Production-safe** - Ignoreras när `debug.enabled = false`
- ✅ **Explicit aktivering** - Test-data filen måste ha `enabled: true`
- ✅ **Comprehensive logging** - All test-aktivitet loggas med 🧪 prefix

## ⚙️ Konfiguration

### **config.json setup:**

```json
{
  "debug": {
    "enabled": true,
    "allow_test_data": true,
    "test_timeout_hours": 1
  }
}
```

### **Produktions-säkerhet:**

```json
{
  "debug": {
    "enabled": false,        // Måste vara false
    "allow_test_data": false // Måste vara false  
  }
}
```

## 🚀 Användning

### **Grundläggande test-cykel:**

```bash
# 1. Starta test-script
python3 test_precipitation_trigger.py

# 2. Välj test-scenario (t.ex. "2" för måttligt regn)
# Script skapar cache/test_precipitation.json

# 3. Avsluta test-script (välj "11")

# 4. Restart daemon för att ladda test-data
python3 restart.py

# 5. Observera loggar för test-aktivering
sudo journalctl -u epaper-weather -f | grep "🧪"

# 6. Ta screenshot för att verifiera layout
python3 screenshot.py --output precipitation_test

# 7. Rensa test-data
python3 test_precipitation_trigger.py
# Välj "10" för att rensa

# 8. Restart för normal drift
python3 restart.py
```

## 📊 Test-Scenarion

### **Tillgängliga scenarion:**

| Scenario | Precipitation | Forecast | Trigger | Förväntat Resultat |
|----------|---------------|----------|---------|-------------------|
| **Lätt regn** | 0.8mm/h | 0.0mm/h | `precipitation > 0` | "Regnar nu: 0.8mm/h" |
| **Måttligt regn** | 2.5mm/h | 0.0mm/h | `precipitation > 0` | "Regnar nu: 2.5mm/h" |
| **Kraftigt regn** | 8.0mm/h | 1.2mm/h | `precipitation > 0` | "Regnar nu: 8.0mm/h" |
| **Prognos-regn** | 0.0mm/h | 1.5mm/h | `forecast_precipitation_2h > 0.2` | "Regn väntat: 1.5mm/h" |
| **Cykel-varning** | 0.0mm/h | 0.3mm/h | `forecast_precipitation_2h > 0.2` | "Regn väntat: 0.3mm/h" |

### **Trigger-logik:**

```
precipitation > 0 OR forecast_precipitation_2h > 0.2
```

**Aktiveras när:**
- Pågående nederbörd (oavsett mängd)
- ELLER prognostiserad nederbörd över 0.2mm/h

## 🔍 Monitorering och Debug

### **Loggar att leta efter:**

```bash
# Test-data aktivering
sudo journalctl -u epaper-weather -f | grep "🧪 TEST-DATA AKTIVT"

# Trigger-aktivering  
sudo journalctl -u epaper-weather -f | grep "🎯 Trigger aktiverad"

# Layout-växling
sudo journalctl -u epaper-weather -f | grep "LAYOUT"

# Nederbörd-rendering 
sudo journalctl -u epaper-weather -f | grep "🌧️ Renderar nederbörd"

# Data overrides
sudo journalctl -u epaper-weather -f | grep "🧪 Override"
```

### **Förväntade logg-meddelanden:**

```
🧪 TEST-DATA AKTIVT: Test nederbörd: 2.5mm/h
🧪 Override precipitation: 2.5mm/h
🎯 Trigger aktiverad: precipitation_trigger → bottom_section.precipitation_active
🌧️ Renderar nederbörd-modul (480×100)
✅ Nederbörd-modul rendered: Regnar nu: 2.5mm/h
```

## 🧰 Test-Script Funktioner

### **Menysystem:**

```bash
python3 test_precipitation_trigger.py
```

**Tillgängliga alternativ:**
- **1-5:** Inject olika nederbörd-scenarion
- **6:** Visa aktuell test-status
- **7:** Analysera trigger-conditions
- **8:** Validera konfiguration  
- **9:** Visa alla test-scenarion
- **10:** Rensa test-data
- **11:** Avsluta

### **Status-kontroll:**

```bash
# Visa test-status utan att starta menyn
python3 -c "
import os, json
if os.path.exists('cache/test_precipitation.json'):
    with open('cache/test_precipitation.json') as f:
        data = json.load(f)
    print(f'Test aktiv: {data.get(\"test_description\", \"N/A\")}')
else:
    print('Normal drift - inget test aktivt')
"
```

## 🔧 Implementation Detaljer

### **weather_client.py modifieringar:**

```python
def _load_test_data_if_enabled(self) -> Optional[Dict]:
    """Säker test-data laddning med multiple säkerhetscheckar"""
    # 1. Kontrollera debug.enabled
    # 2. Kontrollera debug.allow_test_data  
    # 3. Kontrollera att test-fil finns
    # 4. Kontrollera enabled-flag i test-data
    # 5. Kontrollera timeout
    # 6. Auto-cleanup vid timeout

def _apply_test_overrides(self, combined_data: Dict, test_data: Dict) -> Dict:
    """Applicera test-overrides på väderdata"""
    # Override: precipitation, forecast_precipitation_2h, cycling_weather
    # Markera: test_mode = True

# I combine_weather_data() metoden:
test_override = self._load_test_data_if_enabled()
if test_override:
    combined = self._apply_test_overrides(combined, test_override)
```

### **Test-data format:**

```json
{
  "enabled": true,
  "created_at": "2025-01-28T12:00:00",
  "expires_at": "2025-01-28T13:00:00", 
  "test_description": "Test nederbörd: 2.5mm/h",
  "precipitation": 2.5,
  "forecast_precipitation_2h": 0.0,
  "cycling_weather": {
    "cycling_warning": true,
    "precipitation_mm": 2.5,
    "precipitation_type": "Måttligt regn",
    "forecast_time": "13:15",
    "reason": "Test: 2.5mm/h nederbörd"
  }
}
```

## 🚨 Felsökning

### **Test-data ignoreras:**

```bash
# Kontrollera konfiguration
python3 test_precipitation_trigger.py
# Välj "8" för konfiguration-validering

# Vanliga orsaker:
# - debug.enabled = false
# - debug.allow_test_data = false  
# - Test-data timeout (>1h gammal)
# - enabled = false i test-data fil
```

### **Trigger aktiveras inte:**

```bash
# Analysera trigger-conditions
python3 test_precipitation_trigger.py  
# Välj "7" för trigger-analys

# Kontrollera värden:
# precipitation > 0 ELLER forecast_precipitation_2h > 0.2
```

### **Layout växlar inte:**

```bash
# Kontrollera att daemon laddat test-data
sudo journalctl -u epaper-weather -n 20 | grep "🧪"

# Om ingen 🧪 syns - daemon har inte läst test-data
# Lösning: python3 restart.py
```

### **GPIO-konflikter:**

```bash
# Stoppa allt som kan använda GPIO
sudo systemctl stop epaper-weather
sudo pkill -f main_daemon.py

# Vänta och starta om
sleep 5
sudo systemctl start epaper-weather
```

## 📁 Backup och Återställning

### **Skapa backup innan test:**

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/ORIGINAL_precipitation_test_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp modules/weather_client.py "$BACKUP_DIR/"
cp config.json "$BACKUP_DIR/"
```

### **Återställ från backup:**

```bash
# Hitta original backup
ls -la backup/ORIGINAL_*

# Återställ
BACKUP_DIR="backup/ORIGINAL_precipitation_test_YYYYMMDD_HHMMSS"
cp "$BACKUP_DIR/weather_client.py" modules/
cp "$BACKUP_DIR/config.json" .

# Restart för att ladda original kod
python3 restart.py
```

## 🎯 Validering av Lyckad Test

### **Framgångskriterier:**

✅ **Normal layout visas** när ingen test-data är aktiv  
✅ **Nederbörd-layout aktiveras** när test-data injiceras  
✅ **Korrekt meddelanden** baserat på injicerad data  
✅ **Layout växlar tillbaka** när test-data rensas  
✅ **Auto-cleanup fungerar** efter timeout  
✅ **Produktions-säkerhet** blockerar test-data när disabled  

### **Screenshot-jämförelse:**

```bash
# Innan test (normal layout)
python3 screenshot.py --output normal_before_test

# Under test (nederbörd layout)  
python3 screenshot.py --output precipitation_active

# Efter test (normal layout återställd)
python3 screenshot.py --output normal_after_test

# Jämför
ls -la screenshots/
```

## ⚠️ Produktions-Checklista

**Innan deploy till produktion:**

- [ ] `debug.enabled = false` i config.json
- [ ] `debug.allow_test_data = false` i config.json  
- [ ] Ta bort `cache/test_precipitation.json` om den finns
- [ ] Ta bort `test_precipitation_trigger.py` (eller flytta till tools/)
- [ ] Verifiera att inga 🧪 loggar syns i produktion

## 📞 Support

### **Vanliga problem:**

| Problem | Orsak | Lösning |
|---------|-------|---------|
| Test-data ignoreras | Debug inaktiverat | Sätt `debug.allow_test_data = true` |
| GPIO-fel | Service-konflikt | `python3 restart.py` |  
| Layout växlar inte | Daemon läst inte test-data | Restart daemon |
| Test "fastnar" | Glömt rensa test-data | Välj "10" i test-script |

### **Debug-kommandon:**

```bash
# Komplett system-status
sudo systemctl status epaper-weather
ls -la cache/test_precipitation.json
python3 test_precipitation_trigger.py # välj "6" + "8"

# Live monitoring  
sudo journalctl -u epaper-weather -f | grep -E "(🧪|🎯|LAYOUT|ERROR)"
```

---

**Detta test-system ger dig komplett kontroll över precipitation module testning med full säkerhet för produktion.**
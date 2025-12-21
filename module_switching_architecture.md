# 🔄 Modulväxling & Dynamisk/Manuell Funktionalitet

## 📋 Översikt

E-Paper väderstationen använder ett **hybrid-system** för modulhantering som kombinerar **manuell aktivering** (flaggor) med **dynamisk växling** (triggers). Detta möjliggör både stabil grundfunktionalitet och intelligent automatisering.

---

## 📜 Skript-arkitektur: main.py vs main_daemon.py

### **Två Separata Entry Points**

```
epaper_weather/
├── main.py              ← LEGACY SYSTEM (enkelkörning)
├── main_daemon.py       ← DYNAMIC SYSTEM (kontinuerlig daemon)
└── config.json          ← SAMMA config för båda
```

#### **main.py (Legacy System)**
```python
#!/usr/bin/env python3
"""
E-Paper Väderapp - Med riktiga väderdata från SMHI + Weather Icons
ENKELT SYSTEM: Kör en gång och avslutar
"""

# EGENSKAPER:
# ✅ Enkel körning: python3 main.py
# ✅ Använder modules.enabled: true/false  
# ✅ Hårdkodad rendering per modul
# ✅ Smart change detection (jämför värden)
# ❌ Ingen dynamisk växling
# ❌ Ingen trigger-logik
# ❌ Måste köras via cron för uppdateringar

def render_weather_layout(self, weather_data):
    """LEGACY RENDERING - hårdkodad för varje modul"""
    # Rita huvudmodul
    if self.config['modules']['main_weather']['enabled']:
        self.render_main_weather_module(weather_data)
    
    # Rita barometer
    if self.config['modules']['barometer_module']['enabled']:
        self.render_barometer_module(weather_data)
    
    # Rita nederbörd (INGEN växling)
    if self.config['modules']['precipitation_module']['enabled']:
        self.render_precipitation_module(weather_data)
```

#### **main_daemon.py (Dynamic System)**
```python
#!/usr/bin/env python3
"""
E-Paper Weather Daemon - Kontinuerlig väderstation med DYNAMIC MODULE SYSTEM
AVANCERAT SYSTEM: Kör kontinuerligt som daemon
"""

# EGENSKAPER:
# ✅ Kontinuerlig process (daemon)
# ✅ Dynamic Module System med triggers
# ✅ ModuleFactory + renderer pattern
# ✅ Intelligent layout-växling
# ✅ Robust felhantering
# ❌ Mer komplext att felsöka
# ❌ Kräver renderer-implementation för alla moduler

def render_and_display(self, weather_data):
    """DYNAMIC RENDERING - via trigger evaluation"""
    # Bygg trigger context
    trigger_context = self.module_manager.build_trigger_context(weather_data)
    
    # Hämta aktiva moduler baserat på triggers
    active_modules = self.module_manager.get_active_modules(trigger_context)
    
    # Rendera via ModuleFactory
    for module_name in active_modules:
        renderer = self.module_factory.create_renderer(module_name)
        renderer.render(x, y, width, height, weather_data, trigger_context)
```

### **Funktionalitetsjämförelse**

| Feature | main.py (Legacy) | main_daemon.py (Dynamic) |
|---------|------------------|---------------------------|
| **Körning** | En gång och avslutar | Kontinuerlig daemon |
| **Modulaktivering** | enabled: true/false | triggers + module_groups + fallback |
| **Nederbörd-växling** | ❌ Manuell endast | ✅ Automatisk |
| **Wind-implementation** | ⚠️ Kräver hårdkodning | ✅ Via WindRenderer |
| **Komplexitet** | Enkel | Avancerad |
| **Stabilitet** | Mycket stabil | Stabil (när korrekt setup) |
| **Uppgradering** | Svår att utöka | Lätt att lägga till moduler |

### **Vilken Används Aktivt?**

```bash
# Kontrollera vilket skript som körs:
ps aux | grep python | grep -E "(main\.py|main_daemon\.py)"

# Om main_daemon.py körs som systemd service:
sudo systemctl status epaper-weather

# Om main.py körs via cron:
crontab -l | grep main.py
```

### **Systemidentifiering & Växling**

#### **Avgöra Aktivt System**
```bash
# 1. Kontrollera körande processer
ps aux | grep python | grep epaper_weather

# 2. Kontrollera systemd service (daemon)
sudo systemctl is-active epaper-weather
# Resultat: "active" = main_daemon.py körs
# Resultat: "inactive" = ingen daemon körs

# 3. Kontrollera cron jobs (legacy)
crontab -l | grep main.py
# Om finns: main.py körs via cron

# 4. Analysera config.json
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)
    
has_triggers = bool(config.get('triggers', {}))
has_module_groups = bool(config.get('module_groups', {}))

if has_triggers and has_module_groups:
    print('🎯 DYNAMIC SYSTEM (main_daemon.py) - konfigurerad')
else:
    print('🔧 LEGACY SYSTEM (main.py) - konfigurerad')
"
```

#### **Växla mellan System**

##### **Aktivera main_daemon.py (Dynamic)**
```bash
# Stoppa eventuell main.py cron
crontab -l | grep -v main.py | crontab -

# Installera och starta daemon
sudo systemctl enable epaper-weather
sudo systemctl start epaper-weather

# Verifiera
sudo systemctl status epaper-weather
```

##### **Aktivera main.py (Legacy)**
```bash
# Stoppa daemon
sudo systemctl stop epaper-weather
sudo systemctl disable epaper-weather

# Lägg till cron job (var 5:e minut)
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /home/chris/epaper_weather && python3 main.py") | crontab -

# Verifiera
crontab -l
```

### **Modulimplementation i Olika System**

#### **Legacy (main.py) - Hårdkodad Rendering**
```python
def render_wind_module_legacy(self, x, y, width, height, weather_data):
    """HÅRDKODAD wind-rendering i main.py"""
    wind_speed = weather_data.get('wind_speed', 0)
    wind_direction = weather_data.get('wind_direction', 0)
    
    # Rita direkt på canvas
    self.draw.text((x + 20, y + 20), f"{wind_speed} m/s", 
                   font=self.fonts['medium_main'], fill=0)
    
    # Rita riktning
    direction_text = self.get_wind_direction_swedish(wind_direction)
    self.draw.text((x + 20, y + 60), direction_text,
                   font=self.fonts['small_desc'], fill=0)

# MÅSTE läggas till manuellt i render_weather_layout():
if self.config['modules']['wind_module']['enabled']:
    self.render_wind_module_legacy(x, y, width, height, weather_data)
```

#### **Dynamic (main_daemon.py) - Renderer Pattern**
```python
# WindRenderer finns redan - behöver bara registreras
class WindRenderer(ModuleRenderer):
    def render(self, x, y, width, height, weather_data, context_data):
        """MODULÄR wind-rendering via factory pattern"""
        # All logik finns redan i wind_renderer.py
        # Automatiskt använd när wind_module är aktiv
        
# I main_daemon.py - AUTOMATISK:
active_modules = self.module_manager.get_active_modules(trigger_context)
for module_name in active_modules:
    renderer = self.module_factory.create_renderer(module_name)  # ← Hämtar WindRenderer
    renderer.render(x, y, width, height, weather_data, trigger_context)
```

### **Rekommendationer per Use Case**

#### **Använd main.py (Legacy) Om:**
- ✅ Du vill **enkel, pålitlig** funktion
- ✅ Du vill **manuell kontroll** över alla moduler
- ✅ Du **inte behöver** automatisk växling
- ✅ Du är **osäker på** dynamic system-stabilitet

**Implementation:** Hårdkoda wind-rendering i main.py

#### **Använd main_daemon.py (Dynamic) Om:**
- ✅ Du vill **automatisk nederbörd-växling** (som nu)
- ✅ Du vill **intelligent trigger-system**
- ✅ Du vill **lätt lägga till** nya moduler framöver
- ✅ Du vill **modern arkitektur**

**Implementation:** Registrera WindRenderer i ModuleFactory

### **Hybrid Scenario (Aktuell Situation)**
```bash
# PROBLEM: main_daemon.py körs men wind_module inte registrerad
# SYMPTOM: Nederbörd-växling fungerar, wind-modul kraschar system

# LÖSNING: Registrera WindRenderer för main_daemon.py
# RESULTAT: Både nederbörd-växling OCH wind-modul fungerar
```

---

## 🏗️ Systemarkitektur

### **Två Parallella System**

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID MODULE SYSTEM                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │   MANUELL       │         │      DYNAMISK           │   │
│  │   AKTIVERING    │         │      VÄXLING            │   │
│  │                 │         │                         │   │
│  │ modules: {      │         │ module_groups: {        │   │
│  │   enabled: T/F  │   +     │   normal: [...]         │   │
│  │ }               │         │   special: [...]        │   │
│  │                 │         │ }                       │   │
│  │ FALLBACK        │         │ triggers: {             │   │
│  │ SYSTEM          │         │   condition: "..."      │   │
│  └─────────────────┘         │ }                       │   │
│                               │                         │   │
│                               │ INTELLIGENT             │   │
│                               │ SYSTEM                  │   │
│                               └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Manuell Aktivering (Legacy System)

### **Princip: enabled-flaggor**

```json
"modules": {
    "wind_module": {
        "enabled": true,              // ← MANUELL AKTIVERING
        "coords": {"x": 540, "y": 40}
    },
    "barometer_module": {
        "enabled": false             // ← MANUELL INAKTIVERING  
    }
}
```

### **Hur det fungerar**
1. **Systemet läser enabled-flaggor**
2. **Renderar ALLA moduler med enabled: true**
3. **Ignorerar moduler med enabled: false**
4. **Ingen intelligent växling** - statisk layout

### **Fördelar**
- ✅ **Enkelt och pålitligt**
- ✅ **Förutsägbart beteende**
- ✅ **Fungerar som fallback**

### **Nackdelar**
- ❌ **Ingen automatisering**
- ❌ **Manuell konfiguration krävs**
- ❌ **Moduler kan överlappa visuellt**

---

## 🎯 Dynamisk Växling (Intelligent System)

### **Princip: Trigger-baserade Module Groups**

```json
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

"triggers": {
    "precipitation_trigger": {
        "condition": "precipitation > 0 OR forecast_precipitation_2h >= 0.2",
        "target_section": "bottom_section",
        "activate_group": "precipitation_active",
        "priority": 100
    },
    "wind_trigger": {
        "condition": "wind_speed > 10.0",
        "target_section": "medium_right_section", 
        "activate_group": "wind_active",
        "priority": 80
    }
}
```

### **Hur det fungerar**

#### **Steg 1: Trigger Evaluation**
```python
# Varje uppdatering (60 sekunder):
for trigger in triggers:
    if evaluate_condition(trigger.condition, weather_data):
        activate_group(trigger.target_section, trigger.activate_group)
```

#### **Steg 2: Module Resolution**
```python
# För varje section:
active_modules = []
for section_name, active_group in active_groups.items():
    section_modules = module_groups[section_name][active_group]
    active_modules.extend(section_modules)
```

#### **Steg 3: Rendering**
```python
# Endast aktiva moduler renderas:
for module_name in active_modules:
    render_module(module_name)
```

## 🔍 Debugging & Felsökning

### **System-diagnostik**

#### **Vilken fil körs egentligen?**
```bash
# Fullständig process-analys
ps aux | grep python | grep -v grep

# Exempel output:
# chris 1234  0.1  2.3  python3 /home/chris/epaper_weather/main_daemon.py
# → main_daemon.py körs som process

# Om inget hittas:
sudo systemctl status epaper-weather  # Kontrollera daemon
crontab -l                            # Kontrollera cron
```

#### **Systemd Service Status (main_daemon.py)**
```bash
# Detaljerad service-info
sudo systemctl status epaper-weather --no-pager -l

# Exempel healthy output:
# ● epaper-weather.service - E-Paper Weather Display Daemon
#    Active: active (running) since Sun 2025-01-17 14:30:15 CET
#    Process: 1234 ExecStart=/usr/bin/python3 main_daemon.py

# Loggar från daemon
sudo journalctl -u epaper-weather -n 50 -f
```

#### **Config-system Analys**
```bash
# Analysera config för systemtyp
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)

# Räkna dynamic features
triggers = len([t for t in config.get('triggers', {}).keys() if not t.startswith('_')])
groups = len(config.get('module_groups', {}))
enabled_modules = len([m for m, c in config.get('modules', {}).items() if c.get('enabled')])

print(f'🎯 Triggers: {triggers}')
print(f'📊 Module Groups: {groups}') 
print(f'🔧 Enabled Modules: {enabled_modules}')

if triggers > 0 or groups > 0:
    print('→ KONFIGURERAD FÖR: main_daemon.py (dynamic)')
else:
    print('→ KONFIGURERAD FÖR: main.py (legacy)')
"
```

### **Vanliga Problem & Lösningar**

#### **Problem 1: "Modul visas inte trots enabled: true"**
```bash
# DIAGNOS: Vilket system körs?
ps aux | grep main_daemon  # Om detta ger resultat:

# → main_daemon.py körs men använder dynamic system
# → enabled-flaggor kan ignoreras om module_groups finns
# → LÖSNING: Använd triggers ELLER inaktivera module_groups

# Alternativ 1: Sätt modul i module_groups
"module_groups": {
    "medium_right_section": {
        "normal": ["wind_module"]  // ← LÄGG TILL HÄR
    }
}

# Alternativ 2: Växla till main.py
sudo systemctl stop epaper-weather
crontab -e  # Lägg till: */5 * * * * cd /path && python3 main.py
```

#### **Problem 2: "Nederbörd-växling slutade fungera"**
```bash
# DIAGNOS: main.py körs istället för main_daemon.py
ps aux | grep main.py  # Om detta ger resultat:

# → Legacy system har ingen trigger-logik
# → LÖSNING: Växla tillbaka till main_daemon.py

sudo systemctl start epaper-weather
crontab -l | grep -v main.py | crontab -  # Ta bort cron
```

#### **Problem 3: "System kraschar vid start"**
```bash
# DIAGNOS: ModuleFactory registrering saknas
tail -50 logs/weather_daemon.log | grep -i wind

# Typiska felmeddelanden:
# "❌ Fel vid renderer-skapande för wind_module"
# "No module named 'wind_renderer'"

# → LÖSNING: Registrera WindRenderer i ModuleFactory
# (Se huvudplanen för exakta steg)
```

#### **Problem 4: "Triggers aktiveras inte"**
```bash
# DIAGNOS: Context data eller condition problem
tail -50 logs/weather_daemon.log | grep -i trigger

# Exempel output:
# "🎯 Trigger inaktiv: wind_trigger"
# "⚠️ wind_speed värde: 6.5, tröskelvärde: 10.0"

# LÖSNING 1: Sänk tröskelvärde för test
"wind_trigger": {
    "condition": "wind_speed > 0.5"  // ← SÄNKT för test
}

# LÖSNING 2: Kontrollera weather_data
python3 -c "
from modules.weather_client import WeatherClient
import json
with open('config.json', 'r') as f:
    config = json.load(f)
    
client = WeatherClient(config)
data = client.get_combined_weather_data()
print(f'Wind speed: {data.get(\"wind_speed\", \"SAKNAS\")}')
print(f'Wind direction: {data.get(\"wind_direction\", \"SAKNAS\")}')
"
```

### **Live Debugging Commands**

#### **Realtid Trigger Monitoring**
```bash
# Övervaka trigger evaluation live
sudo journalctl -u epaper-weather -f | grep -E "(Trigger|aktiverad|inaktiv)"

# Exempel output:
# 14:35:22 🎯 Trigger inaktiv: wind_trigger  
# 14:35:22 🎯 Trigger aktiverad: precipitation_trigger → bottom_section.precipitation_active
# 14:35:22 📊 Section bottom_section: precipitation_active → [precipitation_module]
```

#### **Module Resolution Debugging**
```bash
# Se vilka moduler som faktiskt renderas
sudo journalctl -u epaper-weather -f | grep "Aktiva moduler"

# Exempel output:
# 🎯 Aktiva moduler: [main_weather, barometer_module, tomorrow_forecast, clock_module, status_module]
```

#### **Factory Registration Check**
```bash
# Kontrollera tillgängliga renderers
python3 -c "
from modules.renderers import ModuleFactory
from modules.icon_manager import WeatherIconManager

factory = ModuleFactory(WeatherIconManager(), {})
available = factory.get_available_renderers()
print('📋 Tillgängliga renderers:')
for module, renderer in available.items():
    print(f'  {module} → {renderer}')

if 'wind_module' in available:
    print('✅ WindRenderer registrerad korrekt')
else:
    print('❌ WindRenderer SAKNAS i factory')
"
```

---

### **Exempel 1: Nederbörd-växling (FUNGERAR)**

#### **Normal situation:**
```
Trigger: precipitation = 0, forecast_precipitation_2h = 0
→ precipitation_trigger: INAKTIV
→ bottom_section: "normal" 
→ Moduler: [clock_module, status_module]

Layout:
┌─────────────────┐  ┌─────────────────┐
│   🕐 13:45     │  │ ● Netatmo OK    │
│   📅 17 Aug    │  │ ● SMHI OK       │  
└─────────────────┘  └─────────────────┘
```

#### **När regn upptäcks:**
```
Trigger: precipitation = 1.2 mm/h
→ precipitation_trigger: AKTIV
→ bottom_section: "precipitation_active"
→ Moduler: [precipitation_module]

Layout:
┌───────────────────────────────────────┐
│ ⚠️  REGNAR NU                        │
│     Lätt intensitet                  │
└───────────────────────────────────────┘
```

#### **Efter regn:**
```
Trigger: precipitation = 0
→ precipitation_trigger: INAKTIV  
→ bottom_section: "normal"
→ Moduler: [clock_module, status_module]

(Återgår till normal layout automatiskt)
```

### **Exempel 2: Wind-växling (PLANERAD)**

#### **Normal situation:**
```
Trigger: wind_speed = 6.5 m/s (< 10.0)
→ wind_trigger: INAKTIV
→ medium_right_section: "normal"
→ Moduler: [barometer_module]

Layout:
┌─────────────────┐
│ 🌡️ 1018 hPa    │
│ ↗️ Stigande     │
└─────────────────┘
```

#### **Vid kraftig vind:**
```
Trigger: wind_speed = 12.3 m/s (> 10.0)  
→ wind_trigger: AKTIV
→ medium_right_section: "wind_active"
→ Moduler: [wind_module]

Layout:
┌─────────────────┐
│ 🌬️ 12.3 m/s    │
│ Frisk vind      │
│ NV (nordväst)   │
└─────────────────┘
```

---

## 🎮 Samspel mellan Systemen

### **Fallback-hierarki**

```python
def get_active_modules(self, context_data):
    # 1. FÖRSÖK: Dynamisk växling
    active_groups = self.evaluate_triggers(context_data)
    active_modules = self.resolve_modules_from_groups(active_groups)
    
    if active_modules:
        return active_modules  # ✅ Dynamic system fungerar
    
    # 2. FALLBACK: Manuell aktivering  
    if self.legacy_modules:
        legacy_active = [name for name, config in self.legacy_modules.items() 
                        if config.get('enabled', False)]
        return legacy_active   # ✅ Legacy system som backup
    
    # 3. NÖDFALLBACK: Tom lista
    return []
```

### **Konflikhantering**

#### **Priority-baserad resolution:**
```python
triggers_by_priority = sorted(triggers, key=lambda x: x['priority'], reverse=True)

# Högre priority vinner:
# precipitation_trigger: priority 100 (viktigast)
# wind_trigger: priority 80
# user_preference: priority 60
```

#### **Exempel - Prioritetskonflikt:**
```
Situation: Regnar OCH kraftig vind samtidigt

precipitation_trigger (priority 100): AKTIV → bottom_section = "precipitation_active"
wind_trigger (priority 80): AKTIV → medium_right_section = "wind_active"

Resultat:
┌───────────────────────────────────────┐ ← NEDERBÖRD (priority 100)
│ ⚠️  REGNAR NU - Kraftig intensitet   │
└───────────────────────────────────────┘
                              ┌─────────────────┐ ← VIND (priority 80)  
                              │ 🌬️ 13.2 m/s    │
                              │ Frisk vind      │
                              └─────────────────┘

Båda moduler visas - ingen konflikt eftersom de påverkar olika sections!
```

---

## 🛡️ Felsäkerhet & Robusthet

### **Graceful Degradation**

```python
# 1. Om trigger evaluation misslyckas:
try:
    active_groups = self.evaluate_triggers(context_data)
except Exception:
    # → Fallback till normal groups för alla sections
    active_groups = {section: 'normal' for section in self.module_groups.keys()}

# 2. Om dynamic system misslyckas helt:
try:
    return self.get_dynamic_modules(context_data)
except Exception:
    # → Fallback till legacy enabled-flaggor
    return self.get_legacy_modules()

# 3. Om även legacy misslyckas:
try:
    return self.get_legacy_modules()
except Exception:
    # → Nödfallback: grundmoduler
    return ['main_weather', 'clock_module']
```

### **Ingen Modul Förlorad**
- **Manuellt aktiverade moduler** renderas alltid (om enabled: true)
- **Dynamiska moduler** aktiveras endast vid triggers
- **Fallback säkerställer** att systemet aldrig blir helt blankt

---

## 🎯 Praktiska Strategier

### **Strategi A: "Ren Manuell" (Säker)**
```json
// Inaktivera alla triggers, använd endast enabled-flaggor
"triggers": {},  // Tom = ingen dynamisk växling
"modules": {
    "wind_module": {"enabled": true},
    "barometer_module": {"enabled": false}
}
```

### **Strategi B: "Hybrid" (Rekommenderad)**
```json
// Dynamisk växling för nederbörd, manuell för wind
"triggers": {
    "precipitation_trigger": {...}  // AKTIV
    // "wind_trigger": {...}        // INAKTIVERAD
},
"modules": {
    "wind_module": {"enabled": true},     // Manuell  
    "barometer_module": {"enabled": false} // Manuell
}
```

### **Strategi C: "Full Dynamisk" (Avancerad)**
```json
// Alla moduler styrs av triggers
"triggers": {
    "precipitation_trigger": {...},  // AKTIV
    "wind_trigger": {...}           // AKTIV  
},
"modules": {
    // enabled-flaggor ignoreras för moduler i groups
}
```

---

## 🔍 Debugging & Förståelse

### **Loggar att Övervaka**
```bash
# Trigger evaluation:
🎯 Trigger aktiverad: precipitation_trigger → bottom_section.precipitation_active

# Module resolution:  
📊 Section bottom_section: precipitation_active → [precipitation_module]

# Fallback användning:
🔄 Använder legacy modules (inga groups definierade)

# Aktiva moduler:
🎯 Aktiva moduler: [main_weather, precipitation_module, barometer_module]
```

### **Vanliga Problem & Lösningar**

| Problem | Orsak | Lösning |
|---------|-------|---------|
| Modul visas inte | enabled: false + ingen trigger | Sätt enabled: true ELLER aktivera trigger |
| Två moduler överlappar | Båda enabled: true | Inaktivera en eller använd dynamic växling |
| Trigger aktiveras inte | Felaktig condition | Kontrollera weather_data-värden |
| System "fastnar" i läge | Trigger evalueras inte | Restart daemon för reset |

---

## 💡 Design-filosofi

### **Flexibilitet med Säkerhet**
- **Default: Manuell aktivering** (förutsägbart)
- **Upgrade: Dynamisk växling** (intelligent)
- **Fallback: Alltid tillgängligt** (robust)

### **Ingen Single Point of Failure**
- Om dynamic system kraschar → legacy fungerar
- Om trigger misslyckas → normal groups används  
- Om modul saknas → graceful degradation

### **Evolutionär Utveckling**
1. **Start:** Alla moduler manuella (enabled: true/false)
2. **Utveckling:** Lägg till triggers en i taget
3. **Mål:** Intelligent, helautomatisk växling

---

*🎯 Detta system möjliggör både enkel manuell kontroll och avancerad automatisering - det bästa av båda världar.*
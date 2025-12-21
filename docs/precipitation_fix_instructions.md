# 🌧️ Precipitation Module Fix - Exakta instruktioner

## 🎯 PROBLEMANALYS
- ✅ Dynamic Module System fungerar (triggers aktiveras, moduler byts ut)
- ✅ PrecipitationRenderer finns i `modules/renderers/precipitation_renderer.py`
- ✅ ModuleFactory finns i `modules/renderers/module_factory.py`
- ❌ **PROBLEM:** `main_daemon.py` rad ~1103 har hårdkodad `elif precipitation_module` som bara ritar tomma ramar

## 🔍 IDENTIFIERAT PROBLEM
**Aktuell kod (rad 1103-1111 i main_daemon.py):**
```python
elif module_name == 'precipitation_module':
    # NYT: Samma stil som clock/status moduler
    self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
    self.draw.line([(x, y), (x, y + height)], fill=0, width=2)
    self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
    self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)
    self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
    self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)
    self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
    self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)
```

**Problem:** Bara ramar, inget innehåll!

## 🔧 EXAKT FIX

### Steg 1: Backup
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/precipitation_fix_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp main_daemon.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/main_daemon.py"
```

### Steg 2: Hitta exakt rad
```bash
grep -n "elif module_name == 'precipitation_module'" main_daemon.py
```

### Steg 3: Ersätt hela elif-sektionen
**Ersätt från:**
```python
elif module_name == 'precipitation_module':
    # NYT: Samma stil som clock/status moduler
    [ALLA DRAW.LINE KOMMANDON]
```

**Till:**
```python
elif module_name == 'precipitation_module':
    # DYNAMIC MODULE SYSTEM: Använd PrecipitationRenderer
    try:
        renderer = self.module_factory.create_renderer('precipitation_module')
        renderer.set_canvas(self.canvas, self.draw)
        context_data = self.build_trigger_context(weather_data)
        renderer.render(x, y, width, height, weather_data, context_data)
        self.logger.info(f"✅ {module_name} renderad via PrecipitationRenderer")
    except Exception as e:
        self.logger.error(f"❌ Fel vid {module_name} rendering: {e}")
        # Fallback: Tom ram med felmeddelande
        self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
        self.draw.text((x + 20, y + 30), "Nederbörd-data laddas...", 
                     font=self.fonts['small_desc'], fill=0)
```

### Steg 4: Kontrollera beroenden
**Se till att main_daemon.py har:**
```python
# I import-sektionen (överst):
from modules.renderers.module_factory import ModuleFactory

# I __init__ eller setup:
self.module_factory = ModuleFactory(self.icon_manager, self.fonts)

# build_trigger_context metod måste finnas
def build_trigger_context(self, weather_data):
    return {
        'precipitation': weather_data.get('precipitation', 0.0),
        'forecast_precipitation_2h': weather_data.get('cycling_weather', {}).get('precipitation_mm', 0.0),
        'temperature': weather_data.get('temperature', 20.0),
        'wind_speed': weather_data.get('wind_speed', 0.0)
    }
```

### Steg 5: Test
```bash
python3 restart.py
```

**Förväntade loggar:**
```
🎨 Skapad specifik renderer: PrecipitationRenderer
🌧️ Renderar nederbörd-modul (480×100)
✅ precipitation_module renderad via PrecipitationRenderer
```

## 🎯 FÖRVÄNTADE RESULTAT

**På E-Paper skärm (istället för tom ram):**
```
⚠️  Nederbörd detekterad
    Cykel-väder: OK (0.0mm/h)
    Inget regn
```

## 🔍 FELSÖKNING

**Om fortfarande tom ram:**
- Kontrollera att `modules/renderers/__init__.py` finns
- Kontrollera att import-sökvägar stämmer
- Kolla loggar för import-fel: `sudo journalctl -u epaper-weather -n 20`

**Om import-fel:**
- Verifiera att alla renderer-filer finns i `modules/renderers/`
- Kontrollera filrättigheter: `ls -la modules/renderers/`

## 🎉 SLUTRESULTAT
Dynamic Module System komplett fungerande med riktig PrecipitationRenderer som visar:
- Aktuell nederbörd-status
- Cykel-väder analys  
- Timing och intensitet
- Beslutsstöd för cykling
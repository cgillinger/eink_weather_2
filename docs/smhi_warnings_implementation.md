# SMHI Vädervarningar Implementation
**Teknisk specifikation för att implementera vädervarningar i E-Paper väderapp**

## 🎯 Projektmål

Utöka E-Paper väderappen med SMHI vädervarningar som automatiskt kombinerar datum- och status-modulerna när aktiva varningar finns för aktuell plats.

## 📋 Översikt

### Normal drift
- **Datummodul**: Kalender-ikon + veckodag + datum (240×100px)
- **Status-modul**: Status + uppdateringstid + datakällor (240×100px)

### Vid vädervarning
- **Kombinerad varningsmodul**: Täcker båda områdena (480×100px)
- Visar varningsnivå, typ, tid och kort beskrivning
- Färgkodad efter SMHI:s klassificering

## 🌩️ SMHI Vädervarnings-API

### API Endpoint
```
https://opendata-download-warnings.smhi.se/api/version/2/geotype/point/lon/{longitude}/lat/{latitude}/data.json
```

### Varningsnivåer
- **Klass 1 (Gul)**: Uppmärksamhet - Mindre risk
- **Klass 2 (Orange)**: Fara - Måttlig risk  
- **Klass 3 (Röd)**: Stor fara - Betydande risk

### Varningstyper (exempel)
- Kraftigt regn
- Snöfall
- Åska
- Stark vind
- Extrem temperatur
- Rimfrost
- Höga flöden

### API Response Format
```json
{
  "approvedTime": "2025-07-25T10:00:00.000Z",
  "referenceTime": "2025-07-25T12:00:00.000Z",
  "timeSeries": [
    {
      "validTime": "2025-07-25T14:00:00Z",
      "parameters": [
        {
          "name": "warn_id",
          "values": ["warning_id_123"]
        },
        {
          "name": "warn_cat", 
          "values": [2]  // Varningsnivå 1-3
        },
        {
          "name": "warn_text",
          "values": ["Kraftigt regn"]
        }
      ]
    }
  ]
}
```

## 🔧 Implementation Detaljer

### 1. Utöka weather_client.py

#### Ny metod för vädervarningar
```python
def get_smhi_warnings(self, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Hämta aktiva vädervarningar från SMHI
    
    Args:
        latitude: Latitud för platsen
        longitude: Longitud för platsen
        
    Returns:
        Dict med varningsdata eller tom dict
    """
    try:
        # API URL för vädervarningar
        url = f"https://opendata-download-warnings.smhi.se/api/version/2/geotype/point/lon/{longitude}/lat/{latitude}/data.json"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parsea aktiva varningar
        active_warnings = self.parse_smhi_warnings(data)
        
        return active_warnings
        
    except Exception as e:
        self.logger.error(f"❌ SMHI varnings-API fel: {e}")
        return {}

def parse_smhi_warnings(self, api_data: Dict) -> Dict[str, Any]:
    """
    Parsea SMHI varningsdata och hitta aktiva varningar
    
    Args:
        api_data: Rå API-data från SMHI
        
    Returns:
        Dict med parsade varningar
    """
    try:
        current_time = datetime.now(timezone.utc)
        active_warnings = []
        
        if 'timeSeries' not in api_data:
            return {}
        
        for forecast in api_data['timeSeries']:
            valid_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
            
            # Kontrollera om varningen är aktiv nu
            if valid_time <= current_time <= (valid_time + timedelta(hours=24)):
                
                warning_data = {}
                for param in forecast['parameters']:
                    if param['name'] == 'warn_cat' and param['values'][0] > 0:
                        warning_data['level'] = param['values'][0]
                    elif param['name'] == 'warn_text':
                        warning_data['text'] = param['values'][0]
                    elif param['name'] == 'warn_id':
                        warning_data['id'] = param['values'][0]
                
                if warning_data and 'level' in warning_data:
                    warning_data['valid_time'] = valid_time
                    active_warnings.append(warning_data)
        
        if active_warnings:
            # Returnera högsta varningsnivån om flera finns
            highest_warning = max(active_warnings, key=lambda x: x['level'])
            
            return {
                'active': True,
                'level': highest_warning['level'],
                'text': highest_warning['text'],
                'valid_time': highest_warning['valid_time'],
                'count': len(active_warnings),
                'all_warnings': active_warnings
            }
        
        return {'active': False}
        
    except Exception as e:
        self.logger.error(f"❌ Fel vid parsning av SMHI varningar: {e}")
        return {'active': False}
```

#### Uppdatera get_current_weather()
```python
def get_current_weather(self) -> Dict[str, Any]:
    """Hämta komplett väderdata från alla källor INKLUSIVE Netatmo sensorer + VÄDERVARNINGAR"""
    try:
        # Befintlig kod...
        smhi_data = self.get_smhi_data()
        netatmo_data = self.get_netatmo_data()
        sun_data = self.get_sun_data()
        
        # NYTT: Hämta vädervarningar
        warnings_data = self.get_smhi_warnings(self.latitude, self.longitude)
        
        # Kombinera data
        combined_data = self.combine_weather_data(smhi_data, netatmo_data, sun_data)
        
        # Lägg till varningsdata
        combined_data['warnings'] = warnings_data
        
        return combined_data
        
    except Exception as e:
        self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
        return self.get_fallback_data()
```

### 2. Uppdatera main.py

#### Ny metod för varningsmodul
```python
def render_warning_module(self, warnings_data: Dict, x: int, y: int, width: int, height: int):
    """
    Rendera kombinerad varningsmodul över båda små modulerna
    
    Args:
        warnings_data: Varningsdata från SMHI
        x, y: Position för modulen
        width, height: Storlek för kombinerad modul (480×100)
    """
    # Rita varningsram med färgkodning (simulerad med linjetjocklek)
    level = warnings_data.get('level', 1)
    
    if level == 3:
        # Klass 3 (Röd) - Stor fara: Tjock ram
        self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=4)
        self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=2)
        warning_prefix = "⚠️ STOR FARA"
    elif level == 2:
        # Klass 2 (Orange) - Fara: Medium ram
        self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=3)
        self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
        warning_prefix = "⚠️ FARA"
    else:
        # Klass 1 (Gul) - Uppmärksamhet: Normal ram
        self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
        warning_prefix = "⚠️ VÄDERVARNING"
    
    # Varningstext (rad 1)
    warning_title = f"{warning_prefix} - KLASS {level}"
    title_truncated = self.truncate_text(warning_title, self.fonts['small_main'], width - 20)
    self.draw.text((x + 10, y + 15), title_truncated, font=self.fonts['small_main'], fill=0)
    
    # Varningsttyp och tid (rad 2)
    warning_text = warnings_data.get('text', 'Okänd varning')
    valid_time = warnings_data.get('valid_time')
    
    if valid_time:
        time_str = valid_time.strftime('%H:%M')
        detail_text = f"{warning_text} från {time_str}"
    else:
        detail_text = warning_text
    
    detail_truncated = self.truncate_text(detail_text, self.fonts['small_desc'], width - 20)
    self.draw.text((x + 10, y + 45), detail_truncated, font=self.fonts['small_desc'], fill=0)
    
    # Antal varningar om flera (rad 3)
    warning_count = warnings_data.get('count', 1)
    if warning_count > 1:
        count_text = f"{warning_count} aktiva varningar"
        self.draw.text((x + 10, y + 70), count_text, font=self.fonts['tiny'], fill=0)
    else:
        # Uppdateringstid istället
        update_time = datetime.now().strftime('%H:%M')
        update_text = f"Uppdaterat: {update_time}"
        self.draw.text((x + 10, y + 70), update_text, font=self.fonts['tiny'], fill=0)

def should_show_warnings(self, warnings_data: Dict) -> bool:
    """
    Bestäm om varningar ska visas baserat på tid och relevans
    
    Args:
        warnings_data: Varningsdata från SMHI
        
    Returns:
        True om varningar ska visas
    """
    if not warnings_data or not warnings_data.get('active', False):
        return False
    
    # Kontrollera om varningen fortfarande är relevant
    valid_time = warnings_data.get('valid_time')
    if valid_time:
        current_time = datetime.now(timezone.utc)
        # Visa varningar upp till 6 timmar efter att de utfärdats
        expiry_time = valid_time + timedelta(hours=6)
        
        if current_time > expiry_time:
            self.logger.info(f"🕐 Vädervarning utgången: {valid_time}")
            return False
    
    # Visa endast varningar av nivå 2 och 3 (orange/röd)
    # Nivå 1 (gul) visas bara under arbetstid 07:00-21:00
    level = warnings_data.get('level', 1)
    current_hour = datetime.now().hour
    
    if level >= 2:
        return True  # Alltid visa orange/röd
    elif level == 1 and 7 <= current_hour <= 21:
        return True  # Visa gul bara under dagen
    else:
        return False
```

#### Uppdatera render_weather_layout()
```python
def render_weather_layout(self):
    """Rendera layout med Netatmo + SMHI + ikoner + exakta soltider + VÄDERVARNINGAR"""
    self.clear_canvas()
    
    # Hämta väderdata (nu inklusive varningar)
    weather_data = self.weather_client.get_current_weather()
    warnings_data = weather_data.get('warnings', {})
    
    # Parsea exakta soltider
    sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)
    current_time = datetime.now()
    
    # Rita alla moduler enligt konfiguration
    modules = self.config['modules']
    
    for module_name, module_config in modules.items():
        if module_config['enabled']:
            x = module_config['coords']['x']
            y = module_config['coords']['y'] 
            width = module_config['size']['width']
            height = module_config['size']['height']
            
            # VÄDERVARNINGS-LOGIK: Skippa små moduler om varningar ska visas
            if self.should_show_warnings(warnings_data) and module_name in ['clock_module', 'status_module']:
                # Skippa individuella moduler, rita kombinerad varningsmodul istället
                if module_name == 'clock_module':  # Rita bara en gång
                    combined_width = 480  # Båda modulernas bredd
                    self.render_warning_module(warnings_data, x, y, combined_width, height)
                continue
            
            # Rita normal modul
            self.draw_module_border(x, y, width, height, module_name)
            
            # Befintlig modul-rendering kod...
            if module_name == 'main_weather':
                # Befintlig main_weather kod...
                pass
            elif module_name == 'barometer_module':
                # Befintlig barometer kod...
                pass
            elif module_name == 'tomorrow_forecast':
                # Befintlig tomorrow kod...
                pass
            elif module_name == 'clock_module':
                # Befintlig datum-modul kod...
                pass
            elif module_name == 'status_module':
                # Befintlig status-modul kod...
                pass
    
    self.logger.info("🎨 Layout renderad med vädervarningar")
```

### 3. Konfigurationsändringar

#### Lägg till i config.json
```json
{
  "warnings": {
    "enabled": true,
    "show_level_1": true,
    "show_level_1_hours": [7, 21],
    "cache_duration_minutes": 30,
    "expiry_hours": 6
  },
  "update_intervals": {
    "warnings_seconds": 1800
  }
}
```

### 4. Avpubliceringslogik

#### Automatisk avpublicering
- **Tidsbaserad**: Varningar försvinner automatiskt 6 timmar efter utfärdande
- **Nivåbaserad**: Gula varningar (nivå 1) visas bara 07:00-21:00
- **API-baserad**: Om SMHI tar bort varningen från API:et
- **Cache-hantering**: Gammal varningsdata rensas vid nästa API-anrop

#### Cache för vädervarningar
```python
def cache_warnings_data(self, warnings_data: Dict):
    """Cacha varningsdata för att undvika API spam"""
    cache_file = "cache/warnings_cache.json"
    cache_data = {
        'warnings': warnings_data,
        'timestamp': time.time(),
        'expires_at': time.time() + (30 * 60)  # 30 min cache
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, default=str)
```

## 🧪 Testning

### Test-scenarion
1. **Ingen varning**: Normal datum + status-visning
2. **Gul varning (dag)**: Kombinerad modul visas
3. **Gul varning (natt)**: Normal visning (gul visas ej nattetid)
4. **Orange varning**: Kombinerad modul med medium ram
5. **Röd varning**: Kombinerad modul med tjock ram
6. **Flera varningar**: Högsta nivån prioriteras
7. **Utgången varning**: Återgår till normal visning

### Debugging
```python
# Lägg till i weather_client.py för testning
def test_warnings_system(self):
    """Test-funktion för vädervarningar"""
    print("🧪 Testar SMHI vädervarnings-system...")
    
    warnings = self.get_smhi_warnings(59.3293, 18.0686)  # Stockholm
    
    if warnings.get('active'):
        print(f"⚠️ Aktiv varning:")
        print(f"  Nivå: {warnings['level']}")
        print(f"  Text: {warnings['text']}")
        print(f"  Tid: {warnings['valid_time']}")
        print(f"  Antal: {warnings['count']}")
    else:
        print("✅ Inga aktiva varningar")
    
    return warnings
```

## 🚀 Implementation Order

1. **Steg 1**: Utöka weather_client.py med warning-funktioner
2. **Steg 2**: Testa API-anrop och parsning separat
3. **Steg 3**: Lägg till warning-logik i main.py
4. **Steg 4**: Implementera kombinerad modul-rendering
5. **Steg 5**: Konfigurera avpubliceringslogik
6. **Steg 6**: Testa alla varningsnivåer
7. **Steg 7**: Optimera cache och prestanda

## 📝 Kod-backup före implementation

```bash
# Skapa backup av befintliga filer
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/warnings_implementation_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp main.py "$BACKUP_DIR/"
cp modules/weather_client.py "$BACKUP_DIR/"
cp config.json "$BACKUP_DIR/"
echo "✅ Backup skapad: $BACKUP_DIR"
```

## 🎯 Förväntade resultat

- **Intelligent varningsvisning** som ersätter mindre viktig information vid behov
- **Automatisk prioritering** av säkerhetsinformation
- **Korrekt avpublicering** baserat på tid och relevans  
- **Minimal påverkan** på befintlig funktionalitet
- **Robust felhantering** om SMHI API är otillgängligt

## 📚 SMHI API Referenser

- **Vädervarningar**: https://opendata.smhi.se/apidocs/warnings/index.html
- **API Format**: JSON med timeSeries struktur
- **Uppdateringsfrekvens**: Var 30:e minut rekommenderat
- **Rate limiting**: Inga kända begränsningar för denna endpoint

---

*Denna specifikation ger all information som behövs för att implementera SMHI vädervarningar i en ny chatt.*
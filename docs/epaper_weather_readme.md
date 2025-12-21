# E-Paper Väderapp - Komplett Projekt
**Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480px)**

## 🏆 Projektöversikt

Komplett väderstation med E-Paper display som kombinerar lokala Netatmo-sensorer med SMHI väderdata och exakta soltider. Appen använder ett modulärt layout-system med högkvalitativa Weather Icons för professionell presentation.

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

**SMHI** (för prognoser och väderdata):
- 🌤️ **Aktuellt väder** (27 SMHI-symboler med dag/natt-varianter)
- 🌦️ **Morgondagens prognos** (temperatur + väder)
- 💨 **Vind och nederbörd**
- 📍 **Exakta geografiska data**

**ipgeolocation.io API** (exakta soltider):
- ☀️ **Soluppgång/solnedgång** (exakt tid för koordinater)
- ⏰ **Dagsljuslängd** (automatisk beräkning)
- 🌅 **Dag/natt-logik** för väderikoner

### Smart Datakombination
Appen använder **intelligent prioritering**:
1. **Netatmo** för lokala mätningar (temperatur, tryck)
2. **SMHI** för väderprognos och meteorologi
3. **API soltider** för exakt sol-information
4. **Fallback-system** vid API-fel

## 🏗️ Arkitektur och Moduler

### Katalogstruktur
```
~/epaper_weather/
├── main.py                    # Huvudapp + E-Paper rendering
├── config.json               # Modulkonfiguration + API-nycklar
├── modules/
│   ├── weather_client.py     # SMHI + Netatmo + SunCalculator
│   ├── icon_manager.py       # Weather Icons hantering
│   └── sun_calculator.py     # Exakta soltider (ipgeolocation.io)
├── icons/                    # Weather Icons PNG-bibliotek
│   ├── weather/              # 54 väderikoner (27×2 dag/natt)
│   ├── pressure/             # Compass-pilar (roterade från wi-wind-deg.svg)
│   ├── sun/                  # Sol-ikoner (sunrise/sunset)
│   └── system/               # System-ikoner (barometer, klocka, status)
├── screenshots/              # Automatiska PNG-screenshots
├── logs/                     # System-logging
├── cache/                    # API-cache + tryckhistorik
└── backup/                   # Automatiska säkerhetskopior
```

### Layout A - FOKUS (Implementerad)
**5 moduler, 720×400px arbetsyta:**

```
┌─────────────────────────┬─────────────┐
│ Stockholm               │ 1007 ↗️     │
│ 25.1°C ⛅              │ hPa         │
│ Lätta regnskurar       │ Stigande    │
│ (NETATMO)              │ (Netatmo)   │
│ 🌅 04:16  🌇 21:30    ├─────────────┤
│ Sol: API ✓             │ Imorgon ⛅  │
├─────────┬──────────────┤ 25.4°C      │
│ 🕰️ 12:07│ Status: ✅   │ Halvklart   │
│ Fre     │ Update: 12:07│ (SMHI)      │
│ 25/7    │ Data: Netatmo│             │
└─────────┴──────────────┴─────────────┘
```

**Moduler:**
- **HERO** (480×300px): Huvudtemperatur + väder + soltider
- **MEDIUM 1** (240×200px): Barometer + 3h-trycktrend
- **MEDIUM 2** (240×200px): Morgondagens väderprognos
- **SMALL 1** (240×100px): Klocka + datum
- **SMALL 2** (240×100px): System-status + datakällor

## 🎨 Ikonsystem - Weather Icons Integration

### SVG→PNG Konverteringssystem
Appen använder **högkvalitativa PNG-ikoner** konverterade från Weather Icons SVG-källor med E-Paper optimering.

**📁 IKON-KÄLLOR:**
- **SVG-källa**: `\\EINK-WEATHER\downloads\weather-icons-master\svg\` (Windows-delning)
- **PNG-destination**: `~/epaper_weather/icons/` (Raspberry Pi)
- **Konvertering**: Via `convert_svg_to_png.py` i virtuell miljö med cairosvg

**🔄 KONVERTERINGSPROCESS:**
1. SVG-filer läses från Windows-delad mapp
2. Konverteras med smart rotation och E-Paper optimering  
3. Sparas som optimerade PNG-filer i rätt storlekar
4. Cachas i icon_manager för snabb åtkomst

#### Ikon-kategorier och Storlekar

**🌤️ WEATHER-IKONER (54 stycken)**
- **Källa**: Erik Flowers Weather Icons
- **Mappning**: Exakt SMHI-symbol → Weather Icons (samma som Väderdisplayens utils.py)
- **Dag/Natt**: Automatisk väljning baserat på soltider
- **Storlekar**: 32×32 (prognos), 48×48 (standard), 96×96 (HERO)
- **Exempel**: wi-day-cloudy.png, wi-night-rain.png, wi-thunderstorm.png

**🧭 PRESSURE-PILAR (Smart Rotation)**
- **Källa**: wi-wind-deg.svg (enda SVG-fil)
- **Smart rotation**: 315° (rising), 135° (falling), 90° (stable)
- **Resultat**: 3 compass-pilar med ringar (meteorologisk standard)
- **Storlekar**: 20×20, 56×56, 64×64 (optimal), 96×96, 120×120
- **Filer**: wi-direction-up.png, wi-direction-down.png, wi-direction-right.png

**☀️ SOL-IKONER**
- **Källa**: wi-sunrise.svg, wi-sunset.svg
- **Storlekar**: 24×24, 40×40 (standard), 56×56, 80×80
- **Användning**: Exakta soltider i HERO-modulen

**📊 SYSTEM-IKONER**
- **Barometer**: wi-barometer.svg → olika storlekar (12-96px)
- **Klocka**: wi-time-7.svg → 32×32 (optimal synlighet)
- **Status**: wi-day-sunny.svg (OK), wi-refresh.svg (update)

#### Ikonsystem-begränsningar

**SVG→PNG Process:**
1. **convert_svg_to_png.py** konverterar från weather-icons-master/svg/
2. **E-Paper optimering**: Kontrast 2.0-2.5, sharpness 1.3-1.6, Floyd-Steinberg dithering
3. **Smart rotation**: wi-wind-deg.svg roteras automatiskt för pressure-pilar
4. **Storlek-mappning**: Varje ikon skapas i flera storlekar

**Begränsningar:**
- **Bas-fil krav**: icon_manager.py förväntar sig bas-filer utan storlekssuffix (wi-time-7.png)
- **SVG-availability**: Begränsad till ikoner som finns i Weather Icons-biblioteket
- **Manual fixes**: wi-towards-X-deg fanns inte → smart rotation av wi-wind-deg.svg lösning
- **Cache-hantering**: Ikoner cachas i minnet för prestanda

**Fallback-system:**
- Saknade ikoner → fallback-generering med text
- API-fel → cached data eller statiska värden
- SVG-konverteringsfel → befintliga PNG-filer behålls

## ⚙️ Konfiguration (config.json)

### API-nycklar
```json
{
  "api_keys": {
    "netatmo": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET", 
      "refresh_token": "YOUR_REFRESH_TOKEN"
    }
  }
}
```

### Plats-konfiguration
```json
{
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686
  }
}
```

### Modul-aktivering
```json
{
  "modules": {
    "main_weather": {"enabled": true, "position": "hero"},
    "barometer_module": {"enabled": true, "position": "medium_1"},
    "tomorrow_forecast": {"enabled": true, "position": "medium_2"},
    "clock_module": {"enabled": true, "position": "small_1"},
    "status_module": {"enabled": true, "position": "small_2"}
  }
}
```

## 🚀 Installation och Användning

### Förutsättningar
```bash
# SPI aktiverat för E-Paper
sudo raspi-config
# → Interfacing Options → SPI → Enable

# Waveshare E-Paper bibliotek installerat
# (specifik för Waveshare 4.26" HAT)
```

### Daglig körning
```bash
# Grundläggande användning
cd ~/epaper_weather
python3 main.py

# Screenshots sparas automatiskt i screenshots/
# Loggar i logs/weather.log
```

### Utveckling och underhåll
```bash
# Testa ikon-system
cd modules && python3 icon_manager.py

# Konvertera nya ikoner från SVG
source .venv/bin/activate
python3 convert_svg_to_png.py
deactivate

# Visa cache-statistik
python3 -c "from modules.weather_client import WeatherClient; WeatherClient({}).get_cache_stats()"
```

## 📈 Prestanda och Optimering

### Prestanda-mål (Uppnådda)
- **Total rendering**: Under 5 sekunder (inklusive API-anrop)
- **E-Paper uppdatering**: Under 10 sekunder total
- **Ikon-laddning**: Under 1 sekund (lokal cache)
- **Minnesanvändning**: Under 100MB RAM
- **API-anrop**: Cached (SMHI 30min, Netatmo 10min, Soltider 4h)

### E-Paper Optimeringar
- **1-bit rendering**: Floyd-Steinberg dithering för bästa kvalitet
- **Kontrast-förbättring**: Dynamisk baserat på ikon-typ och storlek
- **Font-optimering**: DejaVu Sans för E-Paper läsbarhet
- **Smart modulramar**: Undviker dubblering mellan angränsande moduler

## 🛡️ Fel-hantering och Robusthet

### API-fel Hantering
- **Netatmo API-fel**: Fallback till SMHI-data + cached Netatmo
- **SMHI API-fel**: Använd cached data + grundläggande väderinfo
- **Soltider API-fel**: Förenklad solberäkning baserat på koordinater
- **Display-fel**: Fortsätt med screenshot-generering för debugging

### Data-validering
- **3-timmars trycktrend**: Kräver minimum 1.5h data för giltighet
- **Sensor-ålder**: Varnar om Netatmo-data >30 min gammal
- **Koordinat-validering**: Kontrollerar rimliga lat/long värden
- **Text-trunkering**: Säkerställer att text får plats i moduler

## 🔄 Uppdateringsintervaller

### API-anrop Frekvens
- **Netatmo**: Var 10:e minut (mer aktuell lokaldata)
- **SMHI**: Var 30:e minut (prognosdata ändras sällan)
- **Soltider**: Var 4:e timme (ändras långsamt)
- **E-Paper**: Var 5:e minut (eller vid signifikant dataändring)

### Cache-strategi
- **Tryckhistorik**: 24h rullande för trend-analys
- **API-cache**: JSON-filer med timestamp-validering
- **Ikon-cache**: I minnet under körning
- **Backup-system**: Automatiska säkerhetskopior vid alla ändringar

## 🎯 Framtida Förbättringar

### Potentiella tillägg
- **Layout B & C**: Fler modul-konfigurationer
- **Växlingsmoduler**: barometer_module ↔ sun_module toggle
- **Användarvänlig konfiguration**: Web-interface för settings
- **Historiska grafer**: Visuell trend-presentation
- **Fler ikonstorlekar**: 128×128, 144×144 för framtida moduler

### Tekniska optimeringar
- **Partiell uppdatering**: Endast ändrade moduler (kräver avancerat E-Paper stöd)
- **Asynkrona API-anrop**: Parallella calls för snabbare data-hämtning
- **Komprimerade screenshots**: Mindre filstorlek för backup
- **Automatisk ikon-konvertering**: Runtime SVG→PNG för nya ikoner

## 📚 Teknisk Dokumentation

### Kritiska filer för backup
- **main.py**: Huvudapp + rendering-logik
- **config.json**: Komplett konfiguration
- **modules/weather_client.py**: API-integration + datakombination
- **modules/icon_manager.py**: Ikon-hantering + E-Paper optimering
- **modules/sun_calculator.py**: Exakta soltider + cache

### Beroenden
- **PIL (Pillow)**: Bildbehandling + E-Paper rendering
- **requests**: API-anrop (SMHI, Netatmo, ipgeolocation.io)
- **cairosvg**: SVG→PNG konvertering (virtuell miljö)
- **waveshare_epd**: E-Paper HAT drivrutiner

### Utvecklingsverktyg
- **convert_svg_to_png.py**: SVG→PNG batch-konvertering
- **screenshot.py**: Standalone screenshot-generering
- **backup-system**: Automatisk versionhantering av alla ändringar

---

## 🏆 Slutresultat

**Komplett, professionell väderstation** som kombinerar:
- 🏠 **Lokala sensorer** (Netatmo utomhus/inomhus)
- 🌍 **Meteorologisk data** (SMHI prognoser)
- ⭐ **Exakt astronomi** (API-baserade soltider)  
- 🎨 **Högkvalitativa ikoner** (Weather Icons SVG→PNG)
- 📱 **E-Paper optimering** (1-bit, kontrast, cache)

**Resultat**: Kristallklar, läsbar väderstation med meteorologisk precision och professionellt utseende på E-Paper display.

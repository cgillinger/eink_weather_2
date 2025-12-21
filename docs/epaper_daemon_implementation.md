# E-Paper Weather Daemon - Komplett Implementation

## 🎯 Projektöversikt

Konvertering från cron-baserat script till kontinuerlig daemon för E-Paper väderstation. Löser fundamentala problem med tillståndshantering och onödiga uppdateringar.

## 🏗️ Arkitekturell förändring

### Före (Cron-baserat):
```
Varje minut: python3 main.py
├── Ny process (inget minne från föregående körning)
├── Läs cache-fil från disk för att gissa vad som visas
├── Hämta väderdata
├── Jämför mot osäker cache
├── Uppdatera skärm (eller inte?)
└── Avsluta process
```

### Efter (Daemon):
```
En kontinuerlig process:
├── Starta daemon
├── while True:
│   ├── Hämta väderdata
│   ├── Jämför mot känd state i minnet
│   ├── Uppdatera endast vid verklig förändring
│   ├── Uppdatera state i minnet
│   └── sleep(60)
```

## 📁 Filstruktur

```
~/epaper_weather/
├── main_daemon.py          # Ny daemon-version
├── main.py                 # Gammal cron-version (behålls som backup)
├── systemd/
│   └── epaper-weather.service  # Systemd service-fil
├── install_daemon.sh       # Installation script
└── [övriga filer oförändrade]
```

## 🚀 Daemon Implementation

### main_daemon.py
```python
#!/usr/bin/env python3
"""
E-Paper Weather Daemon - Kontinuerlig väderstation
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)

DAEMON VERSION: 
- Kontinuerlig process istället för cron
- State i minnet för perfekt jämförelse
- Minimal E-Paper slitage
- Robust felhantering
"""

import sys
import os
import json
import time
import signal
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont

# Lägg till projektets moduler
sys.path.append('modules')
sys.path.append(os.path.join(os.path.dirname(__file__), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib'))

from weather_client import WeatherClient
from icon_manager import WeatherIconManager

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    sys.exit(1)

class EPaperWeatherDaemon:
    """E-Paper Weather Daemon - Kontinuerlig väderstation"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera daemon"""
        self.running = True
        self.current_display_state = None  # STATE I MINNET!
        self.last_update_time = 0
        self.update_interval = 60  # 1 minut
        self.watchdog_interval = 30 * 60  # 30 minuter
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
        
        # Setup logging för daemon
        self.setup_logging()
        
        # Initialisera komponenter
        self.weather_client = WeatherClient(self.config)
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")
        
        # Initialisera E-Paper display
        self.epd = None
        self.init_display()
        
        # Canvas setup
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)
        self.draw = ImageDraw.Draw(self.canvas)
        
        # Ladda typsnitt
        self.fonts = self.load_fonts()
        
        # Setup signal handlers för graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.logger.info("🌤️ E-Paper Weather Daemon initialiserad")
    
    def signal_handler(self, signum, frame):
        """Hantera shutdown signals"""
        self.logger.info(f"📶 Signal {signum} mottagen - avslutar daemon...")
        self.running = False
    
    def load_config(self, config_path):
        """Ladda JSON-konfiguration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Kan inte ladda konfiguration: {e}")
            return None
    
    def setup_logging(self):
        """Konfigurera logging för daemon"""
        log_level = getattr(logging, self.config['debug']['log_level'], logging.INFO)
        
        # Skapa logs-mapp om den inte finns
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/weather_daemon.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_display(self):
        """Initialisera E-Paper display"""
        try:
            self.logger.info("📱 Initialiserar E-Paper display...")
            self.epd = epd4in26.EPD()
            self.epd.init()
            self.epd.Clear()
            self.logger.info("✅ E-Paper display redo för daemon")
        except Exception as e:
            self.logger.error(f"❌ E-Paper display-fel: {e}")
            if not self.config['debug']['test_mode']:
                sys.exit(1)
    
    def load_fonts(self):
        """Ladda typsnitt"""
        fonts = {}
        font_path = self.config['display']['font_path']
        font_sizes = self.config['fonts']
        
        try:
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.truetype(font_path, size)
            self.logger.info(f"✅ {len(fonts)} typsnitt laddade")
        except Exception as e:
            self.logger.warning(f"⚠️ Typsnitt-fel: {e}, använder default")
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.load_default()
        
        return fonts
    
    def should_update_display(self, new_data: Dict) -> tuple:
        """
        DAEMON STATE JÄMFÖRELSE - i minnet, inte fil!
        
        Args:
            new_data: Ny väderdata
            
        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            # FÖRSTA KÖRNINGEN: Alltid uppdatera
            if self.current_display_state is None:
                return True, "Daemon första körning"
            
            # WATCHDOG: 30-minuters säkerhetsuppdatering
            time_since_last = time.time() - self.last_update_time
            if time_since_last > self.watchdog_interval:
                return True, f"30-min watchdog ({time_since_last/60:.1f} min)"
            
            # DATUM-ÄNDRING: Uppdatera vid midnatt
            current_date = datetime.now().strftime('%Y-%m-%d')
            last_date = self.current_display_state.get('date', '')
            if current_date != last_date:
                return True, f"Nytt datum: {last_date} → {current_date}"
            
            # JÄMFÖR VIKTIGA VÄDERDATA (exakt som cache-versionen)
            comparisons = [
                ('temperature', new_data.get('temperature'), 'Temperatur'),
                ('weather_symbol', new_data.get('weather_symbol'), 'Väderikon'),
                ('weather_description', new_data.get('weather_description'), 'Väderbeskrivning'),
                ('pressure', new_data.get('pressure'), 'Lufttryck'),
                ('pressure_trend_text', new_data.get('pressure_trend_text'), 'Trycktrend text'),
                ('pressure_trend_arrow', new_data.get('pressure_trend_arrow'), 'Trycktrend pil'),
                ('tomorrow_temp', new_data.get('tomorrow', {}).get('temperature'), 'Imorgon temperatur'),
                ('tomorrow_symbol', new_data.get('tomorrow', {}).get('weather_symbol'), 'Imorgon väderikon'),
                ('tomorrow_desc', new_data.get('tomorrow', {}).get('weather_description'), 'Imorgon beskrivning'),
                ('sunrise', new_data.get('sun_data', {}).get('sunrise'), 'Soluppgång'),
                ('sunset', new_data.get('sun_data', {}).get('sunset'), 'Solnedgång'),
            ]
            
            for key, current_value, description in comparisons:
                last_value = self.current_display_state.get(key)
                
                # Numeriska värden med tolerans
                if key in ['temperature', 'pressure', 'tomorrow_temp']:
                    if current_value is not None and last_value is not None:
                        if abs(float(current_value) - float(last_value)) >= 0.1:
                            return True, f"{description}: {last_value} → {current_value}"
                else:
                    # Exakt jämförelse för strängar och heltal
                    if current_value != last_value:
                        return True, f"{description}: {last_value} → {current_value}"
            
            # INGEN FÖRÄNDRING
            return False, "Inga förändringar"
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid jämförelse: {e}")
            return True, f"Fel vid jämförelse: {e}"
    
    def fetch_weather_data(self) -> Dict:
        """Hämta väderdata"""
        try:
            self.logger.debug("🌐 Hämtar väderdata...")
            weather_data = self.weather_client.get_current_weather()
            
            # Lägg till datum för jämförelse
            weather_data['date'] = datetime.now().strftime('%Y-%m-%d')
            
            return weather_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            return {}
    
    def render_and_display(self, weather_data: Dict):
        """Rendera och visa på E-Paper display"""
        try:
            self.logger.info("🎨 Renderar ny layout...")
            
            # RENDER LOGIC - Copy från main.py render_weather_layout()
            # [Samma rendering-kod som i original main.py]
            # Detta blir en exakt kopia av render_weather_layout() metoden
            
            # Placeholder för nu - implementera fullständig rendering
            self.canvas = Image.new('1', (self.width, self.height), 255)
            self.draw = ImageDraw.Draw(self.canvas)
            
            # Enkel placeholder-rendering
            temp = weather_data.get('temperature', 20.0)
            location = weather_data.get('location', 'Stockholm')
            
            self.draw.text((50, 50), f"{location}", font=self.fonts['medium_desc'], fill=0)
            self.draw.text((50, 100), f"{temp:.1f}°C", font=self.fonts['hero_temp'], fill=0)
            self.draw.text((50, 200), f"Daemon: {datetime.now().strftime('%H:%M:%S')}", font=self.fonts['small_desc'], fill=0)
            
            # Visa på display
            if self.epd and not self.config['debug']['test_mode']:
                self.epd.display(self.epd.getbuffer(self.canvas))
                self.logger.info("✅ E-Paper display uppdaterad")
            else:
                self.logger.info("🧪 Test-läge: Display simulering")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering: {e}")
            raise
    
    def update_state(self, weather_data: Dict):
        """Uppdatera daemon state i minnet"""
        self.current_display_state = {
            'temperature': weather_data.get('temperature'),
            'weather_symbol': weather_data.get('weather_symbol'),
            'weather_description': weather_data.get('weather_description'),
            'pressure': weather_data.get('pressure'),
            'pressure_trend_text': weather_data.get('pressure_trend_text'),
            'pressure_trend_arrow': weather_data.get('pressure_trend_arrow'),
            'tomorrow_temp': weather_data.get('tomorrow', {}).get('temperature'),
            'tomorrow_symbol': weather_data.get('tomorrow', {}).get('weather_symbol'),
            'tomorrow_desc': weather_data.get('tomorrow', {}).get('weather_description'),
            'sunrise': weather_data.get('sun_data', {}).get('sunrise'),
            'sunset': weather_data.get('sun_data', {}).get('sunset'),
            'date': weather_data.get('date'),
            'last_update': time.time()
        }
        self.last_update_time = time.time()
    
    def run_daemon(self):
        """Huvudloop för daemon"""
        self.logger.info("🚀 Startar E-Paper Weather Daemon...")
        
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                self.logger.debug(f"🔄 Daemon iteration #{iteration}")
                
                try:
                    # Hämta väderdata
                    weather_data = self.fetch_weather_data()
                    
                    if weather_data:
                        # Avgör om uppdatering behövs
                        should_update, reason = self.should_update_display(weather_data)
                        
                        if should_update:
                            self.logger.info(f"🔄 UPPDATERAR E-Paper: {reason}")
                            
                            # Rendera och visa
                            self.render_and_display(weather_data)
                            
                            # Uppdatera state i minnet
                            self.update_state(weather_data)
                            
                        else:
                            self.logger.info(f"💤 BEHÅLLER skärm: {reason}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Fel i daemon iteration #{iteration}: {e}")
                
                # Vänta till nästa iteration
                if self.running:
                    time.sleep(self.update_interval)
        
        except KeyboardInterrupt:
            self.logger.info("⚠️ Daemon avbruten av användare")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup vid shutdown"""
        try:
            if self.epd:
                self.epd.sleep()
            
            if hasattr(self, 'icon_manager'):
                self.icon_manager.clear_cache()
            
            self.logger.info("🧹 Daemon cleanup genomförd")
        except Exception as e:
            self.logger.error(f"⚠️ Cleanup-fel: {e}")

def main():
    """Huvudfunktion för daemon"""
    daemon = None
    try:
        daemon = EPaperWeatherDaemon()
        daemon.run_daemon()
    except Exception as e:
        print(f"❌ Kritiskt daemon-fel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if daemon:
            daemon.cleanup()

if __name__ == "__main__":
    main()
```

## 🔧 Systemd Service

### systemd/epaper-weather.service
```ini
[Unit]
Description=E-Paper Weather Display Daemon
Documentation=https://github.com/your-repo/epaper-weather
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=chris
Group=chris
WorkingDirectory=/home/chris/epaper_weather
ExecStart=/usr/bin/python3 /home/chris/epaper_weather/main_daemon.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONPATH=/home/chris/epaper_weather
Environment=HOME=/home/chris

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## 📦 Installation Script

### install_daemon.sh
```bash
#!/bin/bash
# E-Paper Weather Daemon Installation

set -e

echo "🚀 Installerar E-Paper Weather Daemon..."

# Kontrollera att vi är i rätt katalog
if [ ! -f "main_daemon.py" ]; then
    echo "❌ main_daemon.py saknas. Kör från projektets root-katalog."
    exit 1
fi

# KRITISKT: Stoppa befintlig cron-job FÖRST
echo "🛑 STOPPAR BEFINTLIGT CRON-JOB..."
echo "   Detta är kritiskt - annars konkurrerar cron och daemon!"

# Backup aktuell crontab
crontab -l > crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "Ingen befintlig crontab"

# Visa nuvarande cron-jobs
echo "📋 Nuvarande cron-jobs:"
crontab -l 2>/dev/null || echo "   Ingen crontab installerad"

# Ta bort E-Paper weather cron-jobs
echo "🗑️ Tar bort E-Paper weather cron-jobs..."
crontab -l 2>/dev/null | grep -v "main.py" | grep -v "epaper" | grep -v "weather" | crontab - 2>/dev/null || true

# Bekräfta att cron stoppats
echo "✅ Cron-jobs efter rensning:"
crontab -l 2>/dev/null || echo "   Crontab helt rensad"

# Vänta lite för att säkerställa att inga cron-processer körs
echo "⏳ Väntar 5 sekunder för att säkerställa att cron-processer avslutas..."
sleep 5

# Kopiera systemd service
echo "📁 Installerar systemd service..."
sudo cp systemd/epaper-weather.service /etc/systemd/system/
sudo systemctl daemon-reload

# Aktivera service
echo "🔄 Aktiverar daemon..."
sudo systemctl enable epaper-weather.service

# Starta service
echo "▶️ Startar daemon..."
sudo systemctl start epaper-weather.service

# Visa status
echo "📊 Status:"
sudo systemctl status epaper-weather.service --no-pager -l

echo ""
echo "✅ Installation klar!"
echo ""
echo "🔧 Användbara kommandon:"
echo "  Status:   sudo systemctl status epaper-weather"
echo "  Starta:   sudo systemctl start epaper-weather"
echo "  Stoppa:   sudo systemctl stop epaper-weather"
echo "  Restart:  sudo systemctl restart epaper-weather"
echo "  Loggar:   sudo journalctl -u epaper-weather -f"
echo "  Avaktiv:  sudo systemctl disable epaper-weather"
```

## ⚠️ KONFLIKT-HANTERING: Cron vs Daemon

### 🚨 Kritisk Risk
Om både cron OCH daemon körs samtidigt:
- ❌ **E-Paper konflikter:** Två processer skriver till samma display
- ❌ **API-överbelastning:** Dubbla anrop till Netatmo/SMHI
- ❌ **Låsningar:** Hårdvaru-konflikter kan krascha system
- ❌ **Oförutsägbar bild:** Oklart vad som faktiskt visas

### 🔍 Konflikt-detektering
```bash
# Kontrollera om cron fortfarande är aktivt
echo "🔍 Letar efter cron-konflikter..."

# Visa cron-jobs som innehåller weather/epaper/main.py
crontab -l 2>/dev/null | grep -E "(weather|epaper|main\.py)" || echo "✅ Inga E-Paper cron-jobs"

# Kontrollera aktiva main.py-processer
ps aux | grep -E "python.*main\.py" | grep -v grep && echo "❌ VARNING: main.py-process upptäckt!" || echo "✅ Inga main.py-processer"

# Kontrollera daemon-status
sudo systemctl is-active epaper-weather >/dev/null && echo "✅ Daemon körs" || echo "❌ Daemon körs inte"
```

### 🛡️ Säker Migration Checklist
- [ ] **Backup crontab:** `crontab -l > backup.txt`
- [ ] **Stoppa cron:** Ta bort alla E-Paper entries
- [ ] **Verifiera:** Inga main.py-processer körs
- [ ] **Testa daemon:** Manuell körning fungerar
- [ ] **Installera service:** Systemd setup
- [ ] **Final kontroll:** Endast daemon körs

---

### ✅ State Management
- **Perfect state:** Vet exakt vad som visas på skärmen
- **Memory state:** Ingen risk för korrupt cache-fil
- **Kontinuitet:** Samma process hela tiden

### ✅ Performance  
- **Ingen process-overhead:** En process istället för 1440/dag
- **Snabbare startup:** Komponenter laddas en gång
- **Bättre caching:** Ikoner och fonts i minnet

### ✅ Tillförlitlighet
- **Robust error handling:** Fortsätter köra vid API-fel
- **Watchdog:** 30-min säkerhetsuppdatering
- **Graceful shutdown:** Proper cleanup vid restart

### ✅ Operativa fördelar
- **Systemd integration:** Auto-start vid boot
- **Proper logging:** Centraliserad via journald
- **Service management:** Standard Linux service-kommandon

## 🚀 Migration Plan

### ⚠️ KRITISK VARNING: Cron-konflikt
**STOPPA CRON FÖRST!** Annars får du både cron OCH daemon som konkurrerar om E-Paper displayen!

### Steg 1: Backup & Cron-kontroll
```bash
# Backup nuvarande setup
cp main.py main_cron_backup.py

# KRITISKT: Backup och visa nuvarande cron
crontab -l > crontab_backup_$(date +%Y%m%d_%H%M%S).txt
echo "📋 Nuvarande cron-jobs:"
crontab -l

# Kontrollera om E-Paper cron körs
ps aux | grep main.py | grep -v grep || echo "Inget main.py-process körs"
```

### Steg 2: Stoppa Cron FÖRE Implementation
```bash
# STOPPA CRON-JOB (obligatoriskt!)
crontab -l | grep -v "main.py" | grep -v "epaper" | crontab -

# Verifiera att cron stoppats
echo "✅ Cron efter rensning:"
crontab -l || echo "Crontab rensad"
```

### Steg 3: Implementation
1. Skapa `main_daemon.py` från artifakt
2. Kopiera fullständig rendering-logik från `main.py`
3. Skapa systemd service-fil
4. **Testa daemon manuellt INNAN systemd**

### Steg 4: Manuell Test (VIKTIGT)
```bash
# Testa daemon manuellt först
python3 main_daemon.py

# Låt köra 2-3 minuter, kolla att:
# - Första körningen uppdaterar skärmen
# - Andra körningen säger "inga förändringar"
# - Loggar ser bra ut
```

### Steg 5: Installation
```bash
chmod +x install_daemon.sh
./install_daemon.sh
```

### Steg 6: Verifiering
```bash
# Kontrollera att daemon körs
sudo systemctl status epaper-weather

# Följ loggar
sudo journalctl -u epaper-weather -f

# KRITISK KONTROLL: Inget cron-job körs längre
ps aux | grep main.py | grep -v grep || echo "✅ Inget main.py cron-process"
```

## 🔍 Nästa steg

1. **Fullständig rendering:** Kopiera alla rendering-metoder från main.py
2. **Testing:** Manuell test av daemon innan systemd
3. **Error handling:** Robust hantering av alla fel-scenarion
4. **Monitoring:** Loggar och status-rapportering
5. **Documentation:** Användarguide för daemon-management

---

**Daemon-versionen löser alla fundamentala problem med state-hantering och ger en mycket mer robust lösning för kontinuerlig E-Paper väderstation!** 🎯
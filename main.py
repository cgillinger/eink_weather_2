#!/usr/bin/env python3
"""
E-Paper Väderapp - Med riktiga väderdata från SMHI + Weather Icons + Exakta soltider + NETATMO
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)
KOMPLETT: Netatmo lokala sensorer + SMHI prognoser + exakta soltider
FIXED: Korrekt 3-timmars trycktrend med meteorologisk standard
UPDATED: Högupplösta SVG-baserade ikoner - eliminerar pixling
IMPROVED: Reboot-screenshots (endast första körning) + auto-cleanup + elegant datummodul
FIXED: Statusmodul med enkla prickar för bättre läsbarhet
NEW: Smart E-Paper uppdateringslogik - endast uppdatera vid förändring + 30-min watchdog
FIXED: Blank skärm-problem - separerad data-hämtning från rendering
"""

import sys
import os
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict
from PIL import Image, ImageDraw, ImageFont
import logging

# Lägg till Waveshare biblioteket i path.
# insert(0), inte append: projektroten (sys.path[0]) innehåller en stub av
# waveshare_epd som annars alltid vinner över den riktiga vendor-drivrutinen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib'))

# Lägg till modules-mappen
sys.path.append('modules')
from weather_client import WeatherClient
from icon_manager import WeatherIconManager

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    print("🔧 Kontrollera att E-Paper biblioteket är installerat korrekt")
    sys.exit(1)

class EPaperWeatherApp:
    """Huvudklass för E-Paper väderapp med Netatmo + SMHI + Weather Icons + exakta soltider"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera appen med konfiguration och ikon-hantering"""
        print("🌤️ E-Paper Väderapp med Netatmo + SMHI + Exakta soltider - Startar...")
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
            
        # Setup logging
        self.setup_logging()
        
        # NYTT: Cache för smart uppdateringslogik
        self.last_values_file = "cache/last_run_values.json"
        self.ensure_cache_directory()
        
        # Initialisera weather client (nu med full Netatmo + SunCalculator)
        self.weather_client = WeatherClient(self.config)
        
        # Initialisera ikon-hanterare
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")
        
        # Initialisera E-Paper display
        self.epd = None
        self.init_display()
        
        # Skapa canvas för rendering
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)  # Vit bakgrund
        self.draw = ImageDraw.Draw(self.canvas)
        
        # Ladda typsnitt
        self.fonts = self.load_fonts()
        
        print("✅ E-Paper Väderapp med Netatmo + exakta soltider + SMART UPPDATERING initialiserad!")
    
    def ensure_cache_directory(self):
        """Säkerställ att cache-mappen finns"""
        cache_dir = os.path.dirname(self.last_values_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            self.logger.info(f"📁 Skapade cache-mapp: {cache_dir}")
    
    def load_last_values(self) -> Dict:
        """
        Ladda senaste cachade värden för jämförelse
        
        Returns:
            Dict med senaste värden eller tom dict om ingen cache finns
        """
        try:
            if os.path.exists(self.last_values_file):
                with open(self.last_values_file, 'r', encoding='utf-8') as f:
                    last_values = json.load(f)
                
                self.logger.debug(f"📋 Laddade senaste värden från cache")
                return last_values
            else:
                self.logger.info(f"📋 Ingen cache hittades - första körningen")
                return {}
                
        except Exception as e:
            self.logger.error(f"❌ Fel vid läsning av cache: {e}")
            return {}
    
    def save_current_values(self, weather_data: Dict):
        """
        Spara aktuella värden för nästa jämförelse
        
        Args:
            weather_data: Komplett väderdata att cacha
        """
        try:
            # Extrahera ENDAST viktiga värden för jämförelse
            current_values = {
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
                'date': datetime.now().strftime('%Y-%m-%d'),  # Datum för midnatt-kontroll
                'last_display_update': time.time(),  # Timestamp för watchdog
                'cached_at': datetime.now().isoformat()
            }
            
            # Spara till cache-fil
            with open(self.last_values_file, 'w', encoding='utf-8') as f:
                json.dump(current_values, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"💾 Sparade aktuella värden till cache")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid sparande av cache: {e}")
    
    def should_update_display(self, weather_data: Dict, last_values: Dict) -> tuple:
        """
        Avgör om displayen behöver uppdateras baserat på dataförändringar
        
        Args:
            weather_data: Nya väderdata
            last_values: Senaste cachade värden
            
        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            if not last_values:
                return True, "Första körningen"
            
            # 30-MINUTERS WATCHDOG: Tvinga uppdatering oavsett
            last_display_update = last_values.get('last_display_update', 0)
            time_since_last_update = time.time() - last_display_update
            
            if time_since_last_update > (30 * 60):  # 30 minuter
                return True, f"30-min watchdog ({time_since_last_update/60:.1f} min sedan)"
            
            # DATUM-KONTROLL: Uppdatera vid midnatt (nytt datum)
            current_date = datetime.now().strftime('%Y-%m-%d')
            last_date = last_values.get('date')
            
            if current_date != last_date:
                return True, f"Nytt datum: {last_date} → {current_date}"
            
            # JÄMFÖR VIKTIGA VÄDERDATA
            comparisons = [
                ('temperature', weather_data.get('temperature'), 'Temperatur'),
                ('weather_symbol', weather_data.get('weather_symbol'), 'Väderikon'),
                ('weather_description', weather_data.get('weather_description'), 'Väderbeskrivning'),
                ('pressure', weather_data.get('pressure'), 'Lufttryck'),
                ('pressure_trend_text', weather_data.get('pressure_trend_text'), 'Trycktrend text'),
                ('pressure_trend_arrow', weather_data.get('pressure_trend_arrow'), 'Trycktrend pil'),
                ('tomorrow_temp', weather_data.get('tomorrow', {}).get('temperature'), 'Imorgon temperatur'),
                ('tomorrow_symbol', weather_data.get('tomorrow', {}).get('weather_symbol'), 'Imorgon väderikon'),
                ('tomorrow_desc', weather_data.get('tomorrow', {}).get('weather_description'), 'Imorgon beskrivning'),
                ('sunrise', weather_data.get('sun_data', {}).get('sunrise'), 'Soluppgång'),
                ('sunset', weather_data.get('sun_data', {}).get('sunset'), 'Solnedgång'),
            ]
            
            for key, current_value, description in comparisons:
                last_value = last_values.get(key)
                
                # Speciell hantering för numeriska värden (temperaturer, tryck)
                if key in ['temperature', 'pressure', 'tomorrow_temp']:
                    if current_value is not None and last_value is not None:
                        # Jämför med 0.1 tolerans för att undvika uppdatering vid små avrundningsfel
                        if abs(float(current_value) - float(last_value)) >= 0.1:
                            return True, f"{description}: {last_value} → {current_value}"
                else:
                    # Exakt jämförelse för strängar och heltal
                    if current_value != last_value:
                        return True, f"{description}: {last_value} → {current_value}"
            
            # INGEN FÖRÄNDRING DETEKTERAD
            self.logger.info(f"🔍 Ingen betydande förändring detekterad - behåller E-Paper skärm")
            return False, "Inga förändringar"
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid jämförelse av värden: {e}")
            # Vid fel, uppdatera ändå för säkerhets skull
            return True, f"Fel vid jämförelse: {e}"
    
    def fetch_weather_data(self) -> Dict:
        """
        NYTT: Hämta väderdata UTAN att rendera någonting
        Separerar data-hämtning från rendering för att fixa blank skärm-problemet
        
        Returns:
            Komplett väderdata från alla källor
        """
        try:
            self.logger.info("🌐 Hämtar väderdata från Netatmo + SMHI + exakta soltider...")
            
            # Hämta riktiga väderdata INKLUSIVE Netatmo sensorer
            weather_data = self.weather_client.get_current_weather()
            
            # Parsea exakta soltider från weather_client
            sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)
            
            # Lägg till parsade soltider i weather_data
            weather_data['parsed_sunrise'] = sunrise
            weather_data['parsed_sunset'] = sunset
            weather_data['parsed_sun_data'] = sun_data
            
            # Debug-logging
            temp_source = weather_data.get('temperature_source', 'unknown')
            pressure_source = weather_data.get('pressure_source', 'unknown')
            sources = weather_data.get('data_sources', [])
            
            self.logger.info(f"📊 Datakällor - Temp: {temp_source}, Tryck: {pressure_source}, Alla: {sources}")
            
            if 'sun_data' in weather_data:
                sun_info = weather_data['sun_data']
                self.logger.info(f"☀️ Soldata: {sunrise.strftime('%H:%M')}-{sunset.strftime('%H:%M')} ({sun_info.get('daylight_duration', 'N/A')}) från {sun_info.get('sun_source', 'unknown')}")
            
            return weather_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            # Returnera fallback-data
            return {
                'temperature': 20.0,
                'weather_description': 'Data ej tillgänglig',
                'pressure': 1013,
                'location': 'Okänd plats',
                'data_sources': ['fallback']
            }
    
    def load_config(self, config_path):
        """Ladda JSON-konfiguration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ Konfiguration laddad från {config_path}")
            return config
        except Exception as e:
            print(f"❌ Kan inte ladda konfiguration: {e}")
            return None
    
    def setup_logging(self):
        """Konfigurera logging"""
        log_level = getattr(logging, self.config['debug']['log_level'], logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/weather.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔧 Logging konfigurerat")
    
    def init_display(self):
        """Initialisera E-Paper display"""
        try:
            if getattr(epd4in26, 'IS_STUB', False) and not self.config['debug']['test_mode']:
                self.logger.error(
                    "❌ Stub-drivrutinen laddades istället för riktig Waveshare-drivrutin "
                    "- skärmen skulle aldrig uppdateras. Installera vendor-biblioteket i "
                    "e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd/"
                )
                sys.exit(1)
            self.logger.info("📱 Initialiserar E-Paper display...")
            self.epd = epd4in26.EPD()
            self.epd.init()
            # OBS: ingen epd.Clear() här - den blankade skärmen vid VARJE
            # cron-körning, även när smart-logiken sedan beslöt att inte rita
            # något (skärmen blev vit tills nästa faktiska uppdatering).
            # Clear görs nu i display_canvas() precis före en riktig uppdatering.
            self.logger.info("✅ E-Paper display redo")
        except Exception as e:
            self.logger.error(f"❌ E-Paper display-fel: {e}")
            if not self.config['debug']['test_mode']:
                sys.exit(1)
    
    def load_fonts(self):
        """Ladda typsnitt för olika moduler"""
        fonts = {}
        font_path = self.config['display']['font_path']
        font_sizes = self.config['fonts']
        
        try:
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.truetype(font_path, size)
            self.logger.info(f"✅ {len(fonts)} typsnitt laddade")
        except Exception as e:
            self.logger.warning(f"⚠️ Typsnitt-fel: {e}, använder default")
            # Fallback till default font
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.load_default()
        
        return fonts
    
    def clear_canvas(self):
        """Rensa canvas (vit bakgrund)"""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=255)
    
    def draw_module_border(self, x, y, width, height, module_name):
        """Rita smarta modulramar som inte dubbleras"""
        # Bara rita vissa sidor för att undvika dubblering
        if module_name == 'main_weather':
            # HERO: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'barometer_module':
            # MEDIUM 1: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'tomorrow_forecast':
            # MEDIUM 2: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'clock_module':
            # SMALL 1: Rita alla sidor utom höger (för att undvika dubblering med status_module)
            # Topp, vänster, botten
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)  # Topp
            self.draw.line([(x, y), (x, y + height)], fill=0, width=2)  # Vänster
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)  # Botten
            # Höger sida - tunnare för att inte konflikta
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=1)  # Höger (tunn)
            
            # Inre ram
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)  # Topp
            self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)  # Vänster
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)  # Botten
            
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'status_module':
            # SMALL 2: Rita alla sidor utom vänster (för att undvika dubblering med clock_module)
            # Topp, höger, botten
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)  # Topp
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)  # Höger
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)  # Botten
            # Vänster sida - tunnare för att inte konflikta
            self.draw.line([(x, y), (x, y + height)], fill=0, width=1)  # Vänster (tunn)
            
            # Inre ram
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)  # Topp
            self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)  # Höger
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)  # Botten
            
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
    
    def get_swedish_date(self, date_obj):
        """
        Konvertera datum till svenska veckodagar och månader
        
        Args:
            date_obj: datetime-objekt
            
        Returns:
            Formaterad svensk datumsträng
        """
        swedish_days = {
            'Monday': 'Måndag', 'Tuesday': 'Tisdag', 'Wednesday': 'Onsdag', 
            'Thursday': 'Torsdag', 'Friday': 'Fredag', 'Saturday': 'Lördag', 'Sunday': 'Söndag'
        }
        
        swedish_months = {
            1: 'Januari', 2: 'Februari', 3: 'Mars', 4: 'April', 5: 'Maj', 6: 'Juni',
            7: 'Juli', 8: 'Augusti', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'December'
        }
        
        english_day = date_obj.strftime('%A')
        swedish_day = swedish_days.get(english_day, english_day)
        
        day_num = date_obj.day
        month_num = date_obj.month
        swedish_month = swedish_months.get(month_num, str(month_num))
        
        return swedish_day, f"{day_num} {swedish_month}"
    
    def get_swedish_date_short(self, date_obj):
        """
        Kort svensk datumformat för kompakt visning
        
        Args:
            date_obj: datetime-objekt
            
        Returns:
            Kort formaterad svensk datumsträng
        """
        swedish_days_short = {
            'Monday': 'Mån', 'Tuesday': 'Tis', 'Wednesday': 'Ons', 
            'Thursday': 'Tor', 'Friday': 'Fre', 'Saturday': 'Lör', 'Sunday': 'Sön'
        }
        
        english_day = date_obj.strftime('%A')
        swedish_day = swedish_days_short.get(english_day, english_day[:3])
        
        day_num = date_obj.day
        month_num = date_obj.month
        
        return f"{swedish_day} {day_num}/{month_num}"
    
    def truncate_text(self, text, font, max_width):
        """Korta text så den får plats inom given bredd"""
        if not text:
            return text
            
        # Kontrollera om texten får plats som den är
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        # Förkorta ord för ord tills den får plats
        words = text.split()
        for i in range(len(words), 0, -1):
            truncated = ' '.join(words[:i])
            bbox = self.draw.textbbox((0, 0), truncated, font=font)
            truncated_width = bbox[2] - bbox[0]
            
            if truncated_width <= max_width:
                return truncated
        
        # Som sista utväg, returnera första ordet
        return words[0] if words else text
    
    def paste_icon_on_canvas(self, icon, x, y):
        """
        Sätt in ikon på canvas på given position
        
        Args:
            icon: PIL Image-objekt (1-bit) från icon_manager
            x, y: Position där ikon ska placeras
        """
        if icon is None:
            return
        
        try:
            # Sätt in ikon på canvas
            # För 1-bit bilder används paste med mask för transparens
            self.canvas.paste(icon, (x, y))
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid ikon-inplacering: {e}")
    
    def parse_sun_data_from_weather(self, weather_data: Dict) -> tuple:
        """
        Parsea soldata från weather_client och skapa soldata för ikon-manager
        
        Args:
            weather_data: Komplett väderdata från WeatherClient
            
        Returns:
            Tuple med (sunrise_datetime, sunset_datetime, sun_data_dict)
        """
        try:
            # Hämta soldata från weather_client
            sun_data = weather_data.get('sun_data', {})
            
            if not sun_data:
                self.logger.warning("⚠️ Ingen soldata från WeatherClient, använder fallback")
                # Fallback till nuvarande tid
                now = datetime.now()
                sunrise = now.replace(hour=6, minute=0, second=0)
                sunset = now.replace(hour=18, minute=0, second=0)
                return sunrise, sunset, {'sunrise': sunrise.isoformat(), 'sunset': sunset.isoformat()}
            
            # Parsea datetime-objekt eller ISO-strängar
            sunrise_time = sun_data.get('sunrise_time')
            sunset_time = sun_data.get('sunset_time')
            
            if not sunrise_time or not sunset_time:
                # Försök parsea från ISO-strängar
                sunrise_str = sun_data.get('sunrise')
                sunset_str = sun_data.get('sunset')
                
                if sunrise_str and sunset_str:
                    try:
                        sunrise_time = datetime.fromisoformat(sunrise_str.replace('Z', '+00:00'))
                        sunset_time = datetime.fromisoformat(sunset_str.replace('Z', '+00:00'))
                    except:
                        # Fallback
                        now = datetime.now()
                        sunrise_time = now.replace(hour=6, minute=0, second=0)
                        sunset_time = now.replace(hour=18, minute=0, second=0)
                else:
                    # Sista fallback
                    now = datetime.now()
                    sunrise_time = now.replace(hour=6, minute=0, second=0)
                    sunset_time = now.replace(hour=18, minute=0, second=0)
            
            # Skapa soldata-dict för ikon-manager
            parsed_sun_data = {
                'sunrise': sunrise_time.isoformat(),
                'sunset': sunset_time.isoformat(),
                'daylight_duration': sun_data.get('daylight_duration', 'N/A'),
                'source': sun_data.get('sun_source', 'unknown')
            }
            
            self.logger.info(f"☀️ Soldata parsead: {sunrise_time.strftime('%H:%M')} - {sunset_time.strftime('%H:%M')} (källa: {parsed_sun_data['source']})")
            
            return sunrise_time, sunset_time, parsed_sun_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av soldata: {e}")
            # Fallback
            now = datetime.now()
            sunrise = now.replace(hour=6, minute=0, second=0)
            sunset = now.replace(hour=18, minute=0, second=0)
            return sunrise, sunset, {'sunrise': sunrise.isoformat(), 'sunset': sunset.isoformat(), 'source': 'error_fallback'}
    
    def format_data_sources(self, weather_data: Dict) -> str:
        """
        NYTT: Formatera datakällor för status-modulen
        
        Args:
            weather_data: Väderdata med källor
            
        Returns:
            Formaterad sträng med datakällor
        """
        try:
            sources = []
            
            # Temperatur-källa
            temp_source = weather_data.get('temperature_source', '')
            if temp_source == 'netatmo':
                sources.append("Netatmo")
            elif temp_source == 'smhi':
                sources.append("SMHI")
            
            # Tryck-källa (om olika från temperatur)
            pressure_source = weather_data.get('pressure_source', '')
            if pressure_source == 'netatmo' and temp_source != 'netatmo':
                if 'Netatmo' not in sources:
                    sources.append("Netatmo")
            elif pressure_source == 'smhi' and temp_source != 'smhi':
                if 'SMHI' not in sources:
                    sources.append("SMHI")
            
            if not sources:
                return "fallback"
            
            return " + ".join(sources)
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid formatering av datakällor: {e}")
            return "unknown"
    
    def render_weather_layout(self, weather_data: Dict):
        """
        NYTT: Rendera layout MED redan hämtad väderdata
        Denna metod anropas BARA när displayen ska uppdateras
        
        Args:
            weather_data: Redan hämtad väderdata
        """
        try:
            self.logger.info("🎨 Renderar layout för E-Paper display...")
            
            # Rensa canvas BARA när vi faktiskt ska rendera
            self.clear_canvas()
            
            # Hämta parsade soltider från weather_data
            sunrise = weather_data.get('parsed_sunrise')
            sunset = weather_data.get('parsed_sunset')
            sun_data = weather_data.get('parsed_sun_data', {})
            
            # Aktuell tid för dag/natt-bestämning
            current_time = datetime.now()
            
            # Rita alla moduler enligt konfiguration
            modules = self.config['modules']
            
            for module_name, module_config in modules.items():
                if module_config['enabled']:
                    x = module_config['coords']['x']
                    y = module_config['coords']['y'] 
                    width = module_config['size']['width']
                    height = module_config['size']['height']
                    
                    # Rita smarta modulramar
                    self.draw_module_border(x, y, width, height, module_name)
                    
                    # Rita innehåll för varje modul MED NETATMO + SMHI DATA
                    if module_name == 'main_weather':
                        temp = weather_data.get('temperature', 20.0)
                        desc = weather_data.get('weather_description', 'Okänt väder')
                        temp_source = weather_data.get('temperature_source', 'fallback')
                        location = weather_data.get('location', 'Okänd plats')
                        smhi_symbol = weather_data.get('weather_symbol', 1)  # SMHI väder-symbol
                        
                        # Plats överst i hero-modulen
                        self.draw.text((x + 20, y + 15), location, font=self.fonts['medium_desc'], fill=0)
                        
                        # VÄDERIKON med exakt dag/natt-logik - VERKLIG HÖGUPPLÖST STORLEK (96x96)
                        weather_icon = self.icon_manager.get_weather_icon_for_time(
                            smhi_symbol, current_time, sun_data, size=(96, 96)
                        )
                        if weather_icon:
                            # Placera ikon till höger om temperaturen - justerad position för 96x96
                            icon_x = x + 320
                            icon_y = y + 50
                            self.paste_icon_on_canvas(weather_icon, icon_x, icon_y)
                            self.logger.info(f"🎨 HERO väderikon: 96x96 SVG-baserad (symbol {smhi_symbol})")
                        
                        # TEMPERATUR (prioriterat från Netatmo!)
                        self.draw.text((x + 20, y + 60), f"{temp:.1f}°", font=self.fonts['hero_temp'], fill=0)
                        
                        # Beskrivning (från SMHI meteorologi)
                        desc_truncated = self.truncate_text(desc, self.fonts['hero_desc'], width - 40)
                        self.draw.text((x + 20, y + 150), desc_truncated, font=self.fonts['hero_desc'], fill=0)
                        
                        # NYTT: Visa temperatur-källa
                        if temp_source == 'netatmo':
                            source_text = "(NETATMO)"
                        elif temp_source == 'smhi':
                            source_text = "(SMHI)"
                        else:
                            source_text = f"({temp_source.upper()})"
                        
                        self.draw.text((x + 20, y + 185), source_text, font=self.fonts['tiny'], fill=0)
                        
                        # EXAKTA SOL-IKONER + tider - HÖGUPPLÖST STORLEK (56x56)
                        if sunrise and sunset:
                            sunrise_str = sunrise.strftime('%H:%M')
                            sunset_str = sunset.strftime('%H:%M')
                            
                            # Soluppgång - ikon + exakt tid
                            sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(56, 56))
                            if sunrise_icon:
                                self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 200)
                                self.draw.text((x + 80, y + 215), sunrise_str, font=self.fonts['medium_desc'], fill=0)
                                self.logger.debug(f"🌅 Sol-ikon: 56x56 SVG-baserad")
                            else:
                                # Fallback utan ikon
                                self.draw.text((x + 20, y + 215), f"🌅 {sunrise_str}", font=self.fonts['medium_desc'], fill=0)
                            
                            # Solnedgång - ikon + exakt tid  
                            sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(56, 56))
                            if sunset_icon:
                                self.paste_icon_on_canvas(sunset_icon, x + 180, y + 200)
                                self.draw.text((x + 240, y + 215), sunset_str, font=self.fonts['medium_desc'], fill=0)
                                self.logger.debug(f"🌇 Sol-ikon: 56x56 SVG-baserad")
                            else:
                                # Fallback utan ikon
                                self.draw.text((x + 180, y + 215), f"🌇 {sunset_str}", font=self.fonts['medium_desc'], fill=0)
                        
                        # NYTT: Visa soldata-källa (diskret)
                        sun_source = sun_data.get('source', 'unknown')
                        if sun_source != 'unknown':
                            source_text = f"Sol: {sun_source}"
                            if sun_source == 'ipgeolocation.io':
                                source_text = "Sol: API ✓"
                            elif sun_source == 'fallback':
                                source_text = "Sol: approx"
                            self.draw.text((x + 20, y + 250), source_text, font=self.fonts['tiny'], fill=0)
                    
                    elif module_name == 'barometer_module':
                        # 🚨 FIXED: Använd RIKTIGA trycktrend-data från weather_client
                        pressure = weather_data.get('pressure', 1013)
                        pressure_source = weather_data.get('pressure_source', 'unknown')
                        
                        # ANVÄND RIKTIGA TREND-DATA från weather_client.py
                        pressure_trend = weather_data.get('pressure_trend', {})
                        trend_text = weather_data.get('pressure_trend_text', 'Samlar data')
                        trend_arrow = weather_data.get('pressure_trend_arrow', 'stable')
                        
                        # 🎯 LOGGA VAD VI FAKTISKT FÅR
                        self.logger.info(f"🔍 BAROMETER DEBUG:")
                        self.logger.info(f"  pressure_trend: {pressure_trend}")
                        self.logger.info(f"  trend_text: {trend_text}")
                        self.logger.info(f"  trend_arrow: {trend_arrow}")
                        
                        # Barometer-ikon - HÖGUPPLÖST STORLEK (80x80)
                        barometer_icon = self.icon_manager.get_system_icon('barometer', size=(80, 80))
                        if barometer_icon:
                            self.paste_icon_on_canvas(barometer_icon, x + 15, y + 20)
                            # Tryck-värde bredvid ikon (justerad position för större ikon)
                            self.draw.text((x + 100, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                            self.logger.info(f"📊 Barometer-ikon: 80x80 SVG-baserad")
                        else:
                            # Fallback utan ikon
                            self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                        
                        # hPa-text (FIXAD: Flyttad längre ner för att inte kollidera med siffran)
                        self.draw.text((x + 100, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)
                        
                        # RIKTIGA TREND-TEXT (från 3h-analys) - RADBRYTS OM DET ÄR "Samlar data"
                        if trend_text == 'Samlar data':
                            self.draw.text((x + 20, y + 125), "Samlar", font=self.fonts['medium_desc'], fill=0)
                            self.draw.text((x + 20, y + 150), "data", font=self.fonts['medium_desc'], fill=0)
                        else:
                            self.draw.text((x + 20, y + 125), trend_text, font=self.fonts['medium_desc'], fill=0)
                        
                        # BONUS: Visa numerisk 3h-förändring om tillgänglig
                        if pressure_trend.get('change_3h') is not None and pressure_trend.get('trend') != 'insufficient_data':
                            change_3h = pressure_trend['change_3h']
                            change_text = f"{change_3h:+.1f} hPa/3h"
                            # Placera under trend-text, anpassat för radbrytsning
                            change_y = y + 175 if trend_text == 'Samlar data' else y + 150
                            self.draw.text((x + 20, change_y), change_text, font=self.fonts['small_desc'], fill=0)
                        
                        # TREND-PIL från Weather Icons - OPTIMERAD STORLEK (64x64)
                        trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(64, 64))
                        if trend_icon:
                            # Höger sida av modulen, optimerad position för 64x64
                            trend_x = x + width - 75  # 75px från höger kant för 64px ikon
                            trend_y = y + 100  # Centrerad vertikalt
                            self.paste_icon_on_canvas(trend_icon, trend_x, trend_y)
                            self.logger.info(f"↗️ Trycktrend-pil: 64x64 SVG-baserad ({trend_arrow})")
                        
                        # NYTT: Visa tryck-källa (diskret) - FLYTTAD FÖR ATT INTE KOLLIDERA MED PIL
                        if pressure_source == 'netatmo':
                            self.draw.text((x + 20, y + height - 20), "(Netatmo)", font=self.fonts['tiny'], fill=0)
                        elif pressure_source == 'smhi':
                            self.draw.text((x + 20, y + height - 20), "(SMHI)", font=self.fonts['tiny'], fill=0)
                    
                    elif module_name == 'tomorrow_forecast':
                        tomorrow = weather_data.get('tomorrow', {})
                        tomorrow_temp = tomorrow.get('temperature', 18.0)
                        tomorrow_desc = tomorrow.get('weather_description', 'Okänt')
                        tomorrow_symbol = tomorrow.get('weather_symbol', 3)
                        
                        # "Imorgon" titel
                        self.draw.text((x + 20, y + 30), "Imorgon", font=self.fonts['medium_desc'], fill=0)
                        
                        # Imorgon väderikon - HÖGUPPLÖST STORLEK (80x80)
                        tomorrow_icon = self.icon_manager.get_weather_icon(tomorrow_symbol, is_night=False, size=(80, 80))
                        if tomorrow_icon:
                            self.paste_icon_on_canvas(tomorrow_icon, x + 140, y + 20)
                            self.logger.debug(f"🌦️ Prognos-ikon: 80x80 SVG-baserad (symbol {tomorrow_symbol})")
                        
                        # Temperatur (alltid från SMHI-prognos)
                        self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)
                        
                        # Väderbeskrivning
                        desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 60)
                        self.draw.text((x + 20, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)
                        
                        # NYTT: Visa att det är SMHI-prognos
                        self.draw.text((x + 20, y + 155), "(SMHI prognos)", font=self.fonts['tiny'], fill=0)
                    
                    elif module_name == 'clock_module':
                        # OMVANDLAD TILL ELEGANT DATUMMODUL - INGEN KLOCKA LÄNGRE
                        now = datetime.now()
                        
                        # Hämta svenska datum-komponenter
                        swedish_weekday, swedish_date = self.get_swedish_date(now)
                        
                        # Kalenderdakts-ikon för modern utseende
                        calendar_icon = self.icon_manager.get_system_icon('calendar', size=(40, 40))
                        if calendar_icon:
                            # Placera ikon till vänster
                            self.paste_icon_on_canvas(calendar_icon, x + 15, y + 20)
                            text_start_x = x + 65  # Text börjar efter ikon
                        else:
                            # Fallback: ingen ikon, text börjar tidigare
                            text_start_x = x + 15
                        
                        # VECKODAG (stor och tydlig)
                        weekday_truncated = self.truncate_text(swedish_weekday, self.fonts['small_main'], width - 80)
                        self.draw.text((text_start_x, y + 20), weekday_truncated, font=self.fonts['small_main'], fill=0)
                        
                        # DATUM (elegant under veckodagen)
                        date_truncated = self.truncate_text(swedish_date, self.fonts['small_desc'], width - 80)
                        self.draw.text((text_start_x, y + 55), date_truncated, font=self.fonts['small_desc'], fill=0)
                        
                        # Dekorativ linje för elegans
                        line_start_x = text_start_x
                        line_end_x = min(x + width - 20, text_start_x + 150)
                        self.draw.line([(line_start_x, y + 80), (line_end_x, y + 80)], fill=0, width=1)
                    
                    elif module_name == 'status_module':
                        update_time = datetime.now().strftime('%H:%M')
                        
                        # FIXED: Status med enkla prickar - PERFEKT LINJERING med text
                        dot_x = x + 10
                        dot_size = 3  # 3px prick
                        
                        # Status prick + text (perfekt centrerad)
                        self.draw.ellipse([
                            (dot_x, y + 28), 
                            (dot_x + dot_size, y + 28 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 20), "Status: OK", font=self.fonts['small_desc'], fill=0)
                        
                        # Update prick + text (perfekt centrerad)
                        self.draw.ellipse([
                            (dot_x, y + 53), 
                            (dot_x + dot_size, y + 53 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 45), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)
                        
                        # Data-källor prick + text (perfekt centrerad)
                        data_sources = self.format_data_sources(weather_data)
                        self.draw.ellipse([
                            (dot_x, y + 78), 
                            (dot_x + dot_size, y + 78 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 70), f"Data: {data_sources}", font=self.fonts['small_desc'], fill=0)
            
            self.logger.info("🎨 Layout renderad med Netatmo + SMHI + HÖGUPPLÖSTA SVG-ikoner")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering av layout: {e}")
            raise
    
    def display_canvas(self, force_update=False, update_reason=""):
        """Visa canvas på E-Paper display - SMART UPPDATERING"""
        try:
            if self.epd and not self.config['debug']['test_mode']:
                if force_update:
                    self.logger.info(f"📱 UPPDATERAR E-Paper display: {update_reason}")
                    # Clear precis före uppdatering (flyttad från init_display)
                    self.epd.Clear()
                    self.epd.display(self.epd.getbuffer(self.canvas))
                    self.logger.info("✅ E-Paper display uppdaterad")
                else:
                    self.logger.info("📱 E-Paper display behåller befintlig bild")
            else:
                if force_update:
                    self.logger.info(f"🧪 Test-läge: Display simulering - {update_reason}")
                else:
                    self.logger.info("🧪 Test-läge: Display behåller bild")
                
        except Exception as e:
            self.logger.error(f"❌ Display-fel: {e}")
    
    def cleanup_old_screenshots(self):
        """Rensa screenshots äldre än 30 dagar"""
        try:
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                return
            
            cutoff_time = time.time() - (30 * 24 * 3600)  # 30 dagar sedan
            files_removed = 0
            
            for filename in os.listdir(screenshot_dir):
                filepath = os.path.join(screenshot_dir, filename)
                if os.path.isfile(filepath) and filename.endswith('.png'):
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        files_removed += 1
            
            if files_removed > 0:
                self.logger.info(f"🗑️ Rensade {files_removed} gamla screenshots (>30 dagar)")
            else:
                self.logger.debug("🧹 Inga gamla screenshots att rensa")
                
        except Exception as e:
            self.logger.error(f"⚠️ Fel vid rensning av screenshots: {e}")
    
    def save_startup_screenshot(self, update_reason=""):
        """Spara screenshot endast vid första körning efter reboot ELLER vid faktisk uppdatering"""
        try:
            # Marker-fil i /tmp (rensas automatiskt vid reboot)
            marker_file = "/tmp/epaper_screenshot_taken"
            
            # Kontrollera om screenshot redan tagits efter denna reboot OCH det inte är en uppdatering
            if os.path.exists(marker_file) and not update_reason:
                self.logger.debug("📋 Screenshot redan tagen efter reboot - hoppar över")
                return
            
            # Skapa screenshots-mapp om den inte finns
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
            
            # Rensa gamla screenshots först (endast första gången)
            if not os.path.exists(marker_file):
                self.cleanup_old_screenshots()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Bestäm filnamnsprefix baserat på anledning
            if update_reason:
                prefix = "update"
                reason_safe = update_reason.replace(" ", "_").replace(":", "").replace("/", "_")[:30]
                filename_prefix = f"{prefix}_{reason_safe}_{timestamp}"
            else:
                prefix = "startup"
                filename_prefix = f"{prefix}_{timestamp}"
            
            # Spara original 1-bit format (E-Paper native)
            original_filename = f"{screenshot_dir}/1bit_{filename_prefix}.png"
            self.canvas.save(original_filename)
            
            # Konvertera till RGB för bättre visning
            rgb_canvas = self.canvas.convert('RGB')
            rgb_filename = f"{screenshot_dir}/{filename_prefix}.png"
            rgb_canvas.save(rgb_filename)
            
            # Skapa marker-fil för att förhindra startup-dubletter
            if not update_reason:
                with open(marker_file, 'w') as f:
                    f.write(f"Screenshot taken at {timestamp}\n")
                self.logger.info(f"📸 Startup screenshot sparad: {rgb_filename}")
            else:
                self.logger.info(f"📸 Update screenshot sparad ({update_reason}): {rgb_filename}")
            
            print(f"📸 Screenshot: {rgb_filename}")
            
        except Exception as e:
            self.logger.error(f"⚠️ Screenshot-fel: {e}")
    
    def save_screenshot(self):
        """Spara screenshot av aktuell rendering - ENDAST för manuell användning"""
        try:
            # Skapa screenshots-mapp om den inte finns
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Spara original 1-bit format
            original_filename = f"{screenshot_dir}/1bit_manual_{timestamp}.png"
            self.canvas.save(original_filename)
            
            # Konvertera till RGB för bättre visning
            rgb_canvas = self.canvas.convert('RGB')
            rgb_filename = f"{screenshot_dir}/manual_{timestamp}.png"
            rgb_canvas.save(rgb_filename)
            
            self.logger.info(f"📸 Manuell screenshot sparad: {rgb_filename}")
            print(f"📸 Manual screenshot: {rgb_filename}")
            
        except Exception as e:
            self.logger.error(f"⚠️ Screenshot-fel: {e}")
    
    def run_weather_app(self):
        """Kör väderapp med Netatmo + SMHI + ikoner + exakta soltider + SMART UPPDATERING"""
        try:
            self.logger.info("🌤️ Startar E-Paper väderapp med Netatmo integration + SMART UPPDATERING...")
            
            # STEG 1: Ladda senaste cachade värden
            last_values = self.load_last_values()
            
            # STEG 2: Hämta väderdata UTAN att rendera till canvas
            weather_data = self.fetch_weather_data()
            
            # STEG 3: Avgör om displayen behöver uppdateras
            should_update, reason = self.should_update_display(weather_data, last_values)
            
            if should_update:
                # UPPDATERA SKÄRM: Förändring detekterad eller watchdog
                self.logger.info(f"🔄 UPPDATERAR skärm: {reason}")
                
                # Rendera layout BARA när vi ska uppdatera
                self.render_weather_layout(weather_data)
                
                # Ta screenshot vid uppdatering (visar vad som faktiskt renderas)
                self.save_startup_screenshot(update_reason=reason)
                
                # Visa på display
                self.display_canvas(force_update=True, update_reason=reason)
                
                # Spara nya värden till cache
                self.save_current_values(weather_data)
                
                print(f"\n✅ E-Paper uppdaterad: {reason}")
                
            else:
                # BEHÅLL SKÄRM: Inga förändringar - RENDA INGENTING!
                self.logger.info(f"💤 BEHÅLLER E-Paper skärm: {reason}")
                # VIKTIGT: Inget anrop till render_weather_layout() eller display_canvas()
                
                print(f"\n💤 E-Paper oförändrad: {reason}")
            
            # Visa sammanfattning
            print("\n" + "="*60)
            print("✅ E-PAPER VÄDERAPP MED SMART UPPDATERINGSLOGIK!")
            print("📱 Kontrollera E-Paper display för komplett väderdata")
            print("📁 Loggar: logs/weather.log")
            print("💾 Cache: cache/last_run_values.json")
            print("🧠 SMART LOGIK:")
            print(f"  🔍 Uppdateringsbeslut: {reason}")
            print(f"  🔄 Display uppdaterad: {'JA' if should_update else 'NEJ'}")
            print(f"  ⏰ 30-min watchdog aktiv")
            print(f"  📊 Jämför: temp, väder, tryck, prognos, sol, datum")
            print("🏠 Netatmo: Temperatur (utomhus) + Lufttryck (inomhus)")
            print("🌤️ SMHI: Väder, prognoser, vind, nederbörd")
            print("☀️ Exakta soltider från ipgeolocation.io API")
            print("🎨 Weather Icons med högupplösta SVG-baserade PNG-filer")
            print("🧠 Intelligent datakombination: Lokalt + Prognoser")
            print("📊 FIXED: 3-timmars trycktrend med meteorologisk standard")
            print("🚀 NEW: Smart E-Paper optimering - minimal slitage & batteri")
            print("🔧 FIXED: Blank skärm-problem - separerad data/rendering")
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"❌ Väderapp misslyckades: {e}")
            raise
    
    def cleanup(self):
        """Städa upp resurser"""
        try:
            if self.epd:
                self.epd.sleep()
            
            # Rensa ikon-cache
            if hasattr(self, 'icon_manager'):
                self.icon_manager.clear_cache()
                
            self.logger.info("🧹 Cleanup genomförd")
        except Exception as e:
            self.logger.error(f"⚠️ Cleanup-fel: {e}")

def main():
    """Huvudfunktion"""
    app = None
    try:
        # Skapa och kör väderapp med Netatmo + alla funktioner + SMART UPPDATERING
        app = EPaperWeatherApp()
        app.run_weather_app()
        
    except KeyboardInterrupt:
        print("\n⚠️ Avbruten av användare")
    except Exception as e:
        print(f"❌ Kritiskt fel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if app:
            app.cleanup()

if __name__ == "__main__":
    main()
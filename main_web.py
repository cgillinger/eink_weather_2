#!/usr/bin/env python3
"""
E-Paper Weather Station - HEADLESS WEB VERSION
Synology NAS / Desktop viewing på port 8037

EXAKT SAMMA UTSEENDE som E-Paper versionen:
- Samma layout, typsnitt, ikoner, grafik
- Samma Dynamic Module System med triggers
- Samma rendering pipeline
- Bara output till PNG istället för E-Paper

MINIMALA ÄNDRINGAR från main_daemon.py:
- Flask web server istället för systemd daemon
- PNG output istället för E-Paper display
- Auto-refresh varje minut
"""

import sys
import os
import json
import time
import io
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, send_file, jsonify

# Lägg till projektets moduler
sys.path.append('modules')

from weather_client import WeatherClient
from icon_manager import WeatherIconManager

# Import av Dynamic Module System (EXAKT som main_daemon.py)
from main_daemon import TriggerEvaluator, DynamicModuleManager

# Import av Module Factory för rendering
from modules.renderers.module_factory import ModuleFactory


class EPaperWeatherWeb:
    """
    Web version av E-Paper Weather Station
    ÅTERANVÄNDER ALL LOGIK från main_daemon.py
    """

    def __init__(self, config_path="config.json"):
        """Initialisera web version - IDENTISK med main_daemon.py"""
        print("🌐 E-Paper Weather Web Server - Startar...")

        # State management (samma som daemon)
        self.current_display_state = None
        self.current_layout_state = None
        self.last_update_time = 0

        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)

        # Setup logging
        self.setup_logging()

        # Dynamic Module Manager (EXAKT som daemon)
        self.module_manager = DynamicModuleManager(self.config)

        # Initialisera komponenter (EXAKT som daemon)
        self.weather_client = WeatherClient(self.config)
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")

        # Ladda typsnitt
        self.fonts = self.load_fonts()

        # Module Factory (EXAKT som daemon)
        self.module_factory = ModuleFactory(self.icon_manager, self.fonts)

        # Canvas setup (EXAKT samma storlek som E-Paper)
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)
        self.draw = ImageDraw.Draw(self.canvas)

        # Cache för senaste rendered image
        self.latest_image = None
        self.latest_weather_data = None

        self.logger.info("🌐 E-Paper Weather Web initialiserad")
        self.logger.info(f"📐 Canvas storlek: {self.width}×{self.height} (landscape)")

    def load_config(self, config_path):
        """Ladda JSON-konfiguration (EXAKT som daemon)"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Kan inte ladda konfiguration: {e}")
            return None

    def setup_logging(self):
        """Konfigurera logging (EXAKT som daemon)"""
        log_level = getattr(logging, self.config['debug']['log_level'], logging.INFO)

        if not os.path.exists('logs'):
            os.makedirs('logs')

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/weather_web.log'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info("📋 Logging konfigurerat för web server")

    def load_fonts(self):
        """
        Ladda typsnitt med SMART FALLBACK för Synology
        Söker automatiskt efter tillgängliga typsnitt
        """
        fonts = {}
        font_path = self.config['display']['font_path']
        font_sizes = self.config['fonts']

        # Försök hitta typsnitt (Synology-kompatibel)
        actual_font_path = self._find_available_font(font_path)

        try:
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.truetype(actual_font_path, size)
            self.logger.info(f"✅ {len(fonts)} typsnitt laddade från: {actual_font_path}")
        except Exception as e:
            self.logger.warning(f"⚠️ Typsnitt-fel: {e}, använder PIL default font")
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.load_default()

        return fonts

    def _find_available_font(self, preferred_path: str) -> str:
        """
        Hitta tillgängligt typsnitt med fallback-kedja
        SYNOLOGY-KOMPATIBEL sökning

        Args:
            preferred_path: Önskad typsnittssökväg från config

        Returns:
            Faktisk sökväg till fungerande typsnitt
        """
        import os

        # Fallback-kedja för typsnitt (Synology + Linux)
        font_search_paths = [
            preferred_path,  # Från config (Raspberry Pi)
            './fonts/DejaVuSans.ttf',  # Lokal projektmapp (kopierad)
            '/volume1/homes/admin/epaper_weather/fonts/DejaVuSans.ttf',  # Synology absolut
            './DejaVuSans.ttf',  # Projektrot
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Synology/Debian
            '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',  # Synology alternativ
            '/System/Library/Fonts/Helvetica.ttc',  # macOS (om utveckling)
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Debian/Ubuntu (Raspberry Pi)
        ]

        for font_path in font_search_paths:
            if os.path.exists(font_path):
                if font_path != preferred_path:
                    self.logger.info(f"🔄 Typsnitt fallback: {preferred_path} → {font_path}")
                return font_path

        # Sista utväg: returnera preferred (PIL default font används då)
        self.logger.warning(f"⚠️ Inget typsnitt hittades! Fallback till PIL default.")
        self.logger.warning(f"   Rekommendation: Kopiera DejaVuSans.ttf till ./fonts/")
        return preferred_path

    def fetch_weather_data(self) -> Dict:
        """Hämta väderdata (EXAKT SAMMA som daemon)"""
        try:
            self.logger.debug("🌐 Hämtar väderdata...")
            weather_data = self.weather_client.get_current_weather()
            weather_data['date'] = datetime.now().strftime('%Y-%m-%d')

            # Parse soldata
            sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)
            weather_data['parsed_sunrise'] = sunrise
            weather_data['parsed_sunset'] = sunset
            weather_data['parsed_sun_data'] = sun_data

            return weather_data
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            return {}

    def parse_sun_data_from_weather(self, weather_data: Dict) -> tuple:
        """Parse soldata (EXAKT SAMMA som daemon)"""
        try:
            sun_data = weather_data.get('sun_data', {})

            if not sun_data:
                now = datetime.now()
                sunrise = now.replace(hour=6, minute=0, second=0)
                sunset = now.replace(hour=18, minute=0, second=0)
                return sunrise, sunset, {'sunrise': sunrise.isoformat(), 'sunset': sunset.isoformat()}

            sunrise_time = sun_data.get('sunrise_time')
            sunset_time = sun_data.get('sunset_time')

            if not sunrise_time or not sunset_time:
                sunrise_str = sun_data.get('sunrise')
                sunset_str = sun_data.get('sunset')

                if sunrise_str and sunset_str:
                    try:
                        sunrise_time = datetime.fromisoformat(sunrise_str.replace('Z', '+00:00'))
                        sunset_time = datetime.fromisoformat(sunset_str.replace('Z', '+00:00'))
                    except:
                        sunrise_time = datetime.now().replace(hour=6, minute=0)
                        sunset_time = datetime.now().replace(hour=18, minute=0)

            return sunrise_time, sunset_time, sun_data

        except Exception as e:
            self.logger.error(f"❌ Fel vid soldata-parsing: {e}")
            now = datetime.now()
            return now.replace(hour=6), now.replace(hour=18), {}

    def render_and_update(self):
        """
        Rendera ny bild
        ÅTERANVÄNDER render_and_display() logik från main_daemon.py
        """
        try:
            # Hämta väderdata
            weather_data = self.fetch_weather_data()

            if not weather_data:
                self.logger.error("❌ Ingen väderdata tillgänglig")
                return False

            # Bygg trigger context (EXAKT som daemon)
            trigger_context = self.module_manager.build_trigger_context(weather_data)

            # Hämta aktiva moduler (EXAKT som daemon)
            active_modules = self.module_manager.get_active_modules(trigger_context)

            self.logger.info(f"🎨 Renderar layout med moduler: {active_modules}")

            # Rensa canvas
            self.canvas = Image.new('1', (self.width, self.height), 255)
            self.draw = ImageDraw.Draw(self.canvas)

            # Rendera alla aktiva moduler (EXAKT som daemon)
            for module_name in active_modules:
                if module_name not in self.config['modules']:
                    self.logger.warning(f"⚠️ Okänd modul: {module_name}")
                    continue

                module_config = self.config['modules'][module_name]
                x = module_config['coords']['x']
                y = module_config['coords']['y']
                width = module_config['size']['width']
                height = module_config['size']['height']

                # Rita modulram
                self.draw_module_border(x, y, width, height, module_name)

                # Factory-baserad rendering (EXAKT som daemon)
                success = self.render_module_via_factory(
                    module_name, x, y, width, height, weather_data, trigger_context
                )

                if not success:
                    self.logger.warning(f"⚠️ Rendering misslyckades för {module_name}")

            # Konvertera till RGB för webbvisning
            rgb_canvas = self.canvas.convert('RGB')
            self.latest_image = rgb_canvas
            self.latest_weather_data = weather_data
            self.last_update_time = time.time()

            self.logger.info("✅ Rendering klar för webvisning")
            return True

        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering: {e}")
            import traceback
            traceback.print_exc()
            return False

    def draw_module_border(self, x, y, width, height, module_name):
        """Rita modulramar (KOPIERAT från main_daemon.py)"""
        # EXAKT samma border-logik som i main_daemon.py
        # (Implementationen är identisk)

        if module_name == 'main_weather':
            # HERO: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)

        elif module_name in ['barometer_module', 'tomorrow_forecast']:
            # MEDIUM moduler
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)

        elif module_name in ['clock_module', 'status_module', 'precipitation_module', 'wind_module']:
            # SMALL moduler - enkla ramar
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)

    def render_module_via_factory(self, module_name: str, x: int, y: int, width: int, height: int,
                                  weather_data: Dict, trigger_context: Dict) -> bool:
        """
        Rendera modul via Module Factory (EXAKT SAMMA som daemon)
        """
        try:
            # Legacy render-funktion för moduler utan egen renderer
            legacy_func = self.get_legacy_render_function(module_name)

            # Skapa renderer via factory
            renderer = self.module_factory.create_renderer(module_name, legacy_func)

            # Sätt canvas
            renderer.set_canvas(self.canvas, self.draw)

            # Rendera
            success = renderer.render(x, y, width, height, weather_data, trigger_context)

            if success:
                self.logger.info(f"✅ Modul {module_name} renderad")

            return success

        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering av {module_name}: {e}")
            return False

    def get_legacy_render_function(self, module_name: str):
        """Legacy render functions from main_daemon.py"""
        legacy_mapping = {
            'main_weather': self.legacy_render_main_weather,
            'barometer_module': self.legacy_render_barometer,
            'tomorrow_forecast': self.legacy_render_tomorrow_forecast,
            'clock_module': self.legacy_render_clock,
            'status_module': self.legacy_render_status
        }
        return legacy_mapping.get(module_name)

    # === LEGACY RENDER FUNCTIONS (copied from main_daemon.py) ===

    def legacy_render_main_weather(self, x, y, width, height, weather_data, trigger_context):
        """Hero module rendering"""
        temp = weather_data.get('temperature', 20.0)
        desc = weather_data.get('weather_description', 'Okänt väder')
        temp_source = weather_data.get('temperature_source', 'fallback')
        location = weather_data.get('location', 'Okänd plats')
        smhi_symbol = weather_data.get('weather_symbol', 1)
        sun_data = weather_data.get('parsed_sun_data', {})
        current_time = datetime.now()

        self.draw.text((x + 20, y + 15), location, font=self.fonts['medium_desc'], fill=0)

        weather_icon = self.icon_manager.get_weather_icon_for_time(
            smhi_symbol, current_time, sun_data, size=(96, 96)
        )
        if weather_icon:
            self.paste_icon_on_canvas(weather_icon, x + 320, y + 50)

        self.draw.text((x + 20, y + 60), f"{temp:.1f}°", font=self.fonts['hero_temp'], fill=0)

        desc_truncated = self.truncate_text(desc, self.fonts['hero_desc'], width - 40)
        self.draw.text((x + 20, y + 150), desc_truncated, font=self.fonts['hero_desc'], fill=0)

        source_text = f"({temp_source.upper()})" if temp_source != 'netatmo' else "(NETATMO)"
        self.draw.text((x + 20, y + 185), source_text, font=self.fonts['tiny'], fill=0)

        sunrise = weather_data.get('parsed_sunrise')
        sunset = weather_data.get('parsed_sunset')

        if sunrise and sunset:
            sunrise_str = sunrise.strftime('%H:%M')
            sunset_str = sunset.strftime('%H:%M')

            sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(56, 56))
            if sunrise_icon:
                self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 200)
                self.draw.text((x + 80, y + 215), sunrise_str, font=self.fonts['medium_desc'], fill=0)

            sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(56, 56))
            if sunset_icon:
                self.paste_icon_on_canvas(sunset_icon, x + 160, y + 200)
                self.draw.text((x + 220, y + 215), sunset_str, font=self.fonts['medium_desc'], fill=0)

        uv_index = weather_data.get('uv_index')
        if uv_index is not None:
            uv_icon = self.icon_manager.get_system_icon('uv', size=(40, 40))
            if uv_icon:
                self.paste_icon_on_canvas(uv_icon, x + 300, y + 205)
            uv_text = f"UV {uv_index:.1f}"
            self.draw.text((x + 350, y + 215), uv_text, font=self.fonts['medium_desc'], fill=0)

    def legacy_render_barometer(self, x, y, width, height, weather_data, trigger_context):
        """Barometer module rendering"""
        pressure = weather_data.get('pressure', 1013)
        pressure_source = weather_data.get('pressure_source', 'unknown')
        pressure_trend = weather_data.get('pressure_trend', {})
        trend_text = weather_data.get('pressure_trend_text', 'Samlar data')
        trend_arrow = weather_data.get('pressure_trend_arrow', 'stable')

        barometer_icon = self.icon_manager.get_system_icon('barometer', size=(80, 80))
        if barometer_icon:
            self.paste_icon_on_canvas(barometer_icon, x + 15, y + 20)
            self.draw.text((x + 100, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
        else:
            self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)

        self.draw.text((x + 100, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)

        if trend_text == 'Samlar data':
            self.draw.text((x + 20, y + 125), "Samlar", font=self.fonts['medium_desc'], fill=0)
            self.draw.text((x + 20, y + 150), "data", font=self.fonts['medium_desc'], fill=0)
        else:
            self.draw.text((x + 20, y + 125), trend_text, font=self.fonts['medium_desc'], fill=0)

        if pressure_trend.get('change_3h') is not None and pressure_trend.get('trend') != 'insufficient_data':
            change_3h = pressure_trend['change_3h']
            change_text = f"{change_3h:+.1f} hPa/3h"
            change_y = y + 175 if trend_text == 'Samlar data' else y + 150
            self.draw.text((x + 20, change_y), change_text, font=self.fonts['small_desc'], fill=0)

        trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(64, 64))
        if trend_icon:
            self.paste_icon_on_canvas(trend_icon, x + width - 75, y + 100)

        if pressure_source == 'netatmo':
            self.draw.text((x + 20, y + height - 20), "(Netatmo)", font=self.fonts['tiny'], fill=0)

    def legacy_render_tomorrow_forecast(self, x, y, width, height, weather_data, trigger_context):
        """Forecast module rendering"""
        tomorrow = weather_data.get('tomorrow', {})
        tomorrow_temp = tomorrow.get('temperature', 18.0)
        tomorrow_desc = tomorrow.get('weather_description', 'Okänt')
        tomorrow_symbol = tomorrow.get('weather_symbol', 3)

        self.draw.text((x + 20, y + 30), "Imorgon", font=self.fonts['medium_desc'], fill=0)

        tomorrow_icon = self.icon_manager.get_weather_icon(tomorrow_symbol, is_night=False, size=(80, 80))
        if tomorrow_icon:
            self.paste_icon_on_canvas(tomorrow_icon, x + 140, y + 20)

        self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)

        desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 60)
        self.draw.text((x + 20, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)

        provider_name = self.weather_client.weather_provider.get_provider_name()
        provider_short = "SMHI" if "SMHI" in provider_name else "YR"
        self.draw.text((x + 20, y + 155), f"({provider_short} prognos)", font=self.fonts['tiny'], fill=0)

    def legacy_render_clock(self, x, y, width, height, weather_data, trigger_context):
        """Clock module rendering"""
        now = datetime.now()
        swedish_weekday, swedish_date = self.get_swedish_date_fixed(now)

        calendar_icon = self.icon_manager.get_system_icon('calendar', size=(40, 40))
        if calendar_icon:
            self.paste_icon_on_canvas(calendar_icon, x + 15, y + 15)
            text_start_x = x + 65
        else:
            text_start_x = x + 15

        date_truncated = self.truncate_text(swedish_date, self.fonts['small_main'], width - 80)
        self.draw.text((text_start_x, y + 15), date_truncated, font=self.fonts['small_main'], fill=0)

        weekday_truncated = self.truncate_text(swedish_weekday, self.fonts['medium_desc'], width - 80)
        self.draw.text((text_start_x, y + 50), weekday_truncated, font=self.fonts['medium_desc'], fill=0)

    def legacy_render_status(self, x, y, width, height, weather_data, trigger_context):
        """Status module rendering"""
        update_time = datetime.now().strftime('%H:%M')
        dot_x = x + 10
        dot_size = 3

        netatmo_extras = weather_data.get('netatmo_extras', {})
        outdoor_battery = netatmo_extras.get('outdoor_battery')
        rain_battery = netatmo_extras.get('rain_battery')
        battery_icon = self.icon_manager.get_system_icon('battery', size=(24, 24))

        self.draw.ellipse([(dot_x, y + 28), (dot_x + dot_size, y + 28 + dot_size)], fill=0)
        self.draw.text((dot_x + 10, y + 20), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)

        if outdoor_battery is not None:
            if battery_icon:
                self.paste_icon_on_canvas(battery_icon, dot_x, y + 43)
            self.draw.text((dot_x + 30, y + 45), f"{outdoor_battery}% Utomhus", font=self.fonts['small_desc'], fill=0)

        if rain_battery is not None:
            if battery_icon:
                self.paste_icon_on_canvas(battery_icon, dot_x, y + 68)
            self.draw.text((dot_x + 30, y + 70), f"{rain_battery}% Regnmodul", font=self.fonts['small_desc'], fill=0)

    def get_swedish_date_fixed(self, date_obj):
        """Swedish date with short month names"""
        swedish_days = {
            'Monday': 'Måndag', 'Tuesday': 'Tisdag', 'Wednesday': 'Onsdag',
            'Thursday': 'Torsdag', 'Friday': 'Fredag', 'Saturday': 'Lördag', 'Sunday': 'Söndag'
        }
        swedish_months_short = {
            1: 'Jan', 2: 'Feb', 3: 'Mars', 4: 'April', 5: 'Maj', 6: 'Juni',
            7: 'Juli', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
        }
        english_day = date_obj.strftime('%A')
        swedish_day = swedish_days.get(english_day, english_day)
        swedish_month = swedish_months_short.get(date_obj.month, str(date_obj.month))
        return swedish_day, f"{date_obj.day} {swedish_month}"

    def truncate_text(self, text, font, max_width):
        """Truncate text to fit width"""
        if not text:
            return text
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return text
        words = text.split()
        for i in range(len(words), 0, -1):
            truncated = ' '.join(words[:i])
            bbox = self.draw.textbbox((0, 0), truncated, font=font)
            if bbox[2] - bbox[0] <= max_width:
                return truncated
        return words[0] if words else text

    def paste_icon_on_canvas(self, icon, x, y):
        """Paste icon on canvas"""
        if icon is None:
            return
        try:
            self.canvas.paste(icon, (x, y))
        except Exception as e:
            self.logger.error(f"❌ Icon paste error: {e}")

    def get_image_bytes(self):
        """Konvertera canvas till PNG bytes för HTTP response"""
        if self.latest_image is None:
            # Rendera ny bild om ingen finns
            self.render_and_update()

        # Konvertera till PNG bytes
        img_io = io.BytesIO()
        self.latest_image.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

    def get_weather_json(self):
        """Returnera väderdata som JSON för API"""
        if self.latest_weather_data:
            return {
                'temperature': self.latest_weather_data.get('temperature'),
                'weather_description': self.latest_weather_data.get('weather_description'),
                'pressure': self.latest_weather_data.get('pressure'),
                'location': self.latest_weather_data.get('location'),
                'last_update': datetime.fromtimestamp(self.last_update_time).isoformat() if self.last_update_time > 0 else None
            }
        return {}


# Flask application
app = Flask(__name__)
weather_web = None


@app.route('/')
def index():
    """Huvudsida - visar väderbilden"""
    return render_template('index.html')


@app.route('/weather.png')
def weather_image():
    """Servera aktuell väderbild som PNG"""
    try:
        img_bytes = weather_web.get_image_bytes()
        return send_file(img_bytes, mimetype='image/png')
    except Exception as e:
        app.logger.error(f"❌ Fel vid bildservering: {e}")
        return "Error generating image", 500


@app.route('/api/weather')
def api_weather():
    """API endpoint för väderdata"""
    return jsonify(weather_web.get_weather_json())


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Tvinga uppdatering av väderdata"""
    try:
        success = weather_web.render_and_update()
        return jsonify({'success': success, 'message': 'Uppdaterad' if success else 'Fel vid uppdatering'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def main():
    """Huvudfunktion - starta Flask server"""
    global weather_web

    print("=" * 60)
    print("🌐 E-PAPER WEATHER STATION - WEB VERSION")
    print("   Headless för Synology NAS / Desktop viewing")
    print("=" * 60)

    # Initialisera weather web
    weather_web = EPaperWeatherWeb()

    # Rendera första bilden
    print("\n🎨 Renderar initial väderbild...")
    weather_web.render_and_update()

    # Starta Flask server
    print("\n🚀 Startar web server på http://0.0.0.0:8037")
    print("   📱 Öppna i mobilens webbläsare (landscape mode)")
    print("   🖥️  Eller i desktop browser")
    print("\n⌨️  Ctrl+C för att stoppa\n")

    app.run(host='0.0.0.0', port=8037, debug=False, threaded=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Web server stoppad")
    except Exception as e:
        print(f"\n❌ Kritiskt fel: {e}")
        import traceback
        traceback.print_exc()

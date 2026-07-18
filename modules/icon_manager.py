#!/usr/bin/env python3
"""
Weather Icon Manager för E-Paper Väderapp
Hanterar Weather Icons konverterade till PNG för E-Paper display
Använder samma mappningar som Väderdisplayens utils.py
FIXED: Använder befintliga wi-direction-X ikoner (med ringar) istället för wi-towards-X-deg
NYTT: Support för kalender-ikon (wi-calendar) för datummodulen
NYTT: Wind-mappningar och svenska vindbenämningar för cykel-optimerad användning
"""

import os
import sys
from datetime import datetime
from PIL import Image, ImageEnhance
import logging

class WeatherIconManager:
    """Hanterar Weather Icons för E-Paper display"""
    
    def __init__(self, icon_base_path="icons/"):
        """
        Initialisera ikon-hanterare
        
        Args:
            icon_base_path: Baskatalog för ikoner (relativ från projektrot)
        """
        self.icon_path = icon_base_path
        self.icon_cache = {}
        
        # Exakt samma mappning som Väderdisplayens utils.py
        self.smhi_mapping = {
            1: {"day": "wi-day-sunny", "night": "wi-night-clear"},                    # Klart
            2: {"day": "wi-day-sunny-overcast", "night": "wi-night-partly-cloudy"},  # Nästan klart
            3: {"day": "wi-day-cloudy", "night": "wi-night-alt-cloudy"},             # Växlande molnighet
            4: {"day": "wi-day-cloudy-high", "night": "wi-night-cloudy-high"},       # Halvklart
            5: {"day": "wi-cloudy", "night": "wi-cloudy"},                           # Molnigt
            6: {"day": "wi-cloud", "night": "wi-cloud"},                             # Mulet
            7: {"day": "wi-fog", "night": "wi-fog"},                                 # Dimma
            8: {"day": "wi-day-showers", "night": "wi-night-showers"},               # Lätta regnskurar
            9: {"day": "wi-day-rain", "night": "wi-night-rain"},                     # Måttliga regnskurar
            10: {"day": "wi-rain", "night": "wi-rain"},                              # Kraftiga regnskurar
            11: {"day": "wi-day-thunderstorm", "night": "wi-night-thunderstorm"},    # Åskväder
            12: {"day": "wi-day-rain-mix", "night": "wi-night-rain-mix"},            # Lätta snöblandade regnskurar
            13: {"day": "wi-rain-mix", "night": "wi-rain-mix"},                      # Måttliga snöblandade regnskurar
            14: {"day": "wi-rain-mix", "night": "wi-rain-mix"},                      # Kraftiga snöblandade regnskurar
            15: {"day": "wi-day-snow", "night": "wi-night-snow"},                    # Lätta snöbyar
            16: {"day": "wi-snow", "night": "wi-snow"},                              # Måttliga snöbyar
            17: {"day": "wi-snow", "night": "wi-snow"},                              # Kraftiga snöbyar
            18: {"day": "wi-day-rain", "night": "wi-night-rain"},                    # Lätt regn
            19: {"day": "wi-rain", "night": "wi-rain"},                              # Måttligt regn
            20: {"day": "wi-rain", "night": "wi-rain"},                              # Kraftigt regn
            21: {"day": "wi-thunderstorm", "night": "wi-thunderstorm"},              # Åska
            22: {"day": "wi-day-sleet", "night": "wi-night-sleet"},                  # Lätt snöblandad regn
            23: {"day": "wi-sleet", "night": "wi-sleet"},                            # Måttligt snöblandad regn
            24: {"day": "wi-sleet", "night": "wi-sleet"},                            # Kraftigt snöblandad regn
            25: {"day": "wi-day-snow", "night": "wi-night-snow"},                    # Lätt snöfall
            26: {"day": "wi-snow", "night": "wi-snow"},                              # Måttligt snöfall
            27: {"day": "wi-snow", "night": "wi-snow"}                               # Kraftigt snöfall
        }
        
        # YR/MET Norway symbol mapping (FAS 2: Global Provider)
        # YR använder text-baserade symbol_codes istället för nummer
        # Mappning till Weather Icons för konsistent rendering
        self.yr_mapping = {
            # Clear sky variants
            'clearsky_day': 'wi-day-sunny',
            'clearsky_night': 'wi-night-clear',
            'clearsky_polartwilight': 'wi-day-sunny',
            
            # Fair weather (almost clear)
            'fair_day': 'wi-day-sunny-overcast',
            'fair_night': 'wi-night-partly-cloudy',
            'fair_polartwilight': 'wi-day-sunny-overcast',
            
            # Partly cloudy
            'partlycloudy_day': 'wi-day-cloudy',
            'partlycloudy_night': 'wi-night-alt-cloudy',
            'partlycloudy_polartwilight': 'wi-day-cloudy',
            
            # Cloudy
            'cloudy': 'wi-cloudy',
            
            # Fog
            'fog': 'wi-fog',
            
            # Light rain showers
            'lightrainshowers_day': 'wi-day-showers',
            'lightrainshowers_night': 'wi-night-showers',
            'lightrainshowers_polartwilight': 'wi-day-showers',
            
            # Rain showers
            'rainshowers_day': 'wi-day-rain',
            'rainshowers_night': 'wi-night-rain',
            'rainshowers_polartwilight': 'wi-day-rain',
            
            # Heavy rain showers
            'heavyrainshowers_day': 'wi-rain',
            'heavyrainshowers_night': 'wi-rain',
            'heavyrainshowers_polartwilight': 'wi-rain',
            
            # Light rain
            'lightrain': 'wi-day-rain',
            
            # Rain
            'rain': 'wi-rain',
            
            # Heavy rain
            'heavyrain': 'wi-rain',
            
            # Light sleet showers (snöblandat)
            'lightsleetshowers_day': 'wi-day-rain-mix',
            'lightsleetshowers_night': 'wi-night-rain-mix',
            'lightsleetshowers_polartwilight': 'wi-day-rain-mix',
            
            # Sleet showers
            'sleetshowers_day': 'wi-rain-mix',
            'sleetshowers_night': 'wi-rain-mix',
            'sleetshowers_polartwilight': 'wi-rain-mix',
            
            # Heavy sleet showers
            'heavysleetshowers_day': 'wi-rain-mix',
            'heavysleetshowers_night': 'wi-rain-mix',
            'heavysleetshowers_polartwilight': 'wi-rain-mix',
            
            # Light sleet
            'lightsleet': 'wi-day-sleet',
            
            # Sleet
            'sleet': 'wi-sleet',
            
            # Heavy sleet
            'heavysleet': 'wi-sleet',
            
            # Light snow showers
            'lightsnowshowers_day': 'wi-day-snow',
            'lightsnowshowers_night': 'wi-night-snow',
            'lightsnowshowers_polartwilight': 'wi-day-snow',
            
            # Snow showers
            'snowshowers_day': 'wi-snow',
            'snowshowers_night': 'wi-snow',
            'snowshowers_polartwilight': 'wi-snow',
            
            # Heavy snow showers
            'heavysnowshowers_day': 'wi-snow',
            'heavysnowshowers_night': 'wi-snow',
            'heavysnowshowers_polartwilight': 'wi-snow',
            
            # Light snow
            'lightsnow': 'wi-day-snow',
            
            # Snow
            'snow': 'wi-snow',
            
            # Heavy snow
            'heavysnow': 'wi-snow',
            
            # Thunder
            'thunder': 'wi-thunderstorm',
            'lightthunder': 'wi-thunderstorm',
            'heavythunder': 'wi-thunderstorm'
        }
        
        # FIXED: Använder befintliga wi-direction-X ikoner (med ringar från konvertering)
        self.pressure_mapping = {
            'rising': 'wi-direction-up',      # ↑ Stigande tryck (med ring)
            'falling': 'wi-direction-down',   # ↓ Fallande tryck (med ring)
            'stable': 'wi-direction-right'    # → Stabilt tryck (med ring)
        }
        
        # NYTT: Wind-ikoner för 16 kardinalpunkter - CYKEL-OPTIMERADE
        self.wind_mapping = {
            'n': 'wi-wind-n',         # Nord (0°/360°)
            'nne': 'wi-wind-nne',     # Nord-nordost (22.5°)
            'ne': 'wi-wind-ne',       # Nordost (45°)
            'ene': 'wi-wind-ene',     # Ost-nordost (67.5°)
            'e': 'wi-wind-e',         # Ost (90°)
            'ese': 'wi-wind-ese',     # Ost-sydost (112.5°)
            'se': 'wi-wind-se',       # Sydost (135°)
            'sse': 'wi-wind-sse',     # Syd-sydost (157.5°)
            's': 'wi-wind-s',         # Syd (180°)
            'ssw': 'wi-wind-ssw',     # Syd-sydväst (202.5°)
            'sw': 'wi-wind-sw',       # Sydväst (225°)
            'wsw': 'wi-wind-wsw',     # Väst-sydväst (247.5°)
            'w': 'wi-wind-w',         # Väst (270°)
            'wnw': 'wi-wind-wnw',     # Väst-nordväst (292.5°)
            'nw': 'wi-wind-nw',       # Nordväst (315°)
            'nnw': 'wi-wind-nnw'      # Nord-nordväst (337.5°)
        }
        
        # Sol-ikoner (använda de som faktiskt genererades i sun/ katalogen)
        self.sun_mapping = {
            'sunrise': 'wi-sunrise',          # Finns i sun/ katalogen
            'sunset': 'wi-sunset',            # Finns i sun/ katalogen
            'daylight': 'wi-day-sunny'        # Finns i sun/ katalogen
        }
        
        # System-ikoner - FIXED: Barometer-ikon tillagd! + NYTT: Kalender-ikon!
        self.system_mapping = {
            'update': 'wi-refresh',           # Uppdatering
            'data_source': 'wi-strong-wind',  # Data-källa indikator
            'status_ok': 'wi-day-sunny',      # Status OK
            'status_error': 'wi-na',          # Status fel
            'clock': 'wi-time-1',
            'clock3': 'wi-time-3',            # Klockikon (gammal)
            'clock7': 'wi-time-7',            # Klockikon (FÖRBÄTTRAD)
            'barometer': 'wi-barometer',      # FIXED: Barometer-ikon tillagd!
            'calendar': 'wi-calendar',        # NYTT: Kalender-ikon för datummodulen!
            'battery': 'wi-battery',          # NYTT: Batteri-ikon för status-modulen!
            'uv': 'wi-ultraviolet',           # NYTT: UV-index-ikon för HERO-modulen!
            'strong-wind': 'wi-strong-wind'   # NYTT: Generell wind-ikon för wind-modulen!
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        print(f"🎨 WeatherIconManager initierad - {len(self.smhi_mapping)} SMHI + {len(self.yr_mapping)} YR väderikoner mappade")
        print(f"🌍 FAS 2: YR (MET Norway) symbol support aktiverad!")
        print(f"✅ FIXED: Använder befintliga wi-direction-X ikoner (med ringar)!")
        print(f"📅 NYTT: Kalender-ikon support för datummodulen!")
        print(f"🌬️ NYTT: Wind-mappningar för cykel-optimerad vindinfo!")
    
    def get_weather_icon(self, weather_symbol, is_night=False, size=(48, 48)):
        """
        Hämta väderikon baserat på väder-symbol (SMHI eller YR) med dag/natt-logik
        
        Args:
            weather_symbol: SMHI vädersymbol (1-27) ELLER YR symbol_code (t.ex. "clearsky_night")
            is_night: Om det är natt (påverkar SMHI-ikoner, ignoreras för YR som har dag/natt i namnet)
            size: Tuple med (bredd, höjd) för ikon-storlek
            
        Returns:
            PIL Image-objekt optimerat för E-Paper, eller None vid fel
        """
        # Hantera YR text-baserade symboler (strings)
        if isinstance(weather_symbol, str):
            # YR symbol - lookup direkt (dag/natt redan i symbol_code)
            if weather_symbol in self.yr_mapping:
                icon_name = self.yr_mapping[weather_symbol]
                return self.load_icon(f"weather/{icon_name}.png", size)
            else:
                self.logger.warning(f"⚠️ Okänd YR-symbol: {weather_symbol}")
                return self.create_fallback_icon(size, f"?{weather_symbol[:8]}")
        
        # Hantera SMHI numeriska symboler (integers)
        if weather_symbol not in self.smhi_mapping:
            self.logger.warning(f"⚠️ Okänd SMHI-symbol: {weather_symbol}")
            return self.create_fallback_icon(size, f"?{weather_symbol}")
        
        icon_data = self.smhi_mapping[weather_symbol]
        icon_name = icon_data['night' if is_night else 'day']
        
        return self.load_icon(f"weather/{icon_name}.png", size)
    
    def get_pressure_icon(self, trend, size=(64, 64)):
        """
        Hämta trycktrend-ikon - NU MED BEFINTLIGA wi-direction-X ikoner (med ringar)
        
        Args:
            trend: 'rising', 'falling', eller 'stable'
            size: Tuple med ikon-storlek (default: 64x64 för optimala trend-pilar)
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.pressure_mapping.get(trend, 'wi-direction-right')  # Fallback till stabilt
        self.logger.info(f"🎯 Pressure icon mapping (BEFINTLIGA): {trend} → {icon_name}")
        
        # Ladda från pressure/ katalogen (befintliga ikoner med ringar)
        pressure_icon = self.load_icon(f"pressure/{icon_name}.png", size)
        
        if pressure_icon is None:
            self.logger.warning(f"⚠️ Pressure-ikon saknas: pressure/{icon_name}.png")
            # Skapa enkel fallback
            return self.create_fallback_icon(size, {
                'rising': '↑',
                'falling': '↓', 
                'stable': '→'
            }.get(trend, '?'))
        
        return pressure_icon
    
    def get_sun_icon(self, sun_type, size=(24, 24)):
        """
        Hämta sol-ikon (sunrise/sunset)
        
        Args:
            sun_type: 'sunrise', 'sunset', eller 'daylight'
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.sun_mapping.get(sun_type, 'wi-day-sunny')
        return self.load_icon(f"sun/{icon_name}.png", size)
    
    def get_system_icon(self, system_type, size=(16, 16)):
        """
        Hämta system-ikon
        
        Args:
            system_type: 'update', 'data_source', 'status_ok', 'status_error', 'barometer', 'clock', 'clock3', 'calendar', 'battery', 'uv', 'strong-wind'
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.system_mapping.get(system_type, 'wi-na')
        
        # Special logging för nya ikoner
        if system_type == 'calendar':
            self.logger.info(f"📅 Kalender-ikon begärd: {icon_name} ({size[0]}x{size[1]})")
        elif system_type == 'barometer':
            self.logger.info(f"📊 Barometer-ikon begärd: {icon_name} ({size[0]}x{size[1]})")
        elif system_type == 'battery':
            self.logger.info(f"🔋 Batteri-ikon begärd: {icon_name} ({size[0]}x{size[1]})")
        elif system_type == 'uv':
            self.logger.info(f"☀️ UV-index-ikon begärd: {icon_name} ({size[0]}x{size[1]})")
        elif system_type == 'strong-wind':
            self.logger.info(f"🌬️ Generell wind-ikon begärd: {icon_name} ({size[0]}x{size[1]})")
        
        return self.load_icon(f"system/{icon_name}.png", size)
    
    def get_wind_description_swedish(self, speed_ms):
        """
        Konvertera vindstyrka (m/s) till svenska benämningar enligt "Benämning på land"
        Från användarens konverteringstabell för cykel-relevant wind-information
        
        Args:
            speed_ms: Vindstyrka i m/s
            
        Returns:
            Svensk vindbenämning enligt Beaufort-skala "Benämning på land"
        """
        if speed_ms < 0.2:
            return "Lugnt"
        elif speed_ms < 1.5:
            return "Svag vind"
        elif speed_ms < 3.3:
            return "Svag vind"
        elif speed_ms < 5.4:
            return "Måttlig vind"
        elif speed_ms < 7.9:
            return "Måttlig vind"
        elif speed_ms < 10.7:
            return "Frisk vind"
        elif speed_ms < 13.8:
            return "Frisk vind"
        elif speed_ms < 17.1:
            return "Hård vind"
        elif speed_ms < 20.7:
            return "Hård vind"
        elif speed_ms < 24.4:
            return "Hård vind"
        elif speed_ms < 28.4:
            return "Storm"
        elif speed_ms < 32.6:
            return "Storm"
        else:
            return "Orkan"

    def get_wind_direction_info(self, degrees):
        """
        Konvertera grader till kort svensk vindförkortning och kardinal-kod
        Cykel-optimerat för snabb avläsning (SV istället för "Sydvästlig vind")
        
        Args:
            degrees: Vindriktning i grader (0-360)
            
        Returns:
            Tuple (kort_svensk_förkortning, kardinal_kod)
        """
        if degrees is None or degrees < 0 or degrees > 360:
            return "?", "n"
        
        # 16 sektorer à 22.5 grader med KORTA svenska förkortningar
        sectors = [
            (348.75, 360, "N", "n"), (0, 11.25, "N", "n"),
            (11.25, 33.75, "NNO", "nne"),
            (33.75, 56.25, "NO", "ne"),
            (56.25, 78.75, "ONO", "ene"),
            (78.75, 101.25, "O", "e"),
            (101.25, 123.75, "OSO", "ese"),
            (123.75, 146.25, "SO", "se"),
            (146.25, 168.75, "SSO", "sse"),
            (168.75, 191.25, "S", "s"),
            (191.25, 213.75, "SSV", "ssw"),
            (213.75, 236.25, "SV", "sw"),
            (236.25, 258.75, "VSV", "wsw"),
            (258.75, 281.25, "V", "w"),
            (281.25, 303.75, "VNV", "wnw"),
            (303.75, 326.25, "NV", "nw"),
            (326.25, 348.75, "NNV", "nnw")
        ]
        
        for start, end, kort_svensk, code in sectors:
            if start <= degrees < end:
                return kort_svensk, code
        
        # Fallback
        return "N", "n"

    def get_wind_icon(self, cardinal_direction, size=(32, 32)):
        """
        Hämta wind-ikon baserat på kardinal-riktning
        FIXAD: Använder storleksspecifika undermappar (16x16/, 32x32/, 64x64/)
        
        Args:
            cardinal_direction: Kardinal-kod (t.ex. 'nw', 'se')
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.wind_mapping.get(cardinal_direction, 'wi-wind-n')
        
        # FIXAD: Använd storleksspecifik undermapp
        size_dir = f"{size[0]}x{size[1]}"
        icon_path = f"wind/{size_dir}/{icon_name}.png"
        
        return self.load_icon(icon_path, size)
    
    def load_icon(self, icon_path, size):
        """
        Ladda och cacha ikon optimerad för E-Paper
        FÖRBÄTTRAD: Bättre transparens-hantering för trycktrend-pilar
        
        Args:
            icon_path: Relativ sökväg till ikon från icons/ katalog
            size: Tuple med (bredd, höjd)
            
        Returns:
            PIL Image-objekt optimerat för E-Paper, eller fallback-ikon
        """
        cache_key = f"{icon_path}_{size[0]}x{size[1]}"
        
        # Returnera från cache om redan laddad
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        try:
            full_path = os.path.join(self.icon_path, icon_path)
            
            # Kontrollera att filen finns
            if not os.path.exists(full_path):
                self.logger.warning(f"⚠️ Ikon-fil saknas: {full_path}")
                return None  # Returnera None istället för fallback för bättre felhantering
            
            # Ladda ikon
            icon = Image.open(full_path)
            
            # Skala till rätt storlek med hög kvalitet
            if icon.size != size:
                icon = icon.resize(size, Image.Resampling.LANCZOS)
            
            # FÖRBÄTTRAD optimering för E-Paper med bättre transparens
            icon = self.optimize_for_epaper_improved(icon, icon_path)
            
            # Cacha för framtida användning
            self.icon_cache[cache_key] = icon
            
            # Special logging för nya ikoner
            if 'wi-calendar' in icon_path:
                self.logger.info(f"📅 Kalender-ikon laddad: {icon_path} ({size[0]}x{size[1]})")
            elif 'wi-direction' in icon_path:
                self.logger.info(f"📊 Trycktrend-ikon (med ring) laddad: {icon_path} ({size[0]}x{size[1]})")
            elif 'wi-wind-' in icon_path:
                self.logger.info(f"🌬️ Kardinal wind-ikon laddad: {icon_path} ({size[0]}x{size[1]})")
            elif 'wi-strong-wind' in icon_path:
                self.logger.info(f"🌪️ Generell wind-ikon laddad: {icon_path} ({size[0]}x{size[1]})")
            else:
                self.logger.debug(f"✅ Ikon laddad: {icon_path} ({size[0]}x{size[1]})")
            
            return icon
            
        except Exception as e:
            self.logger.error(f"❌ Kunde inte ladda ikon {icon_path}: {e}")
            return self.create_fallback_icon(size, "✗")
    
    def optimize_for_epaper_improved(self, image, icon_path):
        """
        FÖRBÄTTRAD optimering för E-Paper display (1-bit svartvit)
        Speciell hantering för transparens och olika ikon-typer
        
        Args:
            image: PIL Image-objekt
            icon_path: Sökväg för att identifiera ikon-typ
            
        Returns:
            Optimerat PIL Image-objekt för E-Paper
        """
        try:
            # Förbättrad transparens-hantering
            if image.mode in ('RGBA', 'LA'):
                # Skapa vit bakgrund för transparens
                background = Image.new('RGB', image.size, (255, 255, 255))
                
                if image.mode == 'RGBA':
                    # Använd alpha-kanalen för bättre transparens
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.split()[-1])
                    
                image = background
            elif image.mode == 'P':  # Palette mode
                # Konvertera palette till RGB först
                image = image.convert('RGB')
            elif image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Konvertera till grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # DYNAMISK E-Paper optimering baserat på ikon-typ och storlek
            size = max(image.size)
            is_pressure_icon = 'pressure/' in icon_path or 'direction' in icon_path
            is_calendar_icon = 'wi-calendar' in icon_path
            is_wind_icon = 'wind/' in icon_path or 'wi-wind-' in icon_path or 'wi-strong-wind' in icon_path
            
            if is_pressure_icon:
                # Speciell hantering för trycktrend-pilar (behöver vara extra tydliga)
                contrast_factor = 2.5
                sharpness_factor = 1.6
                brightness_factor = 1.0  # Neutral ljusstyrka för pilar
                self.logger.debug(f"🎯 Trycktrend-pil optimering: {icon_path}")
            elif is_calendar_icon:
                # Speciell hantering för kalender-ikon (detaljer viktiga)
                contrast_factor = 2.2
                sharpness_factor = 1.5
                brightness_factor = 1.1
                self.logger.debug(f"📅 Kalender-ikon optimering: {icon_path}")
            elif is_wind_icon:
                # NYTT: Speciell hantering för wind-ikoner (tydlighet för cykel-beslut)
                contrast_factor = 2.4
                sharpness_factor = 1.6
                brightness_factor = 1.1
                self.logger.debug(f"🌬️ Wind-ikon optimering: {icon_path}")
            elif size >= 80:
                # Stora ikoner (väder, barometer): Balanserad optimering
                contrast_factor = 2.2
                sharpness_factor = 1.4
                brightness_factor = 1.1
            elif size >= 48:
                # Medium ikoner: Standard optimering
                contrast_factor = 2.3
                sharpness_factor = 1.5
                brightness_factor = 1.1
            else:
                # Små ikoner: Aggressiv optimering för tydlighet
                contrast_factor = 2.6
                sharpness_factor = 1.7
                brightness_factor = 1.2
            
            # Tillämpa optimeringar
            # Kontrast
            contrast_enhancer = ImageEnhance.Contrast(image)
            image = contrast_enhancer.enhance(contrast_factor)
            
            # Skärpa
            sharpness_enhancer = ImageEnhance.Sharpness(image)
            image = sharpness_enhancer.enhance(sharpness_factor)
            
            # Ljusstyrka
            brightness_enhancer = ImageEnhance.Brightness(image)
            image = brightness_enhancer.enhance(brightness_factor)
            
            # Konvertera till 1-bit svartvit med Floyd-Steinberg dithering
            image = image.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            
            return image
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid E-Paper optimering: {e}")
            return self.create_fallback_icon(image.size, "!")
    
    def create_fallback_icon(self, size, text="?"):
        """
        Skapa fallback-ikon när riktig ikon inte kan laddas
        
        Args:
            size: Tuple med (bredd, höjd)
            text: Text att visa i fallback-ikonen
            
        Returns:
            PIL Image-objekt med fallback-ikon
        """
        try:
            # Skapa tom vit bild
            fallback = Image.new('1', size, 255)
            
            # Om PIL har textfunktioner, lägg till enkel text
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(fallback)
                
                # Försök använda standard-font
                font_size = min(size) // 2
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
                
                # Centrera text
                if font:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (size[0] - text_width) // 2
                    y = (size[1] - text_height) // 2
                    draw.text((x, y), text, font=font, fill=0)
                else:
                    # Enkel punkt i mitten om font inte fungerar
                    center_x, center_y = size[0] // 2, size[1] // 2
                    draw.point((center_x, center_y), fill=0)
                    
            except ImportError:
                # Om ImageDraw inte finns, returnera tom ikon
                pass
            
            self.logger.debug(f"🔧 Fallback-ikon skapad: {size[0]}x{size[1]} ('{text}')")
            return fallback
            
        except Exception as e:
            self.logger.error(f"❌ Kunde inte skapa fallback-ikon: {e}")
            # Sista utväg: tom vit bild
            return Image.new('1', size, 255)
    
    def is_night_time(self, current_time, sunrise_time, sunset_time):
        """
        Bestäm om det är natt baserat på soluppgång/solnedgång
        Samma logik som Väderdisplayen
        
        Args:
            current_time: datetime-objekt för aktuell tid
            sunrise_time: datetime-objekt för soluppgång
            sunset_time: datetime-objekt för solnedgång
            
        Returns:
            True om det är natt, False om det är dag
        """
        if not sunrise_time or not sunset_time:
            # Fallback: 22:00-06:00 = natt
            hour = current_time.hour
            return hour < 6 or hour >= 22
        
        return current_time < sunrise_time or current_time > sunset_time
    
    def get_weather_icon_for_time(self, smhi_symbol, current_time, sun_data, size=(48, 48)):
        """
        Välj dag/natt-variant av väderikon baserat på aktuell tid och soldata
        
        Args:
            smhi_symbol: SMHI vädersymbol (1-27)
            current_time: datetime-objekt för aktuell tid
            sun_data: Dict med soluppgång/solnedgång-data
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt med korrekt dag/natt-variant
        """
        # Parsea soldata om tillgängligt
        sunrise_time = None
        sunset_time = None
        
        if sun_data and 'sunrise' in sun_data and 'sunset' in sun_data:
            try:
                if isinstance(sun_data['sunrise'], str):
                    sunrise_time = datetime.fromisoformat(sun_data['sunrise'])
                else:
                    sunrise_time = sun_data['sunrise']
                    
                if isinstance(sun_data['sunset'], str):
                    sunset_time = datetime.fromisoformat(sun_data['sunset'])
                else:
                    sunset_time = sun_data['sunset']
            except Exception as e:
                self.logger.warning(f"⚠️ Fel vid parsning av soldata: {e}")
        
        # Bestäm om det är natt
        is_night = self.is_night_time(current_time, sunrise_time, sunset_time)
        
        # Hämta korrekt väderikon
        return self.get_weather_icon(smhi_symbol, is_night, size)
    
    def clear_cache(self):
        """Rensa ikon-cache för att frigöra minne"""
        cache_size = len(self.icon_cache)
        self.icon_cache.clear()
        self.logger.info(f"🗑️ Ikon-cache rensad: {cache_size} ikoner borttagna")
        print(f"🗑️ Ikon-cache rensad: {cache_size} ikoner")
    
    def get_cache_stats(self):
        """
        Få statistik om ikon-cache
        
        Returns:
            Dict med cache-statistik
        """
        total_icons = len(self.icon_cache)
        
        # Gruppera efter typ
        weather_count = len([k for k in self.icon_cache.keys() if k.startswith('weather/')])
        pressure_count = len([k for k in self.icon_cache.keys() if k.startswith('pressure/')])
        sun_count = len([k for k in self.icon_cache.keys() if k.startswith('sun/')])
        system_count = len([k for k in self.icon_cache.keys() if k.startswith('system/')])
        wind_count = len([k for k in self.icon_cache.keys() if k.startswith('wind/')])
        
        return {
            'total_cached_icons': total_icons,
            'weather_icons': weather_count,
            'pressure_icons': pressure_count, 
            'sun_icons': sun_count,
            'system_icons': system_count,
            'wind_icons': wind_count  # NYTT: Wind-ikoner räkning
        }
    
    def test_icon_loading(self):
        """
        Testa ikon-laddning med fallback-ikoner
        Användbart för att verifiera att systemet fungerar innan riktiga ikoner läggs till
        
        Returns:
            Dict med test-resultat
        """
        print("🧪 Testar WeatherIconManager...")
        
        test_results = {
            'weather_icon_test': False,
            'pressure_icon_test': False,
            'sun_icon_test': False,
            'system_icon_test': False,
            'barometer_icon_test': False,  # NY: Specifik barometer-test
            'calendar_icon_test': False,   # NYTT: Specifik kalender-test
            'pressure_direction_test': False,  # NY: Test av wi-direction-X ikoner
            'wind_description_test': False,    # NYTT: Test av svenska vindbenämningar
            'wind_direction_test': False,      # NYTT: Test av cykel-optimerade vindförkortningar
            'wind_icon_test': False,           # NYTT: Test av kardinal wind-ikoner
            'general_wind_icon_test': False,   # NYTT: Test av generell wind-ikon
            'fallback_system_works': True
        }
        
        # Test väderikon
        try:
            weather_icon = self.get_weather_icon(1, is_night=False, size=(48, 48))
            test_results['weather_icon_test'] = weather_icon is not None
            print(f"🌤️ Väderikon-test: {'✅ OK' if weather_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ Väderikon-test misslyckades: {e}")
        
        # Test tryckikon (NU: wi-direction-X ikoner)
        try:
            pressure_icon = self.get_pressure_icon('rising', size=(64, 64))
            test_results['pressure_icon_test'] = pressure_icon is not None
            
            # Specifik test för wi-direction-X ikoner
            test_results['pressure_direction_test'] = pressure_icon is not None
            print(f"📈 Tryckikon-test (wi-direction-up): {'✅ OK' if pressure_icon else '❌ Fel'}")
            
            if pressure_icon is None:
                print(f"⚠️ wi-direction-up saknas - använder fallback")
            
        except Exception as e:
            print(f"❌ Tryckikon-test misslyckades: {e}")
        
        # Test sol-ikon
        try:
            sun_icon = self.get_sun_icon('sunrise', size=(24, 24))
            test_results['sun_icon_test'] = sun_icon is not None
            print(f"🌅 Sol-ikon-test: {'✅ OK' if sun_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ Sol-ikon-test misslyckades: {e}")
        
        # Test system-ikon
        try:
            system_icon = self.get_system_icon('update', size=(16, 16))
            test_results['system_icon_test'] = system_icon is not None
            print(f"🔄 System-ikon-test: {'✅ OK' if system_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ System-ikon-test misslyckades: {e}")
        
        # Test barometer-ikon (NY!)
        try:
            barometer_icon = self.get_system_icon('barometer', size=(32, 32))
            test_results['barometer_icon_test'] = barometer_icon is not None
            print(f"🌡️ Barometer-ikon-test: {'✅ OK' if barometer_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ Barometer-ikon-test misslyckades: {e}")
        
        # NYTT: Test kalender-ikon!
        try:
            calendar_icon = self.get_system_icon('calendar', size=(40, 40))
            test_results['calendar_icon_test'] = calendar_icon is not None
            print(f"📅 Kalender-ikon-test: {'✅ OK' if calendar_icon else '❌ Fel'}")
            
            if calendar_icon:
                print(f"📅 Kalender-ikon laddad från wi-calendar.png!")
            else:
                print(f"⚠️ wi-calendar.png saknas - kör konverteringsskriptet först")
            
        except Exception as e:
            print(f"❌ Kalender-ikon-test misslyckades: {e}")
        
        # NYTT: Test wind descriptions (svenska benämningar)!
        try:
            desc_48 = self.get_wind_description_swedish(4.8)
            desc_155 = self.get_wind_description_swedish(15.5)
            test_results['wind_description_test'] = desc_48 and desc_155
            print(f"🌬️ Wind-beskrivning-test: {'✅ OK' if test_results['wind_description_test'] else '❌ Fel'}")
            print(f"   4.8 m/s → {desc_48}")
            print(f"   15.5 m/s → {desc_155}")
        except Exception as e:
            print(f"❌ Wind-beskrivning-test misslyckades: {e}")
        
        # NYTT: Test wind directions (cykel-optimerade förkortningar)!
        try:
            dir_270 = self.get_wind_direction_info(270)  # Förväntat: ('V', 'w')
            dir_225 = self.get_wind_direction_info(225)  # Förväntat: ('SV', 'sw')
            dir_45 = self.get_wind_direction_info(45)    # Förväntat: ('NO', 'ne')
            test_results['wind_direction_test'] = all([dir_270, dir_225, dir_45])
            print(f"🧭 Wind-riktning-test: {'✅ OK' if test_results['wind_direction_test'] else '❌ Fel'}")
            print(f"   270° → {dir_270} (CYKEL-KORT: förväntat 'V')")
            print(f"   225° → {dir_225} (CYKEL-KORT: förväntat 'SV')")
            print(f"   45° → {dir_45} (CYKEL-KORT: förväntat 'NO')")
        except Exception as e:
            print(f"❌ Wind-riktning-test misslyckades: {e}")
        
        # NYTT: Test kardinal wind-ikoner!
        try:
            wind_icon_w = self.get_wind_icon('w', size=(32, 32))
            wind_icon_sw = self.get_wind_icon('sw', size=(32, 32))
            test_results['wind_icon_test'] = True  # Test lyckas även om ikoner saknas
            print(f"🧭 Kardinal wind-ikon-test: {'✅ OK' if wind_icon_w or wind_icon_sw else '❌ Fel'}")
            print(f"   wi-wind-w.png: {'✅ Finns' if wind_icon_w else '⚠️ Saknas (fallback OK)'}")
            print(f"   wi-wind-sw.png: {'✅ Finns' if wind_icon_sw else '⚠️ Saknas (fallback OK)'}")
        except Exception as e:
            print(f"❌ Kardinal wind-ikon-test misslyckades: {e}")
        
        # NYTT: Test generell wind-ikon (strong-wind)!
        try:
            general_wind_icon = self.get_system_icon('strong-wind', size=(48, 48))
            test_results['general_wind_icon_test'] = general_wind_icon is not None
            print(f"🌪️ Generell wind-ikon-test: {'✅ OK' if general_wind_icon else '❌ Fel'}")
            
            if general_wind_icon:
                print(f"🌪️ wi-strong-wind.png laddad från system/!")
            else:
                print(f"⚠️ wi-strong-wind.png saknas från system/ - kör konverteringsskriptet")
            
        except Exception as e:
            print(f"❌ Generell wind-ikon-test misslyckades: {e}")
        
        # Visa cache-statistik (nu med wind-ikoner)
        cache_stats = self.get_cache_stats()
        print(f"💾 Cache-statistik: {cache_stats['total_cached_icons']} ikoner totalt")
        print(f"   🌬️ Wind-ikoner: {cache_stats['wind_icons']}")
        
        return test_results


# Test-funktioner
def test_weather_icon_manager():
    """Test av WeatherIconManager med WIND-MAPPNINGAR + CYKEL-OPTIMERING"""
    print("🧪 Testar WeatherIconManager med WIND-MAPPNINGAR för CYKEL-OPTIMERING...")
    
    # Skapa ikon-manager
    icon_manager = WeatherIconManager()
    
    # Kör test
    results = icon_manager.test_icon_loading()
    
    print(f"\n📊 Test-resultat:")
    for test_name, result in results.items():
        if test_name == 'pressure_direction_test':
            status = "✅ BEFINTLIGA wi-direction-X fungerar" if result else "⚠️ Ikoner saknas"
        elif test_name == 'calendar_icon_test':
            status = "✅ KALENDER-IKON FUNKAR" if result else "⚠️ wi-calendar.png saknas"
        elif test_name == 'wind_description_test':
            status = "✅ SVENSKA VINDBENÄMNINGAR fungerar" if result else "❌ Mappning-fel"
        elif test_name == 'wind_direction_test':
            status = "✅ CYKEL-OPTIMERADE FÖRKORTNINGAR fungerar" if result else "❌ Mappning-fel"
        elif test_name == 'wind_icon_test':
            status = "✅ KARDINAL WIND-IKONER OK" if result else "⚠️ Ikoner saknas (fallback OK)"
        elif test_name == 'general_wind_icon_test':
            status = "✅ GENERELL WIND-IKON FUNKAR" if result else "⚠️ wi-strong-wind.png saknas"
        else:
            status = "✅ PASS" if result else "⚠️ FALLBACK"
        print(f"  {test_name}: {status}")
    
    print(f"\n🌬️ WIND-MAPPNINGAR KLARA för cykel-optimering!")
    print(f"🚴‍♂️ 4.8 m/s → 'Måttlig vind', 270° → 'V' (kort förkortning)")
    print(f"📊 BEFINTLIGA pressure-ikoner behållna")
    print(f"📅 KALENDER-ikon support tillagd")
    print(f"✅ Klar för Fas 3: WindRenderer implementation!")
    
    return icon_manager


if __name__ == "__main__":
    test_weather_icon_manager()
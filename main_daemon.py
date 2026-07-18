#!/usr/bin/env python3
"""
E-Paper Weather Daemon - Kontinuerlig väderstation med DYNAMIC MODULE SYSTEM + RENDERING PIPELINE
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)

FAS 3: GENERELL MODULE RENDERING PIPELINE - PRECIPITATION FIX
- PrecipitationRenderer integration komplett
- Ingen hårdkodad rendering av precipitation_module
- Factory-baserad rendering för alla moduler

FAS 2: DYNAMIC MODULE SYSTEM
- DynamicModuleManager: Trigger-baserad modulhantering
- TriggerEvaluator: Säker condition evaluation
- Module Groups: Villkorsbaserade layout-ändringar

FIXAD: MÅNADSNAMN PROBLEM - Korta månadsnamn för långa månader så allt får plats på E-Paper

DAEMON VERSION baserad på avancerad main.py:
- Kontinuerlig process istället för cron
- State i minnet för perfekt jämförelse
- Minimal E-Paper slitage
- Robust felhantering
- Samma smarta uppdateringslogik som main.py
- Alla avancerade funktioner: Netatmo + SMHI + Smart caching + Watchdog
"""

import sys
import os
import json
import time
import re
import signal
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from PIL import Image, ImageDraw, ImageFont

# Lägg till projektets moduler
sys.path.append('modules')
# insert(0), inte append: projektroten (sys.path[0]) innehåller en stub av
# waveshare_epd som annars alltid vinner över den riktiga vendor-drivrutinen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib'))

from weather_client import WeatherClient
from icon_manager import WeatherIconManager

# NYT: Import nya renderer-systemet
from modules.renderers.module_factory import ModuleFactory

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    sys.exit(1)


class TriggerEvaluator:
    """
    Säker evaluering av trigger-conditions för Dynamic Module System

    Stöder conditions som: "precipitation > 0 OR forecast_precipitation_2h > 0.2"
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TriggerEvaluator")

        # Whitelisted functions för säker evaluation
        self.safe_functions = {
            'precipitation': self._get_precipitation,
            'forecast_precipitation_2h': self._get_forecast_precipitation_2h,
            'temperature': self._get_temperature,
            'wind_speed': self._get_wind_speed,
            'pressure_trend': self._get_pressure_trend,
            'time_hour': self._get_current_hour,
            'time_month': self._get_current_month,
            'user_preference': self._get_user_preference,
            'is_daylight': self._get_is_daylight,
            'pcat': self._get_pcat,
        }

    def evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        Säkert evaluera trigger-condition med whitelisted functions

        Args:
            condition: Condition string (t.ex. "precipitation > 0 OR temperature < 5")
            context: Context data för evaluation

        Returns:
            True om condition är uppfylld, False annars
        """
        try:
            if not condition or not isinstance(condition, str):
                return False

            # Ersätt function calls med värden
            evaluated_condition = self._replace_functions_with_values(condition, context)

            # Säker evaluation av logisk expression
            result = self._safe_eval_logic(evaluated_condition)

            self.logger.debug(f"🎯 Trigger condition: '{condition}' → '{evaluated_condition}' → {result}")
            return result

        except Exception as e:
            self.logger.error(f"❌ Fel vid trigger evaluation: {condition} - {e}")
            return False

    def _replace_functions_with_values(self, condition: str, context: Dict) -> str:
        """Ersätt function calls med faktiska värden"""
        import re
        result = condition

        # Sortera functions efter längd (längsta först) för att undvika partiella ersättningar
        sorted_functions = sorted(self.safe_functions.items(), key=lambda x: len(x[0]), reverse=True)

        for func_name, func in sorted_functions:
            # Använd word boundaries för exakt matchning
            pattern = r'\b' + re.escape(func_name) + r'\b'
            if re.search(pattern, result):
                try:
                    value = func(context)
                    # Ersätt HELA function name med värdet
                    result = re.sub(pattern, str(value), result)
                    self.logger.debug(f"🔄 Replaced {func_name} → {value}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Function {func_name} fel: {e}")
                    result = re.sub(pattern, "0", result)  # Fallback

        return result

    def _safe_eval_logic(self, expression: str) -> bool:
        """
        Säker evaluation av logisk expression
        Endast tillåter: numbers, operators (>, <, >=, <=, ==, !=), AND, OR, NOT, ()
        """
        try:
            # Whitelist för tillåtna tokens
            allowed_chars = set('0123456789.<>=!() ')
            allowed_words = {'AND', 'OR', 'NOT', 'True', 'False'}

            # Ersätt logiska operatorer med Python syntax.
            # Ordgränser (\b) krävs: kravet på omgivande mellanslag gjorde att
            # uttryck som BÖRJAR med "NOT ..." aldrig konverterades → eval-syntaxfel → alltid False
            expression = re.sub(r'\bAND\b', 'and', expression)
            expression = re.sub(r'\bOR\b', 'or', expression)
            expression = re.sub(r'\bNOT\b', 'not', expression)

            # Kontrollera att endast säkra tokens används
            tokens = expression.split()
            for token in tokens:
                if not (all(c in allowed_chars for c in token) or token in allowed_words or token in ['and', 'or', 'not']):
                    self.logger.warning(f"⚠️ Osäker token i expression: {token}")
                    return False

            # Evaluera expression
            result = eval(expression)
            return bool(result)

        except Exception as e:
            self.logger.error(f"❌ Fel vid logic evaluation: {expression} - {e}")
            return False

    # Whitelisted functions för context data
    def _get_precipitation(self, context: Dict) -> float:
        """Hämta aktuell nederbörd från context"""
        return float(context.get('precipitation', 0.0))

    def _get_forecast_precipitation_2h(self, context: Dict) -> float:
        """Hämta prognostiserad nederbörd kommande 2h"""
        return float(context.get('forecast_precipitation_2h', 0.0))

    def _get_temperature(self, context: Dict) -> float:
        """Hämta temperatur från context"""
        return float(context.get('temperature', 20.0))

    def _get_wind_speed(self, context: Dict) -> float:
        """Hämta vindstyrka från context"""
        return float(context.get('wind_speed', 0.0))

    def _get_pressure_trend(self, context: Dict) -> str:
        """Hämta trycktrend från context"""
        return str(context.get('pressure_trend_arrow', 'stable'))

    def _get_current_hour(self, context: Dict) -> int:
        """Hämta aktuell timme"""
        return datetime.now().hour

    def _get_current_month(self, context: Dict) -> int:
        """Hämta aktuell månad"""
        return datetime.now().month

    def _get_user_preference(self, context: Dict) -> str:
        """Hämta användarpreferens från context"""
        return str(context.get('user_preferences', {}).get('module_preference', 'normal'))

    def _get_is_daylight(self, context: Dict) -> bool:
        """Kontrollera om det är dagsljus"""
        return bool(context.get('is_daylight', True))

    def _get_pcat(self, context: Dict) -> int:
        """Hämta precipitation category (pcat) kod från context"""
        return int(context.get('pcat', 0))


class DynamicModuleManager:
    """
    Hanterar dynamiska moduler baserat på triggers och module groups

    Kärnkomponent i Dynamic Module System för villkorsbaserade layout-ändringar
    """

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DynamicModuleManager")

        # Läs ny config-struktur med fallback till legacy
        self.module_groups = config.get('module_groups', {})
        self.triggers = config.get('triggers', {})
        self.legacy_modules = config.get('modules', {})

        # Trigger evaluator för condition evaluation
        self.trigger_evaluator = TriggerEvaluator()

        # State tracking för layout-ändringar
        self.current_active_groups = {}
        self.last_trigger_evaluation = 0

        self.logger.info(f"🔄 DynamicModuleManager initierad")
        self.logger.info(f"   📊 Module groups: {len(self.module_groups)}")
        self.logger.info(f"   🎯 Triggers: {len(self.triggers)}")

        # Log loaded triggers för debugging (skippa kommentarer)
        for trigger_name, trigger_config in self.triggers.items():
            # Skippa kommentarer som börjar med "_"
            if trigger_name.startswith('_') or not isinstance(trigger_config, dict):
                continue
            condition = trigger_config.get('condition', 'N/A')
            self.logger.info(f"   🎯 {trigger_name}: '{condition}'")

    def evaluate_triggers(self, context_data: Dict) -> Dict[str, str]:
        """
        Evaluera alla triggers och returnera aktiva module groups

        Args:
            context_data: Väderdata, användarpref, tid, etc.

        Returns:
            Dict med section → active group mapping
            Exempel: {"bottom_section": "precipitation_active", "side_panel": "normal"}
        """
        try:
            active_groups = {}

            # Börja med default groups (normal för alla sections)
            for section_name, groups in self.module_groups.items():
                if 'normal' in groups:
                    active_groups[section_name] = 'normal'
                else:
                    # Använd första tillgängliga group som default
                    first_group = list(groups.keys())[0] if groups else None
                    if first_group:
                        active_groups[section_name] = first_group

            # Evaluera triggers med priority-ordning (skippa kommentarer)
            triggers_by_priority = sorted(
                [(name, config) for name, config in self.triggers.items()
                 if not name.startswith('_') and isinstance(config, dict)],
                key=lambda x: x[1].get('priority', 50),
                reverse=True  # Högsta priority först
            )

            # Sektioner som redan avgjorts av en aktiv trigger med högre prioritet.
            # Utan denna spärr skrev VARJE efterföljande aktiv trigger över sektionen,
            # så lägst prioritet vann - tvärtemot avsedd semantik.
            claimed_sections = set()

            for trigger_name, trigger_config in triggers_by_priority:
                try:
                    condition = trigger_config.get('condition', '')
                    target_section = trigger_config.get('target_section', '')
                    activate_group = trigger_config.get('activate_group', '')

                    if not all([condition, target_section, activate_group]):
                        self.logger.warning(f"⚠️ Ofullständig trigger config: {trigger_name}")
                        continue

                    if target_section in claimed_sections:
                        self.logger.debug(f"🎯 Trigger {trigger_name} skippad: {target_section} redan avgjord av högre prioritet")
                        continue

                    # Evaluera condition
                    if self.trigger_evaluator.evaluate_condition(condition, context_data):
                        # Trigger är aktiv → aktivera group
                        active_groups[target_section] = activate_group
                        claimed_sections.add(target_section)
                        self.logger.info(f"🎯 Trigger aktiverad: {trigger_name} → {target_section}.{activate_group}")
                    else:
                        self.logger.debug(f"🎯 Trigger inaktiv: {trigger_name}")

                except Exception as e:
                    self.logger.error(f"❌ Fel vid trigger evaluation: {trigger_name} - {e}")
                    continue

            self.current_active_groups = active_groups
            self.last_trigger_evaluation = time.time()

            return active_groups

        except Exception as e:
            self.logger.error(f"❌ Fel vid trigger evaluation: {e}")
            # Fallback: alla sections till normal
            return {section: 'normal' for section in self.module_groups.keys()}

    def get_active_modules(self, context_data: Dict) -> List[str]:
        """
        Returnera lista av moduler som ska renderas baserat på aktiva groups

        Args:
            context_data: Context data för trigger evaluation

        Returns:
            Lista av modulnamn som ska renderas
        """
        try:
            # Evaluera triggers för att få aktiva groups
            active_groups = self.evaluate_triggers(context_data)

            active_modules = []

            # Samla moduler från aktiva groups
            for section_name, active_group in active_groups.items():
                if section_name in self.module_groups:
                    section_groups = self.module_groups[section_name]
                    if active_group in section_groups:
                        group_modules = section_groups[active_group]
                        active_modules.extend(group_modules)
                        self.logger.debug(f"📊 Section {section_name}: {active_group} → {group_modules}")

            # Fallback: använd legacy modules om inga groups är definierade
            if not active_modules and self.legacy_modules:
                active_modules = [name for name, config in self.legacy_modules.items() if isinstance(config, dict) and config.get('enabled', False)]
                self.logger.info("🔄 Använder legacy modules (inga groups definierade)")

            self.logger.info(f"🎯 Aktiva moduler: {active_modules}")
            return active_modules

        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av aktiva moduler: {e}")
            # Fallback: legacy modules
            return [name for name, config in self.legacy_modules.items() if config.get('enabled', False)]

    def get_current_layout_state(self, context_data: Dict) -> Dict[str, Any]:
        """
        Få aktuellt layout-state för change detection

        Args:
            context_data: Context data för trigger evaluation

        Returns:
            Dict med layout state information
        """
        active_groups = self.evaluate_triggers(context_data)
        active_modules = self.get_active_modules(context_data)

        return {
            'active_groups': active_groups,
            'active_modules': active_modules,
            'trigger_evaluation_time': self.last_trigger_evaluation
        }

    def should_layout_update(self, context_data: Dict, last_layout_state: Dict) -> tuple:
        """
        Kontrollera om layout har ändrats sedan senast

        Args:
            context_data: Aktuell context data
            last_layout_state: Tidigare layout state

        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            current_layout_state = self.get_current_layout_state(context_data)

            if not last_layout_state:
                return True, "Första layout evaluation"

            # Jämför aktiva groups
            last_groups = last_layout_state.get('active_groups', {})
            current_groups = current_layout_state.get('active_groups', {})

            if last_groups != current_groups:
                changes = []
                for section in set(list(last_groups.keys()) + list(current_groups.keys())):
                    last_group = last_groups.get(section, 'none')
                    current_group = current_groups.get(section, 'none')
                    if last_group != current_group:
                        changes.append(f"{section}: {last_group}→{current_group}")

                return True, f"Layout-ändring: {', '.join(changes)}"

            # Jämför aktiva moduler
            last_modules = set(last_layout_state.get('active_modules', []))
            current_modules = set(current_layout_state.get('active_modules', []))

            if last_modules != current_modules:
                added = current_modules - last_modules
                removed = last_modules - current_modules
                changes = []
                if added:
                    changes.append(f"Tillagda: {', '.join(added)}")
                if removed:
                    changes.append(f"Borttagna: {', '.join(removed)}")

                return True, f"Modul-ändring: {'; '.join(changes)}"

            return False, "Ingen layout-ändring"

        except Exception as e:
            self.logger.error(f"❌ Fel vid layout change detection: {e}")
            return True, f"Fel vid layout-kontroll: {e}"

    def build_trigger_context(self, weather_data: Dict) -> Dict[str, Any]:
        """
        Bygg komplett context för trigger evaluation

        Args:
            weather_data: Väderdata från weather_client

        Returns:
            Dict med all context data för triggers
        """
        try:
            now = datetime.now()

            # Extrahera cykel-väder data om tillgängligt
            cycling_weather = weather_data.get('cycling_weather', {})

            context = {
                # Väderdata
                'precipitation': weather_data.get('precipitation', 0.0),
                'forecast_precipitation_2h': cycling_weather.get('precipitation_mm', 0.0),  # Från cykel-väder analys
                'temperature': weather_data.get('temperature', 20.0),
                'wind_speed': weather_data.get('wind_speed', 0.0),
                'pcat': cycling_weather.get('pcat', 0),  # NYTT: rå pcat-kod för snöfiltrering
                'pressure_trend_arrow': weather_data.get('pressure_trend_arrow', 'stable'),

                # Temporal context
                'time_hour': now.hour,
                'time_month': now.month,
                'time_weekday': now.weekday(),
                'is_daylight': self._determine_daylight(weather_data),

                # User context (från config)
                'user_preferences': self.config.get('user_preferences', {}),

                # System context
                'display_mode': self.config.get('display_mode', 'normal'),
                'debug_mode': self.config.get('debug', {}).get('enabled', False)
            }

            self.logger.debug(f"🌐 Trigger context: precipitation={context['precipitation']}, forecast_2h={context['forecast_precipitation_2h']}")
            return context

        except Exception as e:
            self.logger.error(f"❌ Fel vid context building: {e}")
            return {}

    def _determine_daylight(self, weather_data: Dict) -> bool:
        """Bestäm om det är dagsljus baserat på soldata"""
        try:
            sun_data = weather_data.get('sun_data', {})
            sunrise_time = weather_data.get('parsed_sunrise')
            sunset_time = weather_data.get('parsed_sunset')

            if sunrise_time and sunset_time:
                now = datetime.now()
                return sunrise_time <= now <= sunset_time
            else:
                # Fallback: 06:00-18:00 = dagsljus
                hour = datetime.now().hour
                return 6 <= hour <= 18

        except Exception as e:
            self.logger.warning(f"⚠️ Fel vid dagsljus-bestämning: {e}")
            return True  # Default till dagsljus


class EPaperWeatherDaemon:
    """E-Paper Weather Daemon - Kontinuerlig väderstation med DYNAMIC MODULE SYSTEM + RENDERING PIPELINE"""

    def __init__(self, config_path="config.json"):
        """Initialisera daemon med Dynamic Module System + Rendering Pipeline"""
        print("🌤️ E-Paper Weather Daemon - Startar med PRECIPITATION FIX...")

        # Daemon control
        self.running = True
        self.update_interval = 60  # 1 minut mellan kontroller
        self.watchdog_interval = 30 * 60  # 30 minuter watchdog

        # STATE I MINNET (utökat med layout state)
        self.current_display_state = None  # Perfekt state-hantering!
        self.current_layout_state = None   # Layout state tracking
        self.last_update_time = 0

        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)

        # Setup logging för daemon
        self.setup_logging()

        # Dynamic Module Manager
        self.module_manager = DynamicModuleManager(self.config)

        # Initialisera komponenter
        self.weather_client = WeatherClient(self.config)
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")

        # Ladda typsnitt FÖRST (behövs av ModuleFactory)
        self.fonts = self.load_fonts()

        # NYT: Module Factory för rendering pipeline
        self.module_factory = ModuleFactory(self.icon_manager, self.fonts)

        # Initialisera E-Paper display
        self.epd = None
        self.init_display()

        # Canvas setup
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)
        self.draw = ImageDraw.Draw(self.canvas)

        # Avbrytbar väntan i huvudloopen: time.sleep() släpper inte igenom
        # signaler (PEP 475), så shutdown kunde ta en hel intervall
        self.wake_event = threading.Event()
        self.screenshot_requested = False

        # Setup signal handlers för graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        # SIGUSR1 = skärmdumpsbegäran från screenshot.py; utan handler DÖDAR
        # signalen processen (OS-default)
        signal.signal(signal.SIGUSR1, self.screenshot_signal_handler)

        self.logger.info("🌤️ E-Paper Weather Daemon initialiserad med PRECIPITATION FIX")
        self.logger.info("🎨 Precipitation module använder nu PrecipitationRenderer via ModuleFactory")
        self.logger.info("📅 FIXAD: Månadsnamn problem löst med korta månadsnamn")

    def signal_handler(self, signum, frame):
        """Hantera shutdown signals"""
        self.logger.info(f"📶 Signal {signum} mottagen - avslutar daemon...")
        self.running = False
        self.wake_event.set()

    def screenshot_signal_handler(self, signum, frame):
        """SIGUSR1 från screenshot.py: spara aktuell canvas vid nästa loopvarv"""
        self.screenshot_requested = True
        self.wake_event.set()

    def save_screenshot(self):
        """Spara aktuell canvas som PNG (begärs via SIGUSR1)"""
        try:
            os.makedirs('screenshots', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = os.path.join('screenshots', f'epaper_{timestamp}.png')
            self.canvas.convert('RGB').save(path)
            self.logger.info(f"📸 Skärmdump sparad: {path}")
        except Exception as e:
            self.logger.error(f"❌ Skärmdump misslyckades: {e}")

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
            if getattr(epd4in26, 'IS_STUB', False) and not self.config['debug']['test_mode']:
                self.logger.error(
                    "❌ Stub-drivrutinen laddades istället för riktig Waveshare-drivrutin "
                    "- skärmen skulle aldrig uppdateras. Installera vendor-biblioteket i "
                    "e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd/"
                )
                sys.exit(1)
            self.logger.info(f"🖥️ EPD-drivrutin: {epd4in26.__file__}")
            self.logger.info("📱 Initialiserar E-Paper display för daemon...")
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

    def should_update_display(self, weather_data: Dict) -> tuple:
        """
        DAEMON STATE JÄMFÖRELSE + LAYOUT CHANGE DETECTION
        Samma logik som original men UTÖKAT med Dynamic Module System

        Args:
            weather_data: Ny väderdata

        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            # NYT: Kontrollera layout-ändringar FÖRST (högsta prioritet)
            trigger_context = self.module_manager.build_trigger_context(weather_data)
            layout_changed, layout_reason = self.module_manager.should_layout_update(
                trigger_context, self.current_layout_state
            )

            if layout_changed:
                return True, f"LAYOUT: {layout_reason}"

            # BEFINTLIG LOGIK: Första körningen
            if self.current_display_state is None:
                return True, "Daemon första körning"

            # BEFINTLIG LOGIK: Watchdog
            time_since_last = time.time() - self.last_update_time
            if time_since_last > self.watchdog_interval:
                return True, f"30-min watchdog ({time_since_last/60:.1f} min)"

            # BEFINTLIG LOGIK: Datum-ändring
            current_date = datetime.now().strftime('%Y-%m-%d')
            last_date = self.current_display_state.get('date', '')
            if current_date != last_date:
                return True, f"Nytt datum: {last_date} → {current_date}"

            # BEFINTLIG LOGIK: Väderdata-jämförelse
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
        """Hämta väderdata (samma som original)"""
        try:
            self.logger.debug("🌐 Hämtar väderdata från Netatmo + SMHI + exakta soltider...")

            # Hämta riktiga väderdata INKLUSIVE Netatmo sensorer
            weather_data = self.weather_client.get_current_weather()

            # Parsea exakta soltider från weather_client
            sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)

            # Lägg till parsade soltider i weather_data
            weather_data['parsed_sunrise'] = sunrise
            weather_data['parsed_sunset'] = sunset
            weather_data['parsed_sun_data'] = sun_data

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

    def parse_sun_data_from_weather(self, weather_data: Dict) -> tuple:
        """Parsea soldata (kopierat från original)"""
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

    def render_and_display(self, weather_data: Dict):
        """NYT: Rendera och visa på E-Paper display med MODULE RENDERING PIPELINE"""
        try:
            self.logger.info("🎨 Renderar ny layout med Module Rendering Pipeline...")

            # Bygg trigger context
            trigger_context = self.module_manager.build_trigger_context(weather_data)

            # Hämta aktiva moduler från Dynamic Module Manager
            active_modules = self.module_manager.get_active_modules(trigger_context)

            # FULLSTÄNDIG RENDERING med nya pipeline
            self.clear_canvas()

            # NYT: Rendera moduler via Module Factory + Renderer Pipeline
            for module_name in active_modules:
                if module_name not in self.config['modules']:
                    self.logger.warning(f"⚠️ Okänd modul: {module_name}")
                    continue

                module_config = self.config['modules'][module_name]
                x = module_config['coords']['x']
                y = module_config['coords']['y']
                width = module_config['size']['width']
                height = module_config['size']['height']

                # Rita modulram (behålls från original)
                self.draw_module_border(x, y, width, height, module_name)

                # NYT: Factory-baserad rendering
                success = self.render_module_via_factory(
                    module_name, x, y, width, height, weather_data, trigger_context
                )

                if not success:
                    self.logger.warning(f"⚠️ Factory rendering misslyckades för {module_name}")

            # Visa på display
            if self.epd and not self.config['debug']['test_mode']:
                self.epd.display(self.epd.getbuffer(self.canvas))
                self.logger.info("✅ E-Paper display uppdaterad med Module Rendering Pipeline")
            else:
                self.logger.info("🧪 Test-läge: Display simulering")

        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering: {e}")
            raise

    def render_module_via_factory(self, module_name: str, x: int, y: int, width: int, height: int,
                                  weather_data: Dict, trigger_context: Dict) -> bool:
        """
        NYT: Rendera modul via Module Factory

        Args:
            module_name: Namn på modul att rendera
            x, y, width, height: Position och storlek
            weather_data: Väderdata
            trigger_context: Trigger context data

        Returns:
            True om rendering lyckades
        """
        try:
            # Skapa legacy render-funktion för befintliga moduler
            legacy_func = self.get_legacy_render_function(module_name)

            # Skapa renderer via factory
            renderer = self.module_factory.create_renderer(module_name, legacy_func)

            # Sätt canvas för rendering
            renderer.set_canvas(self.canvas, self.draw)

            # Rendera modulen
            success = renderer.render(x, y, width, height, weather_data, trigger_context)

            if success:
                self.logger.info(f"✅ Modul {module_name} renderad via {renderer.__class__.__name__}")
            else:
                self.logger.warning(f"⚠️ Rendering misslyckades för {module_name}")

            return success

        except Exception as e:
            self.logger.error(f"❌ Factory rendering fel för {module_name}: {e}")
            return False

    def get_legacy_render_function(self, module_name: str):
        """
        Skapa legacy render-funktion för befintliga moduler

        Args:
            module_name: Modulnamn

        Returns:
            Funktion för legacy rendering eller None
        """
        # Mapping från modulnamn till legacy render-metoder
        legacy_mapping = {
            'main_weather': self.legacy_render_main_weather,
            'barometer_module': self.legacy_render_barometer,
            'tomorrow_forecast': self.legacy_render_tomorrow_forecast,
            'clock_module': self.legacy_render_clock,
            'status_module': self.legacy_render_status
        }

        return legacy_mapping.get(module_name)

    # === LEGACY RENDER FUNCTIONS (kopierade från original) ===

    def legacy_render_main_weather(self, x, y, width, height, weather_data, trigger_context):
        """BEFINTLIG: Hero-modul rendering (oförändrad från original)"""
        temp = weather_data.get('temperature', 20.0)
        desc = weather_data.get('weather_description', 'Okänt väder')
        temp_source = weather_data.get('temperature_source', 'fallback')
        location = weather_data.get('location', 'Okänd plats')
        smhi_symbol = weather_data.get('weather_symbol', 1)
        sun_data = weather_data.get('parsed_sun_data', {})
        current_time = datetime.now()

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

        # Visa temperatur-källa
        if temp_source == 'netatmo':
            source_text = "(NETATMO)"
        elif temp_source == 'smhi':
            source_text = "(SMHI)"
        else:
            source_text = f"({temp_source.upper()})"

        self.draw.text((x + 20, y + 185), source_text, font=self.fonts['tiny'], fill=0)

        # EXAKTA SOL-IKONER + tider - HÖGUPPLÖST STORLEK (56x56)
        sunrise = weather_data.get('parsed_sunrise')
        sunset = weather_data.get('parsed_sunset')

        if sunrise and sunset:
            sunrise_str = sunrise.strftime('%H:%M')
            sunset_str = sunset.strftime('%H:%M')

            # Soluppgång - ikon + exakt tid
            sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(56, 56))
            if sunrise_icon:
                self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 200)
                self.draw.text((x + 80, y + 215), sunrise_str, font=self.fonts['medium_desc'], fill=0)
            else:
                self.draw.text((x + 20, y + 215), f"🌅 {sunrise_str}", font=self.fonts['medium_desc'], fill=0)

            # Solnedgång - ikon + exakt tid
            sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(56, 56))
            if sunset_icon:
                self.paste_icon_on_canvas(sunset_icon, x + 160, y + 200)
                self.draw.text((x + 220, y + 215), sunset_str, font=self.fonts['medium_desc'], fill=0)
            else:
                self.draw.text((x + 160, y + 215), f"🌇 {sunset_str}", font=self.fonts['medium_desc'], fill=0)

        # Visa soldata-källa (diskret)
        sun_source = sun_data.get('source', 'unknown')
        if sun_source != 'unknown':
            source_text = f"Sol: {sun_source}"
            if sun_source == 'ipgeolocation.io':
                source_text = "Sol: API ✓"
            elif sun_source == 'fallback':
                source_text = "Sol: approx"
            self.draw.text((x + 20, y + 250), source_text, font=self.fonts['tiny'], fill=0)

        # NYTT: UV-INDEX - till höger om soltider
        uv_index = weather_data.get('uv_index')
        if uv_index is not None:
            # UV-ikon (40×40 - samma storlek som kalenderikon)
            uv_icon = self.icon_manager.get_system_icon('uv', size=(40, 40))
            if uv_icon:
                self.paste_icon_on_canvas(uv_icon, x + 300, y + 205)
            
            # UV-värde
            uv_text = f"UV {uv_index:.1f}"
            self.draw.text((x + 350, y + 215), uv_text, font=self.fonts['medium_desc'], fill=0)

    def legacy_render_barometer(self, x, y, width, height, weather_data, trigger_context):
        """BEFINTLIG: Barometer-modul rendering (oförändrad från original)"""
        pressure = weather_data.get('pressure', 1013)
        pressure_source = weather_data.get('pressure_source', 'unknown')
        pressure_trend = weather_data.get('pressure_trend', {})
        trend_arrow = weather_data.get('pressure_trend_arrow', 'stable')
        level_text = weather_data.get('pressure_level_text', '')

        # Barometer-ikon - HÖGUPPLÖST STORLEK (80x80)
        barometer_icon = self.icon_manager.get_system_icon('barometer', size=(80, 80))
        if barometer_icon:
            self.paste_icon_on_canvas(barometer_icon, x + 15, y + 20)
            self.draw.text((x + 100, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
        else:
            self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)

        # hPa-text
        self.draw.text((x + 100, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)

        # Källa diskret bredvid hPa-texten (nedre raderna upptas av orden)
        if pressure_source == 'netatmo':
            self.draw.text((x + 152, y + 105), "(Netatmo)", font=self.fonts['tiny'], fill=0)
        elif pressure_source == 'smhi':
            self.draw.text((x + 152, y + 105), "(SMHI)", font=self.fonts['tiny'], fill=0)

        # Endast nivåordet (Storm/Regn/Ostadigt/Vackert/Mycket Torrt) visas -
        # trendord (Stiger/Faller/Stabilt) togs bort: två sorters väderord
        # blev förvirrande. Trenden syns via siffran och pilen istället.
        word_max_w = width - 100
        if level_text:
            self.draw.text((x + 20, y + 130),
                           self.truncate_text(level_text, self.fonts['medium_desc'], word_max_w),
                           font=self.fonts['medium_desc'], fill=0)

        # Numerisk 3h-förändring (~ = preliminär), eller insamlingsstatus
        if pressure_trend.get('change_3h') is not None and pressure_trend.get('trend') != 'insufficient_data':
            prefix = '~' if pressure_trend.get('is_preliminary') else ''
            change_text = f"{prefix}{pressure_trend['change_3h']:+.1f} hPa/3h"
            self.draw.text((x + 20, y + 160), change_text, font=self.fonts['small_desc'], fill=0)
        else:
            self.draw.text((x + 20, y + 160), "Samlar data", font=self.fonts['small_desc'], fill=0)

        # TREND-PIL från Weather Icons - OPTIMERAD STORLEK (64x64)
        trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(64, 64))
        if trend_icon:
            trend_x = x + width - 75
            trend_y = y + 130
            self.paste_icon_on_canvas(trend_icon, trend_x, trend_y)

    def legacy_render_tomorrow_forecast(self, x, y, width, height, weather_data, trigger_context):
        """BEFINTLIG: Prognos-modul rendering (oförändrad från original)"""
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

        # Temperatur (från weather provider - SMHI eller YR)
        self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)

        # Väderbeskrivning
        desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 60)
        self.draw.text((x + 20, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)

        # Visa att det är SMHI-prognos
        # FAS 2: Dynamisk provider-text (SMHI eller YR)
        provider_name = self.weather_client.weather_provider.get_provider_name()
        provider_short = "SMHI" if "SMHI" in provider_name else "YR"
        self.draw.text((x + 20, y + 155), f"({provider_short} prognos)", font=self.fonts['tiny'], fill=0)

    def legacy_render_clock(self, x, y, width, height, weather_data, trigger_context):
        """FIXAD: Klock-modul rendering med KORTA MÅNADSNAMN för E-Paper"""
        now = datetime.now()

        # Hämta svenska datum-komponenter med KORTA månadsnamn
        swedish_weekday, swedish_date = self.get_swedish_date_fixed(now)

        # Kalender-ikon för modern utseende (samma storlek)
        calendar_icon = self.icon_manager.get_system_icon('calendar', size=(40, 40))
        if calendar_icon:
            # Placera ikon till vänster
            self.paste_icon_on_canvas(calendar_icon, x + 15, y + 15)
            text_start_x = x + 65  # Text börjar efter ikon
        else:
            # Fallback: ingen ikon, text börjar tidigare
            text_start_x = x + 15

        # DATUM FÖRST I BRA STORLEK (small_main = 32px - lagom större än förut)
        date_truncated = self.truncate_text(swedish_date, self.fonts['small_main'], width - 80)
        self.draw.text((text_start_x, y + 15), date_truncated, font=self.fonts['small_main'], fill=0)

        # VECKODAG UNDER I BRA STORLEK (medium_desc = 24px - större men fortfarande mindre än datum)
        weekday_truncated = self.truncate_text(swedish_weekday, self.fonts['medium_desc'], width - 80)
        self.draw.text((text_start_x, y + 50), weekday_truncated, font=self.fonts['medium_desc'], fill=0)

    def legacy_render_status(self, x, y, width, height, weather_data, trigger_context):
        """MODIFIERAD: Status-modul med Netatmo batteristatus och batteriikon"""
        update_time = datetime.now().strftime('%H:%M')

        # Status med enkla prickar
        dot_x = x + 10
        dot_size = 3
        
        # Hämta Netatmo batteristatus
        netatmo_extras = weather_data.get('netatmo_extras', {})
        outdoor_battery = netatmo_extras.get('outdoor_battery')
        rain_battery = netatmo_extras.get('rain_battery')
        
        # Ladda batteriikon (24×24)
        battery_icon = self.icon_manager.get_system_icon('battery', size=(24, 24))
        
        # RAD 1: Update tid (visas alltid)
        self.draw.ellipse([
            (dot_x, y + 28),
            (dot_x + dot_size, y + 28 + dot_size)
        ], fill=0)
        self.draw.text((dot_x + 10, y + 20), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)

        # RAD 2: Utomhusmodul batteri (om tillgänglig)
        if outdoor_battery is not None:
            # Batteriikon istället för prick
            if battery_icon:
                self.paste_icon_on_canvas(battery_icon, dot_x, y + 43)
            # Text med kort formatering
            self.draw.text((dot_x + 30, y + 45), f"{outdoor_battery}% Utomhus", font=self.fonts['small_desc'], fill=0)
        
        # RAD 3: Regnmodul batteri (om tillgänglig)
        if rain_battery is not None:
            # Batteriikon istället för prick
            if battery_icon:
                self.paste_icon_on_canvas(battery_icon, dot_x, y + 68)
            # Text med kort formatering
            self.draw.text((dot_x + 30, y + 70), f"{rain_battery}% Regnmodul", font=self.fonts['small_desc'], fill=0)

    # === NYA HJÄLPMETODER ===

    def get_swedish_date_fixed(self, date_obj):
        """
        FIXAD: Konvertera datum till svenska veckodagar och KORTA månader för E-Paper
        Löser problemet med att långa månadsnamn som "Augusti" inte får plats
        """
        swedish_days = {
            'Monday': 'Måndag', 'Tuesday': 'Tisdag', 'Wednesday': 'Onsdag',
            'Thursday': 'Torsdag', 'Friday': 'Fredag', 'Saturday': 'Lördag', 'Sunday': 'Söndag'
        }

        # FIXAD: KORTA månadsnamn för E-Paper display
        swedish_months_short = {
            1: 'Jan', 2: 'Feb', 3: 'Mars', 4: 'April', 5: 'Maj', 6: 'Juni',
            7: 'Juli', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
        }

        english_day = date_obj.strftime('%A')
        swedish_day = swedish_days.get(english_day, english_day)

        day_num = date_obj.day
        month_num = date_obj.month
        swedish_month = swedish_months_short.get(month_num, str(month_num))

        return swedish_day, f"{day_num} {swedish_month}"

    # === BEFINTLIGA HJÄLPMETODER (oförändrade från original) ===

    def clear_canvas(self):
        """Rensa canvas (vit bakgrund)"""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=255)

    def draw_module_border(self, x, y, width, height, module_name):
        """Rita smarta modulramar - NYT: PRECIPITATION MODULE INGET HÅRDKODAD INNEHÅLL"""
        if module_name == 'main_weather':
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'barometer_module':
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'tomorrow_forecast':
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'clock_module':
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
            self.draw.line([(x, y), (x, y + height)], fill=0, width=2)
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'status_module':
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x, y), (x, y + height)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
            self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name in ['precipitation_module', 'wind_module']:
            # FIXAT: BARA RAMAR - INGET HÅRDKODAD INNEHÅLL!
            # Innehållet renderas av Precipitation-/WindRenderer via ModuleFactory
            # (wind_module saknade tidigare ram helt, till skillnad från main_web)
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
            self.draw.line([(x, y), (x, y + height)], fill=0, width=2)
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)

    def truncate_text(self, text, font, max_width):
        """Korta text så den får plats inom given bredd (kopierat från original)"""
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
            truncated_width = bbox[2] - bbox[0]

            if truncated_width <= max_width:
                return truncated

        return words[0] if words else text

    def paste_icon_on_canvas(self, icon, x, y):
        """Sätt in ikon på canvas (kopierat från original)"""
        if icon is None:
            return

        try:
            self.canvas.paste(icon, (x, y))
        except Exception as e:
            self.logger.error(f"❌ Fel vid ikon-inplacering: {e}")

    def update_state(self, weather_data: Dict):
        """Uppdatera daemon state i minnet + LAYOUT STATE"""
        # BEFINTLIG state (oförändrad)
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
            'date': datetime.now().strftime('%Y-%m-%d'),
            'last_update': time.time()
        }

        # NYT: Layout state tracking
        trigger_context = self.module_manager.build_trigger_context(weather_data)
        self.current_layout_state = self.module_manager.get_current_layout_state(trigger_context)

        self.last_update_time = time.time()

    def run_daemon(self):
        """Huvudloop för daemon"""
        self.logger.info("🚀 Startar E-Paper Weather Daemon med PRECIPITATION FIX...")
        print("🚀 E-Paper Weather Daemon startad - Månadsnamn FIXAT!")

        iteration = 0

        try:
            while self.running:
                iteration += 1
                self.logger.debug(f"🔄 Daemon iteration #{iteration}")

                # Skärmdumpsbegäran via SIGUSR1
                if self.screenshot_requested:
                    self.screenshot_requested = False
                    self.save_screenshot()

                try:
                    # Hämta väderdata
                    weather_data = self.fetch_weather_data()

                    if weather_data:
                        # Avgör om uppdatering behövs (nu med layout change detection)
                        should_update, reason = self.should_update_display(weather_data)

                        if should_update:
                            self.logger.info(f"🔄 UPPDATERAR E-Paper: {reason}")

                            # Rendera och visa (nu med Rendering Pipeline)
                            self.render_and_display(weather_data)

                            # Uppdatera state i minnet (nu med layout state)
                            self.update_state(weather_data)

                            print(f"🔄 E-Paper uppdaterad: {reason}")

                        else:
                            self.logger.info(f"💤 BEHÅLLER skärm: {reason}")
                            print(f"💤 E-Paper behålls: {reason}")

                except Exception as e:
                    self.logger.error(f"❌ Fel i daemon iteration #{iteration}: {e}")

                # Vänta till nästa iteration - avbrytbart av signaler
                # (time.sleep släpper inte igenom signalavbrott, PEP 475)
                if self.running:
                    self.wake_event.wait(self.update_interval)
                    self.wake_event.clear()

        except KeyboardInterrupt:
            self.logger.info("⚠️ Daemon avbruten av användare")
            print("\n⚠️ Daemon stoppad")

        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup vid shutdown"""
        # Anropas från både run_daemon():s och main():s finally - kör bara en
        # gång (dubbel epd.sleep() mot redan sovande panel är oförutsägbart)
        if getattr(self, '_cleanup_done', False):
            return
        self._cleanup_done = True
        try:
            if self.epd:
                self.epd.sleep()

            if hasattr(self, 'icon_manager'):
                self.icon_manager.clear_cache()

            if hasattr(self, 'module_factory'):
                self.module_factory.clear_cache()

            self.logger.info("🧹 Daemon cleanup genomförd")
            print("🧹 Daemon cleanup genomförd")
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

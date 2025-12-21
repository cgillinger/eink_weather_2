#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weather Client - API-anrop för SMHI och Netatmo + SunCalculator
Hämtar riktiga väderdata för E-Paper displayen
KOMPLETT NETATMO INTEGRATION: OAuth2 + Temperatur + Tryck + Luftfuktighet + RAIN GAUGE
NYTT: CYKEL-VÄDER INTEGRATION: Nederbörd-analys för cykling
SÄKER TEST-DATA INJECTION: Config-driven test-data för precipitation module
NYTT: SMHI OBSERVATIONS API: Exakt "regnar just nu" från senaste timmen
NYTT: NETATMO RAIN GAUGE PRIORITERING: Högsta prioritet för nederbörd (5 min fördröjning)
FIXAD: Test-funktion läser från config.json istället av hårdkodade värden
FIXAD: Test-data prioritering följer samma logik som riktiga väderdata
FIXAD: Cykel-väder bug - analyze_cycling_weather extraherar nu korrekt precipitation från SMHI forecast
FIXAD: Timezone bug - UTC-tider konverteras nu till lokal tid för visning (19:00 UTC → 21:00 CEST)
NYTT: SMHI-inkonsistens fix - synkroniserar weather description med observations för konsistent regnkläder-info
FAS 1: VINDRIKTNING API-UTÖKNING - Hämtar nu både vindstyrka (ws) och vindriktning (wd) från SMHI
NYTT: VINDBY-SUPPORT - Hämtar vindbyar (gust) från SMHI API för "X m/s (Y)" format
NYTT: NETATMO RAIN GAUGE (NAModule3) - Regnmätare med 5-minuters fördröjning som primär källa
NYTT: PRELIMINÄR TRYCKTREND - Visar ~trend vid <3h data, riktig trend vid ≥2.5h data

NEDERBÖRDS-PRIORITERING:
1. Netatmo Rain Gauge (5 min fördröjning) - HÖGSTA PRIORITET
2. SMHI Observations (10-60 min fördröjning) - Fallback om Netatmo saknas/fel
3. SMHI Prognoser - Fallback om både Netatmo och Observations saknas

OM Netatmo säger 0mm → REGNAR INTE (även om SMHI Observations säger något annat)
OM Netatmo API-fel → Använd ordinarie prioritering (Observations > Prognoser)
"""

import requests
import json
import time
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

# Importera SunCalculator (med fallback)
try:
    from sun_calculator import SunCalculator
    SUN_CALCULATOR_AVAILABLE = True
except ImportError:
    print("⚠️ SunCalculator ej tillgänglig - använder förenklad solberäkning")
    SUN_CALCULATOR_AVAILABLE = False

# Importera Weather Provider Factory (FAS 1: Provider System)
from modules.weather_provider_factory import create_weather_provider

class WeatherClient:
    """Klient för att hämta väderdata från SMHI, Netatmo och exakta soltider + CYKEL-VÄDER + SÄKER TEST-DATA + SMHI OBSERVATIONS + VINDRIKTNING + VINDBYAR + NETATMO RAIN GAUGE"""

    def __init__(self, config: Dict[str, Any]):
        """Initialisera med konfiguration"""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # SMHI konfiguration
        self.latitude = config['location']['latitude']
        self.longitude = config['location']['longitude']
        self.location_name = config['location']['name']

        # SMHI Observations configuration
        self.smhi_observations = config.get('smhi_observations', {})
        self.observations_station_id = self.smhi_observations.get('primary_station_id', '98230')
        self.alternative_station_id = self.smhi_observations.get('fallback_station_id', '97390')

        # NETATMO konfiguration (nu fullt implementerad)
        self.netatmo_config = config.get('api_keys', {}).get('netatmo', {})
        self.netatmo_access_token = None
        self.netatmo_token_expires = 0

        # Netatmo API endpoints - UPPDATERAD DOMÄN
        self.netatmo_token_url = "https://api.netatmo.com/oauth2/token"
        self.netatmo_stations_url = "https://api.netatmo.com/api/getstationsdata"

        # SunCalculator för exakta soltider (om tillgänglig)
        if SUN_CALCULATOR_AVAILABLE:
            self.sun_calculator = SunCalculator()
        else:
            self.sun_calculator = None

        # Cache för API-anrop (Netatmo cache kortare - mer aktuell data)
        self.smhi_cache = {'data': None, 'timestamp': 0}
        self.netatmo_cache = {'data': None, 'timestamp': 0}  # 10 min cache för Netatmo
        self.sun_cache = {'data': None, 'timestamp': 0}

        # NYTT: Cache för SMHI observations (15 min - data kommer varje timme)
        self.observations_cache = {'data': None, 'timestamp': 0}

        # NYTT: Cache för UV-index (6 timmar - långsam förändring)
        self.uv_cache = {'data': None, 'timestamp': 0}

        # NYTT: Tryckhistorik för 3-timmars tendenser (meteorologisk standard)
        self.pressure_history_file = "cache/pressure_history.json"
        self.ensure_cache_directory()

        # NYTT: CYKEL-VÄDER konstanter
        self.CYCLING_PRECIPITATION_THRESHOLD = 0.2  # mm/h - Tröskelvärde för cykel-väder varning

        # NYTT: Trycktrend konstanter
        self.PRESSURE_TREND_MIN_MINUTES = 30      # Minst 30 min för preliminär trend
        self.PRESSURE_TREND_FULL_HOURS = 2.5      # 2.5h+ = riktig trend (utan tilde)
        self.PRESSURE_TREND_THRESHOLD_3H = 2.0    # ±2 hPa/3h = meteorologisk standard

        self.logger.info(f"🌍 WeatherClient initialiserad för {self.location_name}")
        self.logger.info(f"☀️ SunCalculator aktiverad för exakta soltider")
        self.logger.info(f"🚴‍♂️ Cykel-väder aktiverat (tröskelvärde: {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
        self.logger.info(f"🌬️ FAS 1: Vindriktning API-utökning aktiverad (ws + wd parametrar)")
        self.logger.info(f"💨 NYTT: Vindby-support aktiverat (gust parameter)")

        # Log observations configuration
        station_name = self.smhi_observations.get('primary_station_name', 'Unknown station')
        self.logger.info(f"📊 SMHI Observations enabled: Station {self.observations_station_id} ({station_name})")

        # NYTT: Logga Netatmo Rain Gauge prioritering
        self.logger.info(f"🌧️ Netatmo Rain Gauge aktiverat som HÖGSTA PRIORITET för nederbörd")
        self.logger.info(f"📍 Nederbörds-prioritering: Netatmo (5min) > SMHI Obs (60min) > SMHI Prognos")

        # Kontrollera Netatmo-konfiguration
        if self.netatmo_config.get('client_id') and self.netatmo_config.get('refresh_token'):
            self.logger.info(f"🏠 Netatmo-integration aktiverad (temp, tryck, RAIN GAUGE)")
        else:
            self.logger.warning(f"⚠️ Netatmo-credentials saknas - använder endast SMHI")

        # NYTT: UV-index API (CurrentUVIndex.com - gratis, ingen API-nyckel krävs)
        self.uv_api_url = "https://currentuvindex.com/api/v1/uvi"
        self.logger.info(f"☀️ UV-index aktiverat från CurrentUVIndex.com (6h cache)")

        # FAS 1: PROVIDER SYSTEM - Skapa weather provider
        self.weather_provider = create_weather_provider(config)
        self.logger.info(f"✅ Provider System aktiverat: {self.weather_provider.get_provider_name()}")

        # NYTT: Kontrollera test-data konfiguration
        debug_config = self.config.get('debug', {})
        if debug_config.get('enabled') and debug_config.get('allow_test_data'):
            self.logger.info(f"🧪 Test-data injection aktiverad (timeout: {debug_config.get('test_timeout_hours', 1)}h)")
        else:
            self.logger.debug(f"🔒 Test-data injection inaktiverad (production-safe)")

    def get_smhi_observations(self) -> Dict[str, Any]:
        """
        NYTT: Hämta SMHI observations data för exakt "regnar just nu"-logik

        Returns:
            Dict med observations data eller tom dict vid fel
        """
        # Kontrollera cache (15 min för observations)
        cache_timeout = self.config.get('update_intervals', {}).get('smhi_observations_seconds', 900)
        if time.time() - self.observations_cache['timestamp'] < cache_timeout:
            if self.observations_cache['data']:
                self.logger.info("📋 Använder cachad SMHI observations-data")
                return self.observations_cache['data']

        try:
            self.logger.info(f"🌧️ Hämtar SMHI observations från station {self.observations_station_id}...")

            # SMHI Observations API enligt handboken
            # Parameter 7 = Nederbördsmängd, summa 1 timme, 1 gång/tim, enhet: millimeter
            url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/{self.observations_station_id}/period/latest-hour/data.json"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parsea observations data
            observations_data = self.parse_smhi_observations(data)

            if observations_data:
                # Uppdatera cache
                self.observations_cache = {'data': observations_data, 'timestamp': time.time()}
                station_name = self.smhi_observations.get('primary_station_name', 'Station')
                precipitation = observations_data.get('precipitation_observed', 0.0)
                self.logger.info(f"✅ SMHI Observations hämtad från {station_name}: {precipitation}mm/h")
            else:
                self.logger.warning("⚠️ Ingen giltig observations-data hittades")

            return observations_data

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️ SMHI Observations API-fel: {e}")
            # Försök med alternativ station
            return self.try_alternative_station()
        except Exception as e:
            self.logger.error(f"❌ SMHI Observations parsningsfel: {e}")
            return {}

    def try_alternative_station(self) -> Dict[str, Any]:
        """
        Försök hämta observations från alternativ station (Arlanda)

        Returns:
            Dict med observations data eller tom dict vid fel
        """
        try:
            self.logger.info(f"🔄 Försöker alternativ station {self.alternative_station_id} (Arlanda)...")

            url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/{self.alternative_station_id}/period/latest-hour/data.json"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            observations_data = self.parse_smhi_observations(data)

            if observations_data:
                observations_data['station_id'] = self.alternative_station_id
                observations_data['station_name'] = 'Arlanda (alternativ)'
                self.logger.info(f"✅ SMHI Observations från alternativ station: {observations_data.get('precipitation_observed', 0)}mm/h")
                return observations_data

            return {}

        except Exception as e:
            self.logger.error(f"❌ Alternativ station misslyckades också: {e}")
            return {}

    def parse_smhi_observations(self, data: Dict) -> Dict[str, Any]:
        """
        Parsea SMHI observations JSON och extrahera nederbördsdata

        Args:
            data: Rå JSON från SMHI Observations API

        Returns:
            Dict med parsad observations-data
        """
        try:
            if 'value' not in data or not data['value']:
                self.logger.warning("⚠️ Tom observations-data från SMHI")
                return {}

            # Senaste mätningen är sista värdet i listan
            latest_observation = data['value'][-1]

            # Extrahera data
            observation_time = datetime.fromtimestamp(latest_observation['date'] / 1000)  # milliseconds → seconds
            precipitation_mm = float(latest_observation['value'])
            quality = latest_observation.get('quality', 'U')  # G=good, Y=suspected, R=rejected, U=uncertain

            # Beräkna data-ålder
            now = datetime.now()
            data_age_minutes = (now - observation_time).total_seconds() / 60

            # Varning om data är för gammal
            if data_age_minutes > 90:
                self.logger.warning(f"⚠️ Observations-data är {data_age_minutes:.0f} min gammal - kan vara föråldrad")

            # Filtrera bort dålig kvalitet
            if quality == 'R':  # Rejected
                self.logger.warning(f"⚠️ Observations-data har dålig kvalitet (R) - ignorerar")
                return {}

            observations_data = {
                'precipitation_observed': precipitation_mm,
                'observation_time': observation_time.isoformat(),
                'quality': quality,
                'station_id': self.observations_station_id,
                'data_age_minutes': data_age_minutes
            }

            self.logger.debug(f"📊 SMHI Observations parsad: {precipitation_mm}mm/h (kvalitet: {quality}, ålder: {data_age_minutes:.1f}min)")

            return observations_data

        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"❌ Fel vid parsning av SMHI observations: {e}")
            return {}

    def ensure_cache_directory(self):
        """Säkerställ att cache-katalog existerar"""
        cache_dir = "cache"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            self.logger.info(f"📁 Skapade cache-katalog: {cache_dir}")

    def save_pressure_measurement(self, pressure: float, source: str = "unknown"):
        """
        NYTT: Spara tryckmätning för 3-timmars trend-analys

        Args:
            pressure: Lufttryck i hPa
            source: Datakälla (netatmo/smhi)
        """
        try:
            # Läs befintlig historik
            history = []
            if os.path.exists(self.pressure_history_file):
                with open(self.pressure_history_file, 'r') as f:
                    history = json.load(f)

            # Lägg till ny mätning
            timestamp = datetime.now().isoformat()
            history.append({
                'timestamp': timestamp,
                'pressure': pressure,
                'source': source
            })

            # Behåll bara senaste 24 timmarna
            cutoff_time = datetime.now() - timedelta(hours=24)
            history = [
                entry for entry in history
                if datetime.fromisoformat(entry['timestamp']) > cutoff_time
            ]

            # Spara uppdaterad historik
            with open(self.pressure_history_file, 'w') as f:
                json.dump(history, f, indent=2)

            self.logger.debug(f"📊 Tryck-mätning sparad: {pressure} hPa från {source}")

        except Exception as e:
            self.logger.error(f"❌ Fel vid sparande av tryckhistorik: {e}")

    def calculate_3h_pressure_trend(self) -> Dict[str, Any]:
        """
        Beräkna trycktrend med stöd för preliminär trend vid uppstart.

        Logik:
        - 0-30 min data: insufficient_data ("Samlar data")
        - 30 min - 2.5h data: Preliminär trend (is_preliminary=True, tilde-prefix)
        - ≥2.5h data: Riktig trend (is_preliminary=False)

        Extrapolerar förändring till 3h-skala för konsistent tröskel (±2 hPa/3h).

        Returns:
            Dict med trend-information inkl. is_preliminary flagga
        """
        try:
            if not os.path.exists(self.pressure_history_file):
                return {
                    'trend': 'insufficient_data',
                    'change': 0.0,
                    'change_3h': None,
                    'period_hours': 0,
                    'is_preliminary': False,
                    'reason': 'Ingen historik ännu'
                }

            # Läs historik
            with open(self.pressure_history_file, 'r') as f:
                history = json.load(f)

            if len(history) < 2:
                return {
                    'trend': 'insufficient_data',
                    'change': 0.0,
                    'change_3h': None,
                    'period_hours': 0,
                    'is_preliminary': False,
                    'reason': 'För få mätningar'
                }

            # Senaste mätningen
            now = datetime.now()
            latest = history[-1]
            latest_time = datetime.fromisoformat(latest['timestamp'])
            latest_pressure = latest['pressure']

            # Hitta äldsta mätningen (för att bestämma tillgänglig period)
            oldest = history[0]
            oldest_time = datetime.fromisoformat(oldest['timestamp'])

            # Total tillgänglig datamängd
            total_period_hours = (latest_time - oldest_time).total_seconds() / 3600
            total_period_minutes = total_period_hours * 60

            # Kontrollera minsta krav (30 minuter)
            if total_period_minutes < self.PRESSURE_TREND_MIN_MINUTES:
                return {
                    'trend': 'insufficient_data',
                    'change': 0.0,
                    'change_3h': None,
                    'period_hours': total_period_hours,
                    'is_preliminary': False,
                    'reason': f'För kort period ({total_period_minutes:.0f} min < {self.PRESSURE_TREND_MIN_MINUTES} min)'
                }

            # Bestäm om vi ska använda 3h-mätning eller äldsta tillgängliga
            target_time = now - timedelta(hours=3)

            # Hitta bästa matchning (närmast 3h tillbaka, eller äldsta om <3h data)
            best_match = None
            best_diff = float('inf')

            for entry in history:
                entry_time = datetime.fromisoformat(entry['timestamp'])
                time_diff = abs((entry_time - target_time).total_seconds())

                if time_diff < best_diff:
                    best_diff = time_diff
                    best_match = entry

            if not best_match:
                # Fallback till äldsta mätningen
                best_match = oldest

            # Beräkna tryckförändring
            old_pressure = best_match['pressure']
            old_time = datetime.fromisoformat(best_match['timestamp'])

            pressure_change = latest_pressure - old_pressure
            time_diff_hours = (latest_time - old_time).total_seconds() / 3600

            # Säkerhetskontroll för division
            if time_diff_hours < 0.1:  # Mindre än 6 minuter
                return {
                    'trend': 'insufficient_data',
                    'change': pressure_change,
                    'change_3h': None,
                    'period_hours': time_diff_hours,
                    'is_preliminary': False,
                    'reason': 'Mätningar för nära i tid'
                }

            # Extrapolera till 3h-skala för konsistent jämförelse
            change_per_hour = pressure_change / time_diff_hours
            change_3h_extrapolated = change_per_hour * 3.0

            # Bestäm om detta är preliminär eller riktig trend
            is_preliminary = time_diff_hours < self.PRESSURE_TREND_FULL_HOURS

            # Klassificera trend baserat på extrapolerat 3h-värde
            if change_3h_extrapolated > self.PRESSURE_TREND_THRESHOLD_3H:
                trend = 'rising'
            elif change_3h_extrapolated < -self.PRESSURE_TREND_THRESHOLD_3H:
                trend = 'falling'
            else:
                trend = 'stable'

            # Loggning
            prefix = "~" if is_preliminary else ""
            self.logger.info(
                f"📊 Trycktrend: {prefix}{trend} "
                f"({pressure_change:+.1f} hPa på {time_diff_hours:.1f}h → "
                f"extrapolerat {change_3h_extrapolated:+.1f} hPa/3h) "
                f"[{'preliminär' if is_preliminary else 'riktig'}]"
            )

            return {
                'trend': trend,
                'change': pressure_change,
                'change_3h': change_3h_extrapolated,
                'period_hours': time_diff_hours,
                'is_preliminary': is_preliminary,
                'old_pressure': old_pressure,
                'new_pressure': latest_pressure
            }

        except Exception as e:
            self.logger.error(f"❌ Fel vid beräkning av trycktrend: {e}")
            return {
                'trend': 'error',
                'change': 0.0,
                'change_3h': None,
                'period_hours': 0,
                'is_preliminary': False,
                'reason': str(e)
            }

    def _load_test_data_if_enabled(self) -> Optional[Dict]:
        """
        SÄKER TEST-DATA: Läs test-data från cache om aktiverat i config

        Returns:
            Test-data dict eller None om inaktiverat/ej tillgängligt
        """
        debug_config = self.config.get('debug', {})

        # Kontrollera om test-data är tillåtet
        if not debug_config.get('enabled') or not debug_config.get('allow_test_data'):
            return None

        test_file = "cache/test_precipitation.json"

        try:
            if not os.path.exists(test_file):
                return None

            with open(test_file, 'r') as f:
                test_data = json.load(f)

            # Kontrollera timeout
            created_time = datetime.fromisoformat(test_data.get('created_at', datetime.now().isoformat()))
            timeout_hours = debug_config.get('test_timeout_hours', 1)

            age_hours = (datetime.now() - created_time).total_seconds() / 3600

            if age_hours > timeout_hours:
                self.logger.info(f"⏱️ Test-data utgånget ({age_hours:.1f}h > {timeout_hours}h) - ignorerar")
                # Ta bort utgånget test-data
                os.remove(test_file)
                return None

            self.logger.warning(f"🧪 TEST-DATA AKTIVT: {test_data.get('description', 'Okänt test')}")
            self.logger.warning(f"⏱️ Test-data ålder: {age_hours:.1f}h / {timeout_hours}h")

            return test_data

        except Exception as e:
            self.logger.error(f"❌ Fel vid läsning av test-data: {e}")
            return None

    def _apply_test_overrides(self, weather_data: Dict, test_data: Dict) -> Dict:
        """
        Applicera test-data overrides på väderdata

        Args:
            weather_data: Riktig väderdata
            test_data: Test-data från cache

        Returns:
            Modifierad väderdata med test-overrides
        """
        # Kopiera så vi inte ändrar originalet
        modified_data = weather_data.copy()

        # Applicera overrides från test-data
        overrides = test_data.get('overrides', {})

        for key, value in overrides.items():
            modified_data[key] = value
            self.logger.debug(f"🧪 Test override: {key} = {value}")

        # Markera att detta är test-data
        modified_data['test_mode'] = True
        modified_data['test_description'] = test_data.get('description', 'Test-data aktivt')
        modified_data['test_created_at'] = test_data.get('created_at')

        return modified_data

    def analyze_cycling_weather(self, smhi_forecast_data: Dict) -> Dict[str, Any]:
        """
        NYTT: Analysera väder för cykling - kolla om nederbörd förväntas inom 2h
        FIXAD: Extraherar nu korrekt precipitation från forecast parameters

        Args:
            smhi_forecast_data: Full SMHI forecast data med timeSeries

        Returns:
            Dict med cykel-väder analys
        """
        try:
            cycling_analysis = {
                'cycling_warning': False,
                'precipitation_mm': 0.0,
                'precipitation_type': 'Ingen',
                'precipitation_description': 'Inget regn',
                'forecast_time': None,
                'reason': 'Inget regn förväntat inom 2h'
            }

            if not smhi_forecast_data or 'timeSeries' not in smhi_forecast_data:
                self.logger.warning("⚠️ Ingen SMHI forecast data tillgänglig för cykel-analys")
                return cycling_analysis

            # Analysera kommande 2 timmar
            now = datetime.now(timezone.utc)
            two_hours_ahead = now + timedelta(hours=2)

            # Filtrera prognoser för kommande 2 timmar
            next_hours_forecasts = []
            for forecast in smhi_forecast_data['timeSeries']:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))

                if now <= forecast_time <= two_hours_ahead:
                    next_hours_forecasts.append((forecast_time, forecast))

            if not next_hours_forecasts:
                self.logger.warning("⚠️ Inga prognoser hittades för kommande 2h")
                return cycling_analysis

            # Hitta max nederbörd inom 2h
            # FIXAD: Extraktion av parameters från forecast-struktur
            max_precipitation = 0.0
            precipitation_type_code = 0
            warning_forecast_time = None

            # DEBUGGING: Logga vad vi faktiskt hittar
            self.logger.debug(f"🔍 CYKEL-VÄDER DEBUG: Analyserar {len(next_hours_forecasts)} prognoser")

            for forecast_time, forecast in next_hours_forecasts:
                # FIXAD: Säkrare parameter-extraktion
                precipitation = 0.0
                precip_type = 0

                try:
                    for param in forecast.get('parameters', []):
                        param_name = param.get('name', '')
                        param_values = param.get('values', [])

                        if param_name == 'pmin' and param_values:  # Nederbörd mm/h
                            precipitation = float(param_values[0])
                        elif param_name == 'pcat' and param_values:  # Nederbörd-typ
                            precip_type = int(param_values[0])

                    # DEBUGGING: Logga varje prognos
                    self.logger.debug(f"  {forecast_time.strftime('%H:%M')}: {precipitation}mm/h (typ: {precip_type})")

                    # FIXAD: Kolla tröskelvärdet korrekt
                    if precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                        if precipitation > max_precipitation:
                            max_precipitation = precipitation
                            precipitation_type_code = precip_type
                            warning_forecast_time = forecast_time

                except Exception as e:
                    self.logger.warning(f"⚠️ Fel vid extraktion av forecast-parametrar: {e}")
                    continue

            # FIXAD: Korrekt result building
            if max_precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                cycling_analysis['cycling_warning'] = True
                cycling_analysis['precipitation_mm'] = max_precipitation
                cycling_analysis['precipitation_type'] = self.get_precipitation_type_description(precipitation_type_code)
                cycling_analysis['precipitation_description'] = self.get_precipitation_intensity_description(max_precipitation)

                # FIXAD TIMEZONE BUG: Konvertera UTC till lokal tid för visning
                if warning_forecast_time:
                    local_time = warning_forecast_time.astimezone()
                    cycling_analysis['forecast_time'] = local_time.strftime('%H:%M')
                else:
                    cycling_analysis['forecast_time'] = 'Okänd tid'

                cycling_analysis['reason'] = f"Nederbörd förväntat: {max_precipitation:.1f}mm/h"

                # FIXAD TIMEZONE BUG: Logging med lokal tid
                local_time_str = local_time.strftime('%H:%M') if warning_forecast_time else 'Okänd tid'
                self.logger.info(f"🚴‍♂️ CYKEL-VARNING: {cycling_analysis['precipitation_description']} {cycling_analysis['precipitation_type']} kl {local_time_str} (lokal tid)")
            else:
                cycling_analysis['precipitation_mm'] = max_precipitation  # FIXAD: Sätt även här för debug
                self.logger.info(f"🚴‍♂️ Cykel-väder OK: Max {max_precipitation:.1f}mm/h (under {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")

            # DEBUGGING: Logga slutresultat
            self.logger.debug(f"🎯 CYKEL-VÄDER SLUTRESULTAT: warning={cycling_analysis['cycling_warning']}, max_precip={cycling_analysis['precipitation_mm']}")

            # NYTT: Lägg till rå pcat-kod för trigger-filtrering (snö vs regn)
            cycling_analysis['pcat'] = precipitation_type_code
            return cycling_analysis

        except Exception as e:
            self.logger.error(f"❌ Fel vid cykel-väder analys: {e}")
            return {'cycling_warning': False, 'reason': f'Analysis error: {e}'}

    def get_precipitation_type_description(self, pcat_code: int) -> str:
        """
        Konvertera SMHI pcat-kod till läsbar beskrivning

        Args:
            pcat_code: SMHI precipitation category kod

        Returns:
            Läsbar beskrivning av nederbörd-typ
        """
        precipitation_types = {
            0: "Ingen nederbörd",
            1: "Snö",
            2: "Snöblandat regn",
            3: "Regn",
            4: "Hagel",
            5: "Hagel + regn",
            6: "Hagel + snö"
        }
        return precipitation_types.get(pcat_code, f"Okänd typ ({pcat_code})")

    def get_precipitation_intensity_description(self, mm_per_hour: float) -> str:
        """
        Konvertera mm/h till läsbar intensitetsbeskrivning

        Args:
            mm_per_hour: Nederbörd i mm per timme

        Returns:
            Beskrivning av nederbörd-intensitet
        """
        if mm_per_hour < 0.1:
            return "Inget regn"
        elif mm_per_hour < 0.5:
            return "Lätt duggregn"
        elif mm_per_hour < 1.0:
            return "Lätt regn"
        elif mm_per_hour < 2.5:
            return "Måttligt regn"
        elif mm_per_hour < 10.0:
            return "Kraftigt regn"
        else:
            return "Mycket kraftigt regn"


# ============================================================
# HÄR SLUTAR DEL ETT
# ============================================================
# ============================================================
# HÄR BÖRJAR DEL TVÅ
# ============================================================

    def get_current_weather(self) -> Dict[str, Any]:
        """Hämta komplett väderdata från alla källor INKLUSIVE Netatmo lokala sensorer + NETATMO RAIN GAUGE + CYKEL-VÄDER + OBSERVATIONS + VINDRIKTNING + VINDBYAR"""
        try:
            # FAS 1: Hämta väderdata från provider (SMHI eller YR)
            # Provider hanterar: forecast, observations (om tillgängligt), cycling weather
            provider_data = self.weather_provider.get_current_weather()

            # Hämta Netatmo-data (nu inkl. Rain Gauge!)
            netatmo_data = self.get_netatmo_data()

            # Hämta exakta soltider
            sun_data = self.get_sun_data()

            # NYTT: Hämta UV-index
            uv_data = self.get_uv_data()

            # Extrahera provider-specifika data för combine_weather_data
            # (behåller backward compatibility med befintlig combine-logik)
            smhi_data = provider_data  # Provider data innehåller SMHI forecast
            observations_data = provider_data.get('observations', {})
            cycling_weather = provider_data.get('cycling_weather', {})

            # Kombinera data intelligent (NETATMO RAIN GAUGE prioriterat högst, sedan Netatmo temp/tryck, sedan Observations, sedan SMHI prognoser)
            combined_data = self.combine_weather_data(smhi_data, netatmo_data, sun_data, observations_data, uv_data)

            # NYTT: Lägg till cykel-väder information
            combined_data['cycling_weather'] = cycling_weather

            # FIXAD: Lägg till forecast_precipitation_2h för trigger evaluation
            if cycling_weather:
                combined_data['forecast_precipitation_2h'] = cycling_weather.get('precipitation_mm', 0.0)
                self.logger.debug(f"🎯 TRIGGER DATA: forecast_precipitation_2h = {combined_data['forecast_precipitation_2h']}")

            sources = []
            if netatmo_data and 'rain' in netatmo_data:
                sources.append("Netatmo-Rain-Gauge")
            if observations_data:
                sources.append(f"{self.weather_provider.get_provider_name()}-Observations")
            if netatmo_data:
                sources.append("Netatmo")
            if smhi_data:
                sources.append(f"{self.weather_provider.get_provider_name()}-Prognoser")

            # NYTT: Logga cykel-väder status
            if cycling_weather.get('cycling_warning'):
                self.logger.info(f"🚴‍♂️ CYKEL-VARNING aktiv: {cycling_weather.get('reason')}")

            # NYTT: Logga nederbördsstatus från alla källor
            if netatmo_data and 'rain' in netatmo_data:
                rain_mm_h = netatmo_data.get('rain', 0.0)
                if rain_mm_h > 0:
                    self.logger.info(f"🌧️ NETATMO RAIN GAUGE: Regnar just nu ({rain_mm_h:.2f}mm/h)")
                else:
                    self.logger.info(f"🌤️ NETATMO RAIN GAUGE: Regnar inte just nu (0mm/h)")
            elif observations_data:
                observed_precip = observations_data.get('precipitation_observed', 0.0)
                if observed_precip > 0:
                    self.logger.info(f"🌧️ OBSERVATIONS: Regnar just nu ({observed_precip}mm senaste timmen)")
                else:
                    self.logger.info(f"🌤️ OBSERVATIONS: Regnar inte just nu (0mm senaste timmen)")

            # FAS 1: Logga vinddata om tillgänglig
            if smhi_data and 'wind_speed' in smhi_data:
                wind_speed = smhi_data.get('wind_speed', 0.0)
                wind_direction = smhi_data.get('wind_direction', 'N/A')
                wind_gust = smhi_data.get('wind_gust', 'N/A')
                if wind_gust != 'N/A':
                    self.logger.info(f"💨 VINDBYAR: Hämtad - Medelvind: {wind_speed} m/s, Byar: {wind_gust} m/s, Riktning: {wind_direction}°")
                else:
                    self.logger.info(f"🌬️ FAS 1: Vinddata hämtad - Styrka: {wind_speed} m/s, Riktning: {wind_direction}°")

            self.logger.info(f"✅ Väderdata hämtad från: {', '.join(sources) if sources else 'fallback'}")
            return combined_data

        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            return self.get_fallback_data()

    def get_netatmo_access_token(self) -> Optional[str]:
        """
        Hämta giltig Netatmo access token via refresh token

        Returns:
            Access token eller None vid fel
        """
        # Kontrollera om befintlig token fortfarande är giltig
        if (self.netatmo_access_token and
            time.time() < self.netatmo_token_expires - 300):  # 5 min marginal
            return self.netatmo_access_token

        try:
            self.logger.info("🔑 Förnyar Netatmo access token...")

            # OAuth2 refresh token request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.netatmo_config['refresh_token'],
                'client_id': self.netatmo_config['client_id'],
                'client_secret': self.netatmo_config['client_secret']
            }

            response = requests.post(self.netatmo_token_url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()

            if 'access_token' in token_data:
                self.netatmo_access_token = token_data['access_token']
                # Access tokens brukar gälla 3 timmar
                expires_in = token_data.get('expires_in', 10800)
                self.netatmo_token_expires = time.time() + expires_in

                self.logger.info(f"✅ Netatmo token förnyad (gäller {expires_in//3600}h)")
                return self.netatmo_access_token
            else:
                self.logger.error(f"❌ Ogiltigt token-svar: {token_data}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Netatmo token-fel: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Oväntat token-fel: {e}")
            return None

    def get_netatmo_data(self) -> Dict[str, Any]:
        """
        Hämta sensordata från Netatmo väderstation INKL. RAIN GAUGE

        Returns:
            Dict med Netatmo sensordata (temp, tryck, rain) eller tom dict vid fel
        """
        # Kontrollera om Netatmo är konfigurerat
        if not self.netatmo_config.get('client_id'):
            self.logger.debug("📋 Netatmo ej konfigurerat")
            return {}

        # Kontrollera cache (10 min för Netatmo - mer aktuell än SMHI)
        if time.time() - self.netatmo_cache['timestamp'] < 600:
            if self.netatmo_cache['data']:
                self.logger.info("📋 Använder cachad Netatmo-data")
                return self.netatmo_cache['data']

        try:
            self.logger.info("🏠 Hämtar Netatmo sensordata...")

            # Hämta access token
            access_token = self.get_netatmo_access_token()
            if not access_token:
                self.logger.error("❌ Kunde inte få Netatmo access token")
                return {}

            # Hämta stations-data
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(self.netatmo_stations_url, headers=headers, timeout=15)
            response.raise_for_status()

            stations_data = response.json()

            # Parsea sensor-data (nu inkl. Rain Gauge)
            netatmo_data = self.parse_netatmo_stations(stations_data)

            # NYTT: Spara tryck för 3-timmars trend-analys
            if netatmo_data and 'pressure' in netatmo_data:
                self.save_pressure_measurement(netatmo_data['pressure'], source="netatmo")

            if netatmo_data:
                # Uppdatera cache
                self.netatmo_cache = {'data': netatmo_data, 'timestamp': time.time()}
                self.logger.info("✅ Netatmo-data hämtad")
            else:
                self.logger.warning("⚠️ Ingen giltig Netatmo-data hittades")

            return netatmo_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Netatmo API-fel: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Netatmo parsningsfel: {e}")
            return {}

    def parse_netatmo_stations(self, stations_data: Dict) -> Dict[str, Any]:
        """
        Parsea Netatmo stations-data och extrahera sensorvärden INKL. RAIN GAUGE (NAModule3)

        Args:
            stations_data: Rå data från Netatmo stations API

        Returns:
            Dict med parsade sensorvärden (temp, tryck, rain)
        """
        try:
            if 'body' not in stations_data or 'devices' not in stations_data['body']:
                self.logger.error("❌ Ogiltigt Netatmo stations-format")
                return {}

            devices = stations_data['body']['devices']
            if not devices:
                self.logger.error("❌ Inga Netatmo enheter hittades")
                return {}

            # Ta första station (användaren har antagligen bara en)
            station = devices[0]

            netatmo_data = {
                'source': 'netatmo',
                'station_name': station.get('station_name', 'Okänd station'),
                'timestamp': datetime.now().isoformat()
            }

            # Hämta data från huvudmodul (inomhus)
            if 'dashboard_data' in station:
                indoor_data = station['dashboard_data']

                # LUFTTRYCK från inomhusmodul (mer exakt än SMHI!)
                if 'Pressure' in indoor_data:
                    netatmo_data['pressure'] = indoor_data['Pressure']
                    self.logger.debug(f"📊 Netatmo tryck: {indoor_data['Pressure']} hPa")

                # Inomhustemperatur (för framtida användning)
                if 'Temperature' in indoor_data:
                    netatmo_data['indoor_temperature'] = indoor_data['Temperature']

                # Luftfuktighet inomhus
                if 'Humidity' in indoor_data:
                    netatmo_data['indoor_humidity'] = indoor_data['Humidity']

                # CO2 och ljudnivå (bonus-data)
                if 'CO2' in indoor_data:
                    netatmo_data['co2'] = indoor_data['CO2']
                if 'Noise' in indoor_data:
                    netatmo_data['noise'] = indoor_data['Noise']

            # Hämta data från utomhusmodul(er)
            if 'modules' in station:
                for module in station['modules']:
                    module_type = module.get('type')

                    # NAModule1 = Utomhusmodul (temperatur/humidity)
                    if module_type == 'NAModule1' and 'dashboard_data' in module:
                        outdoor_data = module['dashboard_data']

                        # TEMPERATUR från utomhusmodul (huvudsensordata!)
                        if 'Temperature' in outdoor_data:
                            netatmo_data['temperature'] = outdoor_data['Temperature']
                            self.logger.debug(f"🌡️ Netatmo utomhustemp: {outdoor_data['Temperature']}°C")

                        # Luftfuktighet utomhus
                        if 'Humidity' in outdoor_data:
                            netatmo_data['outdoor_humidity'] = outdoor_data['Humidity']

                        # Tidsstämpel för senaste mätning
                        if 'time_utc' in outdoor_data:
                            last_seen = datetime.fromtimestamp(outdoor_data['time_utc'])
                            netatmo_data['last_measurement'] = last_seen.isoformat()

                            # Kontrollera att data är färsk (senaste 30 min)
                            data_age_minutes = (datetime.now() - last_seen).total_seconds() / 60
                            if data_age_minutes > 30:
                                self.logger.warning(f"⚠️ Netatmo-data är {data_age_minutes:.1f} min gammal")
                            else:
                                self.logger.debug(f"✅ Netatmo-data är {data_age_minutes:.1f} min gammal")

                        # Batteriinformation utomhusmodul
                        if 'battery_percent' in module:
                            netatmo_data['outdoor_battery'] = module['battery_percent']
                            if module['battery_percent'] < 20:
                                self.logger.warning(f"⚠️ Netatmo utomhusmodul batteri lågt: {module['battery_percent']}%")

                    # NYTT: NAModule3 = Rain Gauge (regnmätare) - HÖGSTA PRIORITET FÖR NEDERBÖRD!
                    elif module_type == 'NAModule3' and 'dashboard_data' in module:
                        rain_data = module['dashboard_data']

                        # RAIN - Nederbörd senaste 5 minuter (mm)
                        if 'Rain' in rain_data:
                            # Konvertera från mm/5min till mm/h för konsistens med SMHI
                            rain_mm_5min = rain_data['Rain']
                            rain_mm_h = rain_mm_5min * 12  # 5 min → 1h (60/5=12)

                            netatmo_data['rain'] = rain_mm_h
                            netatmo_data['rain_sum_1h'] = rain_data.get('sum_rain_1', 0)
                            netatmo_data['rain_sum_24h'] = rain_data.get('sum_rain_24', 0)

                            self.logger.info(f"🌧️ Netatmo Rain Gauge: {rain_mm_h:.2f}mm/h (senaste 5 min: {rain_mm_5min}mm)")

                        # Tidsstämpel för senaste regnmätning
                        if 'time_utc' in rain_data:
                            last_rain_measurement = datetime.fromtimestamp(rain_data['time_utc'])
                            netatmo_data['rain_last_measurement'] = last_rain_measurement.isoformat()

                            # Kontrollera att regndata är färsk
                            rain_age_minutes = (datetime.now() - last_rain_measurement).total_seconds() / 60
                            netatmo_data['rain_age_minutes'] = rain_age_minutes

                            if rain_age_minutes > 10:
                                self.logger.warning(f"⚠️ Netatmo Rain Gauge data är {rain_age_minutes:.1f} min gammal")
                            else:
                                self.logger.debug(f"✅ Netatmo Rain Gauge data är {rain_age_minutes:.1f} min gammal")

                        # Batteriinformation
                        if 'battery_percent' in module:
                            netatmo_data['rain_battery'] = module['battery_percent']
                            if module['battery_percent'] < 20:
                                self.logger.warning(f"⚠️ Netatmo Rain Gauge batteri lågt: {module['battery_percent']}%")

            # Kontrollera att vi fick viktig data
            if 'temperature' not in netatmo_data and 'pressure' not in netatmo_data and 'rain' not in netatmo_data:
                self.logger.warning("⚠️ Varken temperatur, tryck eller regn hittades i Netatmo-data")
                return {}

            # Logga vad vi faktiskt fick
            sensors_found = []
            if 'temperature' in netatmo_data:
                sensors_found.append(f"Temp: {netatmo_data['temperature']}°C")
            if 'pressure' in netatmo_data:
                sensors_found.append(f"Tryck: {netatmo_data['pressure']} hPa")
            if 'outdoor_humidity' in netatmo_data:
                sensors_found.append(f"Luftfuktighet: {netatmo_data['outdoor_humidity']}%")
            if 'rain' in netatmo_data:
                sensors_found.append(f"Regn: {netatmo_data['rain']:.2f}mm/h")

            self.logger.info(f"🏠 Netatmo sensorer: {', '.join(sensors_found)}")

            return netatmo_data

        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av Netatmo-data: {e}")
            return {}

    def get_uv_data(self) -> Dict[str, Any]:
        """
        NYTT: Hämta UV-index från CurrentUVIndex.com API
        
        Returns:
            Dict med UV-data eller tom dict vid fel
        """
        # Kontrollera cache (6 timmar)
        if time.time() - self.uv_cache['timestamp'] < 21600:  # 6h = 21600s
            if self.uv_cache['data']:
                self.logger.info("☀️ Använder cachad UV-data")
                return self.uv_cache['data']

        try:
            self.logger.info("☀️ Hämtar UV-index från CurrentUVIndex.com...")

            # API-anrop med koordinater från config
            url = f"{self.uv_api_url}?latitude={self.latitude}&longitude={self.longitude}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Nuvarande UV
            current_uv = data.get('now', {}).get('uvi', 0)

            # Max UV från prognos (dagens peak)
            max_uv = current_uv
            peak_hour = datetime.now().hour

            if 'forecast' in data and isinstance(data['forecast'], list):
                for forecast in data['forecast']:
                    forecast_uv = forecast.get('uvi', 0)
                    if forecast_uv > max_uv:
                        max_uv = forecast_uv
                        try:
                            forecast_time = datetime.fromisoformat(forecast['hour'].replace('Z', '+00:00'))
                            peak_hour = forecast_time.hour
                        except:
                            pass

            # Klassificera risknivå (svensk standard)
            risk_level, risk_text = self._classify_uv_risk(max_uv)

            uv_data = {
                'uv_index': round(max_uv, 1),
                'current_uv': round(current_uv, 1),
                'peak_hour': peak_hour,
                'risk_level': risk_level,
                'risk_text': risk_text,
                'timestamp': datetime.now().isoformat(),
                'source': 'CurrentUVIndex.com'
            }

            # Uppdatera cache
            self.uv_cache = {'data': uv_data, 'timestamp': time.time()}

            self.logger.info(f"☀️ UV-index: {uv_data['uv_index']} ({risk_text})")
            return uv_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ UV API-fel: {e}")
            
            # Fallback till gammal cache om tillgänglig
            if self.uv_cache['data']:
                self.logger.info("☀️ Använder gammal UV-cache som fallback")
                return self.uv_cache['data']
                
            return {}
        except Exception as e:
            self.logger.error(f"❌ UV parsningsfel: {e}")
            return {}

    def _classify_uv_risk(self, uv_index: float) -> tuple:
        """
        Klassificera UV-risk enligt Strålsäkerhetsmyndigheten
        
        Args:
            uv_index: UV-indexvärde
            
        Returns:
            Tuple (risk_level, risk_text)
        """
        if uv_index <= 2:
            return ('low', 'Låg')
        elif uv_index <= 5:
            return ('moderate', 'Måttlig')
        elif uv_index <= 7:
            return ('high', 'Hög')
        elif uv_index <= 10:
            return ('very_high', 'Mycket hög')
        else:
            return ('extreme', 'Extrem')

    def get_smhi_forecast_data(self) -> Dict[str, Any]:
        """
        NYTT: Hämta full SMHI forecast data för cykel-analys
        (Separerat från get_smhi_data för att få full timeSeries)

        Returns:
            Full SMHI forecast data med timeSeries
        """
        try:
            self.logger.debug("📡 Hämtar full SMHI forecast för cykel-analys...")

            url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{self.longitude}/lat/{self.latitude}/data.json"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            self.logger.debug(f"✅ Full SMHI forecast hämtad ({len(data.get('timeSeries', []))} tidpunkter)")
            return data

        except Exception as e:
            self.logger.error(f"❌ SMHI forecast API-fel: {e}")
            return {}

    def get_smhi_data(self) -> Dict[str, Any]:
        """FAS 1: Hämta SMHI väderdata NU MED VINDRIKTNING + VINDBYAR"""
        # Kontrollera cache (30 min för SMHI)
        if time.time() - self.smhi_cache['timestamp'] < 1800:
            if self.smhi_cache['data']:
                self.logger.info("📋 Använder cachad SMHI-data")
                return self.smhi_cache['data']

        try:
            self.logger.info("📡 Hämtar SMHI-data...")

            url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{self.longitude}/lat/{self.latitude}/data.json"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Hitta närmaste prognos (nu) och morgondagens 12:00
            time_series = data['timeSeries']

            current_forecast = time_series[0] if time_series else None

            # Hitta morgondagens 12:00 prognos
            tomorrow_forecast = None
            now = datetime.now()
            for forecast in time_series:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                tomorrow = now + timedelta(days=1)
                if (forecast_time.date() == tomorrow.date() and
                    forecast_time.hour == 12):
                    tomorrow_forecast = forecast
                    break

            # Extrahera data - NU MED VINDRIKTNING + VINDBYAR!
            smhi_data = self.parse_smhi_forecast(current_forecast, tomorrow_forecast)

            # Uppdatera cache
            self.smhi_cache = {'data': smhi_data, 'timestamp': time.time()}

            self.logger.info("✅ SMHI-data hämtad MED VINDRIKTNING + VINDBYAR")
            return smhi_data

        except Exception as e:
            self.logger.error(f"❌ SMHI API-fel: {e}")
            return {}

    def get_sun_data(self) -> Dict[str, Any]:
        """
        Hämta exakta soltider med SunCalculator

        Returns:
            Dict med soldata eller tom dict vid fel
        """
        # Kontrollera cache (4 timmar för soltider)
        if time.time() - self.sun_cache['timestamp'] < 14400:
            if self.sun_cache['data']:
                self.logger.info("📋 Använder cachade soltider")
                return self.sun_cache['data']

        try:
            self.logger.info("☀️ Hämtar exakta soltider...")

            # Använd SunCalculator för exakta soltider (om tillgänglig)
            if self.sun_calculator:
                sun_data = self.sun_calculator.get_sun_times(
                    latitude=self.latitude,
                    longitude=self.longitude
                )
            else:
                # Fallback: förenklad beräkning
                self.logger.info("⚠️ SunCalculator ej tillgänglig - använder förenklad beräkning")
                return {}

            # Uppdatera cache
            self.sun_cache = {'data': sun_data, 'timestamp': time.time()}

            source = sun_data.get('source', 'unknown')
            cached = sun_data.get('cached', False)
            self.logger.info(f"✅ Soltider hämtade från {source} (cached: {cached})")

            return sun_data

        except Exception as e:
            self.logger.error(f"❌ Soldata-fel: {e}")
            return {}

    def parse_smhi_forecast(self, current: Dict, tomorrow: Dict) -> Dict[str, Any]:
        """FAS 1: Parsa SMHI prognos-data - UTÖKAD MED VINDRIKTNING för cykel-väder + nederbörd + VINDBYAR"""
        data = {
            'source': 'smhi',
            'location': self.location_name,
            'timestamp': datetime.now().isoformat()
        }

        if current:
            # Aktuell väderdata
            for param in current['parameters']:
                if param['name'] == 't':  # Temperatur (kommer att överskrivas av Netatmo)
                    data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':  # Vädersymbol
                    data['weather_symbol'] = param['values'][0]
                    data['weather_description'] = self.get_weather_description(param['values'][0])
                elif param['name'] == 'ws':  # Vindstyrka
                    data['wind_speed'] = param['values'][0]
                elif param['name'] == 'wd':  # FAS 1: VINDRIKTNING TILLAGD
                    data['wind_direction'] = float(param['values'][0])
                elif param['name'] == 'gust':  # NYTT: VINDBYAR TILLAGD
                    data['wind_gust'] = param['values'][0]
                    self.logger.info(f"💨 VINDBYAR hämtad från SMHI: {param['values'][0]} m/s")
                elif param['name'] == 'msl':  # Lufttryck (kommer att överskrivas av Netatmo)
                    data['pressure'] = round(param['values'][0], 0)
                elif param['name'] == 'pmin':  # NYTT: Nederbörd mm/h
                    data['precipitation'] = param['values'][0]
                elif param['name'] == 'pcat':  # NYTT: Nederbörd-typ
                    data['precipitation_type'] = param['values'][0]

        if tomorrow:
            # Morgondagens väder
            tomorrow_data = {}
            for param in tomorrow['parameters']:
                if param['name'] == 't':
                    tomorrow_data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':
                    tomorrow_data['weather_symbol'] = param['values'][0]
                    tomorrow_data['weather_description'] = self.get_weather_description(param['values'][0])
                # FAS 1: Lägg till vinddata för imorgon också
                elif param['name'] == 'ws':
                    tomorrow_data['wind_speed'] = param['values'][0]
                elif param['name'] == 'wd':
                    tomorrow_data['wind_direction'] = float(param['values'][0])
                elif param['name'] == 'gust':  # NYTT: VINDBYAR för imorgon
                    tomorrow_data['wind_gust'] = param['values'][0]
                # NYTT: Lägg till nederbörd för imorgon också
                elif param['name'] == 'pmin':
                    tomorrow_data['precipitation'] = param['values'][0]
                elif param['name'] == 'pcat':
                    tomorrow_data['precipitation_type'] = param['values'][0]

            data['tomorrow'] = tomorrow_data

        return data

    def get_weather_description(self, symbol: int) -> str:
        """Konvertera SMHI vädersymbol till beskrivning"""
        descriptions = {
            1: "Klart", 2: "Mest klart", 3: "Växlande molnighet",
            4: "Halvklart", 5: "Molnigt", 6: "Mulet",
            7: "Dimma", 8: "Lätta regnskurar", 9: "Måttliga regnskurar",
            10: "Kraftiga regnskurar", 11: "Åskväder", 12: "Lätt snöblandad regn",
            13: "Måttlig snöblandad regn", 14: "Kraftig snöblandad regn",
            15: "Lätta snöbyar", 16: "Måttliga snöbyar", 17: "Kraftiga snöbyar",
            18: "Lätt regn", 19: "Måttligt regn", 20: "Kraftigt regn",
            21: "Åska", 22: "Lätt snöblandad regn", 23: "Måttlig snöblandad regn",
            24: "Kraftig snöblandad regn", 25: "Lätt snöfall", 26: "Måttligt snöfall",
            27: "Kraftigt snöfall"
        }
        return descriptions.get(symbol, "Okänt väder")

    def get_observations_synchronized_description(self, weather_symbol: int, observations_precipitation: float) -> str:
        """
        NYTT: Synkronisera weather description med observations för konsistent regnkläder-info

        Löser problemet:
        - Weather symbol 18 = "Lätt regn"
        - Men observations = 0mm/h (regnar inte faktiskt)
        - Ändra till "Regn väntat" istället för "Lätt regn"

        Args:
            weather_symbol: SMHI weather symbol (1-27)
            observations_precipitation: Verklig nederbörd från observations (mm/h)

        Returns:
            Synkroniserad weather description
        """
        try:
            # Hämta original beskrivning
            original_description = self.get_weather_description(weather_symbol)

            # Regn-symboler som kan behöva synkronisering
            rain_symbols = {
                8: "regnskurar",     # Lätta regnskurar
                9: "regnskurar",     # Måttliga regnskurar
                10: "regnskurar",    # Kraftiga regnskurar
                18: "regn",          # Lätt regn
                19: "regn",          # Måttligt regn
                20: "regn",          # Kraftigt regn
                21: "åska",          # Åska
                22: "snöblandad regn", # Lätt snöblandad regn
                23: "snöblandad regn", # Måttlig snöblandad regn
                24: "snöblandad regn"  # Kraftig snöblandad regn
            }

            # Om weather symbol indikerar regn MEN observations visar 0mm/h
            if weather_symbol in rain_symbols and observations_precipitation == 0:
                rain_type = rain_symbols[weather_symbol]

                # Ändra från "regnar nu" till "regn väntat"
                synchronized_description = original_description.replace(
                    rain_type, f"{rain_type} väntat"
                ).replace(
                    "Lätta", "Lätta"  # Behåll intensitet
                ).replace(
                    "Måttliga", "Måttliga"  # Behåll intensitet
                ).replace(
                    "Kraftiga", "Kraftiga"  # Behåll intensitet
                )

                # Special case för åska
                if weather_symbol == 21:
                    synchronized_description = "Åska väntat"

                self.logger.info(f"🔄 SMHI-synkronisering: '{original_description}' → '{synchronized_description}' (observations: {observations_precipitation}mm/h)")
                return synchronized_description

            # Ingen synkronisering behövd - returnera original
            return original_description

        except Exception as e:
            self.logger.error(f"❌ Fel vid weather description synkronisering: {e}")
            return self.get_weather_description(weather_symbol)  # Fallback till original

    def combine_weather_data(self, smhi_data: Dict, netatmo_data: Dict, sun_data: Dict, observations_data: Dict = None, uv_data: Dict = None) -> Dict[str, Any]:
        """
        INTELLIGENT KOMBINERING: Netatmo lokala mätningar + Weather Provider (SMHI/YR) prognoser + OBSERVATIONS prioriterat + UV-INDEX
        NYTT: NETATMO RAIN GAUGE HÖGSTA PRIORITET för nederbörd (5 min fördröjning)
        UTÖKAD: Med SMHI Observations prioritering för nederbörd + FAS 1: VINDRIKTNING + VINDBYAR + UV-INDEX
        FAS 2: Stöd för YR Provider (global coverage)
        NYTT: SMHI-inkonsistens fix - synkroniserar weather description med observations

        NEDERBÖRDS-PRIORITERING (NY):
        1. Netatmo Rain Gauge (5 min fördröjning) - HÖGSTA PRIORITET
           → Om Netatmo säger 0mm → regnar INTE (även om provider säger annat)
           → Om Netatmo API-fel → fortsätt till steg 2
        2. SMHI Observations (10-60 min fördröjning) - Fallback (endast för SMHI provider)
        3. Weather Provider Prognoser (SMHI/YR) - Sista fallback

        Args:
            smhi_data: Weather provider data (SMHI eller YR: prognoser, vind, nederbörd, VINDRIKTNING, VINDBYAR)
            netatmo_data: Netatmo sensordata (temperatur, tryck, RAIN GAUGE)
            sun_data: Exakta soltider från SunCalculator
            observations_data: SMHI observations (senaste timmen, endast för SMHI provider)
            uv_data: UV-index från CurrentUVIndex.com

        Returns:
            Optimalt kombinerad väderdata med Netatmo Rain Gauge-prioritering + observations + provider weather + VINDRIKTNING + VINDBYAR + UV-INDEX
        """
        combined = {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name
        }

        # PRIORITERING: Netatmo för lokala mätningar, NETATMO RAIN GAUGE för nederbörd, OBSERVATIONS för fallback, Weather Provider (SMHI/YR) för prognoser + VINDRIKTNING + VINDBYAR

        # TEMPERATUR: Netatmo utomhus > SMHI
        if netatmo_data and 'temperature' in netatmo_data:
            combined['temperature'] = netatmo_data['temperature']
            combined['temperature_source'] = 'netatmo'
        elif smhi_data and 'temperature' in smhi_data:
            combined['temperature'] = smhi_data['temperature']
            combined['temperature_source'] = 'smhi'

        # LUFTTRYCK: Netatmo inomhus > SMHI
        if netatmo_data and 'pressure' in netatmo_data:
            combined['pressure'] = netatmo_data['pressure']
            combined['pressure_source'] = 'netatmo'
        elif smhi_data and 'pressure' in smhi_data:
            combined['pressure'] = smhi_data['pressure']
            combined['pressure_source'] = 'smhi'

        # ============================================
        # NEDERBÖRD: NETATMO RAIN GAUGE prioriterat HÖGST!
        # ============================================

        netatmo_rain_valid = False

        # STEG 1: Försök använda Netatmo Rain Gauge (HÖGSTA PRIORITET)
        if netatmo_data and 'rain' in netatmo_data:
            # Kontrollera att regndata är färsk (max 10 min gammal)
            rain_age = netatmo_data.get('rain_age_minutes', 0)

            if rain_age <= 10:
                # ANVÄND NETATMO RAIN GAUGE
                combined['precipitation'] = netatmo_data['rain']
                combined['precipitation_source'] = 'netatmo_rain_gauge'
                combined['precipitation_age_minutes'] = rain_age

                # Spara även detaljer om regnmätning
                combined['rain_sum_1h'] = netatmo_data.get('rain_sum_1h', 0)
                combined['rain_sum_24h'] = netatmo_data.get('rain_sum_24h', 0)
                combined['rain_last_measurement'] = netatmo_data.get('rain_last_measurement')

                netatmo_rain_valid = True

                if netatmo_data['rain'] > 0:
                    self.logger.info(f"🎯 PRIORITERING: Nederbörd från Netatmo Rain Gauge ({netatmo_data['rain']:.2f}mm/h, {rain_age:.1f} min gammal)")
                else:
                    self.logger.info(f"🎯 PRIORITERING: Netatmo Rain Gauge säger 0mm → REGNAR INTE (även om andra källor säger annat)")
            else:
                self.logger.warning(f"⚠️ Netatmo Rain Gauge data för gammal ({rain_age:.1f} min) - använder fallback")

        # STEG 2: Om Netatmo Rain Gauge saknas/för gammal → SMHI Observations (FALLBACK)
        if not netatmo_rain_valid:
            if observations_data and 'precipitation_observed' in observations_data:
                # Använd observations för huvudvärdet
                combined['precipitation'] = observations_data['precipitation_observed']
                combined['precipitation_source'] = 'smhi_observations'

                # Behåll observations-data för detaljerad info
                combined['precipitation_observed'] = observations_data['precipitation_observed']
                combined['observation_time'] = observations_data.get('observation_time')
                combined['observation_quality'] = observations_data.get('quality', 'U')
                combined['observation_station'] = observations_data.get('station_id')
                combined['observation_age_minutes'] = observations_data.get('data_age_minutes', 0)

                self.logger.info(f"🔄 FALLBACK: Nederbörd från SMHI Observations ({observations_data['precipitation_observed']}mm/h) - Netatmo Rain Gauge ej tillgänglig")

            # STEG 3: Om både Netatmo och Observations saknas → SMHI Prognoser (SISTA FALLBACK)
            elif smhi_data and 'precipitation' in smhi_data:
                # Fallback till SMHI prognoser
                combined['precipitation'] = smhi_data['precipitation']
                combined['precipitation_source'] = 'smhi_forecast'
                self.logger.debug("🔄 FALLBACK: Nederbörd från SMHI prognoser (varken Netatmo Rain Gauge eller Observations tillgänglig)")

        # FAS 1: VINDDATA från SMHI (nu både styrka, riktning och VINDBYAR!)
        if smhi_data:
            combined['wind_speed'] = smhi_data.get('wind_speed', 0.0)
            combined['wind_direction'] = smhi_data.get('wind_direction', 0.0)  # FAS 1: TILLAGT

            # NYTT: VINDBYAR om tillgänglig
            if 'wind_gust' in smhi_data:
                combined['wind_gust'] = smhi_data['wind_gust']
                self.logger.debug(f"💨 VINDBYAR: {smhi_data['wind_gust']} m/s kombinerad med vinddata")

            # Logga vinddata för debugging
            if 'wind_speed' in smhi_data and 'wind_direction' in smhi_data:
                if 'wind_gust' in smhi_data:
                    self.logger.debug(f"💨 KOMPLETT vinddata - Medel: {smhi_data['wind_speed']} m/s, Byar: {smhi_data['wind_gust']} m/s, Riktning: {smhi_data['wind_direction']}°")
                else:
                    self.logger.debug(f"🌬️ FAS 1: Komplett vinddata - {smhi_data['wind_speed']} m/s från {smhi_data['wind_direction']}°")

        # LUFTFUKTIGHET: Netatmo (bonus-data)
        if netatmo_data:
            if 'outdoor_humidity' in netatmo_data:
                combined['humidity'] = netatmo_data['outdoor_humidity']
                combined['humidity_source'] = 'netatmo_outdoor'
            elif 'indoor_humidity' in netatmo_data:
                combined['indoor_humidity'] = netatmo_data['indoor_humidity']

        # VÄDER OCH PROGNOSER: Alltid från weather provider (SMHI eller YR)
        if smhi_data:
            combined['weather_symbol'] = smhi_data.get('weather_symbol')

            # FAS 2: Hantera både SMHI (int) och YR (str) symboler
            weather_symbol = smhi_data.get('weather_symbol')
            
            # Kolla om det är YR (string symbol) eller SMHI (numerisk symbol)
            is_yr_provider = isinstance(weather_symbol, str)
            
            if is_yr_provider:
                # YR Provider: Använd weather_description direkt från provider
                # YR har redan korrekt beskrivning i sin data
                combined['weather_description'] = smhi_data.get('weather_description', 'Okänt väder')
                self.logger.debug(f"🌍 YR weather description: {combined['weather_description']}")
            else:
                # SMHI Provider: Synkronisera weather description med ACTIVE nederbördskälla
                # Om Netatmo Rain Gauge är aktiv, synkronisera med den
                # Annars synkronisera med observations om tillgänglig
                if netatmo_rain_valid and weather_symbol:
                    combined['weather_description'] = self.get_observations_synchronized_description(
                        weather_symbol,
                        netatmo_data.get('rain', 0.0)
                    )
                elif observations_data and weather_symbol:
                    combined['weather_description'] = self.get_observations_synchronized_description(
                        weather_symbol,
                        observations_data.get('precipitation_observed', 0.0)
                    )
                else:
                    # Fallback till original description
                    combined['weather_description'] = smhi_data.get('weather_description', 'Okänt väder')

            # Nederbörd-typ från prognoser (observations och Netatmo har ingen typ-info)
            combined['precipitation_type'] = smhi_data.get('precipitation_type')
            combined['tomorrow'] = smhi_data.get('tomorrow', {})

        # SOLTIDER: Exakta från SunCalculator
        if sun_data:
            combined['sun_data'] = {
                'sunrise': sun_data.get('sunrise'),
                'sunset': sun_data.get('sunset'),
                'sunrise_time': sun_data.get('sunrise_time'),
                'sunset_time': sun_data.get('sunset_time'),
                'daylight_duration': sun_data.get('daylight_duration'),
                'sun_source': sun_data.get('source', 'unknown')
            }

            # För bakåtkompatibilitet med main.py
            combined['sunrise'] = sun_data.get('sunrise')
            combined['sunset'] = sun_data.get('sunset')

        # BONUS NETATMO-DATA (för framtida användning)
        if netatmo_data:
            combined['netatmo_extras'] = {}
            for key in ['co2', 'noise', 'indoor_temperature', 'station_name', 'last_measurement', 'outdoor_battery', 'rain_battery']:
                if key in netatmo_data:
                    combined['netatmo_extras'][key] = netatmo_data[key]

        # NYTT: 3-TIMMARS TRYCKTREND (meteorologisk standard) MED PRELIMINÄR TREND-STÖD
        pressure_trend = self.calculate_3h_pressure_trend()
        combined['pressure_trend'] = pressure_trend

        # DEBUG: Visa exakt vad vi får från trend-beräkningen
        self.logger.info(f"🔍 DEBUG pressure_trend: {pressure_trend}")

        # Lägg till trend-beskrivning för display - NU MED TILDE FÖR PRELIMINÄR
        if pressure_trend['trend'] in ['rising', 'falling', 'stable']:
            # Bastext för trend
            trend_texts = {
                'rising': 'Stigande',
                'falling': 'Fallande',
                'stable': 'Stabilt'
            }
            base_text = trend_texts[pressure_trend['trend']]

            # NYTT: Lägg till tilde (~) för preliminär trend
            if pressure_trend.get('is_preliminary', False):
                combined['pressure_trend_text'] = f"~{base_text}"
                self.logger.info(f"🎯 Använder PRELIMINÄR trend: ~{pressure_trend['trend']} → '{combined['pressure_trend_text']}' ({pressure_trend['period_hours']:.1f}h data)")
            else:
                combined['pressure_trend_text'] = base_text
                self.logger.info(f"🎯 Använder RIKTIG trend: {pressure_trend['trend']} → '{combined['pressure_trend_text']}' ({pressure_trend['period_hours']:.1f}h data)")

            combined['pressure_trend_arrow'] = pressure_trend['trend']
        else:
            # Fallback för otillräcklig data - TYDLIGT meddelande
            combined['pressure_trend_text'] = 'Samlar data'
            combined['pressure_trend_arrow'] = 'stable'  # Horisontell pil under uppbyggnad
            self.logger.info(f"🎯 Otillräcklig data: {pressure_trend['trend']} → 'Samlar data'")

        # DATAKÄLLA-SAMMANFATTNING + FAS 1: VINDRIKTNING + VINDBYAR + NETATMO RAIN GAUGE
        sources = []
        if netatmo_rain_valid:
            sources.append("Netatmo-Rain")
        if observations_data and not netatmo_rain_valid:
            sources.append("Observations")
        if netatmo_data:
            if 'temperature' in netatmo_data:
                sources.append("Netatmo-temp")
            if 'pressure' in netatmo_data:
                sources.append("Netatmo-tryck")
        if smhi_data:
            sources.append("SMHI-prognos")
            if 'wind_direction' in smhi_data:
                sources.append("SMHI-vindriktning")  # FAS 1: Tillagt
            if 'wind_gust' in smhi_data:
                sources.append("SMHI-vindbyar")  # NYTT: Tillagt

        combined['data_sources'] = sources

        # UV-INDEX: Lägg till om tillgänglig
        if uv_data:
            combined['uv_index'] = uv_data.get('uv_index', 0)
            combined['uv_current'] = uv_data.get('current_uv', 0)
            combined['uv_risk_level'] = uv_data.get('risk_level', 'low')
            combined['uv_risk_text'] = uv_data.get('risk_text', 'Låg')
            combined['uv_peak_hour'] = uv_data.get('peak_hour', 12)
            combined['uv_source'] = uv_data.get('source', 'CurrentUVIndex.com')
            sources.append("UV-index")

        # === SÄKER TEST-DATA OVERRIDE ===
        test_override = self._load_test_data_if_enabled()
        if test_override:
            combined = self._apply_test_overrides(combined, test_override)

        return combined

    def get_fallback_data(self) -> Dict[str, Any]:
        """Fallback-data vid API-fel - UTÖKAD MED CYKEL-VÄDER fallback + OBSERVATIONS + FAS 1: VINDRIKTNING + VINDBYAR + NETATMO RAIN GAUGE"""
        return {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name,
            'temperature': 20.0,
            'weather_description': 'Data ej tillgänglig',
            'weather_symbol': 1,
            'pressure': 1013,
            'temperature_source': 'fallback',
            'pressure_source': 'fallback',
            'precipitation': 0.0,  # NYTT
            'precipitation_type': 0,  # NYTT
            'precipitation_source': 'fallback',
            'precipitation_observed': 0.0,  # NYTT: Observations fallback
            'forecast_precipitation_2h': 0.0,  # FIXAD: Lägg till för trigger
            # FAS 1: VINDRIKTNING fallback + VINDBYAR + NETATMO RAIN GAUGE
            'wind_speed': 0.0,
            'wind_direction': 0.0,
            'wind_gust': 0.0,  # NYTT: Vindby fallback
            'rain': 0.0,  # NYTT: Netatmo Rain Gauge fallback
            'tomorrow': {
                'temperature': 18.0,
                'weather_description': 'Okänt',
                'wind_speed': 0.0,        # FAS 1: Fallback vinddata
                'wind_direction': 0.0,    # FAS 1: Fallback vindriktning
                'wind_gust': 0.0          # NYTT: Fallback vindbyar
            },
            # Fallback soltider
            'sun_data': {
                'sunrise': datetime.now().replace(hour=6, minute=0).isoformat(),
                'sunset': datetime.now().replace(hour=18, minute=0).isoformat(),
                'daylight_duration': '12h 0m',
                'sun_source': 'fallback'
            },
            # NYTT: Fallback cykel-väder
            'cycling_weather': {
                'cycling_warning': False,
                'precipitation_mm': 0.0,
                'precipitation_type': 'Ingen',
                'reason': 'Fallback data - ingen nederbörd-info'
            },
            'data_sources': ['fallback']
        }


def test_weather_client():
    """
    FAS 1: UPPDATERAD Test-funktion med VINDRIKTNING-verifiering + VINDBYAR + NETATMO RAIN GAUGE

    Testar säkra test-data injection system och korrekt SMHI Observations integration + VINDRIKTNING + VINDBYAR + NETATMO RAIN GAUGE
    """
    print("💨 Test av WeatherClient MED NETATMO RAIN GAUGE + VINDRIKTNING + VINDBYAR + SMHI OBSERVATIONS + CYKEL-VÄDER + TEST-DATA")
    print("=" * 90)

    try:
        # FIXAD: Läs från samma config.json som produktionssystemet
        config_path = "config.json"  # Antaget från projektrot

        # Försök läsa från aktuell katalog först
        if not os.path.exists(config_path):
            # Om vi kör från modules/ katalog, gå upp en nivå
            config_path = "../config.json"

        if not os.path.exists(config_path):
            print("❌ Kunde inte hitta config.json - kör från rätt katalog!")
            return False

        # Läs konfiguration från fil
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Display configuration that will be used
        smhi_observations = config.get('smhi_observations', {})
        print(f"📁 CONFIGURATION (from {config_path}):")
        print(f"   Station ID: {smhi_observations.get('primary_station_id', 'Missing')}")
        print(f"   Station name: {smhi_observations.get('primary_station_name', 'Missing')}")
        print(f"   Debug aktiverat: {config.get('debug', {}).get('enabled', False)}")
        print(f"   Test-data tillåtet: {config.get('debug', {}).get('allow_test_data', False)}")

        print(f"\n🌧️ NETATMO RAIN GAUGE + 🌬️ VINDRIKTNING + 💨 VINDBYAR API-UTÖKNING TEST:")
        print(f"   🎯 Målparametrar: 'Rain' (Netatmo NAModule3) + 'wd' (wind direction) + 'gust' (wind gusts) från SMHI")
        print(f"   📊 Befintlig parameter: 'ws' (wind speed) ska fungera som vanligt")
        print(f"   🔄 Styrka, riktning, vindbyar OCH regn ska finnas i weather_data")
        print(f"   🏆 PRIORITERING: Netatmo Rain > SMHI Obs > SMHI Prognos")

        print(f"\n🚀 KÖR WEATHERCLIENT-TEST MED NETATMO RAIN GAUGE:")
        print("-" * 60)

        # Setup logging för test
        logging.basicConfig(level=logging.INFO)

        # Skapa och testa klient
        client = WeatherClient(config)
        weather_data = client.get_current_weather()

        print(f"\n📊 NETATMO RAIN GAUGE + VINDRIKTNING + VINDBYAR TEST-RESULTAT:")
        print("-" * 50)

        # Specifika tester för regndata
        precipitation = weather_data.get('precipitation', 'SAKNAS')
        precip_source = weather_data.get('precipitation_source', 'SAKNAS')

        print(f"🌧️ NEDERBÖRD VERIFIERING:")
        print(f"   📊 Nederbörd: {precipitation} mm/h")
        print(f"   🎯 Källa: {precip_source}")

        if precip_source == 'netatmo_rain_gauge':
            print(f"   ✅ FRAMGÅNG: Netatmo Rain Gauge är primär källa!")
            rain_age = weather_data.get('precipitation_age_minutes', 'N/A')
            print(f"   ⏱️ Data-ålder: {rain_age} minuter")
            print(f"   📈 Summa 1h: {weather_data.get('rain_sum_1h', 'N/A')} mm")
            print(f"   📈 Summa 24h: {weather_data.get('rain_sum_24h', 'N/A')} mm")
        elif precip_source == 'smhi_observations':
            print(f"   🔄 FALLBACK: SMHI Observations används (Netatmo Rain Gauge ej tillgänglig)")
        elif precip_source == 'smhi_forecast':
            print(f"   ⚠️ FALLBACK: SMHI Prognoser används (varken Netatmo eller Observations tillgänglig)")
        else:
            print(f"   ❌ PROBLEM: Okänd källa eller ingen nederbörd-data")

        # Specifika tester för vinddata
        wind_speed = weather_data.get('wind_speed', 'SAKNAS')
        wind_direction = weather_data.get('wind_direction', 'SAKNAS')
        wind_gust = weather_data.get('wind_gust', 'SAKNAS')

        print(f"\n🌬️ VINDDATA VERIFIERING:")
        print(f"   📊 Vindstyrka (ws): {wind_speed} m/s")
        print(f"   🧭 Vindriktning (wd): {wind_direction}° {'✅ FUNKAR' if wind_direction != 'SAKNAS' else '❌ SAKNAS'}")
        print(f"   💨 Vindbyar (gust): {wind_gust} m/s {'✅ FUNKAR' if wind_gust != 'SAKNAS' else '❌ SAKNAS'}")

        if wind_direction != 'SAKNAS' and wind_gust != 'SAKNAS':
            print(f"   🎯 FULLSTÄNDIG FRAMGÅNG: Alla tre vindparametrar hämtade från SMHI!")
            # Beräkna gust/wind ratio för validering
            if wind_speed > 0 and wind_gust != 'SAKNAS':
                ratio = float(wind_gust) / float(wind_speed)
                print(f"   📈 Gust/Wind ratio: {ratio:.2f} ({'Normal' if 1.0 <= ratio <= 3.0 else 'Ovanlig'})")
        elif wind_direction != 'SAKNAS':
            print(f"   ⚠️ DELVIS: Vindriktning OK men vindbyar saknas")
        else:
            print(f"   ❌ PROBLEM: Vindriktning saknas - kontrollera parse_smhi_forecast()")

        # Visa även morgondagens vinddata om tillgängligt
        tomorrow = weather_data.get('tomorrow', {})
        if tomorrow.get('wind_speed') is not None and tomorrow.get('wind_direction') is not None:
            tomorrow_gust = tomorrow.get('wind_gust', 'N/A')
            print(f"   📅 Imorgon: {tomorrow['wind_speed']} m/s från {tomorrow['wind_direction']}° (byar: {tomorrow_gust})")

        # Specificera tester för SMHI Observations (befintlig från före Fas 1)
        observations_tested = 'precipitation_observed' in weather_data
        print(f"\n🌧️ SMHI Observations: {'✅ Fungerar' if observations_tested else '❌ Ej tillgänglig'}")

        if observations_tested:
            print(f"   📍 Station: {weather_data.get('observation_station', 'Okänd')}")
            print(f"   📊 Nederbörd: {weather_data.get('precipitation_observed', 0)}mm/h")
            print(f"   🕐 Ålder: {weather_data.get('observation_age_minutes', 0):.1f} min")
            print(f"   ✅ Kvalitet: {weather_data.get('observation_quality', 'Okänd')}")

        # Data-prioritering test
        print(f"\n🎯 PRIORITERING:")
        print(f"   🌡️ Temperatur: {weather_data.get('temperature_source', 'N/A')}")
        print(f"   📊 Tryck: {weather_data.get('pressure_source', 'N/A')}")
        print(f"   🌧️ Nederbörd: {weather_data.get('precipitation_source', 'N/A')}")

        # Cykel-väder test (befintlig)
        cycling = weather_data.get('cycling_weather', {})
        print(f"\n🚴‍♂️ CYKEL-VÄDER:")
        print(f"   Varning: {'⚠️ Aktiv' if cycling.get('cycling_warning', False) else '✅ OK'}")
        print(f"   Nederbörd: {cycling.get('precipitation_mm', 0):.1f}mm/h")
        print(f"   Typ: {cycling.get('precipitation_type', 'Okänd')}")
        print(f"   Tid: {cycling.get('forecast_time', 'N/A')}")
        print(f"   Orsak: {cycling.get('reason', 'N/A')}")

        # Visa forecast_precipitation_2h för trigger debugging
        forecast_2h = weather_data.get('forecast_precipitation_2h', 0.0)
        print(f"\n🎯 TRIGGER DATA:")
        print(f"   precipitation: {weather_data.get('precipitation', 0.0)}mm/h")
        print(f"   forecast_precipitation_2h: {forecast_2h}mm/h")
        print(f"   TRIGGER CONDITION: precipitation > 0 OR forecast_precipitation_2h > 0.2")
        print(f"   SKULLE TRIGGA: {weather_data.get('precipitation', 0.0) > 0 or forecast_2h > 0.2}")

        # Test SMHI-inkonsistens fix
        print(f"\n🔄 SMHI-INKONSISTENS FIX:")
        print(f"   Weather description: {weather_data.get('weather_description', 'N/A')}")
        print(f"   Weather symbol: {weather_data.get('weather_symbol', 'N/A')}")
        if observations_tested or precip_source == 'netatmo_rain_gauge':
            print(f"   Synkroniserad med verklig nederbörd: {'✅ Ja' if 'väntat' in weather_data.get('weather_description', '') else '📊 Ingen konflikt'}")

        # Test-data status
        if weather_data.get('test_mode'):
            print(f"\n🧪 TEST-LÄGE AKTIVT:")
            print(f"   📝 Beskrivning: {weather_data.get('test_description', 'N/A')}")
            print(f"   ⚠️ VIKTIGT: Detta är test-data, inte riktiga mätningar!")

        # Datakällor
        sources = weather_data.get('data_sources', [])
        print(f"\n📡 DATAKÄLLOR: {', '.join(sources) if sources else 'Ingen data'}")

        print(f"\n✅ KOMPLETT TEST SLUTFÖRT - WeatherClient med NETATMO RAIN GAUGE + VINDRIKTNING + VINDBYAR!")

        # Sammanfattning baserat på resultat
        if precip_source == 'netatmo_rain_gauge':
            print(f"🏆 NETATMO RAIN GAUGE FRAMGÅNG: Regnmätare är primär källa för nederbörd")
            print(f"🌧️ Nederbörd: {precipitation}mm/h från Netatmo (5 min fördröjning)")
            print(f"📊 Data redo för prioriterad visning på E-Paper")

        if wind_direction != 'SAKNAS' and wind_gust != 'SAKNAS':
            print(f"🎯 FULLSTÄNDIG FRAMGÅNG: API-utökning för vindriktning + vindbyar KLAR")
            print(f"🌬️ Alla tre vindparametrar hämtade från SMHI:")
            print(f"   - Vindstyrka: {wind_speed} m/s")
            print(f"   - Vindriktning: {wind_direction}°")
            print(f"   - Vindbyar: {wind_gust} m/s")
            print(f"🔧 parse_smhi_forecast() nu utökad med både 'wd' och 'gust' parametrar")
            print(f"📊 Data redo för WindRenderer att visa 'X m/s (Y)' format")
        elif wind_direction != 'SAKNAS':
            print(f"🎯 DELVIS FRAMGÅNG: Vindriktning OK, vindbyar saknas")
            print(f"🔧 Kontrollera att 'gust' parameter finns i SMHI API-svaret")
        else:
            print(f"❌ PROBLEM: Vindriktning saknas")
            print(f"🔧 Kontrollera att 'wd' parameter läggs till i parse_smhi_forecast()")

        return True

    except Exception as e:
        print(f"❌ Test misslyckades: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Huvud-funktion för att köra test"""
    test_weather_client()


if __name__ == "__main__":
    main()

# ============================================================
# HÄR SLUTAR DEL TVÅ
# ============================================================

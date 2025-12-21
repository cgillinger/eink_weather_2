"""
SMHI Weather Provider - Sweden only

Provides weather forecasts and real-time observations for Sweden
using SMHI (Swedish Meteorological and Hydrological Institute) APIs.

Features:
- Weather forecasts (point forecasts)
- Real-time observations from weather stations
- Precipitation category filtering (snow vs rain)
- Cycling weather analysis
- 27 SMHI weather symbols
"""

from typing import Dict, Any, Optional
import logging
import time
import requests
from datetime import datetime, timedelta, timezone
import json

from .base_provider import WeatherProvider


class SMHIWeatherProvider(WeatherProvider):
    """
    SMHI weather provider implementation
    
    Supports:
    - Point forecasts for any location in Sweden
    - Real-time observations from weather stations
    - Precipitation type filtering (pcat)
    - 27 SMHI weather symbols with day/night variants
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SMHI provider
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # SMHI-specific configuration
        self.smhi_observations = config.get('smhi_observations', {})
        self.observations_station_id = self.smhi_observations.get('primary_station_id', '98230')
        self.alternative_station_id = self.smhi_observations.get('fallback_station_id', '97390')
        
        # Cache for API calls
        self.smhi_cache = {'data': None, 'timestamp': 0}
        self.observations_cache = {'data': None, 'timestamp': 0}
        self.forecast_cache = {'data': None, 'timestamp': 0}
        
        # SMHI API endpoints
        self.forecast_base_url = "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point"
        self.observations_base_url = "https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7"
        
        # Cycling weather threshold
        self.CYCLING_PRECIPITATION_THRESHOLD = 0.2  # mm/h
        
        # Log configuration
        station_name = self.smhi_observations.get('primary_station_name', 'Unknown station')
        self.logger.info(f"📊 SMHI Observations: Station {self.observations_station_id} ({station_name})")
        self.logger.info(f"🌧️ Netatmo Rain Gauge: Highest priority for precipitation")
        self.logger.info(f"📍 Precipitation priority: Netatmo (5min) > SMHI Obs (60min) > SMHI Forecast")
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "SMHI"
    
    def supports_observations(self) -> bool:
        """SMHI supports real-time observations from weather stations"""
        return True
    
    def get_weather_symbol(self, data: Dict) -> int:
        """
        Get SMHI weather symbol (1-27)
        
        Args:
            data: Weather data containing Wsymb2
            
        Returns:
            SMHI symbol code (1-27)
        """
        return data.get('Wsymb2', 1)
    
    # ============================================================
    # OBSERVATIONS - Real-time weather station data
    # ============================================================
    
    def get_smhi_observations(self) -> Dict[str, Any]:
        """
        Get SMHI observations data for accurate "raining now" detection
        
        Returns:
            Dict with observations data or empty dict on error
        """
        # Check cache (15 min for observations)
        cache_timeout = self.config.get('update_intervals', {}).get('smhi_observations_seconds', 900)
        if time.time() - self.observations_cache['timestamp'] < cache_timeout:
            if self.observations_cache['data']:
                self.logger.info("📋 Using cached SMHI observations data")
                return self.observations_cache['data']
        
        try:
            self.logger.info(f"🌧️ Fetching SMHI observations from station {self.observations_station_id}...")
            
            # SMHI Observations API
            # Parameter 7 = Precipitation amount, sum 1 hour, 1 time/hour, unit: millimeter
            url = f"{self.observations_base_url}/station/{self.observations_station_id}/period/latest-hour/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse observations data
            observations_data = self.parse_smhi_observations(data)
            
            if observations_data:
                # Update cache
                self.observations_cache = {'data': observations_data, 'timestamp': time.time()}
                station_name = self.smhi_observations.get('primary_station_name', 'Station')
                precipitation = observations_data.get('precipitation_observed', 0.0)
                self.logger.info(f"✅ SMHI Observations from {station_name}: {precipitation}mm/h")
            else:
                self.logger.warning("⚠️ No valid observations data found")
            
            return observations_data
        
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️ SMHI Observations API error: {e}")
            # Try alternative station
            return self.try_alternative_station()
        except Exception as e:
            self.logger.error(f"❌ SMHI Observations parsing error: {e}")
            return {}
    
    def try_alternative_station(self) -> Dict[str, Any]:
        """
        Try to fetch observations from alternative station (Arlanda)
        
        Returns:
            Dict with observations data or empty dict on error
        """
        try:
            self.logger.info(f"🔄 Trying alternative station {self.alternative_station_id} (Arlanda)...")
            
            url = f"{self.observations_base_url}/station/{self.alternative_station_id}/period/latest-hour/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            observations_data = self.parse_smhi_observations(data)
            
            if observations_data:
                observations_data['station_id'] = self.alternative_station_id
                observations_data['station_name'] = 'Arlanda (alternative)'
                self.logger.info(f"✅ SMHI Observations from alternative station: {observations_data.get('precipitation_observed', 0)}mm/h")
                return observations_data
            
            return {}
        
        except Exception as e:
            self.logger.error(f"❌ Alternative station also failed: {e}")
            return {}
    
    def parse_smhi_observations(self, data: Dict) -> Dict[str, Any]:
        """
        Parse SMHI observations JSON and extract precipitation data
        
        Args:
            data: Raw JSON from SMHI Observations API
            
        Returns:
            Dict with parsed observations data
        """
        try:
            if 'value' not in data or not data['value']:
                self.logger.warning("⚠️ Empty observations data from SMHI")
                return {}
            
            # Latest measurement is last value in list
            latest_observation = data['value'][-1]
            
            # Extract data
            observation_time = datetime.fromtimestamp(latest_observation['date'] / 1000)  # milliseconds → seconds
            precipitation_mm = float(latest_observation['value'])
            quality = latest_observation.get('quality', 'U')  # G=good, Y=suspected, R=rejected, U=uncertain
            
            # Calculate data age
            now = datetime.now()
            data_age_minutes = (now - observation_time).total_seconds() / 60
            
            # Warning if data is too old
            if data_age_minutes > 90:
                self.logger.warning(f"⚠️ Observations data is {data_age_minutes:.0f} min old - may be outdated")
            
            # Filter out bad quality
            if quality == 'R':  # Rejected
                self.logger.warning(f"⚠️ Observations data has poor quality (R) - ignoring")
                return {}
            
            observations_data = {
                'precipitation_observed': precipitation_mm,
                'observation_time': observation_time.isoformat(),
                'quality': quality,
                'data_age_minutes': int(data_age_minutes),
                'station_id': self.observations_station_id,
                'station_name': self.smhi_observations.get('primary_station_name', 'Station')
            }
            
            return observations_data
        
        except Exception as e:
            self.logger.error(f"❌ Error parsing observations: {e}")
            return {}

# ============================================================
# HÄR SLUTAR DEL ETT
# ============================================================
# ============================================================
    # HÄR BÖRJAR DEL TVÅ
    # ============================================================
    
    # ============================================================
    # FORECASTS - Weather forecast data
    # ============================================================
    
    def get_smhi_forecast_data(self) -> Dict[str, Any]:
        """
        Get full SMHI forecast data for cycling weather analysis
        (Separated from get_smhi_data to get full timeSeries)
        
        Returns:
            Full SMHI forecast data with timeSeries
        """
        try:
            self.logger.debug("📡 Fetching full SMHI forecast for cycling analysis...")
            
            url = f"{self.forecast_base_url}/lon/{self.longitude}/lat/{self.latitude}/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            self.logger.debug(f"✅ Full SMHI forecast fetched ({len(data.get('timeSeries', []))} time points)")
            return data
        
        except Exception as e:
            self.logger.error(f"❌ SMHI forecast API error: {e}")
            return {}
    
    def get_smhi_data(self) -> Dict[str, Any]:
        """
        Get SMHI weather data with wind direction and gusts
        
        Returns:
            Dict with parsed SMHI forecast data
        """
        # Check cache (30 min for SMHI)
        cache_timeout = self.config.get('update_intervals', {}).get('smhi_seconds', 1800)
        if time.time() - self.smhi_cache['timestamp'] < cache_timeout:
            if self.smhi_cache['data']:
                self.logger.info("📋 Using cached SMHI data")
                return self.smhi_cache['data']
        
        try:
            self.logger.info("📡 Fetching SMHI data...")
            
            url = f"{self.forecast_base_url}/lon/{self.longitude}/lat/{self.latitude}/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Find nearest forecast (now) and tomorrow's 12:00
            time_series = data['timeSeries']
            
            current_forecast = time_series[0] if time_series else None
            
            # Find tomorrow's 12:00 forecast
            tomorrow_forecast = None
            now = datetime.now()
            for forecast in time_series:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                tomorrow = now + timedelta(days=1)
                if (forecast_time.date() == tomorrow.date() and
                    forecast_time.hour == 12):
                    tomorrow_forecast = forecast
                    break
            
            # Extract data - NOW WITH WIND DIRECTION + GUSTS!
            smhi_data = self.parse_smhi_forecast(current_forecast, tomorrow_forecast)
            
            # Update cache
            self.smhi_cache = {'data': smhi_data, 'timestamp': time.time()}
            
            self.logger.info("✅ SMHI data fetched WITH WIND DIRECTION + GUSTS")
            return smhi_data
        
        except Exception as e:
            self.logger.error(f"❌ SMHI API error: {e}")
            return {}
    
    def parse_smhi_forecast(self, current: Dict, tomorrow: Dict) -> Dict[str, Any]:
        """
        Parse SMHI forecast data - EXTENDED WITH WIND DIRECTION and GUSTS
        
        Args:
            current: Current forecast data point
            tomorrow: Tomorrow's 12:00 forecast data point
            
        Returns:
            Dict with parsed forecast data
        """
        data = {
            'source': 'smhi',
            'location': self.location_name,
            'timestamp': datetime.now().isoformat()
        }
        
        if current:
            # Current weather data
            for param in current['parameters']:
                if param['name'] == 't':  # Temperature (will be overridden by Netatmo)
                    data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':  # Weather symbol
                    data['weather_symbol'] = param['values'][0]
                    data['weather_description'] = self.get_weather_description(param['values'][0])
                elif param['name'] == 'ws':  # Wind speed
                    data['wind_speed'] = param['values'][0]
                elif param['name'] == 'wd':  # Wind direction
                    data['wind_direction'] = float(param['values'][0])
                elif param['name'] == 'gust':  # Wind gusts
                    data['wind_gust'] = param['values'][0]
                    self.logger.info(f"💨 Wind gusts from SMHI: {param['values'][0]} m/s")
                elif param['name'] == 'msl':  # Air pressure (will be overridden by Netatmo)
                    data['pressure'] = round(param['values'][0], 0)
                elif param['name'] == 'pmin':  # Precipitation mm/h
                    data['precipitation'] = param['values'][0]
                elif param['name'] == 'pcat':  # Precipitation type
                    data['precipitation_type'] = param['values'][0]
        
        if tomorrow:
            # Tomorrow's weather
            tomorrow_data = {}
            for param in tomorrow['parameters']:
                if param['name'] == 't':
                    tomorrow_data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':
                    tomorrow_data['weather_symbol'] = param['values'][0]
                    tomorrow_data['weather_description'] = self.get_weather_description(param['values'][0])
                elif param['name'] == 'ws':
                    tomorrow_data['wind_speed'] = param['values'][0]
                elif param['name'] == 'wd':
                    tomorrow_data['wind_direction'] = float(param['values'][0])
                elif param['name'] == 'gust':  # Wind gusts for tomorrow
                    tomorrow_data['wind_gust'] = param['values'][0]
                elif param['name'] == 'pmin':
                    tomorrow_data['precipitation'] = param['values'][0]
                elif param['name'] == 'pcat':
                    tomorrow_data['precipitation_type'] = param['values'][0]
            
            data['tomorrow'] = tomorrow_data
        
        return data
    
    # ============================================================
    # CYCLING WEATHER ANALYSIS
    # ============================================================
    
    def analyze_cycling_weather(self, smhi_forecast_data: Dict) -> Dict[str, Any]:
        """
        Analyze weather for cycling - check if precipitation expected within 2h
        FIXED: Now correctly extracts precipitation from forecast parameters
        
        Args:
            smhi_forecast_data: Full SMHI forecast data with timeSeries
            
        Returns:
            Dict with cycling weather analysis
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
                self.logger.warning("⚠️ No SMHI forecast data available for cycling analysis")
                return cycling_analysis
            
            # Analyze next 2 hours
            now = datetime.now(timezone.utc)
            two_hours_ahead = now + timedelta(hours=2)
            
            # Filter forecasts for next 2 hours
            next_hours_forecasts = []
            for forecast in smhi_forecast_data['timeSeries']:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                
                if now <= forecast_time <= two_hours_ahead:
                    next_hours_forecasts.append((forecast_time, forecast))
            
            if not next_hours_forecasts:
                self.logger.warning("⚠️ No forecasts found for next 2h")
                return cycling_analysis
            
            # Find max precipitation within 2h
            max_precipitation = 0.0
            precipitation_type_code = 0
            warning_forecast_time = None
            
            self.logger.debug(f"🔍 CYCLING WEATHER DEBUG: Analyzing {len(next_hours_forecasts)} forecasts")
            
            for forecast_time, forecast in next_hours_forecasts:
                precipitation = 0.0
                precip_type = 0
                
                try:
                    for param in forecast.get('parameters', []):
                        param_name = param.get('name', '')
                        param_values = param.get('values', [])
                        
                        if param_name == 'pmin' and param_values:  # Precipitation mm/h
                            precipitation = float(param_values[0])
                        elif param_name == 'pcat' and param_values:  # Precipitation type
                            precip_type = int(param_values[0])
                    
                    self.logger.debug(f"  {forecast_time.strftime('%H:%M')}: {precipitation}mm/h (type: {precip_type})")
                    
                    if precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                        if precipitation > max_precipitation:
                            max_precipitation = precipitation
                            precipitation_type_code = precip_type
                            warning_forecast_time = forecast_time
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Error extracting forecast parameters: {e}")
                    continue
            
            if max_precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                cycling_analysis['cycling_warning'] = True
                cycling_analysis['precipitation_mm'] = max_precipitation
                cycling_analysis['precipitation_type'] = self.get_precipitation_type_description(precipitation_type_code)
                cycling_analysis['precipitation_description'] = self.get_precipitation_intensity_description(max_precipitation)
                
                # Convert UTC to local time for display
                if warning_forecast_time:
                    local_time = warning_forecast_time.astimezone()
                    cycling_analysis['forecast_time'] = local_time.strftime('%H:%M')
                else:
                    cycling_analysis['forecast_time'] = 'Unknown time'
                
                cycling_analysis['reason'] = f"Precipitation expected: {max_precipitation:.1f}mm/h"
                
                local_time_str = local_time.strftime('%H:%M') if warning_forecast_time else 'Unknown time'
                self.logger.info(f"🚴‍♂️ CYCLING WARNING: {cycling_analysis['precipitation_description']} {cycling_analysis['precipitation_type']} at {local_time_str} (local time)")
            else:
                cycling_analysis['precipitation_mm'] = max_precipitation
                self.logger.info(f"🚴‍♂️ Cycling weather OK: Max {max_precipitation:.1f}mm/h (below {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
            
            self.logger.debug(f"🎯 CYCLING WEATHER RESULT: warning={cycling_analysis['cycling_warning']}, max_precip={cycling_analysis['precipitation_mm']}")
            
            # Add raw pcat code for trigger filtering (snow vs rain)
            cycling_analysis['pcat'] = precipitation_type_code
            return cycling_analysis
        
        except Exception as e:
            self.logger.error(f"❌ Error in cycling weather analysis: {e}")
            return {'cycling_warning': False, 'reason': f'Analysis error: {e}'}
    
    def get_precipitation_type_description(self, pcat_code: int) -> str:
        """
        Convert SMHI pcat code to readable description
        
        Args:
            pcat_code: SMHI precipitation category code
            
        Returns:
            Readable precipitation type description
        """
        precipitation_types = {
            0: "No precipitation",
            1: "Snow",
            2: "Mixed snow/rain",
            3: "Rain",
            4: "Hail",
            5: "Hail + rain",
            6: "Hail + snow"
        }
        return precipitation_types.get(pcat_code, f"Unknown type ({pcat_code})")
    
    def get_precipitation_intensity_description(self, mm_per_hour: float) -> str:
        """
        Convert mm/h to readable intensity description
        
        Args:
            mm_per_hour: Precipitation in mm per hour
            
        Returns:
            Precipitation intensity description
        """
        if mm_per_hour < 0.1:
            return "No rain"
        elif mm_per_hour < 0.5:
            return "Light drizzle"
        elif mm_per_hour < 1.0:
            return "Light rain"
        elif mm_per_hour < 2.5:
            return "Moderate rain"
        elif mm_per_hour < 10.0:
            return "Heavy rain"
        else:
            return "Very heavy rain"
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def get_weather_description(self, symbol: int) -> str:
        """
        Convert SMHI weather symbol to description
        
        Args:
            symbol: SMHI weather symbol (1-27)
            
        Returns:
            Weather description in Swedish
        """
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
        Synchronize weather description with observations for consistent rain gear info
        
        Solves the problem:
        - Weather symbol 18 = "Light rain"
        - But observations = 0mm/h (not actually raining)
        - Change to "Rain expected" instead of "Light rain"
        
        Args:
            weather_symbol: SMHI weather symbol (1-27)
            observations_precipitation: Actual precipitation from observations (mm/h)
            
        Returns:
            Synchronized weather description
        """
        try:
            # Get original description
            original_description = self.get_weather_description(weather_symbol)
            
            # Rain symbols that may need synchronization
            rain_symbols = {
                8: "regnskurar",     # Light rain showers
                9: "regnskurar",     # Moderate rain showers
                10: "regnskurar",    # Heavy rain showers
                18: "regn",          # Light rain
                19: "regn",          # Moderate rain
                20: "regn",          # Heavy rain
                21: "åska",          # Thunder
                22: "snöblandad regn", # Light mixed rain
                23: "snöblandad regn", # Moderate mixed rain
                24: "snöblandad regn"  # Heavy mixed rain
            }
            
            # If weather symbol indicates rain BUT observations show 0mm/h
            if weather_symbol in rain_symbols and observations_precipitation == 0:
                rain_type = rain_symbols[weather_symbol]
                
                # Change from "raining now" to "rain expected"
                synchronized_description = original_description.replace(
                    rain_type, f"{rain_type} väntat"
                )
                
                # Special case for thunder
                if weather_symbol == 21:
                    synchronized_description = "Åska väntat"
                
                self.logger.info(f"🔄 SMHI synchronization: '{original_description}' → '{synchronized_description}' (observations: {observations_precipitation}mm/h)")
                return synchronized_description
            
            # No synchronization needed - return original
            return original_description
        
        except Exception as e:
            self.logger.error(f"❌ Error in weather description synchronization: {e}")
            return self.get_weather_description(weather_symbol)  # Fallback to original
    
    # ============================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ============================================================
    
    def get_forecast_data(self) -> Dict[str, Any]:
        """
        Implementation of abstract method - Get SMHI forecast data
        
        Returns:
            SMHI forecast data
        """
        return self.get_smhi_data()
    
    def get_current_weather(self) -> Dict[str, Any]:
        """
        Implementation of abstract method - Get current weather from SMHI
        
        This method combines:
        - SMHI forecasts
        - SMHI observations (if available)
        - Cycling weather analysis
        
        Returns:
            Combined weather data in standardized format
        """
        try:
            # Get SMHI forecast
            smhi_data = self.get_smhi_data()
            
            # Get SMHI observations
            observations_data = self.get_smhi_observations()
            
            # Get full forecast for cycling analysis
            smhi_forecast_data = self.get_smhi_forecast_data()
            cycling_weather = self.analyze_cycling_weather(smhi_forecast_data)
            
            # Combine all data
            combined_data = {
                **smhi_data,
                'observations': observations_data,
                'cycling_weather': cycling_weather
            }
            
            # Add observation precipitation if available
            if observations_data and 'precipitation_observed' in observations_data:
                combined_data['precipitation_observed'] = observations_data['precipitation_observed']
            
            # Synchronize weather description with observations
            if observations_data and 'precipitation_observed' in observations_data:
                weather_symbol = smhi_data.get('weather_symbol', 1)
                observations_precipitation = observations_data.get('precipitation_observed', 0.0)
                combined_data['weather_description'] = self.get_observations_synchronized_description(
                    weather_symbol, 
                    observations_precipitation
                )
            
            return combined_data
        
        except Exception as e:
            self.logger.error(f"❌ Error getting current weather: {e}")
            return {}

# ============================================================
# HÄR SLUTAR DEL TVÅ
# ============================================================

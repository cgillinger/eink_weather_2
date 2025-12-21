"""
YR Weather Provider - Global coverage

Provides weather forecasts globally using YR/MET Norway APIs.
YR is powered by the Norwegian Meteorological Institute.

Features:
- Global weather forecasts (any location on Earth)
- Forecast-only (no real-time observations)
- Comprehensive symbol set with day/night variants
- Respects YR API rate limits and caching requirements

Limitations:
- No real-time observations (forecast data only)
- Minimum 10 minute update interval required by YR
"""

from typing import Dict, Any, Optional
import logging
import time
import requests
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json

from .base_provider import WeatherProvider


class YRWeatherProvider(WeatherProvider):
    """
    YR/MET Norway weather provider implementation
    
    Supports:
    - Point forecasts for any location globally
    - Comprehensive weather symbols with day/night variants
    - Respects YR API caching and rate limits
    
    Does NOT support:
    - Real-time observations (use SMHI for Sweden if needed)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize YR provider
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # YR API configuration
        self.api_base = "https://api.met.no/weatherapi"
        self.forecast_version = "2.0"
        
        # User-Agent is REQUIRED by YR API
        self.user_agent = "EpaperWeatherStation/1.0 github.com/yourusername/epaper_weather"
        
        # Cache for API calls
        self.forecast_cache = {
            'data': None, 
            'timestamp': 0,
            'expires': None,
            'last_modified': None
        }
        
        # Cycling weather threshold (same as SMHI)
        self.CYCLING_PRECIPITATION_THRESHOLD = 0.2  # mm/h
        
        # Log configuration
        self.logger.info(f"🌍 YR Provider: Global coverage enabled")
        self.logger.info(f"⚠️ YR Provider: Forecast-only (no real-time observations)")
        self.logger.info(f"⏰ YR Provider: Minimum 10 min update interval (API requirement)")
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "YR (MET Norway)"
    
    def supports_observations(self) -> bool:
        """YR does NOT support real-time observations"""
        return False
    
    def get_weather_symbol(self, data: Dict) -> int:
        """
        Get YR weather symbol mapped to icon
        
        YR uses string symbol_code (e.g., "cloudy", "partlycloudy_day")
        We need to map this to a standardized format for icon lookup
        
        Args:
            data: Weather data containing symbol_code
            
        Returns:
            Icon identifier (we'll use the symbol_code string directly)
        """
        symbol_code = data.get('symbol_code', 'cloudy')
        return symbol_code
    
    # ============================================================
    # FORECASTS - Weather forecast data from YR API
    # ============================================================
    
    def get_yr_forecast_data(self) -> Dict[str, Any]:
        """
        Get YR locationforecast data
        
        Returns:
            Full YR forecast data with timeseries
        """
        # Check cache validity
        if self.forecast_cache['data']:
            # Check if cache has expired
            if self.forecast_cache['expires']:
                try:
                    # Try ISO format first (new format after our fix)
                    expires = datetime.fromisoformat(self.forecast_cache['expires'])
                except (ValueError, TypeError):
                    try:
                        # Fallback to HTTP date format (old cached data or direct from API)
                        expires = parsedate_to_datetime(self.forecast_cache['expires'])
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to parse cache expiry: {e}")
                        expires = None
                
                if expires and datetime.now(timezone.utc) < expires:
                    self.logger.info("📋 Using cached YR forecast data")
                    return self.forecast_cache['data']
                    # Clear invalid cache
                    self.forecast_cache['data'] = None
                    self.forecast_cache['expires'] = None
        
        try:
            self.logger.info("📡 Fetching YR forecast data...")
            
            # Round coordinates to max 4 decimals (YR API requirement)
            lat = round(self.latitude, 4)
            lon = round(self.longitude, 4)
            
            # Build URL
            url = f"{self.api_base}/locationforecast/{self.forecast_version}/complete"
            params = {
                'lat': lat,
                'lon': lon
            }
            
            # Required headers
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json'
            }
            
            # Add conditional request headers if we have cached data
            if self.forecast_cache.get('last_modified'):
                headers['If-Modified-Since'] = self.forecast_cache['last_modified']
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                self.logger.info("📋 YR data not modified, using cache")
                return self.forecast_cache['data']
            
            response.raise_for_status()
            
            data = response.json()
            
            # Parse Expires header from HTTP date format to ISO format
            expires_iso = None
            if response.headers.get('Expires'):
                try:
                    expires_dt = parsedate_to_datetime(response.headers['Expires'])
                    expires_iso = expires_dt.isoformat()
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not parse Expires header: {e}")
            
            # Cache the response with expiry information
            self.forecast_cache = {
                'data': data,
                'timestamp': time.time(),
                'expires': expires_iso,
                'last_modified': response.headers.get('Date')
            }
            
            timeseries_count = len(data.get('properties', {}).get('timeseries', []))
            self.logger.info(f"✅ YR forecast fetched ({timeseries_count} time points)")
            
            return data
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ YR API error: {e}")
            
            # Return cached data if available (even if expired)
            if self.forecast_cache['data']:
                self.logger.warning("⚠️ Using expired cached data due to API error")
                return self.forecast_cache['data']
            
            return {}
        except Exception as e:
            self.logger.error(f"❌ YR forecast parsing error: {e}")
            return {}
    
    def parse_yr_forecast(self, forecast_data: Dict) -> Dict[str, Any]:
        """
        Parse YR forecast data and extract current + tomorrow's weather
        
        Args:
            forecast_data: Full YR forecast response
            
        Returns:
            Dict with parsed forecast data
        """
        data = {
            'source': 'yr',
            'location': self.location_name,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if not forecast_data or 'properties' not in forecast_data:
                self.logger.warning("⚠️ No forecast data available")
                return data
            
            timeseries = forecast_data['properties'].get('timeseries', [])
            if not timeseries:
                self.logger.warning("⚠️ Empty timeseries in forecast")
                return data
            
            # Current forecast (first time point)
            current = timeseries[0]
            
            if current:
                instant = current.get('data', {}).get('instant', {}).get('details', {})
                next_1h = current.get('data', {}).get('next_1_hours', {})
                
                # Extract instant data
                data['temperature'] = instant.get('air_temperature')
                data['wind_speed'] = instant.get('wind_speed')
                data['wind_direction'] = instant.get('wind_from_direction')
                data['wind_gust'] = instant.get('wind_speed_of_gust')
                data['pressure'] = instant.get('air_pressure_at_sea_level')
                data['humidity'] = instant.get('relative_humidity')
                
                # Extract next_1_hours summary
                if next_1h:
                    summary = next_1h.get('summary', {})
                    details = next_1h.get('details', {})
                    
                    data['symbol_code'] = summary.get('symbol_code', 'cloudy')
                    data['weather_symbol'] = data['symbol_code']  # For compatibility
                    data['precipitation'] = details.get('precipitation_amount', 0.0)
            
            # Tomorrow's 12:00 forecast
            now = datetime.now(timezone.utc)
            tomorrow_noon = now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            tomorrow_data = {}
            for forecast in timeseries:
                forecast_time = datetime.fromisoformat(forecast['time'].replace('Z', '+00:00'))
                
                # Find closest to tomorrow 12:00
                if abs((forecast_time - tomorrow_noon).total_seconds()) < 3600:  # Within 1 hour
                    instant = forecast.get('data', {}).get('instant', {}).get('details', {})
                    next_6h = forecast.get('data', {}).get('next_6_hours', {})
                    
                    tomorrow_data['temperature'] = instant.get('air_temperature')
                    tomorrow_data['wind_speed'] = instant.get('wind_speed')
                    tomorrow_data['wind_direction'] = instant.get('wind_from_direction')
                    
                    if next_6h:
                        summary = next_6h.get('summary', {})
                        details = next_6h.get('details', {})
                        
                        tomorrow_data['symbol_code'] = summary.get('symbol_code', 'cloudy')
                        tomorrow_data['weather_symbol'] = tomorrow_data['symbol_code']
                        tomorrow_data['weather_description'] = self.get_weather_description(tomorrow_data['symbol_code'])
                        tomorrow_data['precipitation'] = details.get('precipitation_amount', 0.0)
                    
                    break
            
            if tomorrow_data:
                data['tomorrow'] = tomorrow_data
            
            return data
        
        except Exception as e:
            self.logger.error(f"❌ Error parsing YR forecast: {e}")
            return data

# ============================================================
# HÄR SLUTAR DEL ETT
# ============================================================
# ============================================================
    # HÄR BÖRJAR DEL TVÅ
    # ============================================================
    
    # ============================================================
    # CYCLING WEATHER ANALYSIS
    # ============================================================
    
    def analyze_cycling_weather(self, forecast_data: Dict) -> Dict[str, Any]:
        """
        Analyze weather for cycling - check if precipitation expected within 2h
        
        YR NOTE: We don't have pcat (precipitation category) like SMHI,
        so we can't distinguish snow from rain as easily.
        We'll use symbol_code to filter out snow-only conditions.
        
        Args:
            forecast_data: Full YR forecast data with timeseries
            
        Returns:
            Dict with cycling weather analysis
        """
        try:
            cycling_analysis = {
                'cycling_warning': False,
                'precipitation_mm': 0.0,
                'precipitation_type': 'None',
                'precipitation_description': 'No rain',
                'forecast_time': None,
                'reason': 'No rain expected within 2h',
                'pcat': 0  # Set to 0 for YR (no pcat system)
            }
            
            if not forecast_data or 'properties' not in forecast_data:
                self.logger.warning("⚠️ No YR forecast data available for cycling analysis")
                return cycling_analysis
            
            timeseries = forecast_data['properties'].get('timeseries', [])
            if not timeseries:
                self.logger.warning("⚠️ Empty timeseries for cycling analysis")
                return cycling_analysis
            
            # Analyze next 2 hours
            now = datetime.now(timezone.utc)
            two_hours_ahead = now + timedelta(hours=2)
            
            # Filter forecasts for next 2 hours
            next_hours_forecasts = []
            for forecast in timeseries:
                forecast_time = datetime.fromisoformat(forecast['time'].replace('Z', '+00:00'))
                
                if now <= forecast_time <= two_hours_ahead:
                    next_hours_forecasts.append((forecast_time, forecast))
            
            if not next_hours_forecasts:
                self.logger.warning("⚠️ No forecasts found for next 2h")
                return cycling_analysis
            
            self.logger.debug(f"🔍 CYCLING WEATHER DEBUG: Analyzing {len(next_hours_forecasts)} forecasts")
            
            # Find max precipitation within 2h (that's NOT pure snow)
            max_precipitation = 0.0
            warning_forecast_time = None
            warning_symbol = None
            
            for forecast_time, forecast in next_hours_forecasts:
                try:
                    data = forecast.get('data', {})
                    next_1h = data.get('next_1_hours', {})
                    
                    if next_1h:
                        details = next_1h.get('details', {})
                        summary = next_1h.get('summary', {})
                        
                        precipitation = details.get('precipitation_amount', 0.0)
                        symbol_code = summary.get('symbol_code', '')
                        
                        # Filter out pure snow conditions
                        # Snow symbols: 'snow', 'lightsnow', 'heavysnow', 'snowshowers', etc.
                        # We WANT: rain, sleet (mixed), but NOT pure snow
                        is_pure_snow = any(snow_word in symbol_code.lower() 
                                          for snow_word in ['snow', 'snø'] 
                                          if 'sleet' not in symbol_code.lower())
                        
                        self.logger.debug(f"  {forecast_time.strftime('%H:%M')}: {precipitation}mm/h (symbol: {symbol_code}, snow: {is_pure_snow})")
                        
                        # Only count if it's not pure snow and above threshold
                        if precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD and not is_pure_snow:
                            if precipitation > max_precipitation:
                                max_precipitation = precipitation
                                warning_forecast_time = forecast_time
                                warning_symbol = symbol_code
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Error extracting forecast data: {e}")
                    continue
            
            if max_precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                cycling_analysis['cycling_warning'] = True
                cycling_analysis['precipitation_mm'] = max_precipitation
                cycling_analysis['precipitation_type'] = self._get_precipitation_type_from_symbol(warning_symbol)
                cycling_analysis['precipitation_description'] = self.get_precipitation_intensity_description(max_precipitation)
                
                # Convert UTC to local time
                if warning_forecast_time:
                    local_time = warning_forecast_time.astimezone()
                    cycling_analysis['forecast_time'] = local_time.strftime('%H:%M')
                else:
                    cycling_analysis['forecast_time'] = 'Unknown time'
                
                cycling_analysis['reason'] = f"Precipitation expected: {max_precipitation:.1f}mm/h"
                
                local_time_str = local_time.strftime('%H:%M') if warning_forecast_time else 'Unknown time'
                self.logger.info(f"🚴‍♂️ CYCLING WARNING: {cycling_analysis['precipitation_description']} at {local_time_str} (local time)")
            else:
                cycling_analysis['precipitation_mm'] = max_precipitation
                self.logger.info(f"🚴‍♂️ Cycling weather OK: Max {max_precipitation:.1f}mm/h (below {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
            
            self.logger.debug(f"🎯 CYCLING WEATHER RESULT: warning={cycling_analysis['cycling_warning']}, max_precip={cycling_analysis['precipitation_mm']}")
            
            return cycling_analysis
        
        except Exception as e:
            self.logger.error(f"❌ Error in cycling weather analysis: {e}")
            return {'cycling_warning': False, 'reason': f'Analysis error: {e}', 'pcat': 0}
    
    def _get_precipitation_type_from_symbol(self, symbol_code: str) -> str:
        """
        Guess precipitation type from YR symbol code
        
        Args:
            symbol_code: YR symbol code
            
        Returns:
            Precipitation type description
        """
        if not symbol_code:
            return 'Unknown'
        
        symbol_lower = symbol_code.lower()
        
        if 'sleet' in symbol_lower:
            return 'Mixed rain/snow'
        elif 'rain' in symbol_lower:
            return 'Rain'
        elif 'snow' in symbol_lower:
            return 'Snow'
        elif 'thunder' in symbol_lower:
            return 'Thunder'
        else:
            return 'Precipitation'
    
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
    
    def get_weather_description(self, symbol_code: str) -> str:
        """
        Convert YR symbol code to human-readable description
        
        YR uses descriptive codes like 'partlycloudy_day', 'rain', etc.
        We'll provide Swedish translations for consistency with SMHI.
        
        Args:
            symbol_code: YR symbol code
            
        Returns:
            Weather description in Swedish
        """
        # Map YR symbol codes to Swedish descriptions
        descriptions = {
            'clearsky': 'Klart',
            'fair': 'Mest klart',
            'partlycloudy': 'Delvis molnigt',
            'cloudy': 'Molnigt',
            'fog': 'Dimma',
            'lightrainshowers': 'Lätta regnskurar',
            'rainshowers': 'Regnskurar',
            'heavyrainshowers': 'Kraftiga regnskurar',
            'lightrain': 'Lätt regn',
            'rain': 'Regn',
            'heavyrain': 'Kraftigt regn',
            'lightsleetshowers': 'Lätta snöblandade skurar',
            'sleetshowers': 'Snöblandade skurar',
            'heavysleetshowers': 'Kraftiga snöblandade skurar',
            'lightsleet': 'Lätt snöblandat regn',
            'sleet': 'Snöblandat regn',
            'heavysleet': 'Kraftigt snöblandat regn',
            'lightsnowshowers': 'Lätta snöbyar',
            'snowshowers': 'Snöbyar',
            'heavysnowshowers': 'Kraftiga snöbyar',
            'lightsnow': 'Lätt snöfall',
            'snow': 'Snöfall',
            'heavysnow': 'Kraftigt snöfall',
            'thunder': 'Åska',
        }
        
        # Remove day/night/polartwilight suffix if present
        base_symbol = symbol_code.replace('_day', '').replace('_night', '').replace('_polartwilight', '')
        
        return descriptions.get(base_symbol, symbol_code.replace('_', ' ').title())
    
    # ============================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ============================================================
    
    def get_forecast_data(self) -> Dict[str, Any]:
        """
        Implementation of abstract method - Get YR forecast data
        
        Returns:
            YR forecast data
        """
        forecast_data = self.get_yr_forecast_data()
        return self.parse_yr_forecast(forecast_data)
    
    def get_current_weather(self) -> Dict[str, Any]:
        """
        Implementation of abstract method - Get current weather from YR
        
        This method combines:
        - YR forecasts (forecast data only, no observations)
        - Cycling weather analysis
        
        Returns:
            Combined weather data in standardized format
        """
        try:
            # Get YR forecast
            forecast_data = self.get_yr_forecast_data()
            parsed_data = self.parse_yr_forecast(forecast_data)
            
            # Analyze cycling weather
            cycling_weather = self.analyze_cycling_weather(forecast_data)
            
            # Combine all data
            combined_data = {
                **parsed_data,
                'observations': {},  # YR has no observations
                'cycling_weather': cycling_weather
            }
            
            # Add weather description
            if 'symbol_code' in combined_data:
                combined_data['weather_description'] = self.get_weather_description(
                    combined_data['symbol_code']
                )
            
            return combined_data
        
        except Exception as e:
            self.logger.error(f"❌ Error getting current weather: {e}")
            return {}

# ============================================================
# HÄR SLUTAR DEL TVÅ
# ============================================================

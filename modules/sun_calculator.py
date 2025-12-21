#!/usr/bin/env python3
"""
SunCalculator - Exakta soltider från ipgeolocation.io API
Baserad på Väderdisplay-projektets implementation
Ersätter förenklad algoritm med verkliga soltider
"""

import os
import json
import time
import math
import requests
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Any

class SunCalculator:
    """
    Beräknar exakta soltider med ipgeolocation.io API
    Baserad på Väderdisplay-projektets utils.py
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialisera SunCalculator
        
        Args:
            api_key: ipgeolocation.io API-nyckel (samma som Väderdisplay)
        """
        # Samma API-nyckel som Väderdisplay-projektet
        self.api_key = api_key or "8fd423c5ca0c49f198f9598baeb5a059"
        self.api_base_url = "https://api.ipgeolocation.io/astronomy"
        
        # Cache-konfiguration (24h cache som Väderdisplayen)
        self.cache_file = "cache/sun_cache.json"
        self.cache_duration_hours = 24
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Skapa cache-mapp om den inte finns
        cache_dir = os.path.dirname(self.cache_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        print(f"☀️ SunCalculator initierad med ipgeolocation.io API")
    
    def get_sun_times(self, latitude: float, longitude: float, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Hämta exakta soltider för given plats och datum
        
        Args:
            latitude: Latitud (ex: 59.3293 för Stockholm)
            longitude: Longitud (ex: 18.0686 för Stockholm)
            target_date: Datum att hämta soltider för (default: idag)
            
        Returns:
            Dict med soldata: {
                'sunrise': '2025-07-24T03:27:15',
                'sunset': '2025-07-24T20:32:41',
                'sunrise_time': datetime-objekt,
                'sunset_time': datetime-objekt,
                'daylight_duration': '17h 5m',
                'source': 'ipgeolocation.io' eller 'fallback',
                'cached': True/False
            }
        """
        if target_date is None:
            target_date = date.today()
            
        # Kontrollera cache först
        cache_key = f"{latitude}_{longitude}_{target_date.isoformat()}"
        cached_data = self._get_cached_data(cache_key)
        
        if cached_data:
            self.logger.info(f"☀️ Använder cachade soltider för {target_date}")
            return cached_data
        
        # Försök hämta från API
        try:
            api_data = self._fetch_from_api(latitude, longitude, target_date)
            if api_data:
                # Cacha resultatet
                self._save_to_cache(cache_key, api_data)
                self.logger.info(f"☀️ Nya soltider hämtade från API för {target_date}")
                return api_data
                
        except Exception as e:
            self.logger.warning(f"⚠️ API-fel för soltider: {e}")
        
        # Fallback till förenklad beräkning
        self.logger.info("☀️ Använder fallback-beräkning för soltider")
        fallback_data = self._calculate_fallback(latitude, longitude, target_date)
        
        # Cacha även fallback (kortare tid)
        fallback_data['cached'] = False
        self._save_to_cache(cache_key, fallback_data, cache_hours=2)
        
        return fallback_data
    
    def _fetch_from_api(self, latitude: float, longitude: float, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Hämta soltider från ipgeolocation.io API
        
        Args:
            latitude: Latitud
            longitude: Longitud  
            target_date: Datum
            
        Returns:
            Dict med API-data eller None vid fel
        """
        try:
            # Samma API-anrop som Väderdisplayen
            params = {
                'apiKey': self.api_key,
                'lat': latitude,
                'long': longitude,
                'date': target_date.isoformat()
            }
            
            self.logger.debug(f"🌐 API-anrop: {self.api_base_url} för {latitude}, {longitude}")
            
            response = requests.get(self.api_base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parsea API-svar
            if 'sunrise' in data and 'sunset' in data:
                return self._parse_api_response(data, target_date)
            else:
                self.logger.warning(f"⚠️ Ofullständig API-data: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ API-anropsfel: {e}")
            return None
        except (KeyError, ValueError) as e:
            self.logger.error(f"❌ API-parsningsfel: {e}")
            return None
    
    def _parse_api_response(self, api_data: Dict, target_date: date) -> Dict[str, Any]:
        """
        Parsea API-svar till standardformat
        
        Args:
            api_data: Rå API-data
            target_date: Datum
            
        Returns:
            Standardiserat soldata-dict
        """
        try:
            # API returnerar tider i format "03:27" eller "03:27:15"
            sunrise_str = api_data['sunrise']
            sunset_str = api_data['sunset']
            
            # Konvertera till full ISO-format med datum
            sunrise_time = self._parse_time_string(sunrise_str, target_date)
            sunset_time = self._parse_time_string(sunset_str, target_date)
            
            # Beräkna dagsljuslängd
            daylight_duration = self._calculate_daylight_duration(sunrise_time, sunset_time)
            
            return {
                'sunrise': sunrise_time.isoformat(),
                'sunset': sunset_time.isoformat(),
                'sunrise_time': sunrise_time,
                'sunset_time': sunset_time,
                'daylight_duration': daylight_duration,
                'source': 'ipgeolocation.io',
                'cached': False,
                'api_raw': api_data  # För debug
            }
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av API-data: {e}")
            raise
    
    def _parse_time_string(self, time_str: str, target_date: date) -> datetime:
        """
        Konvertera tidsträng från API till datetime-objekt
        
        Args:
            time_str: Tid från API (ex: "03:27" eller "03:27:15")
            target_date: Datum
            
        Returns:
            datetime-objekt
        """
        try:
            # Hantera olika format från API
            if len(time_str.split(':')) == 2:
                # Format: "03:27"
                hour, minute = map(int, time_str.split(':'))
                second = 0
            else:
                # Format: "03:27:15"
                hour, minute, second = map(int, time_str.split(':'))
            
            return datetime.combine(target_date, datetime.min.time().replace(
                hour=hour, minute=minute, second=second
            ))
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av tid '{time_str}': {e}")
            # Fallback: midnatt
            return datetime.combine(target_date, datetime.min.time())
    
    def _calculate_daylight_duration(self, sunrise: datetime, sunset: datetime) -> str:
        """
        Beräkna dagsljuslängd i timmar och minuter
        
        Args:
            sunrise: Soluppgång datetime
            sunset: Solnedgång datetime
            
        Returns:
            Formaterad sträng (ex: "17h 5m")
        """
        try:
            duration = sunset - sunrise
            total_seconds = int(duration.total_seconds())
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            return f"{hours}h {minutes}m"
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid beräkning av dagsljuslängd: {e}")
            return "N/A"
    
    def _calculate_fallback(self, latitude: float, longitude: float, target_date: date) -> Dict[str, Any]:
        """
        Fallback-beräkning med förenklad algoritm (samma som nuvarande main.py)
        
        Args:
            latitude: Latitud
            longitude: Longitud
            target_date: Datum
            
        Returns:
            Dict med fallback-data
        """
        try:
            # Samma algoritm som nuvarande main.py
            day_of_year = target_date.timetuple().tm_yday
            
            # Solens deklination
            P = math.asin(0.39795 * math.cos(0.01723 * (day_of_year - 173)))
            
            # Latitud i radianer
            lat_rad = math.radians(latitude)
            
            # Timvinkel för soluppgång/nedgång
            try:
                argument = -math.tan(lat_rad) * math.tan(P)
                argument = max(-0.99, min(0.99, argument))
                H = math.acos(argument)
            except:
                H = 0
            
            # Lokal tid för soluppgång och solnedgång
            sunrise_hour = 12 - (H * 12 / math.pi)
            sunset_hour = 12 + (H * 12 / math.pi)
            
            # Konvertera till datetime objekt
            sunrise_time = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=sunrise_hour)
            sunset_time = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=sunset_hour)
            
            # Beräkna dagsljuslängd
            daylight_duration = self._calculate_daylight_duration(sunrise_time, sunset_time)
            
            return {
                'sunrise': sunrise_time.isoformat(),
                'sunset': sunset_time.isoformat(),
                'sunrise_time': sunrise_time,
                'sunset_time': sunset_time,
                'daylight_duration': daylight_duration,
                'source': 'fallback',
                'cached': False
            }
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid fallback-beräkning: {e}")
            # Sista utväg: statiska tider
            now = datetime.now()
            sunrise_time = now.replace(hour=6, minute=0, second=0)
            sunset_time = now.replace(hour=18, minute=0, second=0)
            
            return {
                'sunrise': sunrise_time.isoformat(),
                'sunset': sunset_time.isoformat(),
                'sunrise_time': sunrise_time,
                'sunset_time': sunset_time,
                'daylight_duration': '12h 0m',
                'source': 'static_fallback',
                'cached': False
            }
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Hämta data från cache om tillgänglig och giltig
        
        Args:
            cache_key: Nyckel för cache-uppslagning
            
        Returns:
            Cachad data eller None
        """
        try:
            if not os.path.exists(self.cache_file):
                return None
                
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if cache_key not in cache_data:
                return None
            
            entry = cache_data[cache_key]
            
            # Kontrollera om cache är giltig
            cache_time = datetime.fromisoformat(entry['cached_at'])
            cache_age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            max_age = entry.get('cache_hours', self.cache_duration_hours)
            
            if cache_age_hours < max_age:
                # Konvertera tillbaka till datetime-objekt
                entry['data']['sunrise_time'] = datetime.fromisoformat(entry['data']['sunrise'])
                entry['data']['sunset_time'] = datetime.fromisoformat(entry['data']['sunset'])
                entry['data']['cached'] = True
                
                return entry['data']
            else:
                self.logger.debug(f"🗑️ Cache utgången för {cache_key} ({cache_age_hours:.1f}h)")
                return None
                
        except Exception as e:
            self.logger.warning(f"⚠️ Cache-läsningsfel: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any], cache_hours: Optional[int] = None):
        """
        Spara data i cache
        
        Args:
            cache_key: Nyckel för cache
            data: Data att cacha
            cache_hours: Cache-tid i timmar (default: 24h)
        """
        try:
            # Ladda befintlig cache
            cache_data = {}
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                except:
                    cache_data = {}
            
            # Förbered data för JSON (ta bort datetime-objekt)
            json_data = data.copy()
            json_data.pop('sunrise_time', None)
            json_data.pop('sunset_time', None)
            
            # Lägg till cache-metadata
            cache_data[cache_key] = {
                'data': json_data,
                'cached_at': datetime.now().isoformat(),
                'cache_hours': cache_hours or self.cache_duration_hours
            }
            
            # Spara till fil
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
            self.logger.debug(f"💾 Soldata cachad för {cache_key}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Cache-sparningsfel: {e}")
    
    def clear_cache(self):
        """Rensa all cache"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("🗑️ Soldata-cache rensad")
            else:
                print("💭 Ingen cache att rensa")
        except Exception as e:
            self.logger.error(f"❌ Fel vid cache-rensning: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Få statistik om cache
        
        Returns:
            Dict med cache-info
        """
        try:
            if not os.path.exists(self.cache_file):
                return {'entries': 0, 'file_exists': False}
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Räkna giltiga vs utgångna entries
            now = datetime.now()
            valid_entries = 0
            expired_entries = 0
            
            for cache_key, entry in cache_data.items():
                try:
                    cache_time = datetime.fromisoformat(entry['cached_at'])
                    cache_age_hours = (now - cache_time).total_seconds() / 3600
                    max_age = entry.get('cache_hours', self.cache_duration_hours)
                    
                    if cache_age_hours < max_age:
                        valid_entries += 1
                    else:
                        expired_entries += 1
                except:
                    expired_entries += 1
            
            return {
                'entries': len(cache_data),
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'file_exists': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid cache-statistik: {e}")
            return {'entries': 0, 'error': str(e)}


def test_sun_calculator():
    """Test SunCalculator med Stockholm-koordinater"""
    print("🧪 Testar SunCalculator...")
    
    # Skapa calculator
    sun_calc = SunCalculator()
    
    # Test Stockholm
    stockholm_lat = 59.3293
    stockholm_lon = 18.0686
    
    print(f"📍 Testar för Stockholm ({stockholm_lat}, {stockholm_lon})")
    
    # Hämta soltider
    sun_data = sun_calc.get_sun_times(stockholm_lat, stockholm_lon)
    
    print("\n☀️ Soldata-resultat:")
    print(f"  🌅 Soluppgång: {sun_data['sunrise']}")
    print(f"  🌇 Solnedgång: {sun_data['sunset']}")
    print(f"  ⏱️ Dagsljuslängd: {sun_data['daylight_duration']}")
    print(f"  🔍 Källa: {sun_data['source']}")
    print(f"  💾 Cachad: {sun_data['cached']}")
    
    # Cache-statistik
    cache_stats = sun_calc.get_cache_stats()
    print(f"\n💾 Cache-statistik: {cache_stats}")
    
    return sun_calc


if __name__ == "__main__":
    test_sun_calculator()

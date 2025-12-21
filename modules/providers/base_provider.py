"""
Abstract base class for weather providers

This module defines the interface that all weather providers must implement.
Providers can be SMHI (Sweden), YR (Global), or future additions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging


class WeatherProvider(ABC):
    """
    Abstract base class for weather data providers
    
    All weather providers must inherit from this class and implement
    all abstract methods. This ensures consistent interface across
    different weather data sources.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize weather provider
        
        Args:
            config: Configuration dictionary containing location and settings
        """
        self.config = config
        self.latitude = config['location']['latitude']
        self.longitude = config['location']['longitude']
        self.location_name = config['location']['name']
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info(f"🌍 {self.get_provider_name()} initialized for {self.location_name}")
    
    @abstractmethod
    def get_forecast_data(self) -> Dict[str, Any]:
        """
        Get weather forecast data from provider
        
        Returns:
            Dictionary containing forecast data in provider-specific format
        """
        pass
    
    @abstractmethod
    def get_current_weather(self) -> Dict[str, Any]:
        """
        Get current weather conditions
        
        This method should combine forecast data, observations (if available),
        and return a standardized format that the rest of the application expects.
        
        Returns:
            Dictionary containing current weather data in standardized format
        """
        pass
    
    @abstractmethod
    def supports_observations(self) -> bool:
        """
        Check if this provider supports real-time observations
        
        Returns:
            True if provider has observation data, False if forecast-only
        """
        pass
    
    @abstractmethod
    def get_weather_symbol(self, data: Dict) -> int:
        """
        Get standardized weather symbol code for icon mapping
        
        Different providers use different symbol systems. This method
        should convert provider-specific symbols to a standard format
        that can be used with the Weather Icons library.
        
        Args:
            data: Weather data containing provider-specific symbol
            
        Returns:
            Integer symbol code for icon lookup
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get human-readable provider name
        
        Returns:
            Provider name (e.g., "SMHI", "YR")
        """
        pass

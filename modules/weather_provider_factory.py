"""
Weather Provider Factory

Factory function to create the appropriate weather provider
based on configuration.

Supports:
- SMHI (Sweden only)
- YR (Global - to be implemented in Fas 2)
"""

from typing import Dict, Any
import logging


def create_weather_provider(config: Dict[str, Any]):
    """
    Factory function to create weather provider instance
    
    Args:
        config: Configuration dictionary containing 'weather_provider' field
        
    Returns:
        WeatherProvider instance (SMHIWeatherProvider or YRWeatherProvider)
        
    Raises:
        ValueError: If unknown provider specified
        
    Examples:
        >>> config = {'weather_provider': 'smhi', 'location': {...}}
        >>> provider = create_weather_provider(config)
        >>> isinstance(provider, SMHIWeatherProvider)
        True
        
        >>> config = {'weather_provider': 'yr', 'location': {...}}
        >>> provider = create_weather_provider(config)
        >>> isinstance(provider, YRWeatherProvider)
        True
    """
    logger = logging.getLogger(__name__)
    
    # Get provider name from config, default to SMHI for backward compatibility
    provider_name = config.get('weather_provider', 'smhi').lower()
    
    logger.info(f"🏭 Weather Provider Factory: Creating '{provider_name}' provider...")
    
    if provider_name == 'smhi':
        # Import SMHI provider
        from modules.providers.smhi_provider import SMHIWeatherProvider
        
        logger.info("✅ Creating SMHI provider (Sweden only)")
        return SMHIWeatherProvider(config)
    
    elif provider_name == 'yr':
        # Import YR provider (will be implemented in Fas 2)
        try:
            from modules.providers.yr_provider import YRWeatherProvider
            logger.info("✅ Creating YR provider (Global coverage)")
            return YRWeatherProvider(config)
        except ImportError:
            logger.error("❌ YR provider not yet implemented!")
            raise ValueError(
                "YR provider is not yet implemented. "
                "Please use 'smhi' or wait for Fas 2 implementation."
            )
    
    else:
        # Unknown provider
        logger.error(f"❌ Unknown weather provider: '{provider_name}'")
        raise ValueError(
            f"Unknown weather provider: '{provider_name}'. "
            f"Supported providers: 'smhi', 'yr'"
        )


def get_supported_providers() -> list:
    """
    Get list of supported weather providers
    
    Returns:
        List of provider names
    """
    return ['smhi', 'yr']


def validate_provider_config(config: Dict[str, Any]) -> bool:
    """
    Validate provider configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, False otherwise
        
    Raises:
        ValueError: If configuration is invalid
    """
    logger = logging.getLogger(__name__)
    
    # Check if location exists
    if 'location' not in config:
        logger.error("❌ Missing 'location' in config")
        raise ValueError("Configuration must contain 'location' with latitude/longitude")
    
    location = config['location']
    
    # Check latitude
    if 'latitude' not in location:
        logger.error("❌ Missing 'latitude' in location config")
        raise ValueError("Location must contain 'latitude'")
    
    # Check longitude
    if 'longitude' not in location:
        logger.error("❌ Missing 'longitude' in location config")
        raise ValueError("Location must contain 'longitude'")
    
    # Validate latitude range
    lat = location['latitude']
    if not -90 <= lat <= 90:
        logger.error(f"❌ Invalid latitude: {lat}")
        raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
    
    # Validate longitude range
    lon = location['longitude']
    if not -180 <= lon <= 180:
        logger.error(f"❌ Invalid longitude: {lon}")
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
    
    # Check provider name if specified
    provider_name = config.get('weather_provider', 'smhi').lower()
    supported = get_supported_providers()
    
    if provider_name not in supported:
        logger.error(f"❌ Unsupported provider: {provider_name}")
        raise ValueError(
            f"Provider '{provider_name}' not supported. "
            f"Supported providers: {', '.join(supported)}"
        )
    
    logger.info("✅ Provider configuration validated successfully")
    return True

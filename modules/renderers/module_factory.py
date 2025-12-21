#!/usr/bin/env python3
"""
Module Factory för Dynamic Module System
Skapar rätt renderer-instans baserat på modulnamn

Factory Pattern för enkel extensibility:
- Nya moduler = lägg till i registry
- Automatisk fallback till legacy rendering
- Centraliserad renderer-hantering
"""

import logging
from typing import Dict, Optional, Callable, Any
from .base_renderer import ModuleRenderer, LegacyModuleRenderer
from .precipitation_renderer import PrecipitationRenderer
from .wind_renderer import WindRenderer

class ModuleFactory:
    """
    Factory för att skapa renderer-instanser
    
    Hanterar mappning mellan modulnamn och renderer-klasser
    """
    
    def __init__(self, icon_manager, fonts: Dict):
        """
        Args:
            icon_manager: WeatherIconManager instans
            fonts: Dict med laddade typsnitt
        """
        self.icon_manager = icon_manager
        self.fonts = fonts
        self.logger = logging.getLogger(f"{__name__}.ModuleFactory")
        
        # Registry för renderer-klasser
        self._renderer_registry = {
            'precipitation_module': PrecipitationRenderer,
            'wind_module': WindRenderer,
            # Framtida moduler läggs till här:
            # 'uv_module': UVRenderer,
            # 'air_quality_module': AirQualityRenderer,
        }
        
        # Cache för skapade renderer-instanser
        self._renderer_cache = {}
        
        self.logger.info(f"🏭 ModuleFactory initierad med {len(self._renderer_registry)} renderer-typer")
    
    def create_renderer(self, module_name: str, 
                       legacy_render_func: Optional[Callable] = None) -> ModuleRenderer:
        """
        Skapa renderer för given modul
        
        Args:
            module_name: Namn på modulen som ska renderas
            legacy_render_func: Optional legacy rendering-funktion
            
        Returns:
            ModuleRenderer-instans (ny eller legacy)
        """
        try:
            # Kontrollera cache först
            if module_name in self._renderer_cache:
                self.logger.debug(f"🔄 Använder cachad renderer för {module_name}")
                return self._renderer_cache[module_name]
            
            # Skapa ny renderer
            renderer = self._create_new_renderer(module_name, legacy_render_func)
            
            # Cacha för framtida användning
            self._renderer_cache[module_name] = renderer
            
            self.logger.info(f"✅ Renderer skapad för {module_name}: {renderer.__class__.__name__}")
            return renderer
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid renderer-skapande för {module_name}: {e}")
            
            # Sista utväg: skapa minimal legacy renderer
            return self._create_fallback_renderer(module_name)
    
    def _create_new_renderer(self, module_name: str, 
                            legacy_render_func: Optional[Callable]) -> ModuleRenderer:
        """Skapa ny renderer-instans"""
        
        # Kontrollera om det finns en specifik renderer
        if module_name in self._renderer_registry:
            renderer_class = self._renderer_registry[module_name]
            renderer = renderer_class(self.icon_manager, self.fonts)
            self.logger.info(f"🎨 Skapad specifik renderer: {renderer_class.__name__}")
            return renderer
        
        # Fallback till legacy renderer om render-funktion finns
        elif legacy_render_func:
            renderer = LegacyModuleRenderer(
                self.icon_manager, 
                self.fonts, 
                legacy_render_func
            )
            self.logger.info(f"🔄 Skapad legacy renderer för {module_name}")
            return renderer
        
        # Ingen renderer eller legacy-funktion tillgänglig
        else:
            raise ValueError(f"Ingen renderer tillgänglig för {module_name}")
    
    def _create_fallback_renderer(self, module_name: str) -> ModuleRenderer:
        """Skapa minimal fallback-renderer vid allvarliga fel"""
        
        def fallback_render_func(x, y, width, height, weather_data, context_data):
            """Minimal rendering som alltid fungerar"""
            pass  # LegacyModuleRenderer hanterar felhantering
        
        renderer = LegacyModuleRenderer(
            self.icon_manager, 
            self.fonts, 
            fallback_render_func
        )
        
        self.logger.warning(f"⚠️ Skapad fallback renderer för {module_name}")
        return renderer
    
    def register_renderer(self, module_name: str, renderer_class) -> bool:
        """
        Registrera ny renderer-klass (för framtida utbyggnad)
        
        Args:
            module_name: Modulnamn
            renderer_class: Klass som ärver från ModuleRenderer
            
        Returns:
            True om registreringen lyckades
        """
        try:
            if not issubclass(renderer_class, ModuleRenderer):
                self.logger.error(f"❌ {renderer_class} ärver inte från ModuleRenderer")
                return False
            
            self._renderer_registry[module_name] = renderer_class
            
            # Rensa cache för denna modul om den finns
            if module_name in self._renderer_cache:
                del self._renderer_cache[module_name]
            
            self.logger.info(f"✅ Registrerad ny renderer: {module_name} → {renderer_class.__name__}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid renderer-registrering: {e}")
            return False
    
    def get_available_renderers(self) -> Dict[str, str]:
        """
        Få lista över tillgängliga renderer-typer
        
        Returns:
            Dict med module_name → renderer_class_name
        """
        return {
            module_name: renderer_class.__name__ 
            for module_name, renderer_class in self._renderer_registry.items()
        }
    
    def get_renderer_info(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Få information om en specifik renderer
        
        Args:
            module_name: Modulnamn
            
        Returns:
            Dict med renderer-information eller None
        """
        try:
            if module_name in self._renderer_registry:
                renderer_class = self._renderer_registry[module_name]
                
                # Skapa temporär instans för att få info
                temp_renderer = renderer_class(self.icon_manager, self.fonts)
                return temp_renderer.get_module_info()
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Fel vid renderer-info hämtning: {e}")
            return None
    
    def clear_cache(self):
        """Rensa renderer-cache"""
        cache_size = len(self._renderer_cache)
        self._renderer_cache.clear()
        self.logger.info(f"🗑️ Renderer-cache rensad: {cache_size} instanser")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Få statistik om renderer-cache
        
        Returns:
            Dict med cache-statistik
        """
        return {
            'cached_renderers': len(self._renderer_cache),
            'available_types': len(self._renderer_registry),
            'cached_modules': list(self._renderer_cache.keys()),
            'available_types_list': list(self._renderer_registry.keys())
        }


def test_module_factory():
    """Test-funktion för ModuleFactory"""
    print("🧪 Testar ModuleFactory...")
    
    # Mock objekt för test
    class MockIconManager:
        pass
    
    mock_fonts = {
        'small_main': None,
        'small_desc': None,
        'tiny': None
    }
    
    try:
        # Skapa factory
        factory = ModuleFactory(MockIconManager(), mock_fonts)
        
        # Test renderer-skapande
        precip_renderer = factory.create_renderer('precipitation_module')
        print(f"✅ Precipitation renderer skapad: {precip_renderer.__class__.__name__}")
        
        # Test legacy fallback
        def mock_legacy_func(x, y, w, h, data, ctx):
            pass
        
        legacy_renderer = factory.create_renderer('unknown_module', mock_legacy_func)
        print(f"✅ Legacy renderer skapad: {legacy_renderer.__class__.__name__}")
        
        # Test cache
        cached_renderer = factory.create_renderer('precipitation_module')
        print(f"✅ Cached renderer hämtad: {cached_renderer is precip_renderer}")
        
        # Test info
        available = factory.get_available_renderers()
        print(f"✅ Tillgängliga renderers: {available}")
        
        cache_stats = factory.get_cache_stats()
        print(f"✅ Cache stats: {cache_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Factory test misslyckades: {e}")
        return False


if __name__ == "__main__":
    test_module_factory()
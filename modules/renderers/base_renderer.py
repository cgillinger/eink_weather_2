#!/usr/bin/env python3
"""
Base Renderer Framework för Dynamic Module System
Abstrakt basklass för alla modul-renderers

Designprinciper:
- Single responsibility: En renderer, en modultyp
- Consistent interface: Alla renderers följer samma mönster  
- Data-driven: Inget hårdkodat innehåll
- Error-resilient: Graceful fallback vid fel
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

class ModuleRenderer(ABC):
    """
    Abstrakt basklass för alla modul-renderers
    
    Varje konkret renderer implementerar render() metoden för sin specifika modultyp
    """
    
    def __init__(self, icon_manager, fonts: Dict[str, ImageFont.ImageFont]):
        """
        Initialisera renderer med gemensamma resurser
        
        Args:
            icon_manager: WeatherIconManager instans för ikoner
            fonts: Dict med laddade typsnitt från config
        """
        self.icon_manager = icon_manager
        self.fonts = fonts
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Gemensamma renderingsverktyg (sätts av main_daemon)
        self.canvas = None
        self.draw = None
    
    def set_canvas(self, canvas: Image.Image, draw: ImageDraw.ImageDraw):
        """
        Sätt canvas och draw-objekt för rendering
        Anropas av main_daemon innan render()
        """
        self.canvas = canvas
        self.draw = draw
    
    @abstractmethod
    def render(self, x: int, y: int, width: int, height: int, 
               weather_data: Dict, context_data: Dict) -> bool:
        """
        Rendera modulen på given position
        
        Args:
            x, y: Position på canvas
            width, height: Modulens storlek
            weather_data: Väderdata från weather_client
            context_data: Trigger context data
            
        Returns:
            True om rendering lyckades, False vid fel
        """
        pass
    
    @abstractmethod
    def get_required_data_sources(self) -> List[str]:
        """
        Vilka datakällor behöver denna modul
        
        Returns:
            Lista av datakälla-namn (t.ex. ['smhi', 'netatmo'])
        """
        pass
    
    def get_module_info(self) -> Dict[str, Any]:
        """
        Metadata om denna renderer
        
        Returns:
            Dict med modul-information
        """
        return {
            'name': self.__class__.__name__,
            'data_sources': self.get_required_data_sources(),
            'description': self.__doc__ or 'Ingen beskrivning tillgänglig'
        }
    
    # === GEMENSAMMA HJÄLPMETODER ===
    
    def truncate_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        """
        Korta text så den får plats inom given bredd
        
        Args:
            text: Text att korta
            font: Typsnitt att använda
            max_width: Max bredd i pixlar
            
        Returns:
            Förkortad text som får plats
        """
        if not text or not self.draw:
            return text or ""
            
        try:
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
            
        except Exception as e:
            self.logger.warning(f"⚠️ Text truncation fel: {e}")
            return text
    
    def paste_icon_on_canvas(self, icon: Image.Image, x: int, y: int) -> bool:
        """
        Sätt in ikon på canvas med felhantering
        
        Args:
            icon: PIL Image-objekt
            x, y: Position på canvas
            
        Returns:
            True om lyckades, False vid fel
        """
        if icon is None or self.canvas is None:
            return False
        
        try:
            self.canvas.paste(icon, (x, y))
            return True
        except Exception as e:
            self.logger.error(f"❌ Ikon-placering fel: {e}")
            return False
    
    def draw_text_with_fallback(self, position: Tuple[int, int], text: str, 
                               font: ImageFont.ImageFont, fill: int = 0,
                               max_width: int = None) -> bool:
        """
        Rita text med automatisk truncation och felhantering
        
        Args:
            position: (x, y) position
            text: Text att rita
            font: Typsnitt
            fill: Färg (0=svart, 255=vit)
            max_width: Max bredd för truncation
            
        Returns:
            True om lyckades, False vid fel
        """
        if not text or self.draw is None:
            return False
        
        try:
            # Truncate om max_width specificerad
            if max_width:
                text = self.truncate_text(text, font, max_width)
            
            self.draw.text(position, text, font=font, fill=fill)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Text rendering fel: {e}")
            return False
    
    def safe_get_value(self, data: Dict, key: str, default: Any = None, 
                      expected_type: type = None) -> Any:
        """
        Säker hämtning av värde från data-dict med type checking
        
        Args:
            data: Data dict
            key: Nyckel att hämta
            default: Default-värde vid fel
            expected_type: Förväntad typ för validering
            
        Returns:
            Värde eller default vid fel
        """
        try:
            value = data.get(key, default)
            
            if expected_type and value is not None and not isinstance(value, expected_type):
                self.logger.warning(f"⚠️ Type mismatch för {key}: {type(value)} != {expected_type}")
                return default
            
            return value
            
        except Exception as e:
            self.logger.warning(f"⚠️ Fel vid hämtning av {key}: {e}")
            return default
    
    def render_fallback_content(self, x: int, y: int, width: int, height: int, 
                               error_message: str = "Rendering fel") -> bool:
        """
        Rendera fallback-innehåll vid fel
        
        Args:
            x, y: Position
            width, height: Storlek
            error_message: Felmeddelande att visa
            
        Returns:
            True om fallback lyckades
        """
        try:
            if not self.draw:
                return False
            
            # Enkel fallback med error-meddelande
            center_x = x + width // 2
            center_y = y + height // 2
            
            # Rita varningsikon (om möjligt)
            self.draw_text_with_fallback(
                (x + 10, y + 10), 
                "⚠️", 
                self.fonts.get('medium_desc', self.fonts.get('small_main')), 
                fill=0
            )
            
            # Rita felmeddelande
            self.draw_text_with_fallback(
                (x + 50, y + 15), 
                error_message, 
                self.fonts.get('small_desc', self.fonts.get('tiny')), 
                fill=0,
                max_width=width - 60
            )
            
            self.logger.info(f"🔧 Fallback rendering utförd: {error_message}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Även fallback rendering misslyckades: {e}")
            return False


class LegacyModuleRenderer(ModuleRenderer):
    """
    Fallback renderer för befintliga moduler som inte har egen renderer
    Använder original rendering-logik från main_daemon
    """
    
    def __init__(self, icon_manager, fonts, legacy_render_func):
        """
        Args:
            legacy_render_func: Funktion från main_daemon för denna modul
        """
        super().__init__(icon_manager, fonts)
        self.legacy_render_func = legacy_render_func
    
    def render(self, x: int, y: int, width: int, height: int, 
               weather_data: Dict, context_data: Dict) -> bool:
        """
        Använd legacy rendering-funktion
        """
        try:
            self.legacy_render_func(x, y, width, height, weather_data, context_data)
            return True
        except Exception as e:
            self.logger.error(f"❌ Legacy rendering fel: {e}")
            return self.render_fallback_content(x, y, width, height, "Legacy rendering fel")
    
    def get_required_data_sources(self) -> List[str]:
        """Legacy moduler använder alla tillgängliga datakällor"""
        return ['weather_data', 'context_data']
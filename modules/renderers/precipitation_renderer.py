#!/usr/bin/env python3
"""
Precipitation Module Renderer - LAYOUT FÖRBÄTTRAD för bättre läsbarhet
Optimerad för snabba beslut om regnkläder utan onödiga tips

Ansvarar för rendering av nederbörd-modul med:
- Tydlig status (REGNAR NU / REGN VÄNTAT)
- Intensitet (LÄTT/MÅTTLIGT/KRAFTIGT) 
- Timing (startar XX:XX)
- FÖRBÄTTRAD LAYOUT: Bättre spacing och centrering
"""

from typing import Dict, List
from .base_renderer import ModuleRenderer

class PrecipitationRenderer(ModuleRenderer):
    """
    Renderer för nederbörd-modul - LAYOUT FÖRBÄTTRAD
    
    Fokus på snabb avläsning med förbättrad layout:
    - STOR status-text för snabb identifiering
    - Tydlig intensitet istället för mm/h-värden
    - Korrekt timing utan dubblering
    - FÖRBÄTTRAD: Mer luft mellan rader för E-Paper
    - FÖRBÄTTRAD: Bättre varningsikon-centrering
    """
    
    def render(self, x: int, y: int, width: int, height: int, 
               weather_data: Dict, context_data: Dict) -> bool:
        """
        Rendera nederbörd-modul för snabb avläsning med förbättrad layout
        
        Förbättrad layout:
        ⚠️   REGNAR NU          eller    ⚠️   REGN VÄNTAT  
             Lätt intensitet             Måttligt - startar 13:00
        (mer luft mellan raderna)
        """
        try:
            self.logger.info(f"🌧️ Renderar layout-förbättrad nederbörd-modul ({width}×{height})")
            
            # Hämta nederbörd-data med säker fallback
            precipitation = self.safe_get_value(context_data, 'precipitation', 0.0, float)
            forecast_2h = self.safe_get_value(context_data, 'forecast_precipitation_2h', 0.0, float)
            cycling_weather = self.safe_get_value(weather_data, 'cycling_weather', {}, dict)
            
            # Bestäm huvudstatus och layout
            main_status, detail_text = self._determine_improved_status(
                precipitation, forecast_2h, cycling_weather
            )
            
            # === FÖRBÄTTRAD LAYOUT RENDERING ===
            
            # 1. Varningsikon (FÖRBÄTTRAD centrering)
            icon_success = self._render_warning_icon_centered(x, y)
            
            # 2. HUVUDSTATUS (stort, tydligt)
            text_start_x = x + 65 if icon_success else x + 20  # Lite mer plats efter ikon
            self._render_main_status_large(text_start_x, y, width - (text_start_x - x), main_status)
            
            # 3. DETALJER (FÖRBÄTTRAT: mer luft mellan raderna)
            self._render_details_spaced(x, y, width, detail_text)
            
            self.logger.info(f"✅ Layout-förbättrad nederbörd-modul rendered: {main_status}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid nederbörd rendering: {e}")
            return self.render_fallback_content(x, y, width, height, 
                                               "Nederbörd-data ej tillgänglig")
    
    def _determine_improved_status(self, precipitation: float, forecast_2h: float, 
                                 cycling_weather: Dict) -> tuple:
        """
        FÖRBÄTTRAD status-logik för snabb avläsning
        
        Returns:
            Tuple (main_status, detail_text)
        """
        try:
            # Pågående nederbörd - prioritet 1
            if precipitation > 0:
                main_status = "REGNAR NU"
                intensity = self._get_intensity_level(precipitation)
                detail_text = f"{intensity} intensitet"
                
            # Prognostiserad nederbörd - prioritet 2  
            elif forecast_2h > 0:
                main_status = "REGN VÄNTAT"
                intensity = self._get_intensity_level(forecast_2h)
                
                # Timing från cykel-väder analys
                forecast_time = cycling_weather.get('forecast_time', 'snart')
                detail_text = f"{intensity} - startar {forecast_time}"
                
            # Fallback (borde inte hända då trigger inte skulle vara aktiv)
            else:
                main_status = "NEDERBÖRD DETEKTERAD"
                detail_text = "Kontrollerar data..."
            
            return main_status, detail_text
            
        except Exception as e:
            self.logger.warning(f"⚠️ Fel vid förbättrad status-bestämning: {e}")
            return "NEDERBÖRD-INFO", "Data ej tillgänglig"
    
    def _get_intensity_level(self, mm_per_hour: float) -> str:
        """
        Konvertera mm/h till TYDLIGA intensitetsnivåer för snabb avläsning
        Fokus på stora skillnader istället för mm/h-värden
        """
        if mm_per_hour < 0.1:
            return "INGET"
        elif mm_per_hour < 0.5:
            return "DUGGREGN"
        elif mm_per_hour < 1.0:
            return "LÄTT"
        elif mm_per_hour < 2.5:
            return "MÅTTLIG"
        elif mm_per_hour < 10.0:
            return "KRAFTIG"
        else:
            return "MYCKET KRAFTIG"
    
    def _render_warning_icon_centered(self, x: int, y: int) -> bool:
        """
        FÖRBÄTTRAD: Rendera varningsikon med bättre centrering
        """
        try:
            # Justerad position för bättre centrering inom modulområdet
            return self.draw_text_with_fallback(
                (x + 18, y + 18),  # Lite mer centrat (var x+15, y+15)
                "⚠️", 
                self.fonts.get('medium_main', self.fonts.get('small_main')), 
                fill=0
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Varningsikon fel: {e}")
            return self.draw_text_with_fallback(
                (x + 18, y + 18), 
                "!", 
                self.fonts.get('medium_main', self.fonts.get('small_main')), 
                fill=0
            )
    
    def _render_main_status_large(self, x: int, y: int, max_width: int, main_status: str) -> bool:
        """
        FÖRBÄTTRAD: Rendera huvudstatus med STOR, tydlig text
        """
        try:
            # Använd större font för snabb igenkänning
            return self.draw_text_with_fallback(
                (x, y + 20), 
                main_status, 
                self.fonts.get('small_main', self.fonts.get('medium_desc')),  # Större font
                fill=0,
                max_width=max_width
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Huvudstatus rendering fel: {e}")
            return False
    
    def _render_details_spaced(self, x: int, y: int, width: int, detail_text: str) -> bool:
        """
        FÖRBÄTTRAD: Rendera intensitet + timing med mer luft mellan raderna
        """
        try:
            # FÖRBÄTTRING: Ökat från y+50 till y+65 för mer luft mellan raderna
            return self.draw_text_with_fallback(
                (x + 65, y + 65),  # Var: y+50, nu: y+65 (15px mer luft)
                detail_text, 
                self.fonts.get('medium_desc', self.fonts.get('small_desc')),
                fill=0,
                max_width=width - 85  # Justerat för ny x-position
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Detaljer rendering fel: {e}")
            return False
    
    def get_required_data_sources(self) -> List[str]:
        """
        Nederbörd-modul behöver SMHI prognosdata och cykel-väder analys
        """
        return ['smhi', 'cycling_weather', 'forecast']
    
    def get_module_info(self) -> Dict:
        """Metadata för nederbörd-modul - LAYOUT FÖRBÄTTRAD VERSION"""
        info = super().get_module_info()
        info.update({
            'purpose': 'Snabb nederbörd-avläsning för regnkläder-beslut',
            'triggers': ['precipitation > 0', 'forecast_precipitation_2h > 0.2'],
            'layout_priority': 'Ersätter bottom_section vid nederbörd',
            'improvements': [
                'Större, tydligare text för snabb avläsning',
                'Inga mm/h-värden (ersatta med intensitetsnivåer)', 
                'Fixad dubblering av "regn regn"',
                'Kompakt layout utan handlingsrekommendationer',
                'Förbättrade fontstorlekar för timing',
                'NYTT: Förbättrat radavstånd (15px mer luft)',
                'NYTT: Bättre varningsikon-centrering',
                'NYTT: Optimerad för E-Paper läsbarhet'
            ]
        })
        return info
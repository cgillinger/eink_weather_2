# 🔄 Dynamic Module System Projektplan
**E-Paper Weather Daemon - Generell arkitektur för villkorsbaserade och användarkonfigurerade moduler**

## 🎯 **PROJEKTMÅL**
Skapa ett flexibelt system där moduler kan ersättas dynamiskt baserat på:
1. **Villkor** (t.ex. nederbörd, stark vind, temperatur-extremer)
2. **Användarinställningar** (t.ex. växla mellan barometer/sol-modul)
3. **Tid/säsong** (t.ex. UV-index sommartid, mörka månader)

**Nederbörd-modulen blir det första exemplet, inte speciallösningen.**

---

## 📋 **ARKITEKTONISK VISION**

### **Målarkitektur:**
```json
{
  "module_groups": {
    "bottom_section": {
      "normal": ["clock_module", "status_module"],
      "precipitation_active": ["precipitation_module"],
      "wind_warning": ["wind_module"],
      "user_override": ["barometer_detail", "sun_detail"]
    },
    "side_panel": {
      "normal": ["barometer_module"],
      "summer_mode": ["uv_index_module"],
      "user_preference": ["sun_module"]
    }
  },
  "triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR forecast_2h_precipitation > 0",
      "activate_group": "bottom_section.precipitation_active",
      "deactivate_group": "bottom_section.normal",
      "priority": 100
    },
    "user_preference_trigger": {
      "condition": "config.user_module_preference == 'sun_focus'",
      "activate_group": "side_panel.user_preference", 
      "deactivate_group": "side_panel.normal",
      "priority": 50
    }
  }
}
```

### **Befintlig struktur som påverkas:**
- **main_daemon.py** - Generell trigger-engine och dynamic module system
- **config.json** - Ny trigger/group-struktur
- **weather_client.py** - Trigger-data leverantör
- **Framtida moduler** - Enkelt att lägga till

---

## 🔄 **FAS 1: Core Dynamic Module Framework**
**Mål:** Skapa grundläggande arkitektur för villkorsbaserade moduler

### **Leverabler:**
- `DynamicModuleManager` klass
- Trigger evaluation engine  
- Module group management
- Generell config-struktur

### **Teknisk implementation:**
```python
class DynamicModuleManager:
    def __init__(self, config: Dict):
        self.config = config
        self.module_groups = config.get('module_groups', {})
        self.triggers = config.get('triggers', {})
        self.active_overrides = {}
    
    def evaluate_triggers(self, context_data: Dict) -> Dict[str, str]:
        """
        Evaluera alla triggers och returnera aktiva module groups
        
        Args:
            context_data: Väderdata, användarpref, tid, etc.
            
        Returns:
            {"bottom_section": "precipitation_active", "side_panel": "normal"}
        """
        
    def get_active_modules(self) -> List[str]:
        """Returnera lista av moduler som ska renderas baserat på aktiva groups"""
        
    def should_update_layout(self, context_data: Dict) -> tuple:
        """Kontrollera om layout har ändrats sedan senast"""
```

### **Config-struktur:**
```json
{
  "module_groups": {
    "bottom_section": {
      "normal": ["clock_module", "status_module"],
      "precipitation_active": ["precipitation_module"]
    }
  },
  "triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR forecast_precipitation_2h > 0",
      "target_section": "bottom_section", 
      "activate_group": "precipitation_active",
      "priority": 100,
      "description": "Visa nederbörd-info vid regn"
    }
  },
  "modules": {
    "precipitation_module": {
      "enabled": true,
      "size": {"width": 480, "height": 100},
      "coords": {"x": 40, "y": 360},
      "data_sources": ["smhi"]
    }
  }
}
```

### **Filförändringar:**
- **main_daemon.py** - Ny DynamicModuleManager klass
- **config.json** - Ny struktur (bakåtkompatibel)

### **Test-scenarios:**
- Normal layout utan aktiva triggers
- Trigger aktiveras → layout ändras
- Multipla triggers → priority-hantering
- Konfiguration valideras korrekt

### **Acceptanskriteria:**
- Generell trigger-engine fungerar
- Modulgrupper kan aktiveras/avaktiveras
- Bakåtkompatibilitet med befintlig config
- Ingen hårdkodad nederbörd-logik

---

## ⚙️ **FAS 2: Trigger Evaluation System**
**Mål:** Implementera flexibelt system för condition evaluation

### **Leverabler:**
- `TriggerEvaluator` klass med safe expression parsing
- Context data provider
- Trigger priority system
- Logging och debugging av trigger-beslut

### **Teknisk implementation:**
```python
class TriggerEvaluator:
    def __init__(self):
        self.safe_functions = {
            'precipitation': self._get_precipitation,
            'forecast_precipitation_2h': self._get_forecast_precipitation,
            'temperature': self._get_temperature,
            'wind_speed': self._get_wind_speed,
            'time_hour': self._get_current_hour,
            'user_preference': self._get_user_preference
        }
    
    def evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        Säkert evaluera trigger-conditions
        Exempel: "precipitation > 0 OR forecast_precipitation_2h > 0.2"
        """
        
    def _get_precipitation(self, context: Dict) -> float:
        """Hämta aktuell nederbörd från context"""
        
    def _get_forecast_precipitation(self, context: Dict, hours: int = 2) -> float:
        """Hämta prognostiserad nederbörd kommande X timmar"""
```

### **Condition examples:**
```json
{
  "precipitation_trigger": {
    "condition": "precipitation > 0 OR forecast_precipitation_2h > 0.2"
  },
  "wind_warning_trigger": {
    "condition": "wind_speed > 10 AND temperature < 5"  
  },
  "summer_uv_trigger": {
    "condition": "time_month >= 5 AND time_month <= 8 AND time_hour >= 10 AND time_hour <= 16"
  },
  "user_override_trigger": {
    "condition": "user_preference('bottom_section') == 'detailed_sun'"
  }
}
```

### **Safety considerations:**
- Endast whitelisted functions
- Ingen kod-execution
- Validering av condition syntax
- Fallback vid evaluation-fel

### **Filförändringar:**
- **main_daemon.py** - TriggerEvaluator integration
- **weather_client.py** - Context data provider-methods

### **Test-scenarios:**
- Enkla conditions (precipitation > 0)
- Komplexa conditions (AND/OR kombinationer)
- Invalid conditions → graceful failure
- Performance med många triggers

### **Acceptanskriteria:**
- Säker condition evaluation
- Flexibel syntax för nya triggers
- Robust fel-hantering
- Bra prestanda

---

## 🎨 **FAS 3: Generell Module Rendering Pipeline**
**Mål:** Abstrahera module rendering för dynamiska moduler

### **Leverabler:**
- `ModuleRenderer` baseklass
- Specific renderers (PrecipitationRenderer, WindRenderer, etc.)
- Layout coordination system
- Module registry

### **Teknisk implementation:**
```python
class ModuleRenderer:
    def __init__(self, icon_manager, fonts):
        self.icon_manager = icon_manager
        self.fonts = fonts
    
    def render(self, canvas, draw, x, y, width, height, context_data):
        """Basemetod för all modulrendering"""
        raise NotImplementedError
    
    def get_required_data_sources(self) -> List[str]:
        """Vilka datakällor behöver denna modul"""
        return []

class PrecipitationRenderer(ModuleRenderer):
    def render(self, canvas, draw, x, y, width, height, context_data):
        # Nederbörd-specifik rendering
        precipitation = context_data.get('precipitation', 0.0)
        precip_type = context_data.get('precipitation_type', 0)
        
        # ! Utropstecken-ikon
        # Huvudtext baserat på timing
        # Intensitet-beskrivning
        
    def get_required_data_sources(self) -> List[str]:
        return ['smhi', 'forecast']

class ModuleFactory:
    renderers = {
        'precipitation_module': PrecipitationRenderer,
        'wind_module': WindRenderer,
        'uv_module': UVRenderer
    }
    
    @classmethod
    def create_renderer(cls, module_name: str) -> ModuleRenderer:
        renderer_class = cls.renderers.get(module_name)
        if renderer_class:
            return renderer_class()
        else:
            return DefaultModuleRenderer()  # Fallback
```

### **Rendering pipeline:**
```python
def render_dynamic_layout(self, weather_data: Dict):
    # 1. Evaluera triggers → få aktiva module groups
    active_modules = self.module_manager.get_active_modules()
    
    # 2. För varje aktiv modul → skapa renderer
    for module_name in active_modules:
        module_config = self.config['modules'][module_name]
        renderer = ModuleFactory.create_renderer(module_name)
        
        # 3. Rendera med rätt koordinater
        renderer.render(
            self.canvas, self.draw,
            module_config['coords']['x'],
            module_config['coords']['y'],
            module_config['size']['width'], 
            module_config['size']['height'],
            weather_data
        )
```

### **Filförändringar:**
- **main_daemon.py** - Ny rendering pipeline
- **modules/renderers/** - Nya renderer-klasser (ny mapp)

### **Test-scenarios:**
- Nederbörd-modul renderas korrekt
- Fallback renderer för okända moduler
- Layout-konflikter hanteras gracefully
- Prestanda med många moduler

### **Acceptanskriteria:**
- Modulariserad rendering-arkitektur
- Enkelt att lägga till nya modultyper
- Inga layout-konflikter
- Konsekvent design mellan moduler

---

## 📊 **FAS 4: Intelligent Change Detection**
**Mål:** Utöka change detection för layout-ändringar

### **Leverabler:**
- Layout state tracking
- Trigger change detection  
- Intelligent update decisions
- Performance optimizations

### **Teknisk implementation:**
```python
def should_update_display(self, weather_data: Dict) -> tuple:
    # Befintlig väderdata-jämförelse
    # ...
    
    # NYA: Layout change detection
    current_layout = self.current_display_state.get('active_layout', {})
    new_layout = self.module_manager.get_current_layout(weather_data)
    
    if current_layout != new_layout:
        changes = self._describe_layout_changes(current_layout, new_layout)
        return True, f"Layout-ändring: {changes}"
    
    # NYA: Trigger-specific change detection  
    for trigger_name, trigger_config in self.config['triggers'].items():
        if self._trigger_state_changed(trigger_name, weather_data):
            return True, f"Trigger-ändring: {trigger_name}"
    
    return False, "Inga förändringar"

def update_state(self, weather_data: Dict):
    self.current_display_state = {
        # Befintlig data
        # ...
        
        # NYA layout state
        'active_layout': self.module_manager.get_current_layout(weather_data),
        'active_triggers': self.module_manager.get_active_triggers(weather_data),
        'last_trigger_evaluation': time.time()
    }
```

### **Layout change examples:**
- Normal → Precipitation active
- Barometer → Sun module (user preference)
- Summer → Winter layout (seasonal)

### **Filförändringar:**
- **main_daemon.py** - Utökad change detection

### **Test-scenarios:**
- Layout-ändringar detekteras
- Onödiga uppdateringar undviks
- Trigger-kombinationer hanteras
- Performance påverkan minimal

### **Acceptanskriteria:**
- Precis change detection för layout
- Minimal E-Paper wear
- Tydlig logging av förändringar
- Stabil prestanda

---

## 🌐 **FAS 5: Extended Data Sources & Context**
**Mål:** Utöka context data för fler trigger-möjligheter

### **Leverabler:**
- SMHI observationsdata integration (nederbörd "just nu")
- Seasonal/temporal context
- User preference management
- Extended weather context

### **Context data provider:**
```python
def build_trigger_context(self, weather_data: Dict) -> Dict:
    """
    Bygg komplett context för trigger evaluation
    """
    now = datetime.now()
    
    return {
        # Väderdata
        'precipitation': weather_data.get('precipitation', 0.0),
        'forecast_precipitation_2h': self.get_forecast_precipitation_2h(weather_data),
        'temperature': weather_data.get('temperature', 20.0),
        'wind_speed': weather_data.get('wind_speed', 0.0),
        'pressure_trend': weather_data.get('pressure_trend_arrow', 'stable'),
        
        # Temporal context  
        'time_hour': now.hour,
        'time_month': now.month,
        'time_weekday': now.weekday(),
        'is_daylight': self.is_daylight(weather_data),
        
        # User context
        'user_preferences': self.config.get('user_preferences', {}),
        
        # System context
        'display_mode': self.config.get('display_mode', 'normal'),
        'debug_mode': self.config.get('debug', {}).get('enabled', False)
    }
```

### **New trigger examples:**
```json
{
  "winter_focus_trigger": {
    "condition": "time_month >= 11 OR time_month <= 2",
    "target_section": "side_panel",
    "activate_group": "winter_details",
    "description": "Visa barometer-fokus under vintermånader"
  },
  "night_mode_trigger": {
    "condition": "NOT is_daylight",
    "target_section": "hero_section", 
    "activate_group": "night_optimized",
    "description": "Natt-optimerad layout"
  },
  "strong_wind_trigger": {
    "condition": "wind_speed > 8 AND temperature < 10",
    "target_section": "bottom_section",
    "activate_group": "wind_warning", 
    "priority": 90,
    "description": "Vindvarning för cykling"
  }
}
```

### **Filförändringar:**
- **weather_client.py** - Observationsdata + extended context
- **main_daemon.py** - Context building integration
- **config.json** - Example triggers för olika scenarion

### **Test-scenarios:**
- Observationsdata för nederbörd
- Seasonal triggers fungerar
- User preference triggers
- Komplex trigger-kombinationer

### **Acceptanskriteria:**
- Rik context data tillgänglig
- SMHI observationsdata integrerat
- Flexibla trigger-möjligheter
- Robust fallback-hantering

---

## 🧪 **FAS 6: Advanced Features & Testing**
**Mål:** Slutför systemet med avancerade features och robust testing

### **Leverabler:**
- Trigger debugging interface
- Configuration validation
- Advanced module features
- Comprehensive test suite
- Documentation

### **Advanced features:**
```python
# Trigger debugging
def debug_trigger_evaluation(self, context_data: Dict) -> Dict:
    """Detaljerad trigger evaluation för debugging"""
    
# Configuration validation  
def validate_trigger_config(self, config: Dict) -> List[str]:
    """Validera trigger-konfiguration för fel"""
    
# Hot-reload configuration
def reload_trigger_config(self):
    """Ladda om trigger-config utan restart"""
    
# Trigger analytics
def get_trigger_statistics(self) -> Dict:
    """Statistik över trigger-aktivering"""
```

### **Test framework:**
```python
class DynamicModuleTestSuite:
    def test_precipitation_scenario(self):
        # Simulera nederbörd → kontrollera layout-switch
        
    def test_user_preference_override(self):
        # Testa user-driven module switching
        
    def test_trigger_priority_conflicts(self):
        # Multipla triggers → priority resolution
        
    def test_performance_many_triggers(self):
        # Performance med många aktiva triggers
```

### **Configuration examples:**
```json
{
  "advanced_triggers": {
    "cycling_optimal_trigger": {
      "condition": "precipitation == 0 AND wind_speed < 5 AND temperature > 5 AND temperature < 25",
      "target_section": "bottom_section",
      "activate_group": "cycling_optimal",
      "description": "Optimala cykelförhållanden"
    },
    "extreme_weather_trigger": {
      "condition": "temperature < -10 OR temperature > 30 OR wind_speed > 15",
      "target_section": "hero_section",
      "activate_group": "extreme_weather_warning",
      "priority": 200,
      "description": "Extremväder-varning"
    }
  }
}
```

### **Filförändringar:**
- **main_daemon.py** - Advanced features
- **tests/** - Comprehensive test suite
- **docs/** - Updated documentation
- **config_examples/** - Template configurations

### **Test-scenarios:**
- Alla trigger-kombinationer
- Performance under load
- Configuration edge-cases
- Error recovery

### **Acceptanskriteria:**
- Production-ready stability
- Comprehensive testing
- Clear documentation
- Example configurations

---

## 🏗️ **FRAMTIDA TILLÄGG (Post-Project)**

Med denna arkitektur blir följande enkla tillägg:

### **Nya modultyper:**
- **UV Index Module** (sommartid)
- **Wind Warning Module** (stark vind + låg temp)
- **Air Quality Module** (PM2.5 data)
- **Sunrise/Sunset Detail Module** (vinterhalvåret)

### **Nya triggers:**
- **Seasonal triggers** (sommar/vinter layout)
- **Time-based triggers** (arbetsdag vs helg)
- **Trend-based triggers** (tryck-trend extremer)
- **User activity triggers** (cykel-dagar vs bil-dagar)

### **Advanced integrations:**
- **Calendar integration** (växla layout baserat på aktiviteter)
- **Location awareness** (hemma vs kontor)
- **Weather alerts** (SMHI varningar)

---

## 🔧 **INSTRUKTIONER FÖR FRAMTIDA AI-ASSISTENTER**

### **Viktiga designprinciper:**
1. **Generalitet först** - Bygg aldrig speciallösningar
2. **Configuration-driven** - Allt ska vara konfigurerbart
3. **Extensibility** - Enkelt att lägga till nya moduler/triggers
4. **Performance** - Minimal påverkan på E-Paper uppdateringar
5. **Robusthet** - Graceful degradation vid fel

### **Trigger design guidelines:**
- **Simple conditions** - Lätt att förstå och debugga
- **Safe evaluation** - Ingen kod-execution
- **Clear priority** - Konflikt-resolution
- **Descriptive names** - Självförklarande purpose

### **Module design guidelines:**
- **Single responsibility** - En modul, en uppgift
- **Consistent sizing** - Standardiserade storlekar
- **Data-driven** - Inget hårdkodat innehåll
- **Error-resilient** - Fallback vid data-fel

---

## 🎯 **SLUTRESULTAT**
Ett flexibelt, generellt system för dynamiska moduler som:
- **Löser nederbörd-use case** som första exempel
- **Möjliggör framtida tillägg** utan kod-ändringar
- **Är användarkonfigurerbart** via config.json
- **Presterar optimalt** med minimal E-Paper påverkan
- **Följer modern arkitektur** med separation of concerns

**Nederbörd-modulen blir bevis på att systemet fungerar, inte målet.**
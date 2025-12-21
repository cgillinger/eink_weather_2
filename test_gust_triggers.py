#!/usr/bin/env python3
"""
STEG 3 GUST TRIGGER TEST - Isolerad testning utan GPIO/E-Paper beroenden
Testar TriggerEvaluator med wind_gust funktionalitet
"""

import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Setup minimal logging
logging.basicConfig(level=logging.INFO)

class TriggerEvaluator:
    """
    Isolerad kopia av TriggerEvaluator för testning
    STEG 3: Inkluderar wind_gust och wind_direction stöd
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TriggerEvaluator")
        
        # Whitelisted functions för säker evaluation
        self.safe_functions = {
            'precipitation': self._get_precipitation,
            'forecast_precipitation_2h': self._get_forecast_precipitation_2h,
            'temperature': self._get_temperature,
            'wind_speed': self._get_wind_speed,
            'wind_gust': self._get_wind_gust,  # STEG 3: NYTT
            'wind_direction': self._get_wind_direction,  # STEG 3: BONUS
            'pressure_trend': self._get_pressure_trend,
            'time_hour': self._get_current_hour,
            'time_month': self._get_current_month,
            'user_preference': self._get_user_preference,
            'is_daylight': self._get_is_daylight
        }
    
    def evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        Säkert evaluera trigger-condition med whitelisted functions
        STEG 3: Stöder nu wind_gust variabler
        """
        try:
            # Store context för whitelisted functions
            self._context = context
            
            # Parse och evaluera condition
            result = self._parse_and_evaluate(condition)
            
            self.logger.debug(f"Trigger evaluation: '{condition}' = {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Trigger evaluation fel: '{condition}' - {e}")
            return False
    
    def _parse_and_evaluate(self, condition: str) -> bool:
        """Parse och evaluera condition säkert"""
        try:
            # Ersätt function calls med värden
            expression = condition
            
            for func_name, func in self.safe_functions.items():
                # STEG 3: FÖRBÄTTRAD regex för bättre function call parsing
                import re
                pattern = f'{func_name}\\b'
                if re.search(pattern, expression):
                    value = func(self._context)
                    expression = re.sub(pattern, str(value), expression)
            
            # Säkerhetsvalidering av expression
            allowed_chars = set('0123456789.><= ()+-*/!%&|andornotTrueFalse ')
            allowed_words = {'AND', 'OR', 'NOT', 'True', 'False'}
            
            # Ersätt logiska operatorer med Python syntax
            expression = expression.replace(' AND ', ' and ')
            expression = expression.replace(' OR ', ' or ')
            expression = expression.replace(' NOT ', ' not ')
            
            # Kontrollera att endast säkra tokens används
            tokens = expression.split()
            for token in tokens:
                if not (all(c in allowed_chars for c in token) or token in allowed_words or token in ['and', 'or', 'not']):
                    self.logger.warning(f"Osäker token i expression: {token}")
                    return False
            
            # Evaluera expression
            result = eval(expression)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Fel vid logic evaluation: {expression} - {e}")
            return False
    
    # Whitelisted functions för context data
    def _get_precipitation(self, context: Dict) -> float:
        return float(context.get('precipitation', 0.0))
    
    def _get_forecast_precipitation_2h(self, context: Dict) -> float:
        return float(context.get('forecast_precipitation_2h', 0.0))
    
    def _get_temperature(self, context: Dict) -> float:
        return float(context.get('temperature', 20.0))
    
    def _get_wind_speed(self, context: Dict) -> float:
        return float(context.get('wind_speed', 0.0))
    
    def _get_wind_gust(self, context: Dict) -> float:
        """STEG 3: NYTT - Hämta vindbyar från context"""
        return float(context.get('wind_gust', 0.0))
    
    def _get_wind_direction(self, context: Dict) -> float:
        """STEG 3: BONUS - Hämta vindriktning från context"""
        return float(context.get('wind_direction', 0.0))
    
    def _get_pressure_trend(self, context: Dict) -> str:
        return str(context.get('pressure_trend_arrow', 'stable'))
    
    def _get_current_hour(self, context: Dict) -> int:
        return datetime.now().hour
    
    def _get_current_month(self, context: Dict) -> int:
        return datetime.now().month
    
    def _get_user_preference(self, context: Dict) -> str:
        return str(context.get('user_preferences', {}).get('module_preference', 'normal'))
    
    def _get_is_daylight(self, context: Dict) -> bool:
        return bool(context.get('is_daylight', True))


def test_gust_trigger_scenarios():
    """
    Komplett test av STEG 3 gust-trigger funktionalitet
    """
    print("🌬️ STEG 3 GUST TRIGGER TEST")
    print("=" * 50)
    
    evaluator = TriggerEvaluator()
    
    # Test scenarios för gust-triggers
    test_scenarios = [
        {
            "name": "Scenario 1: Gust trigger (medelvind under, gust över)",
            "context": {"wind_speed": 7.0, "wind_gust": 10.5},
            "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
            "expected": True,
            "description": "Ska aktivera eftersom gust (10.5) > 8.0"
        },
        {
            "name": "Scenario 2: Ingen trigger (båda under tröskelvärde)",
            "context": {"wind_speed": 6.5, "wind_gust": 7.8},
            "condition": "wind_speed > 8.0 OR wind_gust > 8.0", 
            "expected": False,
            "description": "Ska INTE aktivera eftersom båda < 8.0"
        },
        {
            "name": "Scenario 3: Medelvind trigger (gust under)",
            "context": {"wind_speed": 9.2, "wind_gust": 7.5},
            "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
            "expected": True,
            "description": "Ska aktivera eftersom medelvind (9.2) > 8.0"
        },
        {
            "name": "Scenario 4: Båda över tröskelvärde",
            "context": {"wind_speed": 10.2, "wind_gust": 15.8},
            "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
            "expected": True,
            "description": "Ska aktivera eftersom båda > 8.0"
        },
        {
            "name": "Scenario 5: Gränsvärdes-test",
            "context": {"wind_speed": 8.0, "wind_gust": 8.0},
            "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
            "expected": False,
            "description": "Ska INTE aktivera eftersom båda = 8.0 (ej >)"
        },
        {
            "name": "Scenario 6: Över gränsvärde",
            "context": {"wind_speed": 8.1, "wind_gust": 7.9},
            "condition": "wind_speed > 8.0 OR wind_gust > 8.0",
            "expected": True,
            "description": "Ska aktivera eftersom medelvind 8.1 > 8.0"
        },
        {
            "name": "Scenario 7: Avancerat - gust-differential",
            "context": {"wind_speed": 8.0, "wind_gust": 14.0},
            "condition": "(wind_gust - wind_speed) > 5.0",
            "expected": True,
            "description": "Ska aktivera eftersom (14.0 - 8.0) = 6.0 > 5.0"
        },
        {
            "name": "Scenario 8: Vindriktning + gust",
            "context": {"wind_speed": 6.0, "wind_gust": 12.0, "wind_direction": 225},
            "condition": "wind_gust > 10.0 AND wind_direction >= 180 AND wind_direction <= 270",
            "expected": True,
            "description": "Kraftig südväst-vind: gust > 10 OCH riktning 180-270°"
        },
        {
            "name": "Scenario 9: Vindriktning fel",
            "context": {"wind_speed": 6.0, "wind_gust": 12.0, "wind_direction": 45},
            "condition": "wind_gust > 10.0 AND wind_direction >= 180 AND wind_direction <= 270",
            "expected": False,
            "description": "Gust > 10 men riktning är nordost (45°), inte sydväst"
        }
    ]
    
    # Kör alla test scenarios
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Context: {scenario['context']}")
        print(f"   Condition: {scenario['condition']}")
        print(f"   {scenario['description']}")
        
        try:
            result = evaluator.evaluate_condition(scenario['condition'], scenario['context'])
            expected = scenario['expected']
            
            if result == expected:
                print(f"   ✅ PASS: {result} (förväntad: {expected})")
                passed += 1
            else:
                print(f"   ❌ FAIL: {result} (förväntad: {expected})")
                failed += 1
                
        except Exception as e:
            print(f"   💥 ERROR: {e}")
            failed += 1
    
    # Sammanfattning
    print(f"\n" + "=" * 50)
    print(f"TEST RESULTAT:")
    print(f"✅ PASS: {passed}")
    print(f"❌ FAIL: {failed}")
    print(f"📊 TOTAL: {passed + failed}")
    
    if failed == 0:
        print(f"\n🎉 ALLA TESTER GODKÄNDA - STEG 3 TRIGGER-SYSTEM FUNGERAR!")
        print(f"🌬️ Wind gust triggers implementerat korrekt")
        print(f"🔧 OR-logik fungerar för medelvind OCH vindbyar")
        return True
    else:
        print(f"\n⚠️ {failed} TESTER MISSLYCKADES - Behöver felsökning")
        return False


def test_real_weather_scenarios():
    """
    Test med realistiska väder-scenarios
    """
    print(f"\n🌤️ REALISTISKA VÄDER-SCENARIOS")
    print("=" * 50)
    
    evaluator = TriggerEvaluator()
    
    realistic_scenarios = [
        {
            "name": "Lugnt väder",
            "context": {"wind_speed": 3.2, "wind_gust": 4.5, "temperature": 15.0},
            "conditions": {
                "wind_trigger": "wind_speed > 8.0 OR wind_gust > 8.0",
                "extreme_cold": "temperature < 0.0 AND wind_gust > 5.0"
            },
            "expected": {"wind_trigger": False, "extreme_cold": False}
        },
        {
            "name": "Frisk vind (cykel-relevant)",
            "context": {"wind_speed": 9.1, "wind_gust": 13.2, "temperature": 12.0},
            "conditions": {
                "wind_trigger": "wind_speed > 8.0 OR wind_gust > 8.0",
                "cycling_warning": "wind_gust > 12.0"
            },
            "expected": {"wind_trigger": True, "cycling_warning": True}
        },
        {
            "name": "Kraftiga vindbyar (estimerade)",
            "context": {"wind_speed": 7.8, "wind_gust": 10.9, "temperature": 8.0},
            "conditions": {
                "wind_trigger": "wind_speed > 8.0 OR wind_gust > 8.0",
                "gust_differential": "(wind_gust - wind_speed) > 2.5"
            },
            "expected": {"wind_trigger": True, "gust_differential": True}
        },
        {
            "name": "Vinterstorm",
            "context": {"wind_speed": 15.2, "wind_gust": 22.1, "temperature": -3.0},
            "conditions": {
                "wind_trigger": "wind_speed > 8.0 OR wind_gust > 8.0",
                "winter_storm": "wind_gust > 20.0 AND temperature < 5.0",
                "dangerous_cycling": "wind_gust > 15.0 AND temperature < 0.0"
            },
            "expected": {"wind_trigger": True, "winter_storm": True, "dangerous_cycling": True}
        }
    ]
    
    for scenario in realistic_scenarios:
        print(f"\n📋 {scenario['name']}")
        print(f"   Väderdata: {scenario['context']}")
        
        for condition_name, condition in scenario['conditions'].items():
            result = evaluator.evaluate_condition(condition, scenario['context'])
            expected = scenario['expected'][condition_name]
            
            status = "✅" if result == expected else "❌"
            print(f"   {status} {condition_name}: {result} (condition: {condition})")


if __name__ == "__main__":
    print("🧪 STEG 3 GUST TRIGGER TESTING - Isolerad från E-Paper")
    print(f"🕐 Test körs: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Huvudtest
    success = test_gust_trigger_scenarios()
    
    # Realistiska scenarios
    test_real_weather_scenarios()
    
    # Slutsats
    if success:
        print(f"\n🎯 SLUTSATS: STEG 3 implementerat korrekt!")
        print(f"✅ TriggerEvaluator stöder wind_gust och wind_direction")
        print(f"✅ OR-logik fungerar för dubbla wind-triggers")
        print(f"✅ Avancerade conditions (differential, riktning) fungerar")
        print(f"\n📋 NÄSTA STEG: Implementera WindRenderer för visning")
    else:
        print(f"\n⚠️ Trigger-systemet behöver felsökning innan fortsättning")
    
    print(f"\n🔧 För att testa med riktiga vinddata, kör: python3 modules/weather_client.py")
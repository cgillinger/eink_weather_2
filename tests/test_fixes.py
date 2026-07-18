#!/usr/bin/env python3
"""Enhetstester för fixarna i eink_weather_2 (tryckhistorik + triggers)."""
import sys, os, json, logging, tempfile, threading
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'modules'))
logging.basicConfig(level=logging.CRITICAL)

passed = []

def check(name, cond, extra=''):
    if cond:
        passed.append(name)
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name} {extra}")
        sys.exit(1)

# ---------- Tryckhistorik ----------
print("Tryckhistorik:")
from weather_client import WeatherClient

wc = object.__new__(WeatherClient)
wc.logger = logging.getLogger('test')
tmpdir = tempfile.mkdtemp()
wc.pressure_history_file = os.path.join(tmpdir, 'pressure_history.json')
wc.pressure_history_lock = threading.Lock()
wc.PRESSURE_SAVE_MIN_INTERVAL_MINUTES = 5
wc.PRESSURE_TREND_MIN_MINUTES = 30
wc.PRESSURE_TREND_FULL_HOURS = 2.5
wc.PRESSURE_TREND_THRESHOLD_3H = 2.0
wc.PRESSURE_TREND_STABLE_3H = 0.5

# 1. Dedupe: två sparningar direkt efter varandra -> 1 post
wc.save_pressure_measurement(1000, 'smhi')
wc.save_pressure_measurement(1001, 'smhi')
with open(wc.pressure_history_file) as f:
    h = json.load(f)
check('dedupe (1 post trots 2 sparningar)', len(h) == 1, f"fick {len(h)}")
check('SMHI-källa sparas', h[0]['source'] == 'smhi')

# 2. Riktig trend: 3h historik, +5 hPa -> rising, ej preliminär
now = datetime.now()
hist = [
    {'timestamp': (now - timedelta(hours=3)).isoformat(), 'pressure': 1000, 'source': 'smhi'},
    {'timestamp': now.isoformat(), 'pressure': 1005, 'source': 'smhi'},
]
with open(wc.pressure_history_file, 'w') as f:
    json.dump(hist, f)
t = wc.calculate_3h_pressure_trend()
check('riktig trend rising vid 3h/+5hPa', t['trend'] == 'rising', str(t))
check('ej preliminär vid 3h', t['is_preliminary'] is False, str(t))

# 3. Preliminär trend: 40 min historik, +1 hPa -> rising (extrapolerat 4.5 hPa/3h), preliminär
hist = [
    {'timestamp': (now - timedelta(minutes=40)).isoformat(), 'pressure': 1000, 'source': 'netatmo'},
    {'timestamp': now.isoformat(), 'pressure': 1001, 'source': 'netatmo'},
]
with open(wc.pressure_history_file, 'w') as f:
    json.dump(hist, f)
t = wc.calculate_3h_pressure_trend()
check('preliminär trend vid 40 min', t['trend'] == 'rising' and t['is_preliminary'] is True, str(t))

# 4. För kort period: 10 min -> insufficient_data
hist = [
    {'timestamp': (now - timedelta(minutes=10)).isoformat(), 'pressure': 1000, 'source': 'smhi'},
    {'timestamp': now.isoformat(), 'pressure': 1001, 'source': 'smhi'},
]
with open(wc.pressure_history_file, 'w') as f:
    json.dump(hist, f)
t = wc.calculate_3h_pressure_trend()
check('insufficient_data vid 10 min', t['trend'] == 'insufficient_data', str(t))

# 5. Korrupt fil: självläkning i både läsning och sparning
with open(wc.pressure_history_file, 'w') as f:
    f.write('{trasig json')
t = wc.calculate_3h_pressure_trend()
check('korrupt fil -> insufficient_data (inte error)', t['trend'] == 'insufficient_data', str(t))
wc.save_pressure_measurement(1002, 'netatmo')
with open(wc.pressure_history_file) as f:
    h = json.load(f)
check('sparning självläker korrupt fil', len(h) == 1 and h[0]['pressure'] == 1002)
check('ingen kvarlämnad temp-fil', not os.path.exists(wc.pressure_history_file + '.tmp'))

# ---------- Triggers ----------
print("Triggers:")
from main_daemon import TriggerEvaluator, DynamicModuleManager

te = TriggerEvaluator()
check('NOT i början av uttryck', te._safe_eval_logic('NOT (1 > 2)') is True)
check('NOT True -> False', te._safe_eval_logic('NOT True') is False)
check('AND fungerar fortfarande', te._safe_eval_logic('1 > 0 AND 2 > 1') is True)
check('osäkra tokens avvisas', te._safe_eval_logic('__import__(1)') is False)

config = {
    'module_groups': {'bottom_section': {'normal': ['a'], 'low_group': ['b'], 'high_group': ['c']}},
    'triggers': {
        'low_prio': {'condition': '1 > 0', 'target_section': 'bottom_section',
                     'activate_group': 'low_group', 'priority': 10},
        'high_prio': {'condition': '1 > 0', 'target_section': 'bottom_section',
                      'activate_group': 'high_group', 'priority': 90},
    }
}
dm = DynamicModuleManager(config)
res = dm.evaluate_triggers({})
check('högsta prioritet vinner sektionen', res.get('bottom_section') == 'high_group', str(res))

# Lägre prioritet vinner när högre är inaktiv
config['triggers']['high_prio']['condition'] = '1 > 2'
dm2 = DynamicModuleManager(config)
res2 = dm2.evaluate_triggers({})
check('lägre prioritet vinner när högre är inaktiv', res2.get('bottom_section') == 'low_group', str(res2))

# ---------- Tryckord (pressure-descriptions.md) ----------
print("Tryckord:")
check('nivå: 975 -> Storm', wc.describe_pressure_level(975) == 'Storm')
check('nivå: 990 -> Regn', wc.describe_pressure_level(990) == 'Regn')
check('nivå: 1005 -> Ostadigt', wc.describe_pressure_level(1005) == 'Ostadigt')
check('nivå: 1013 -> Vackert (gräns)', wc.describe_pressure_level(1013) == 'Vackert')
check('nivå: 1045 -> Mycket Torrt', wc.describe_pressure_level(1045) == 'Mycket Torrt')
check('trend: -3 -> Faller snabbt', wc.describe_pressure_trend(-3) == 'Faller snabbt')
check('trend: -1 -> Faller', wc.describe_pressure_trend(-1) == 'Faller')
check('trend: 0 -> Stabilt', wc.describe_pressure_trend(0) == 'Stabilt')
check('trend: +1 -> Stiger', wc.describe_pressure_trend(1) == 'Stiger')
check('trend: +3 -> Stiger snabbt', wc.describe_pressure_trend(3) == 'Stiger snabbt')

# Pilklassificering följer nu stabilt-bandet ±0.5 (inte ±2)
hist = [
    {'timestamp': (now - timedelta(hours=3)).isoformat(), 'pressure': 1000, 'source': 'smhi'},
    {'timestamp': now.isoformat(), 'pressure': 1001, 'source': 'smhi'},
]
with open(wc.pressure_history_file, 'w') as f:
    json.dump(hist, f)
t = wc.calculate_3h_pressure_trend()
check('pil: +1 hPa/3h -> rising (spec-band)', t['trend'] == 'rising', str(t))

# ---------- Uppföljnings-PR: UV, vindriktning ----------
print("UV & vindriktning:")
from unittest.mock import patch, MagicMock

wc2 = object.__new__(WeatherClient)
wc2.logger = logging.getLogger('test')
wc2.uv_cache = {'data': None, 'timestamp': 0}
wc2.uv_api_url = 'http://example.invalid/uv'
wc2.latitude = 59.3
wc2.longitude = 18.0

resp = MagicMock()
resp.raise_for_status.return_value = None
resp.json.return_value = {
    'now': {'uvi': None},
    'forecast': [
        {'hour': '2026-07-18T10:00:00Z', 'uvi': None},
        {'hour': '2026-07-18T12:00:00Z', 'uvi': 5.0},
    ]
}
with patch('weather_client.requests.get', return_value=resp):
    uv = wc2.get_uv_data()
check('UV: null-uvi kraschar inte, max hittas', uv.get('uv_index') == 5.0, str(uv))
expected_local_hour = datetime.fromisoformat('2026-07-18T12:00:00+00:00').astimezone().hour
check('UV: peak-timme i lokal tid', uv.get('peak_hour') == expected_local_hour,
      f"fick {uv.get('peak_hour')}, väntade {expected_local_hour}")

wc2.uv_cache = {'data': {'uv_index': 3.3}, 'timestamp': 0}
resp2 = MagicMock()
resp2.raise_for_status.return_value = None
resp2.json.side_effect = ValueError('trasigt svar')
with patch('weather_client.requests.get', return_value=resp2):
    uv2 = wc2.get_uv_data()
check('UV: parsningsfel faller tillbaka på cache', uv2.get('uv_index') == 3.3, str(uv2))

from icon_manager import WeatherIconManager
im = WeatherIconManager(icon_base_path=os.path.join(REPO, 'icons/'))
check('vindriktning None -> "?" utan krasch', im.get_wind_direction_info(None) == ("?", "n"))
check('vindriktning 90 -> O', im.get_wind_direction_info(90)[0] == "O")

print(f"\nAlla {len(passed)} tester gröna.")

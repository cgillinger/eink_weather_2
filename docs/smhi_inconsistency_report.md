# SMHI API Inkonsistens - Problemanalys och Lösningsförslag

## 🔍 Problemidentifiering

### Observerat beteende:
- **HERO-modul visar:** "Lätt regn" 
- **Nederbörd-modul visar:** "Regn väntat kl 21:00"
- **Observations-data:** 0.0mm/h (regnar inte faktiskt)
- **Användarförvirring:** Motsägelsefull information på samma skärm

### Teknisk manifestation:
```
┌─────────────────────────┬─────────────┐
│ Stockholm               │ Barometer   │
│ 26.4°C ☔ "Lätt regn"  │             │  ← Weather symbol 18
├─────────────────────────┤─────────────┤
│ ⚠️  REGN VÄNTAT 21:00  │ Imorgon     │  ← Precipitation > 0.2mm/h 
│     Måttligt regn       │             │    men observations = 0
└─────────────────────────┴─────────────┘
```

## 🔎 Grundorsak - SMHI API Inkonsistens

### Datakälla-konflikt:

#### 1. **Weather Symbol (Wsymb2)**
- **Källa:** SMHI meteorologiska bedömning för nuvarande timme
- **Typ:** Kategorisk symbol (1-27)
- **Värde:** 18 = "Lätt regn" 
- **Interpretation:** Vädersituation "nu"

#### 2. **Precipitation Data (pmin)**  
- **Källa:** SMHI kvantitativa mätningar/prognoser
- **Typ:** Numerisk (mm/h)
- **Värde:** 0.0mm/h för nuvarande, >0.2mm/h för framtida
- **Interpretation:** Faktisk nederbörd "nu" vs "senare"

#### 3. **SMHI Observations**
- **Källa:** Observatorielunden (station 98230) senaste timmen
- **Typ:** Verklig mätning
- **Värde:** 0.0mm/h
- **Interpretation:** Faktisk nederbörd "nu"

### API-struktur problem:

```json
// SMHI API returnerar inkonsistenta signaler:
{
  "timeSeries": [
    {
      "validTime": "2025-07-30T17:00:00Z", // Nu (19:00 lokal)
      "parameters": [
        {"name": "Wsymb2", "values": [18]},    // "Lätt regn" 
        {"name": "pmin", "values": [0.0]}      // 0mm/h (!!)
      ]
    },
    {
      "validTime": "2025-07-30T19:00:00Z", // Senare (21:00 lokal)
      "parameters": [
        {"name": "Wsymb2", "values": [6]},     // "Mulet"
        {"name": "pmin", "values": [0.5]}      // 0.5mm/h
      ]
    }
  ]
}
```

## 🧠 Problemanalys

### Orsaker till inkonsistens:

1. **Olika tidshorisonter**
   - Weather symbol: Meteorologisk bedömning för "aktuell vädertyp"
   - Precipitation: Kvantitativ prognos för specifik timme
   - Kan representera olika tidsperioder inom samma "timme"

2. **Olika prognosmodeller**
   - Weather symbol: Kvalitativ vädertyp-algoritm
   - Precipitation: Kvantitativ nederbörd-modell  
   - Modellerna kan ge olika resultat för samma situation

3. **Meteorologisk komplexitet**
   - "Lätt regn" kan betyda "regnväder pågår i området"
   - Men specifik plats får 0mm/h just nu
   - Observations bekräftar: inget regn på exakt position

4. **API-design brister**
   - Ingen synkronisering mellan olika parametrar
   - Användare förväntar sig konsistent data
   - Systemet måste hantera inkonsistenser

## ✅ Lösningsförslag

### **Lösning 1: Data-prioritering med observations (REKOMMENDERAT)**

**Koncept:** Prioritera verklig mätdata över prognoser för "nu"-visning

**Implementation:**
```python
def get_current_weather_description(weather_symbol, observations_precipitation, pmin_current):
    """Synkronisera weather description med observations"""
    
    # Om observations visar att det INTE regnar nu
    if observations_precipitation == 0.0:
        # Men weather symbol säger regn
        if weather_symbol in [8, 9, 10, 18, 19, 20, 21]:  # Regn-symboler
            # Ändra till "väntat" istället för "pågår"
            regn_descriptions = {
                8: "Regnskurar väntat",
                9: "Regnskurar väntat", 
                10: "Kraftiga regnskurar väntat",
                18: "Regn väntat",
                19: "Regn väntat", 
                20: "Kraftigt regn väntat",
                21: "Åska väntat"
            }
            return regn_descriptions.get(weather_symbol, "Regn väntat")
    
    # Använd normal mappning om observations stämmer
    return standard_weather_descriptions[weather_symbol]
```

**Fördelar:**
- ✅ Konsistent med observations-data
- ✅ Ärlig mot användaren (regnar inte nu, men väntat)
- ✅ Behåller meteorologisk information
- ✅ Minimal kodändring

**Nackdelar:**
- ⚠️ Kräver observations-data (fallback behövs)
- ⚠️ Kan "dölja" meteorologiska nyanser

---

### **Lösning 2: Dubbel informationsvisning**

**Koncept:** Visa både meteorologisk bedömning och faktisk situation

**Implementation:**
```python
def get_enhanced_weather_description(weather_symbol, observations, pmin_current):
    """Visa både prognos och observations"""
    
    base_description = standard_weather_descriptions[weather_symbol]
    
    # Om inkonsistens mellan symbol och observations
    if weather_symbol in [18, 19, 20] and observations == 0.0:
        return f"{base_description} (ej lokalt just nu)"
    
    return base_description
```

**HERO-modul skulle visa:**
```
Stockholm
26.4°C ☔ Lätt regn (ej lokalt just nu)
(NETATMO)
```

**Fördelar:**
- ✅ Transparent - visar både prognos och verklighet  
- ✅ Utbildar användaren om meteorologi
- ✅ Behåller all information

**Nackdelar:**
- ❌ Längre text (kan bli trångt)
- ❌ Mer komplext för användaren
- ❌ Teknisk information för icke-meteorologer

---

### **Lösning 3: Intelligent trigger-logik**

**Koncept:** Förbättra trigger-systemet att hantera inkonsistenser

**Implementation:**
```python  
def evaluate_precipitation_trigger(weather_symbol, observations, forecast_2h):
    """Intelligent trigger som hanterar SMHI-inkonsistenser"""
    
    # Prioritet 1: Regnar faktiskt nu
    if observations > 0:
        return True, "REGNAR NU"
    
    # Prioritet 2: Regn väntat inom 2h
    if forecast_2h >= 0.2:
        return True, f"REGN VÄNTAT"
    
    # Prioritet 3: Weather symbol indikerar regn MEN observations = 0
    if weather_symbol in [18, 19, 20] and observations == 0:
        return True, "REGN MÖJLIGT (meteorologisk bedömning)"
    
    return False, "Ingen nederbörd"
```

**Fördelar:**
- ✅ Hanterar alla edge cases
- ✅ Ger tydlig information till användaren  
- ✅ Använder all tillgänglig data optimalt

**Nackdelar:**
- ⚠️ Komplexare logik att underhålla
- ⚠️ Fler trigger-aktiveringar (kan vara "fladdrig")

---

### **Lösning 4: Cache-synkronisering**

**Koncept:** Säkerställ att alla datakällor använder samma tid-snapshot

**Implementation:**
```python
def get_synchronized_weather_data():
    """Hämta synkroniserad data från samma API-anrop"""
    
    # Använd SAMMA SMHI API-anrop för både weather_symbol och precipitation
    raw_smhi_data = fetch_smhi_forecast()
    current_forecast = get_current_hour_forecast(raw_smhi_data)
    
    # Extrahera BÅDA värden från samma tidsstämpel
    weather_symbol = current_forecast.get_weather_symbol()
    precipitation_now = current_forecast.get_precipitation()
    
    # Om fortfarande inkonsistens, logga och prioritera observations
    if weather_symbol in [18,19,20] and precipitation_now == 0:
        logger.warning(f"SMHI inkonsistens: Symbol {weather_symbol} men pmin=0")
        
    return synchronized_data
```

**Fördelar:**  
- ✅ Eliminerar cache-timing problem
- ✅ Säkerställer data-konsistens
- ✅ Lättare att debugga

**Nackdelar:**
- ⚠️ Löser inte grundproblemet (SMHI-inkonsistens kvarstår)
- ⚠️ Kan öka API-anrop

## 🎯 Rekommendation

**Kombinera Lösning 1 + 3:** 

1. **Implementera observations-baserad weather description** (Lösning 1)
2. **Förbättra trigger-logiken** för edge cases (Lösning 3)

Detta ger:
- ✅ Konsistent användarupplevelse
- ✅ Ärlig information (regnar inte nu = visa inte "regnar nu")  
- ✅ Intelligent hantering av meteorologisk komplexitet
- ✅ Användbar information för praktiska beslut

**Minimal implementation:** Börja med Lösning 1 eftersom den löser det mest irriterande problemet (felaktig "regnar nu" information) med minsta kodändring.

## 📊 Implementation Priority

1. **Hög prioritet:** Lösning 1 - Observations-synkroniserad weather description
2. **Medium prioritet:** Lösning 3 - Förbättrad trigger-logik  
3. **Låg prioritet:** Lösning 4 - Cache-synkronisering
4. **Ej rekommenderat:** Lösning 2 - För komplext för användaren

## 🔧 Teknisk Implementation

För att implementera Lösning 1, ändra i `weather_client.py`, funktionen `combine_weather_data()`:

```python
# Lägg till efter weather_symbol assignment:
if observations_data and combined.get('weather_symbol'):
    # Synkronisera weather description med observations
    combined['weather_description'] = self.get_observations_synchronized_description(
        combined['weather_symbol'], 
        observations_data.get('precipitation_observed', 0.0)
    )
```

Detta löser problemet med minimal impact på befintlig kod.
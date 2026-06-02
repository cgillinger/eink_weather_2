# E-Paper Weather Station

**Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480px)**

**🚴‍♂️ Intelligent weather warnings for cyclists and pedestrians** - automatically alerts for rain and strong winds to help you plan your commute.

> This is a personal hobby project I build for my own use and publish in case it's useful to someone else. I work on it in my spare time, so issues and PRs are welcome but replies may be slow. Use at your own risk.

---

## 🌍 Multi-Provider Weather System

**NEW:** This weather station now supports **two weather data providers** with automatic provider selection:

- **🇸🇪 SMHI** - Swedish Meteorological Institute (Sweden only, full features including real-time observations)
- **🌐 YR** - MET Norway (Global coverage anywhere on Earth, forecast-only)

Switch between providers by simply changing one line in `config.json` - the system automatically adapts features and display based on the selected provider's capabilities.

---

## Project Overview

An intelligent weather station with E-Paper display built around your **Netatmo Weather Station** as the central data source, complemented by professional weather forecasts and astronomical data. The system combines your local sensor measurements with global weather providers through a **dynamic module system** that automatically adapts based on current conditions.

### Core Architecture

**🏠 Netatmo Weather Station (Your Local Observatory)**
- Your own weather station provides the most accurate local data
- Temperature, pressure, humidity, and precipitation measurements
- Real-time updates every 10 minutes from your sensors
- Works with both Gen 1 and Gen 2 Netatmo stations

**🌍 Weather Forecasts (Choose Your Provider)**
- **SMHI** (Sweden) - adds official weather station observations + forecasts
- **YR** (Global) - adds professional forecasts for anywhere on Earth
- Complement your Netatmo data with professional meteorological predictions

**☀️ Additional Data Sources**
- **UV Index** - CurrentUVIndex.com (global coverage)
- **Sun Times** - ipgeolocation.io (precise astronomical data)

### Key Features

- **🚴‍♂️ Cycling & Pedestrian Warnings**: Automatic alerts for rain and strong winds (>6 m/s) to help plan your commute
- **🏠 Netatmo Integration**: Your local weather station is the primary data source
- **🌍 Multi-Provider Forecasts**: Choose between SMHI (Sweden) or YR (Global) for forecast data
- **🔄 Dynamic Module System**: Modules activate automatically based on weather conditions
- **📊 Real-time Observations**: From your Netatmo sensors + SMHI weather stations (Sweden only)
- **☀️ UV Index**: Current UV levels from CurrentUVIndex.com
- **🧠 Intelligent Fallbacks**: Works even if some APIs are unavailable
- **🎨 Professional Icons**: High-quality Weather Icons with provider-specific symbol mapping

### What if I Don't Have Netatmo?

**The system works perfectly without Netatmo!** Here's what changes:

**Without Netatmo:**
- ✅ **Still works** - weather forecasts from SMHI/YR provider
- ✅ **Still works** - UV index and sun times
- ✅ **Temperature** - from weather provider instead of local sensor
- ✅ **Pressure** - from weather provider instead of local barometer
- ❌ **Lost** - local precipitation measurements (must rely on forecasts or SMHI observations)
- ❌ **Lost** - precise 3-hour pressure trends (uses forecast data instead)
- ❌ **Lost** - battery status monitoring

**Recommendation:** If you don't have Netatmo:
- For Sweden: Use **SMHI provider** to get official weather station observations
- For Global: Use **YR provider** with forecast-based precipitation detection
- The station still provides excellent weather information from professional sources!

---

## Weather Provider Comparison

Choose the weather provider that best complements your Netatmo Weather Station (or works standalone if you don't have Netatmo).

| Feature | SMHI (Sweden) | YR (Global) | Netatmo (Optional) |
|---------|---------------|-------------|-------------------|
| **Geographic Coverage** | 🇸🇪 Sweden only | 🌍 Worldwide | 🏠 Your location |
| **Weather Forecasts** | ✅ Yes (27 symbols) | ✅ Yes (102 conditions) | ❌ No |
| **Real-time Observations** | ✅ Yes (weather stations) | ❌ No (forecast-only) | ✅ Yes (your sensors) |
| **Temperature** | ✅ Forecast | ✅ Forecast | ✅ **Local measurement** |
| **Barometric Pressure** | ✅ Forecast | ✅ Forecast | ✅ **Local measurement** |
| **Precipitation** | ✅ Stations + Forecast | ❌ Forecast only | ✅ **Rain gauge** |
| **3-hour Pressure Trend** | ❌ No | ❌ No | ✅ **Yes** |
| **Wind Data** | ✅ Forecast | ✅ Forecast | ❌ No |
| **Cycling Weather Analysis** | ✅ Yes (obs + forecast) | ✅ Yes (forecast-only) | ✅ Enhances both |
| **Snow Filtering** | ✅ Yes (pcat codes) | ✅ Yes (symbol-based) | N/A |
| **API Key Required** | ❌ No (free API) | ❌ No (free API) | ✅ Yes (free account) |
| **Update Interval** | 30 min (forecast), 15 min (obs) | 10 min minimum | **10 minutes** |
| **Best For** | Swedish users wanting official data | Global users, travelers | **Everyone!** |

### Recommended Combinations

**🏆 Best Setup (Sweden):**
- ✅ Netatmo Weather Station (your local observatory)
- ✅ SMHI Provider (official stations + forecasts)
- ✅ Result: Triple verification (Netatmo + SMHI station + SMHI forecast)

**🏆 Best Setup (Global):**
- ✅ Netatmo Weather Station (your local observatory)
- ✅ YR Provider (global forecasts)
- ✅ Result: Local precision + professional forecasts

**🏆 Without Netatmo (Sweden):**
- ✅ SMHI Provider (official weather stations + forecasts)
- ✅ Result: Still excellent with official observations

**🏆 Without Netatmo (Global):**
- ✅ YR Provider (global forecasts)
- ✅ Result: Professional forecast coverage worldwide

---

## Hardware Requirements

### Components
- **Raspberry Pi 3B** (or newer)
- **Waveshare 4.26" E-Paper HAT** (800×480px, black & white)
- **SPI enabled** (`lsmod | grep spi` should show spi modules)
- **Internet connection** for API calls

### E-Paper Specifications
- **Resolution**: 800×480 pixels
- **Colors**: 1-bit black & white (optimized for E-Paper)
- **Refresh time**: ~10 seconds per render
- **Power consumption**: Very low (E-Paper retains image without power)

---

## Data Sources

### 🏠 Netatmo Weather Station (Your Primary Data Source)

**Your local weather station - the core of the system**

The Netatmo Weather Station is your personal observatory and provides the most accurate local measurements. All other data sources complement what Netatmo provides.

**Measurements from your Netatmo:**
- 🌡️ **Outdoor Temperature** (NAModule1 outdoor module) - most accurate local temperature
- 📊 **Air Pressure** (indoor base station) - precise local barometric pressure
- 🌧️ **Precipitation** (NAModule3 rain gauge) - real-time rain detection with 5-minute precision
- 💨 **Humidity** (outdoor + indoor modules) - local humidity measurements
- 📈 **3-hour Pressure Trend** - meteorological standard for weather prediction
- 🔋 **Battery Status** - monitor outdoor module and rain gauge batteries

**Netatmo Compatibility:**
- ✅ **Gen 1** - Fully supported (uses external UV data)
- ✅ **Gen 2** - Fully supported (uses external UV data, Gen 2's native UV ignored)

**Required Modules:**
- **Base Station** (indoor module) - required
- **NAModule1** (outdoor module) - required for temperature/humidity
- **NAModule3** (rain gauge) - optional but highly recommended

**Update Interval:** Every 10 minutes from your sensors

### 🌍 Weather Forecast Providers (Choose One to Complement Netatmo)

Your Netatmo provides local measurements. Choose a weather provider to add professional forecasts and weather symbols.

#### 🇸🇪 SMHI (Swedish Meteorological Institute)
**For users in Sweden - adds official observations + forecasts**

What SMHI adds to your Netatmo data:
- 🌤️ **Weather Symbols** (27 SMHI symbols with day/night variants)
- 📊 **Official Weather Stations** - real-time precipitation from Swedish meteorological stations
- 🌧️ **"Is it raining NOW?"** - combine your Netatmo with nearby SMHI station for verification
- 🚴 **Cycling Weather Analysis** - combines your Netatmo + SMHI observations + forecasts
- 🌨️ **Snow Filtering** - prevents snow from triggering rain warnings
- 💨 **Wind Forecast** - wind speed and direction predictions

**Data Priority with SMHI:**
1. Your Netatmo (temperature, pressure, rain) - HIGHEST priority
2. SMHI weather stations (verification/fallback for precipitation)
3. SMHI forecasts (weather symbols, future conditions)

**Best for:**
- ✅ Swedish users wanting official weather station data
- ✅ Verifying your Netatmo rain gauge with nearby stations
- ✅ Most accurate precipitation detection for cycling

#### 🌐 YR (MET Norway)
**For global users - adds professional forecasts anywhere on Earth**

What YR adds to your Netatmo data:
- 🌍 **Global Coverage** - works anywhere (Tokyo, New York, Sydney, etc.)
- 🌤️ **Weather Symbols** (102 weather conditions mapped to ~29 icon types)
- 💨 **Wind Forecast** - wind speed and direction predictions
- 🌡️ **Temperature Forecast** - future temperature predictions
- 🌧️ **Precipitation Forecast** - rain/snow predictions

**Data Priority with YR:**
1. Your Netatmo (temperature, pressure, rain) - HIGHEST priority
2. YR forecasts (weather symbols, future conditions)

**Best for:**
- ✅ Users outside Sweden
- ✅ Global deployment (multiple locations worldwide)
- ✅ Travelers wanting to deploy in different countries
- ✅ Access to comprehensive weather conditions (102 vs SMHI's 27)

**Note:** YR doesn't provide real-time observations - only forecasts

### ☀️ Additional Data Sources (Works with All Configurations)

#### CurrentUVIndex.com (UV Data)
- ☀️ **Current UV Index** - real-time measurement
- 📈 **Daily Peak UV** - forecast maximum
- 🎯 **Risk Classification** - Low/Moderate/High/Very High/Extreme
- 🆓 **Free API** - no key required, 500 calls/day
- ⏱️ **6-hour Cache** - balances freshness with API limits

#### ipgeolocation.io API (Sun Times)
- ☀️ **Sunrise/Sunset** - precise times for your coordinates
- ⏰ **Daylight Duration** - automatic calculation
- 🌅 **Day/Night Logic** - for weather icon selection

### Without Netatmo - Provider-Only Mode

**Don't have Netatmo? The system still works excellently!**

**What you get without Netatmo:**

Using **SMHI provider** (Sweden):
- ✅ Temperature from SMHI forecasts
- ✅ Pressure from SMHI forecasts  
- ✅ **Real-time precipitation from official SMHI weather stations** (e.g., Observatorielunden in Stockholm)
- ✅ Weather symbols and forecasts
- ✅ UV index and sun times
- ❌ No local measurements (less accurate than having your own station)
- ❌ No battery monitoring
- ❌ No precise 3-hour pressure trends (uses forecast trends instead)

Using **YR provider** (Global):
- ✅ Temperature from YR forecasts
- ✅ Pressure from YR forecasts
- ✅ Weather symbols and forecasts
- ✅ UV index and sun times
- ❌ No real-time precipitation observations (forecast-only)
- ❌ No local measurements
- ❌ No battery monitoring
- ❌ No precise 3-hour pressure trends

**Recommendation without Netatmo:**
- 🇸🇪 **In Sweden**: Use SMHI provider to get official weather station observations
- 🌍 **Outside Sweden**: Use YR provider for global forecast coverage

The station provides professional weather information even without Netatmo, you just lose the hyper-local precision of your own sensors.

---

## Data Priority System

The system intelligently prioritizes data sources, always preferring your local Netatmo measurements over remote forecasts.

### Core Principle: Local First, Forecasts Second

**Your Netatmo sensors are ALWAYS prioritized** when available:
- Your outdoor temperature > Provider temperature forecast
- Your barometric pressure > Provider pressure forecast  
- Your rain gauge > Any remote precipitation data

### Detailed Priority Rules

#### Temperature & Pressure
1. **Netatmo** - Your local sensors (highest accuracy)
2. **Weather Provider** (SMHI/YR) - Forecast fallback if Netatmo unavailable

#### Precipitation (with Netatmo + SMHI)
1. **Netatmo Rain Gauge** (5-min delay) - Your local rain measurement
2. **SMHI Weather Stations** (10-60 min delay) - Official observations for verification
3. **SMHI Forecasts** - Prediction fallback

#### Precipitation (with Netatmo + YR)  
1. **Netatmo Rain Gauge** (5-min delay) - Your local rain measurement
2. **YR Forecasts** - Only forecast data available (YR has no observations)

#### Precipitation (WITHOUT Netatmo)

With **SMHI provider:**
1. **SMHI Weather Stations** - Official observations from nearby station
2. **SMHI Forecasts** - Prediction fallback

With **YR provider:**
1. **YR Forecasts** - Only source available (no observations)

#### UV Index (All Configurations)
1. **CurrentUVIndex.com** (6-hour cache)
2. **No fallback** - displays only when available

#### Sun Times (All Configurations)
1. **ipgeolocation.io** - Astronomical calculations
2. **No fallback** - displays only when available

### Why Netatmo First?

Your Netatmo Weather Station measures **actual conditions at your exact location**, while forecast providers:
- Predict conditions for a general area
- Update less frequently
- Can be less accurate for hyper-local conditions

**Example scenario:**
- Your Netatmo measures 18.5°C at your home
- SMHI forecasts 20°C for your region
- **Display shows: 18.5°C** (Netatmo is the truth)

---

## Configuration

### Basic Setup

The system requires two main configuration choices:

1. **Weather Provider**: Choose SMHI (Sweden) or YR (Global)
2. **Netatmo**: Configure if you have a Netatmo Weather Station, skip if you don't

### Configuration for Users WITH Netatmo

**Edit `config.json`:**

```json
{
  "weather_provider": "smhi",  // or "yr" for global coverage
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686
  },
  "api_keys": {
    "netatmo": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET",
      "refresh_token": "YOUR_REFRESH_TOKEN"
    }
  }
}
```

**Get Netatmo credentials:**
1. Go to https://dev.netatmo.com
2. Create app to get client_id and client_secret
3. Use OAuth flow to get refresh_token
4. Add to config.json

### Configuration for Users WITHOUT Netatmo

**Edit `config.json`:**

```json
{
  "weather_provider": "smhi",  // or "yr"
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686
  }
}
```

**Important:** Simply **omit the `api_keys.netatmo` section** entirely. The system will:
- ✅ Detect Netatmo is not configured
- ✅ Automatically fall back to provider data for temperature/pressure
- ✅ Use SMHI observations (if SMHI provider) or forecasts (if YR provider) for precipitation
- ✅ Continue to work perfectly with available data sources

**No errors, no warnings** - it just works with what's available!

### Switching Between Providers

**Change provider in `config.json`:**

```json
{
  "weather_provider": "smhi",  // or "yr" for global coverage
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686
  }
}
```

**Then restart:**
```bash
python3 ~/epaper_weather/restart.py
```

### Configuration Examples

#### Example 1: SMHI Provider (Sweden)
```json
{
  "weather_provider": "smhi",
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686
  },
  "smhi_observations": {
    "primary_station_id": "98230",
    "primary_station_name": "Stockholm-Observatoriekullen A",
    "fallback_station_id": "97390",
    "fallback_station_name": "Stockholm-Arlanda"
  }
}
```

**Other Swedish Cities:**
- **Göteborg**: Primary `71420` (Göteborg A), Fallback `71380` (Vinga A)
- **Malmö**: Primary `52350` (Malmö A), Fallback `62040` (Helsingborg A)

Find more stations at: https://www.smhi.se/data/meteorologi/ladda-ner-meteorologiska-observationer

#### Example 2: YR Provider (Global)
```json
{
  "weather_provider": "yr",
  "location": {
    "name": "Tokyo",
    "latitude": 35.6762,
    "longitude": 139.6503
  }
}
```

**Note:** YR doesn't use observation stations - the `smhi_observations` section is ignored.

**Global Location Examples:**
- **New York**: `40.7128, -74.0060`
- **London**: `51.5074, -0.1278`
- **Sydney**: `-33.8688, 151.2093`
- **Singapore**: `1.3521, 103.8198`

---

## Netatmo Setup Guide

**If you have a Netatmo Weather Station**, follow these steps to connect it to the E-Paper display.

### Step 1: Create Netatmo Developer Account

1. Go to: https://dev.netatmo.com
2. Click "Create an account" (or login if you already have one)
3. Use the same email as your Netatmo Weather Station account
4. Verify your email address

### Step 2: Create an App

1. Once logged in, go to "My Apps": https://dev.netatmo.com/apps
2. Click "Create" to create a new app
3. Fill in the form:
   - **App Name**: "E-Paper Weather Station" (or any name you want)
   - **Description**: "Personal weather display" (or any description)
   - **Data Protection Officer**: Your email
   - **Website**: Can be empty or your personal website
   - **App type**: Select "Weather Station"
   - **Redirect URI**: `http://localhost` (important!)
4. Click "Save"
5. You'll now see your app with:
   - **Client ID** - Copy this, you'll need it for config.json
   - **Client Secret** - Click "Show" and copy this too

### Step 3: Get Refresh Token

This is the trickiest part. You need to get a refresh token using OAuth2 flow.

**Method 1: Using Web Browser (Easiest)**

1. Build this URL (replace YOUR_CLIENT_ID with your actual Client ID):
   ```
   https://api.netatmo.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&scope=read_station&state=any
   ```

2. Open this URL in your web browser
3. Login with your Netatmo account (same account that has your weather station)
4. Click "Allow" to grant access
5. You'll be redirected to `http://localhost/?code=SOME_CODE&state=any`
6. **Copy the CODE from the URL** (the part after `code=` and before `&state`)

7. Now exchange this code for a refresh token using curl:
   ```bash
   curl -X POST "https://api.netatmo.com/oauth2/token" \
     -d "grant_type=authorization_code" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "code=THE_CODE_YOU_COPIED" \
     -d "redirect_uri=http://localhost" \
     -d "scope=read_station"
   ```

8. You'll get a JSON response with:
   ```json
   {
     "access_token": "...",
     "refresh_token": "THIS_IS_WHAT_YOU_NEED|...",
     "expires_in": 10800
   }
   ```

9. **Copy the refresh_token** - it's the long string that looks like `5c3dd9b22733bf0c008b8f1c|29bed9d652a614b35738718f5ae859ce`

**Method 2: Using Python Script (Alternative)**

Create a file `get_netatmo_token.py`:

```python
#!/usr/bin/env python3
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs

# Your app credentials
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "http://localhost"

# Step 1: Get authorization
auth_url = (
    f"https://api.netatmo.com/oauth2/authorize?"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={REDIRECT_URI}&"
    f"scope=read_station&"
    f"state=any"
)

print("Opening browser for authorization...")
print("After authorizing, copy the FULL URL from your browser")
webbrowser.open(auth_url)

redirect_url = input("\nPaste the redirect URL here: ")

# Extract code
parsed = urlparse(redirect_url)
code = parse_qs(parsed.query)['code'][0]
print(f"\n✅ Authorization code: {code}")

# Step 2: Exchange for tokens
token_url = "https://api.netatmo.com/oauth2/token"
data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "scope": "read_station"
}

response = requests.post(token_url, data=data)
tokens = response.json()

if 'refresh_token' in tokens:
    print(f"\n✅ SUCCESS! Your refresh token:")
    print(f"\n{tokens['refresh_token']}\n")
    print("Copy this to config.json in the netatmo.refresh_token field")
else:
    print(f"\n❌ Error: {tokens}")
```

Run it:
```bash
python3 get_netatmo_token.py
```

### Step 4: Add to config.json

Now add all three values to your `config.json`:

```json
{
  "api_keys": {
    "netatmo": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET",
      "refresh_token": "YOUR_REFRESH_TOKEN"
    }
  }
}
```

### Step 5: Verify Setup

Restart the daemon and check logs:

```bash
python3 ~/epaper_weather/restart.py
sudo journalctl -u epaper-weather -f | grep Netatmo
```

You should see:
```
✅ Netatmo token förnyad (gäller 3h)
🏠 Netatmo sensorer: Temp: XX.X°C, Tryck: XXXX hPa...
```

### Troubleshooting Netatmo Setup

**"Invalid client" error:**
- Check that client_id and client_secret are correct
- Make sure there are no extra spaces or quotes

**"Invalid refresh token" error:**
- Refresh token has expired (they expire after ~2 months of no use)
- Generate a new refresh token following Step 3 again

**"No weather station data" error:**
- Make sure your Netatmo account actually has a weather station connected
- Check that you authorized the correct Netatmo account (same one with the weather station)

**Token expires too quickly:**
- Normal! The system automatically refreshes the access token every 3 hours
- The refresh_token is long-lived and should work for months

### Important Notes

- **Refresh tokens are long-lived** - they last for months and are automatically used to get new access tokens
- **Access tokens expire after 3 hours** - the system handles this automatically
- **Keep your credentials secret** - don't commit config.json to public repositories
- **One app can access multiple weather stations** - if you have multiple Netatmo stations on the same account

---

## SMHI Observations Configuration

**For SMHI provider users in Sweden:**

The observation system uses Swedish weather stations to provide "is it raining NOW?" real-time data.

### Configuration Fields

```json
{
  "smhi_observations": {
    "primary_station_id": "98230",
    "primary_station_name": "Stockholm-Observatoriekullen A",
    "fallback_station_id": "97390",
    "fallback_station_name": "Stockholm-Arlanda"
  }
}
```

**Fields:**
- `primary_station_id` - Main weather station ID for precipitation observations
- `primary_station_name` - Station name (for display/logging)
- `fallback_station_id` - Backup station if primary fails
- `fallback_station_name` - Backup station name

### Station Examples for Major Cities

| City | Primary Station | Fallback Station |
|------|----------------|------------------|
| **Stockholm** | `98230` (Observatoriekullen A) | `97390` (Arlanda) |
| **Göteborg** | `71420` (Göteborg A) | `71380` (Vinga A) |
| **Malmö** | `52350` (Malmö A) | `62040` (Helsingborg A) |
| **Uppsala** | `97510` (Uppsala Aut) | `97530` (Uppsala Flygplats) |
| **Linköping** | `85240` (Linköping-Malmslätt) | `86420` (Kolmården-Strömsfors A) |

**Find stations for your city:**
1. Visit: https://www.smhi.se/data/meteorologi/ladda-ner-meteorologiska-observationer
2. Select "Nederbörd" (precipitation) parameter
3. Zoom map to your city
4. Click stations to see station ID and name
5. Add to your `config.json`

---

## Dynamic Module System

**🚴‍♂️ Perfect for daily commute planning** - the system automatically alerts you when conditions are unfavorable for cycling or walking.

The system automatically switches between different modules based on:
- 🌧️ **Precipitation Detection** - warns cyclists when rain is detected or forecast
- 💨 **Wind Conditions** - alerts when wind exceeds safe cycling thresholds (>6 m/s)
- 👤 **User Settings** - customize trigger thresholds for your preferences
- ⏰ **Time/Season** - potential for UV index in summer, dark month layouts
- 🎯 **Trigger Conditions** - fully customizable conditions

### Cycling Weather Warnings

**Precipitation Warning:**
- Triggers when rain is detected by your Netatmo Rain Gauge
- Or when SMHI weather stations report precipitation (Sweden)
- Or when rain is forecast within 2 hours
- Display shows: **"⚠️ RAINING NOW"** or **"⚠️ RAIN EXPECTED"**

**Wind Warning:**
- Triggers when wind speed exceeds 6 m/s (moderate wind)
- Customizable threshold in config.json
- Display shows: Wind speed, direction, and Swedish wind description
- Helps decide if cycling is safe/comfortable

### Trigger-Based Modules

```json
{
  "triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR (forecast_precipitation_2h >= 0.2 AND (pcat == 2 OR pcat == 3 OR pcat == 5))",
      "target_section": "bottom_section",
      "activate_group": "precipitation_active",
      "priority": 100,
      "description": "Activate on: 1) Rain now (Netatmo/Observations), or 2) Rain expected within 2h"
    },
    "wind_trigger": {
      "condition": "wind_speed > 6.0",
      "target_section": "medium_right_section",
      "activate_group": "wind_active",
      "priority": 80,
      "description": "Activate wind module at wind speed >6 m/s"
    }
  }
}
```

**Dynamic Switching Example:**
- **Normal layout**: Clock + Status at bottom, Barometer on right
- **Precipitation detected**: Automatic switch to precipitation warning
- **Strong wind**: Wind module replaces barometer
- **After weather event**: Automatic return to normal layout

---

## Layout

### Layout A (Default)

**Total data points: 16+**

```
┌─────────────────────────┬─────────────┐
│ Stockholm               │ 1007 ↗️     │
│ 25.1°C ⛅              │ hPa         │
│ Light rain showers     │ Rising      │
│ (NETATMO/YR forecast)  │ (Netatmo)   │
│ 🌅 04:16  🌇 21:30    ├─────────────┤
│ ☀️ UV 3.2             │ Tomorrow ⛅  │
├─────────┬──────────────┤ 25.4°C      │
│ 📅 25/7 │ Update: 12:07│ Partly cloud│
│ Friday  │ 🔋 85% Out   │ (YR prognos)│
│         │ 🔋 92% Rain  │             │
└─────────┴──────────────┴─────────────┘
```

**Provider-specific display:**
- **SMHI**: Shows "(SMHI prognos)" or "(Observatorielunden)" based on data source
- **YR**: Shows "(YR prognos)"

### Dynamic Bottom Section

**Normal (no precipitation):**
```
┌─────────┬──────────────┐
│ Clock   │ Status       │
└─────────┴──────────────┘
```

**Precipitation detected:**
```
┌───────────────────────────┐
│ ⚠️  RAINING NOW: LIGHT   │
│     (Observatorielunden)  │  ← SMHI only
│     2.5mm last hour       │
└───────────────────────────┘
```

or

```
┌───────────────────────────┐
│ ⚠️  RAIN EXPECTED: LIGHT │
│     (YR forecast)         │  ← YR provider
│     Next 2 hours          │
└───────────────────────────┘
```

---

## Icon System - Weather Icons Integration

### SVG→PNG Conversion System
The app uses high-quality PNG icons converted from Weather Icons SVG sources with E-Paper optimization.

**Icon Sources:**
- **SVG source**: `\\EINK-WEATHER\downloads\weather-icons-master\svg\` (Windows share)
- **PNG destination**: `~/epaper_weather/icons/` (Raspberry Pi)
- **Conversion**: Via `convert_svg_to_png.py` in virtual environment with cairosvg

### Provider-Specific Icon Mapping

**SMHI Symbols (27 total):**
- Integer codes 1-27
- Day/night variants
- Mapped to Weather Icons (e.g., symbol 1 → "day-sunny.png")

**YR Symbols (102 weather conditions):**
- String codes (e.g., "clearsky_day", "partlycloudy_night", "lightrain")
- Includes day/night/polar twilight variants
- Multiple conditions map to same icons (e.g., polar_twilight uses day icons)
- Maps to ~29 unique Weather Icons types

### Icon Categories and Sizes

**Weather Icons**
- **Source**: Erik Flowers Weather Icons
- **SMHI Mapping**: 27 symbols → Weather Icons
- **YR Mapping**: 102 weather conditions → ~29 icon types
- **Day/Night**: Automatic selection based on sun times
- **Sizes**: 32×32 (forecast), 48×48 (standard), 96×96 (HERO)

**Pressure Arrows**
- **Source**: wi-direction-up/down/right.png
- **Sizes**: 20×20, 56×56, 64×64 (optimal), 96×96, 120×120
- **Usage**: 3-hour pressure trend (meteorological standard)

**Sun Icons**
- **Source**: wi-sunrise.svg, wi-sunset.svg
- **Sizes**: 24×24, 40×40 (standard), 56×56, 80×80
- **Usage**: Precise sun times in HERO module

**System Icons**
- **Barometer**: wi-barometer.svg
- **Clock**: wi-time-7.svg
- **Calendar**: wi-calendar.svg
- **Battery**: wi-battery.svg
- **UV**: wi-ultraviolet.svg

---

## Installation

### 1. System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y

# Install ImageMagick (for icon conversion)
sudo apt install imagemagick -y

# Install E-Paper dependencies
sudo apt install python3-pil python3-numpy -y
```

### 2. Enable SPI

```bash
# Enable SPI via raspi-config
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable

# Verify SPI is enabled
lsmod | grep spi
# Should show: spi_bcm2835
```

### 3. Clone and Setup

```bash
# Clone repository
cd ~
git clone <your-repo-url> epaper_weather
cd epaper_weather

# Install Python dependencies
pip3 install flask requests Pillow

# Create configuration file
nano config.json
```

**Minimal config.json example:**
```json
{
  "weather_provider": "smhi",
  "location": {
    "name": "Stockholm",
    "latitude": 59.3293,
    "longitude": 18.0686
  },
  "layout": {
    "screen_width": 800,
    "screen_height": 480
  },
  "display": {
    "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
  },
  "fonts": {
    "hero_temp": 72,
    "hero_desc": 24,
    "medium_main": 36,
    "medium_desc": 18,
    "small_main": 24,
    "small_desc": 14,
    "tiny": 10
  },
  "modules": {
    "main_weather": {
      "enabled": true,
      "coords": {"x": 0, "y": 0},
      "size": {"width": 440, "height": 280}
    },
    "barometer_module": {
      "enabled": true,
      "coords": {"x": 440, "y": 0},
      "size": {"width": 360, "height": 200}
    },
    "tomorrow_forecast": {
      "enabled": true,
      "coords": {"x": 440, "y": 200},
      "size": {"width": 360, "height": 180}
    },
    "clock_module": {
      "enabled": true,
      "coords": {"x": 0, "y": 280},
      "size": {"width": 220, "height": 100}
    },
    "status_module": {
      "enabled": true,
      "coords": {"x": 220, "y": 280},
      "size": {"width": 220, "height": 100}
    }
  },
  "debug": {
    "test_mode": false,
    "log_level": "INFO"
  }
}
```

**Important:** For Netatmo setup, see the detailed **[Netatmo Setup Guide](#netatmo-setup-guide)** section which explains how to get your API credentials.

**Note:** The `install_daemon.sh` script requires you to edit the service file paths to match your username and installation directory.

### 4. Install as Systemd Service

```bash
# Install daemon
sudo bash install_daemon.sh

# Check status
sudo systemctl status epaper-weather

# View logs
sudo journalctl -u epaper-weather -f
```

---

## Usage

### Mobile Web Viewer (iPhone/iPad)

View the weather display on your phone or tablet - perfect for when you're away from the physical E-Paper display.

**Start the web server on your Raspberry Pi:**
```bash
python3 web_server.py
```

**Add to iPhone/iPad home screen:**
1. Open Safari on your iPhone/iPad
2. Go to `http://<raspberry-pi-ip>:5000`
3. Tap the Share button → "Add to Home Screen"
4. Name it "Väder" (or any name you prefer)
5. Tap "Add"

**Usage:**
- Open the home screen shortcut - displays the latest weather image
- **Tap anywhere on the screen** to refresh and get the latest weather
- The display mimics the E-Paper aesthetic (no visible buttons or UI)

**Run as background service (optional):**
```bash
# Create systemd service for web server
sudo nano /etc/systemd/system/epaper-web.service
```

Add (adjust paths and username to match your setup):
```ini
[Unit]
Description=E-Paper Weather Web Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/YOUR_USER/epaper_weather/web_server.py
WorkingDirectory=/home/YOUR_USER/epaper_weather
User=YOUR_USER
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable epaper-web
sudo systemctl start epaper-web
```

### Daemon Commands

```bash
# Restart daemon (after config changes)
python3 restart.py

# View live logs
sudo journalctl -u epaper-weather -f

# View specific logs
sudo journalctl -u epaper-weather -f | grep -E "Provider|Precipitation|UV"

# Stop daemon
sudo systemctl stop epaper-weather

# Start daemon
sudo systemctl start epaper-weather
```

### Switching Providers

```bash
# 1. Edit config
nano ~/epaper_weather/config.json

# 2. Change provider
#    "weather_provider": "yr"  (for global coverage)
#    or
#    "weather_provider": "smhi"  (for Sweden with observations)

# 3. Update location if switching to YR globally
#    "location": {
#      "name": "Tokyo",
#      "latitude": 35.6762,
#      "longitude": 139.6503
#    }

# 4. Restart
python3 restart.py

# 5. Verify in logs
sudo journalctl -u epaper-weather -f | grep "Provider"
# Should show: "✅ Creating YR provider (Global coverage)"
# or: "✅ Creating SMHI provider (Sweden only)"
```

### Testing Triggers

```bash
# Test wind gust and precipitation triggers
python3 test_gust_triggers.py

# Restart daemon after testing
python3 restart.py
```

---

## Trigger System

### Trigger Syntax

**Operators:** `> < >= <= == != AND OR`

**Functions:** `precipitation`, `forecast_precipitation_2h`, `temperature`, `wind_speed`, `time_hour`, `time_month`, `pcat`

**Examples:**
```python
"precipitation > 0"  # Currently raining (Netatmo or Observations - SMHI only)
"forecast_precipitation_2h >= 0.2 AND pcat == 3"  # Rain expected (SMHI)
"forecast_precipitation_2h >= 0.2"  # Rain expected (YR - no pcat)
"wind_speed > 6.0"  # Wind speed threshold
"time_month >= 6 AND time_month <= 8"  # Summer months
```

### Precipitation Categories (pcat - SMHI only)

| pcat | Type | Trigger? |
|------|------|----------|
| 0 | No precipitation | ❌ |
| 1 | Snow | ❌ |
| 2 | Mixed rain/snow | ✅ (you get wet) |
| 3 | Rain | ✅ |
| 4 | Hail (no rain) | ❌ |
| 5 | Hail + rain | ✅ |
| 6 | Hail + snow | ❌ |

**Note:** YR provider doesn't use pcat codes - precipitation type is determined from symbol codes instead.

---

## Troubleshooting

### Display Not Updating

```bash
# Check daemon status
sudo systemctl status epaper-weather

# Check logs for errors
sudo journalctl -u epaper-weather -n 50

# Verify SPI
lsmod | grep spi

# Restart daemon
python3 restart.py
```

### Provider Issues

**Check which provider is active:**
```bash
sudo journalctl -u epaper-weather | grep "Provider"
# Should show: "✅ Creating SMHI provider" or "✅ Creating YR provider"
```

**SMHI Provider:**
```bash
# Check if SMHI data is fetching
sudo journalctl -u epaper-weather | grep "SMHI"

# Check observations
sudo journalctl -u epaper-weather | grep "Observations"

# Verify station ID in config.json
nano ~/epaper_weather/config.json
```

**YR Provider:**
```bash
# Check if YR data is fetching
sudo journalctl -u epaper-weather | grep "YR"

# Check for cache issues
sudo journalctl -u epaper-weather | grep "cache"

# Verify coordinates are valid
nano ~/epaper_weather/config.json
```

### API Issues

**Netatmo:**
```bash
# Check credentials in config.json
# Verify token refresh works
sudo journalctl -u epaper-weather | grep "Netatmo"
```

**UV API:**
```bash
# Check UV logs
sudo journalctl -u epaper-weather | grep "UV"

# Verify coordinates in config.json
# Check API limit (500/day)
```

### Battery Status Not Showing

```bash
# Verify Netatmo modules are connected
sudo journalctl -u epaper-weather | grep "Battery"

# Check if modules are reporting battery
sudo journalctl -u epaper-weather | grep "Netatmo"
```

---

## Architecture

### Multi-Provider System

```
┌─────────────────────────────────────────┐
│         Configuration (config.json)      │
│  - weather_provider: "smhi" or "yr"     │
│  - location: {lat, lon}                 │
│  - smhi_observations (SMHI only)        │
└──────────────┬──────────────────────────┘
               │
               v
┌─────────────────────────────────────────┐
│    Weather Provider Factory              │
│  Creates appropriate provider instance   │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        v             v
┌──────────────┐  ┌──────────────┐
│ SMHI Provider│  │  YR Provider │
│ - Forecasts  │  │ - Forecasts  │
│ - Observations│  │ (Global)    │
│ (Sweden)     │  │              │
└──────────────┘  └──────────────┘
        │             │
        └──────┬──────┘
               v
┌─────────────────────────────────────────┐
│         Weather Client                   │
│  Combines provider + Netatmo + UV data  │
└──────────────┬──────────────────────────┘
               │
               v
┌─────────────────────────────────────────┐
│        Dynamic Module Manager            │
│  Triggers → Module activation            │
└──────────────┬──────────────────────────┘
               │
               v
┌─────────────────────────────────────────┐
│        E-Paper Display                   │
│  Final rendered output                   │
└─────────────────────────────────────────┘
```

### Directory Structure

```
epaper_weather/
├── main_daemon.py              # Main daemon with dynamic system
├── main.py                     # Single-run version (for testing)
├── web_server.py               # Web server for mobile viewing
├── config.json                 # Configuration file (create this)
├── restart.py                  # Restart daemon helper
├── screenshot.py               # Manual screenshot utility
├── install_daemon.sh           # Systemd service installer
├── convert_svg_high_res.py     # Icon conversion utility
├── test_gust_triggers.py       # Test precipitation/wind triggers
├── modules/
│   ├── weather_client.py       # Integrates all data sources
│   ├── weather_provider_factory.py  # Creates provider instances
│   ├── providers/              # Weather provider implementations
│   │   ├── base_provider.py   # Abstract base class
│   │   ├── smhi_provider.py   # SMHI implementation (Sweden)
│   │   └── yr_provider.py     # YR implementation (Global)
│   ├── icon_manager.py         # Icon mapping for both providers
│   ├── sun_calculator.py       # Sun calculations
│   └── renderers/              # Module renderers
│       ├── base_renderer.py
│       ├── module_factory.py
│       ├── precipitation_renderer.py
│       └── wind_renderer.py
├── icons/
│   ├── weather/                # Weather Icons (SMHI + YR symbols)
│   ├── pressure/               # Pressure trend arrows
│   ├── sun/                    # Sunrise/sunset icons
│   ├── system/                 # System icons (barometer, calendar, etc.)
│   └── wind/                   # Wind direction icons
├── systemd/
│   └── epaper-weather.service  # Systemd service file
├── screenshots/                # Auto-generated weather screenshots
├── cache/                      # Runtime cache (auto-created)
└── logs/                       # Log files (auto-created)
```

---

## Credits and Licenses

### Weather Data APIs
- **SMHI Open Data** - CC0 1.0 Universal (Sweden)
- **YR/MET Norway API** - Free API, requires User-Agent header
- **Netatmo API** - OAuth2 integration
- **CurrentUVIndex.com** - Free UV API (CC BY 4.0)
- **ipgeolocation.io** - Sun times API

### Icon Sources
- **Weather Icons** by Erik Flowers - SIL OFL 1.1
- **UV Icon** by Freepik - [Flaticon](https://www.flaticon.com/free-icons/uv)
- **Battery Icon** by Stockio - [Flaticon](https://www.flaticon.com/free-icons/battery)
- **Conversion**: ImageMagick + cairosvg

### Libraries
- **Waveshare E-Paper Library** - MIT License
- **Pillow** - PIL License
- **Requests** - Apache 2.0

---

## Frequently Asked Questions

### Do I need a Netatmo Weather Station?

**No, but it's highly recommended!** 

**With Netatmo:**
- ✅ Most accurate local measurements (your exact location)
- ✅ Real-time precipitation detection (5-minute updates)
- ✅ Precise 3-hour pressure trends
- ✅ Battery monitoring
- ✅ Hyper-local temperature and humidity

**Without Netatmo:**
- ✅ Still works great with forecast data
- ✅ SMHI users get official weather station observations
- ✅ YR users get global forecast coverage
- ❌ Less accurate (forecast vs. actual measurement)
- ❌ No pressure trends
- ❌ No battery monitoring

### How do I configure without Netatmo?

Simply **omit the entire `api_keys.netatmo` section** from `config.json`. The system automatically detects this and uses forecast data instead. No errors, no warnings - it just works!

### Which weather provider should I choose?

**Choose SMHI if:**
- You're in Sweden
- You want real-time weather station observations (even without Netatmo)
- You need "is it raining NOW?" detection from official stations
- You want the most accurate local data for Sweden

**Choose YR if:**
- You're anywhere outside Sweden
- You're traveling and want to deploy in multiple locations
- Forecast-only data is sufficient
- You want comprehensive weather condition coverage (102 conditions vs SMHI's 27)

### Can I use both providers?

Not simultaneously in the same instance, but you can:
- Run multiple instances on different Raspberry Pis with different providers
- Switch providers by editing `config.json` and restarting

### Does Netatmo work with both providers?

**Yes!** Netatmo integration is completely provider-agnostic:
- Works perfectly with SMHI
- Works perfectly with YR
- Your Netatmo measurements are always prioritized over forecast data
- Provider only adds weather symbols and forecast information

### What happens to observations when using YR?

**With Netatmo + YR:**
- Your Netatmo Rain Gauge provides real-time precipitation observations
- YR provides weather symbols and forecasts
- System works perfectly - you have local observations from Netatmo!

**Without Netatmo + YR:**
- No real-time observations available
- System falls back to YR forecast data
- Still works well, just forecast-based instead of observation-based

### How do I find SMHI observation stations?

**For users in Sweden who don't have Netatmo:**

1. Visit: https://www.smhi.se/data/meteorologi/ladda-ner-meteorologiska-observationer
2. Select "Nederbörd" (precipitation)
3. Zoom to your city on the map
4. Click stations to see ID and name
5. Add station IDs to `config.json`

This gives you official weather station observations even without your own Netatmo!

### Can I use YR for Swedish locations?

Yes! YR works globally including Sweden. However:
- You won't get real-time observations (unless you have Netatmo)
- SMHI is more accurate for Swedish locations
- YR gives you more weather conditions (102 vs SMHI's 27)

**Best practice:**
- **Have Netatmo + in Sweden**: Choose SMHI for verification + observations
- **Have Netatmo + outside Sweden**: Choose YR for global forecasts
- **No Netatmo + in Sweden**: Choose SMHI for weather station observations
- **No Netatmo + outside Sweden**: Choose YR for global coverage

### What if my Netatmo goes offline?

The system gracefully falls back to forecast data:
- Temperature → from weather provider
- Pressure → from weather provider
- Precipitation → from SMHI observations (Sweden) or forecasts
- UV and Sun times continue working normally
- Display automatically shows data source (forecast vs. observation)

### Can I add Netatmo later?

**Absolutely!** Just:
1. Get Netatmo Weather Station
2. Set up your Netatmo account
3. Add credentials to `config.json`
4. Restart: `python3 restart.py`

The system automatically detects Netatmo and starts using your local measurements!

---

## License

MIT License - See LICENSE file for details

---

**Created:** 2024
**Last Updated:** January 2025
**Platform:** Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT
**Version:** Multi-Provider System v2.1 (+ Mobile Web Viewer)

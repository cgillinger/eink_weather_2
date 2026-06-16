# Barometric Pressure — Word Descriptions

Reference spec for displaying atmospheric pressure as plain-language descriptions
(analogous to the Beaufort scale for wind), as an optional display mode in weather apps.

## Why

Most users have no intuition for hPa/mbar values. A word band gives them a reference
frame. **Note:** absolute pressure predicts weather poorly on its own — the 3-hour
*tendency* (rising/falling) matters as much or more. Prefer showing both: level + trend.

## Units

`hPa` and `mbar` are numerically identical (1 hPa = 1 mbar), so the thresholds below
cover both. Convert from other units before lookup:
- `mmHg → hPa`: `hPa = mmHg * 1.33322`
- `inHg → hPa`: `hPa = inHg * 33.8639`

## Level bands

Boundaries derived from the physical barometer (see Source), rounded to whole hPa.
1013 hPa = standard sea-level pressure = natural low/high split.

| Description (sv) | Description (en) | hPa / mbar |
|---|---|---|
| Storm | Stormy | < 980 |
| Regn | Rain | 980–1000 |
| Ostadigt | Changeable | 1000–1013 |
| Vackert | Fair | 1013–1040 |
| Mycket Torrt | Very Dry | > 1040 |

## Trend (3-hour tendency)

`delta3h` = current pressure − pressure 3 hours ago, in hPa. Standard meteorological
tendency thresholds:

| Trend (sv) | Trend (en) | Δ per 3 h |
|---|---|---|
| faller snabbt | falling rapidly | < −2 |
| faller | falling | −2 … −0.5 |
| stabilt | steady | −0.5 … +0.5 |
| stiger | rising | +0.5 … +2 |
| stiger snabbt | rising rapidly | > +2 |

## Reference implementation

```js
const PRESSURE_BANDS = [
  { max: 980,      sv: "Storm",        en: "Stormy" },
  { max: 1000,     sv: "Regn",         en: "Rain" },
  { max: 1013,     sv: "Ostadigt",     en: "Changeable" },
  { max: 1040,     sv: "Vackert",      en: "Fair" },
  { max: Infinity, sv: "Mycket Torrt", en: "Very Dry" },
];

const TREND = [
  { max: -2,       sv: "faller snabbt", en: "falling rapidly" },
  { max: -0.5,     sv: "faller",        en: "falling" },
  { max: 0.5,      sv: "stabilt",       en: "steady" },
  { max: 2,        sv: "stiger",        en: "rising" },
  { max: Infinity, sv: "stiger snabbt", en: "rising rapidly" },
];

// hPa === mbar. delta3h optional; lang: "sv" | "en"
function describePressure(hPa, delta3h = 0, lang = "sv") {
  const band  = PRESSURE_BANDS.find(b => hPa < b.max);
  const trend = TREND.find(t => delta3h < t.max);
  return { level: band[lang], trend: trend[lang] };
}
```

## Notes for implementers

- Bands are open-ended at both extremes (`< 980`, `> 1040`).
- Words are deliberately coarse; do not present them as forecasts. Pair with the
  trend, or with the numeric value, to avoid misleading readers (e.g. "Vackert" while
  pressure is falling rapidly).
- Adjust readings to sea level if the data source reports station pressure.

## Source

Scale digitized from a physical aneroid **precision barometer** with a Swedish-language
dial (Storm · Regn · Ostadigt · Vackert · Mycket Torrt).

- **Manufacturer:** Huger (Hugo Gerlach), West Germany
- **Marking:** "HUGER · PRÄCISIONS-BAROMETER · West Germany"
- Approx. 1970s; dial range 960–1070 mbar / 720–800 mmHg.

The English equivalents (Stormy · Rain · Change/Changeable · Fair · Very Dry) follow the
conventional English barometer wording. Word-to-pressure boundaries are not an official
standard and vary between makers; these reflect this specific instrument, rounded.

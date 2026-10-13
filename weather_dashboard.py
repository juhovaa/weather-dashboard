"""Console weather dashboard using the Open-Meteo APIs."""

import json
import sys
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10
USER_AGENT = "weather-dashboard/1.0 (educational; stdlib)"


def weather_emoji(code):
    """Return an emoji for a WMO weather interpretation code."""
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "?"

    if code == 0:
        return "☀️"
    if code in (1, 2):
        return "⛅"
    if code == 3:
        return "☁️"
    if code in (45, 48):
        return "🌫️"
    if 51 <= code <= 57:
        return "🌦️"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "🌧️"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "❄️"
    if 95 <= code <= 99:
        return "⛈️"
    return "🌡️"


def fetch_json(url):
    """GET a URL and return the decoded JSON object."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def geocode_city(name):
    """Resolve a city name to coordinates, or None if not found."""
    query = urlencode({"name": name, "count": 1, "language": "en"})
    data = fetch_json(f"{GEOCODING_URL}?{query}")
    results = data.get("results") or []
    if not results:
        return None
    place = results[0]
    return {
        "name": place.get("name", name),
        "country": place.get("country") or "Unknown",
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


def fetch_forecast(latitude, longitude):
    """Fetch current conditions and a 5-day daily forecast."""
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "auto",
            "forecast_days": 5,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "wind_speed_10m,weather_code"
            ),
            "daily": (
                "weather_code,temperature_2m_max,"
                "temperature_2m_min,rain_sum"
            ),
        }
    )
    return fetch_json(f"{FORECAST_URL}?{query}")


def weekday_label(iso_date):
    """Turn a YYYY-MM-DD string into a three-letter weekday."""
    return date.fromisoformat(iso_date).strftime("%a")


def print_dashboard(location, forecast):
    """Print the city header, current conditions, and 5-day table."""
    city = location["name"]
    country = location["country"]
    current = forecast["current"]
    daily = forecast["daily"]

    header = f"Weather: {city}, {country}"
    rule = "=" * max(len(header) + 4, 52)

    print()
    print(rule)
    print(f"  {header}")
    print(rule)
    print()
    print("Current conditions")
    print(
        "  {emoji}  Temperature : {temp:.1f} °C".format(
            emoji=weather_emoji(current.get("weather_code")),
            temp=float(current["temperature_2m"]),
        )
    )
    print(
        "      Humidity    : {humidity:.0f} %".format(
            humidity=float(current["relative_humidity_2m"]),
        )
    )
    print(
        "      Wind speed  : {wind:.1f} km/h".format(
            wind=float(current["wind_speed_10m"]),
        )
    )
    print()
    print("5-day forecast")
    print(
        "{day:<10} | {high:<8} | {low:<8} | {rain:<9} | {cond}".format(
            day="Day",
            high="High",
            low="Low",
            rain="Rain (mm)",
            cond="Condition",
        )
    )
    print(
        "{0:<10} | {1:<8} | {2:<8} | {3:<9} | {4}".format(
            "-" * 10,
            "-" * 8,
            "-" * 8,
            "-" * 9,
            "-" * 9,
        )
    )

    days = daily["time"]
    highs = daily["temperature_2m_max"]
    lows = daily["temperature_2m_min"]
    rain = daily["rain_sum"]
    codes = daily["weather_code"]
    rows = zip(days, highs, lows, rain, codes)

    for iso_day, high, low, rain_mm, code in rows:
        print(
            "{day:<10} | {high:>6.1f}°C | {low:>6.1f}°C |"
            " {rain:>9.1f} | {emoji}".format(
                day=weekday_label(iso_day),
                high=float(high),
                low=float(low),
                rain=float(rain_mm or 0),
                emoji=weather_emoji(code),
            )
        )
    print()


def prompt_city():
    """Ask for a city name until the user enters a non-empty value."""
    while True:
        try:
            city = input("Enter a city name: ").strip()
        except EOFError:
            print()
            return None
        if city:
            return city
        print("Please enter a city name.")


def main():
    """Prompt for a city, fetch weather, and print the dashboard."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    city = prompt_city()
    if city is None:
        return 1

    try:
        location = geocode_city(city)
        if location is None:
            print(
                "Could not find a city named '{0}'. "
                "Try a different spelling.".format(city)
            )
            return 1
        forecast = fetch_forecast(
            location["latitude"],
            location["longitude"],
        )
        print_dashboard(location, forecast)
    except HTTPError as exc:
        print(
            "The weather service returned an error (HTTP {0}).".format(
                exc.code
            )
        )
        return 1
    except URLError:
        print(
            "Could not reach the weather service. "
            "Check your internet connection."
        )
        return 1
    except json.JSONDecodeError:
        print("Received an unexpected response from the weather service.")
        return 1
    except (KeyError, TypeError, ValueError, IndexError):
        print("Weather data was incomplete or could not be displayed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

import requests
from dataclasses import dataclass, field
from datetime import datetime

WEATHER_DESCRIPTION = {
    0: "Clear",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light Drizzle",
    53: "Drizzle",
    55: "Dense Drizzle",
    56: "Freezing Drizzle",
    57: "Freezing Drizzle",
    61: "Freezing Rain",
    63: "Freezing Rain",
    65: "Freezing Rain",
    66: "Rain",
    67: "Heavy Rain",
    71: "Slight Snow",
    73: "Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Slight Rain",
    81: "Rain ",
    82: "Heavy Rain",
    85: "Snow",
    86: "Heavy Snow",
    95: "Storm",
    96: "Storm Hail",
    99: "Storm Hail"
}


@dataclass
class CurrentUnits:
    temperature: str = ""
    precipitation: str = ""
    wind_speed: str = ""


@dataclass
class Current:
    time: str = ""
    temperature: float = 0.0
    humidity: int = 0
    is_day: bool = False
    precipitation: float = 0.0
    weather_code: int = 0
    weather_description: str = ""
    cloud_cover: int = 0
    wind_speed: float = 0.0
    wind_direction: int = 0


@dataclass
class Daily:
    date: datetime = None
    weather_code: int = 0
    weather_description: str = ""
    sunrise: datetime = None
    sunset: datetime = None
    uv_index: float = 0.0
    precipitation_probability: int = 0
    temperature_max: float = 0.0
    temperature_min: float = 0.0


@dataclass
class WeatherData:
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = ""
    current_units: CurrentUnits = None
    current: Current = None
    daily: list = field(default_factory=list)


@dataclass
class Geocode:
    lat: float = 0.0
    lng: float = 0.0
    city: str = ""
    country_code: str = ""
    country: str = ""
    display_name: str = ""


@dataclass
class IPInfo:
    ip: str = ""
    hostname: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    lat: float = ""
    lng: float = ""
    org: str = ""
    postal: str = ""
    timezone: str = ""


class ApiClient:
    def get_weather(self, lat, lng, timezone = "", temp_unit = "celsius"):
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,is_day,precipitation,weather_code,relative_humidity_2m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_probability_max",
            "timezone": timezone,
            "temperature_unit": temp_unit,
            "forecast_days": 5
        }

        try:
            response = requests.get(url, params = params)
            response.raise_for_status()
            data = response.json()
            
            cur = data.get("current", {})
            current = Current(
                time = cur.get("time", ""),
                temperature = cur.get("temperature_2m", 0.0),
                humidity = cur.get("relative_humidity_2m", 0.0),
                is_day = cur.get("is_day") == 1,
                precipitation = cur.get("precipitation", 0.0),
                weather_code = cur.get("weather_code", 0),
                weather_description = WEATHER_DESCRIPTION[cur.get("weather_code", 0)],
                cloud_cover = cur.get("cloud_cover"),
                wind_speed = cur.get("wind_speed_10m", 0.0),
                wind_direction = cur.get("wind_direction_10m", 0)
            )

            units = data.get("current_units", {})
            cur_units = CurrentUnits(
                temperature = units.get("temperature_2m", ""),
                precipitation = units.get("precipitation", ""),
                wind_speed = units.get("wind_speed_10m", ""),
            )

            d = data.get("daily", {})
            daily = [
                Daily(
                    date = datetime.strptime(d.get("time")[i], "%Y-%m-%d"),
                    weather_code = d.get("weather_code")[i],
                    weather_description = WEATHER_DESCRIPTION[d.get("weather_code")[i]],
                    temperature_max = d.get("temperature_2m_max")[i],
                    temperature_min = d.get("temperature_2m_min")[i],
                    sunrise = datetime.strptime(d.get("sunrise")[i], "%Y-%m-%dT%H:%M"),
                    sunset = datetime.strptime(d.get("sunset")[i], "%Y-%m-%dT%H:%M"),
                    uv_index = d.get("uv_index_max")[i],
                    precipitation_probability = d.get("precipitation_probability_max")[i]
                )
                for i in range(len(d.get("time", [])))
            ]

            weatherData = WeatherData(
                latitude = data.get("latitude", 0.0),
                longitude = data.get("longitude", 0.0),
                timezone = data.get("timezone", ""),
                current_units = cur_units,
                current = current,
                daily = daily
            )
            return weatherData
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None


    def get_geocode(self, address):
        url = "https://nominatim.openstreetmap.org/search"
        headers = {
            "User-Agent": "RaspberryPiZero/1.0 (clin4185@usc.edu)"
        }
        params = {
            "q": address,
            "format": "json",
            "addressdetails": 1
        }
        try:
            response = requests.get(url, params = params, headers = headers)
            response.raise_for_status()
            data = response.json()[0]
            address = data.get("address", {})
            return Geocode(
                lat = data.get("lat", 0.0),
                lng = data.get("lon", 0.0),
                display_name = data.get("display_name", ""),
                city = address.get("city", ""),
                country_code = address.get("country_code", ""),
                country = address.get("country", "")
            )
        except requests.RequestException as e:
            print(f"Error fetching Geocode: {e}")
            return None


    def get_ip_info(self):
        url = "https://ipinfo.io/json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            lat, lng = map(float, data.get("loc", "0.0,0.0").split(","))
            ip_info = IPInfo(
                ip = data.get("ip", ""),
                hostname = data.get("hostname", ""),
                city = data.get("city", ""),
                region = data.get("region", ""),
                country = data.get("country", ""),
                lat = lat,
                lng = lng,
                org = data.get("org", ""),
                postal = data.get("postal", ""),
                timezone = data.get("timezone", ""),
            )
            print(f'Detected city: {ip_info.city}, lat: {ip_info.lat}, lng: {ip_info.lng}')
            return ip_info
        except requests.RequestException as e:
            print(f"Error fetching IP information: {e}")
            return None


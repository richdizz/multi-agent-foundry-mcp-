#!/usr/bin/env python3
"""
Weather MCP Server - Model Context Protocol server for OpenWeatherMap data
Provides weather information through standardized MCP tools
"""

import os
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Create FastMCP server instance
mcp = FastMCP("weather-mcp-server")

# Store API configuration
api_key = os.getenv("WEATHER_API_KEY")
base_url = "https://api.openweathermap.org/data/2.5"


@mcp.tool()
async def get_current_weather(location: str, units: str = "imperial") -> Dict[str, Any]:
    """Get current weather conditions for a location"""
    try:
        if not api_key:
            return None

        params = {
            "q": location,
            "appid": api_key,
            "units": units
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{base_url}/weather", params=params)
                response.raise_for_status()
                data = response.json()

                # Check for API error
                if data.get("cod") != 200:
                    return None

                return _format_weather_data(data, units)

            except httpx.RequestError:
                return None
    except Exception as e:
        return {"error": f"Failed to get current weather: {str(e)}"}


@mcp.tool()
async def get_weather_forecast(location: str, units: str = "imperial", cnt: int = 8) -> Dict[str, Any]:
    """Get 5-day weather forecast with 3-hour intervals"""
    try:
        if not api_key:
            return None

        params = {
            "q": location,
            "appid": api_key,
            "units": units,
            "cnt": cnt
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{base_url}/forecast", params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("cod") != "200":
                    return None

                return _format_forecast_data(data, units)

            except httpx.RequestError:
                return None
    except Exception as e:
        return {"error": f"Failed to get weather forecast: {str(e)}"}


def _format_weather_data(data: Dict[str, Any], units: str) -> Dict[str, Any]:
    """Format weather data response"""
    temp_unit = {"metric": "°C", "imperial": "°F", "kelvin": "K"}[units]
    speed_unit = {"metric": "m/s",
                  "imperial": "mph", "kelvin": "m/s"}[units]

    return {
        "location": {
            "name": data.get("name", "Unknown"),
            "country": data.get("sys", {}).get("country", ""),
            "coordinates": {
                "lat": data.get("coord", {}).get("lat"),
                "lon": data.get("coord", {}).get("lon")
            }
        },
        "current": {
            "temperature": data.get("main", {}).get("temp"),
            "temperature_unit": temp_unit,
            "feels_like": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity"),
            "pressure": data.get("main", {}).get("pressure"),
            "visibility": data.get("visibility"),
            "uv_index": None  # Not available in basic weather endpoint
        },
        "wind": {
            "speed": data.get("wind", {}).get("speed"),
            "speed_unit": speed_unit,
            "direction": data.get("wind", {}).get("deg"),
            "gust": data.get("wind", {}).get("gust")
        },
        "weather": {
            "main": data.get("weather", [{}])[0].get("main"),
            "description": data.get("weather", [{}])[0].get("description"),
            "icon": data.get("weather", [{}])[0].get("icon")
        },
        "clouds": {
            "coverage": data.get("clouds", {}).get("all")
        },
        "rain": data.get("rain", {}),
        "snow": data.get("snow", {}),
        "timestamp": data.get("dt"),
        "timezone": data.get("timezone"),
        "sunrise": data.get("sys", {}).get("sunrise"),
        "sunset": data.get("sys", {}).get("sunset")
    }


def _format_forecast_data(data: Dict[str, Any], units: str) -> Dict[str, Any]:
    """Format forecast data response"""
    temp_unit = {"metric": "°C", "imperial": "°F", "kelvin": "K"}[units]

    return {
        "location": {
            "name": data.get("city", {}).get("name", "Unknown"),
            "country": data.get("city", {}).get("country", ""),
            "coordinates": {
                "lat": data.get("city", {}).get("coord", {}).get("lat"),
                "lon": data.get("city", {}).get("coord", {}).get("lon")
            }
        },
        "forecast": [
            {
                "datetime": item.get("dt_txt"),
                "timestamp": item.get("dt"),
                "temperature": {
                    "temp": item.get("main", {}).get("temp"),
                    "feels_like": item.get("main", {}).get("feels_like"),
                    "temp_min": item.get("main", {}).get("temp_min"),
                    "temp_max": item.get("main", {}).get("temp_max"),
                    "unit": temp_unit
                },
                "weather": {
                    "main": item.get("weather", [{}])[0].get("main"),
                    "description": item.get("weather", [{}])[0].get("description"),
                    "icon": item.get("weather", [{}])[0].get("icon")
                },
                "humidity": item.get("main", {}).get("humidity"),
                "pressure": item.get("main", {}).get("pressure"),
                "wind": {
                    "speed": item.get("wind", {}).get("speed"),
                    "direction": item.get("wind", {}).get("deg")
                },
                "clouds": item.get("clouds", {}).get("all"),
                "rain": item.get("rain", {}),
                "snow": item.get("snow", {})
            }
            for item in data.get("list", [])
        ]
    }

def main():
    """Main entry point for the Weather MCP Server"""
    print("Starting Weather MCP Server...", flush=True)
    mcp.run()


if __name__ == "__main__":
    main()
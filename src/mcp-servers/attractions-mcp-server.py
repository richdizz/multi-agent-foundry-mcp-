#!/usr/bin/env python3
"""
Attractions MCP Server - Model Context Protocol server for TripAdvisor attractions data
Provides attraction information through standardized MCP tools
"""

import os
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Create FastMCP server instance
mcp = FastMCP("attractions-mcp-server")

# Store API configuration
api_key = os.getenv("TRIPADVISOR_KEY")  # Fixed: was looking for TRIPADVISOR_API_KEY
base_url = "https://api.content.tripadvisor.com/api/v1"


@mcp.tool()
async def get_current_attractions(location: str) -> Dict[str, Any]:
    """Get current attractions for a location"""
    try:
        if not api_key:
            return {
                "error": "TripAdvisor API key not found. Please set TRIPADVISOR_KEY in your .env file.",
                "attractions": [],
                "location": location
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # TripAdvisor API v1 location search endpoint
                url = f"{base_url}/location/search"
                params = {
                    "key": api_key,
                    "searchQuery": location,
                    "category": "attractions",
                    "language": "en"
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract and format attraction data
                if "data" in data and data["data"]:
                    attractions = []
                    for item in data["data"][:10]:  # Limit to top 10
                        attraction = {
                            "name": item.get("name", "Unknown"),
                            "location_id": item.get("location_id"),
                            "address": item.get("address_obj", {}).get("address_string", "Address not available"),
                            "rating": item.get("rating"),
                            "num_reviews": item.get("num_reviews", 0),
                            "category": item.get("category", {}).get("name", "Attraction")
                        }
                        attractions.append(attraction)
                    
                    return {
                        "success": True,
                        "location": location,
                        "attractions": attractions,
                        "total_found": len(data["data"])
                    }
                else:
                    return {
                        "success": False,
                        "location": location,
                        "attractions": [],
                        "message": "No attractions found for this location",
                        "raw_response": data
                    }

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code} error: {e.response.text}"
                print(f"TripAdvisor API HTTP error: {error_msg}")
                return {
                    "error": error_msg,
                    "attractions": [],
                    "location": location,
                    "status_code": e.response.status_code
                }
            except httpx.RequestError as e:
                error_msg = f"Request error: {str(e)}"
                print(f"TripAdvisor API request error: {error_msg}")
                return {
                    "error": error_msg,
                    "attractions": [],
                    "location": location
                }
    except Exception as e:
        error_msg = f"Failed to get current attractions: {str(e)}"
        print(f"Unexpected error: {error_msg}")
        return {
            "error": error_msg,
            "attractions": [],
            "location": location
        }


def main():
    """Main entry point for the Attractions MCP Server"""
    print("Starting Attractions MCP Server...", flush=True)
    mcp.run()


if __name__ == "__main__":
    main()
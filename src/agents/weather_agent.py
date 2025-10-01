"""
Weather Agent - Specializes in providing weather information and forecasts
"""

import asyncio
import importlib.util
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionToolDefinition


class WeatherAgent:
    """Agent specialized in weather-related inquiries"""

    def __init__(self, client: AIProjectClient, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model
        self.agent = None
        self._setup_mcp_functions()
        self._create_agent()
    
    def _setup_mcp_functions(self):
        """Setup MCP server functions"""
        try:
            mcp_path = Path(__file__).parent.parent / 'mcp-servers' / 'weather-mcp-server.py'
            spec = importlib.util.spec_from_file_location("weather_mcp_server", mcp_path)
            self.weather_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.weather_module)
            print("✓ Weather MCP server loaded")
        except Exception as e:
            print(f"✗ Weather MCP server error: {e}")
            self.weather_module = None
    
    def _create_agent(self):
        """Create the weather agent"""
        # Define tools that connect to MCP server
        tools = [
            FunctionToolDefinition(
                function={
                    "name": "get_current_weather",
                    "description": "Get current weather conditions for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location name"},
                            "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
                        },
                        "required": ["location"]
                    }
                }
            ),
            FunctionToolDefinition(
                function={
                    "name": "get_weather_forecast",
                    "description": "Get weather forecast for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location name"},
                            "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"},
                            "cnt": {"type": "integer", "description": "Number of intervals", "default": 8}
                        },
                        "required": ["location"]
                    }
                }
            )
        ]
        
        self.agent = self.client.agents.create_agent(
            model=self.model,
            name="weather-agent",
            instructions=(
                "You specialize in providing weather information and forecasts. "
                "Your role is to:\n"
                "1. Use get_current_weather tool to gather current weather data for the specified location\n"
                "2. Use get_weather_forecast tool to get weather forecasts for the specified location\n"
                "3. Analyze weather patterns and trends\n"
                "4. Provide recommendations for weather-related inquiries\n"
                "5. Compare and contrast different weather scenarios\n"
                "6. Draw meaningful conclusions from weather data\n\n"
                "IMPORTANT: The location will be provided to you. Use this exact location when calling weather tools. "
                "Do not try to extract or parse location from the user message - use the location parameter directly."
            ),
            tools=tools
        )
        print(f"Created weather agent: {self.agent.id}")
    
    def get_weather_data(self, location: str, forecast: bool = False):
        """Get weather data using MCP server"""
        if not self.weather_module:
            return {"error": "Weather service not available"}
        
        try:
            import asyncio
            if forecast:
                return asyncio.run(self.weather_module.get_weather_forecast(location))
            else:
                return asyncio.run(self.weather_module.get_current_weather(location))
        except Exception as e:
            return {"error": f"Failed to get weather data: {str(e)}"}

    @property
    def id(self):
        """Get the agent ID"""
        return self.agent.id if self.agent else None
    
    def process_task(self, task: str) -> str:
        """Process a weather task and return the response"""
        if not self.agent:
            raise ValueError("Weather agent not initialized")

        try:
            # Create thread for this task
            thread = self.client.agents.threads.create()
            
            # Add message to thread with explicit location
            message = self.client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=task
            )
            
            # Run the agent with timeout
            run = self.client.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self.agent.id
            )
            
            # Get response
            messages = self.client.agents.messages.list(thread_id=thread.id)
            for msg in messages:
                if msg.role == "assistant":
                    return msg.content[0].text.value
            
            return "No response received from weather agent"
            
        except Exception as e:
            return f"Weather agent error: {str(e)}"
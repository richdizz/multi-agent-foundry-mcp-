import os
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from agents import WeatherAgent, AttractionsAgent, OrchestratorAgent
import logging

# Reduce Azure SDK logging
logging.getLogger('azure').setLevel(logging.WARNING)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

# Load environment variables from .env file in the project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup
endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
if not endpoint:
    raise ValueError("Please set AZURE_AI_PROJECT_ENDPOINT env var to your Foundry project endpoint")

credential = DefaultAzureCredential()
client = AIProjectClient(credential=credential, endpoint=endpoint)

# Create agent instances
weather_agent = WeatherAgent(client)
attractions_agent = AttractionsAgent(client)
orchestrator = OrchestratorAgent(client)

# Connect the subagents to the orchestrator
orchestrator.set_subagents(weather_agent, attractions_agent)

# Enable global function calls for MCP servers
def get_current_weather(location: str, units: str = "imperial"):
    return weather_agent.get_weather_data(location, forecast=False)

def get_weather_forecast(location: str, units: str = "imperial", cnt: int = 8):
    return weather_agent.get_weather_data(location, forecast=True)

def get_current_attractions(location: str):
    return attractions_agent.get_attractions_data(location)

# Register functions globally
try:
    client.agents.enable_auto_function_calls(
        {get_current_weather, get_weather_forecast, get_current_attractions}
    )
    print("Global MCP functions enabled")
except Exception as e:
    print(f"Could not enable global function calls: {e}")

print("Multi-agent system ready!")

# Get user input and process through orchestrator
user_message = input("\nEnter your question or task: ")
result = orchestrator.process_request(user_message)

if result:
    print(f"\n=== FINAL RESULT ===")
    print(f"Agents used: {', '.join(result['agents_used'])}")
    print(f"\nFinal Answer:")
    print(result["final_answer"])
    
    print(f"\n=== INDIVIDUAL AGENT RESPONSES ===")
    for agent_type, response in result["subagent_responses"].items():
        print(f"\n{agent_type.upper()} AGENT:")
        print(response[:500] + "..." if len(response) > 500 else response)
else:
    print("Error: Could not complete multi-agent workflow")

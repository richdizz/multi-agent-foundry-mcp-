"""
Attractions Agent - Specializes in attractions information based on location
"""

import asyncio
import importlib.util
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionToolDefinition


class AttractionsAgent:
    """Agent specialized in attractions"""
    
    def __init__(self, client: AIProjectClient, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model
        self.agent = None
        self._setup_mcp_functions()
        self._create_agent()
    
    def _setup_mcp_functions(self):
        """Setup MCP server functions"""
        try:
            mcp_path = Path(__file__).parent.parent / 'mcp-servers' / 'attractions-mcp-server.py'
            spec = importlib.util.spec_from_file_location("attractions_mcp_server", mcp_path)
            self.attractions_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.attractions_module)
            print("✓ Attractions MCP server loaded")
        except Exception as e:
            print(f"✗ Attractions MCP server error: {e}")
            self.attractions_module = None
    
    def _create_agent(self):
        """Create the attractions agent"""
        # Define tools that connect to MCP server
        tools = [
            FunctionToolDefinition(
                function={
                    "name": "get_current_attractions",
                    "description": "Get current attractions for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "Location name"}
                        },
                        "required": ["location"]
                    }
                }
            )
        ]
        
        self.agent = self.client.agents.create_agent(
            model=self.model,
            name="attractions-agent",
            instructions=(
                "You specialize in researching attractions information based on location. "
                "Your role is to:\n"
                "1. Use get_current_attractions tool to gather attraction information for the specified location\n"
                "2. Identify credible sources and key data points\n"
                "3. Summarize findings in a clear, organized manner\n"
                "4. Highlight important facts, statistics, and recent developments\n"
                "5. Provide context and background information when relevant\n\n"
                "IMPORTANT: The location will be provided to you. Use this exact location when calling attraction tools. "
                "Do not try to extract or parse location from the user message - use the location parameter directly."
            ),
            tools=tools
        )
        print(f"Created attractions agent: {self.agent.id}")
    
    def get_attractions_data(self, location: str):
        """Get attractions data using MCP server"""
        if not self.attractions_module:
            return {"error": "Attractions service not available"}
        
        try:
            import asyncio
            return asyncio.run(self.attractions_module.get_current_attractions(location))
        except Exception as e:
            return {"error": f"Failed to get attractions data: {str(e)}"}

    @property
    def id(self):
        """Get the agent ID"""
        return self.agent.id if self.agent else None
    
    def process_task(self, task: str) -> str:
        """Process an attractions task and return the response"""
        if not self.agent:
            raise ValueError("Attractions agent not initialized")
        
        try:
            # Create thread for this task
            thread = self.client.agents.threads.create()
            
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
            
            return "No response received from attractions agent"
            
        except Exception as e:
            return f"Attractions agent error: {str(e)}"
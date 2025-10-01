"""
Orchestrator Agent - Coordinates and manages other agents
"""

import json
from typing import Dict, List, Any, Optional
from azure.ai.projects import AIProjectClient


class OrchestratorAgent:
    """Agent that orchestrates and coordinates other agents"""

    def __init__(self, client: AIProjectClient, weather_agent=None, attractions_agent=None, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model
        self.weather_agent = weather_agent
        self.attractions_agent = attractions_agent
        self.agent = None
        self.final_agent = None
        self._create_agents()

    def set_subagents(self, weather_agent, attractions_agent):
        """Set the subagents that this orchestrator can coordinate"""
        self.weather_agent = weather_agent
        self.attractions_agent = attractions_agent

    def _create_agents(self):
        """Create the orchestrator agents"""
        # Main orchestrator for task analysis
        self.agent = self.client.agents.create_agent(
            model=self.model,
            name="orchestrator-agent",
            instructions=(
                "You are the orchestrator agent. Your job is to:\n"
                "1. Analyze the user's task\n"
                "2. Determine which specialist agents are needed (weather-agent, attractions-agent, or both)\n"
                "3. Provide clear instructions for each selected agent\n"
                "4. Extract the geographic location from the user's request such as **Austin** for the prompt 'what are good things to do in Austin'\n"
                "5. Later, you'll combine their responses into a final answer\n\n"
                "Respond ONLY with a JSON object in this format:\n"
                "{\n"
                '  "agents_needed": ["weather-agent", "attractions-agent"],\n'
                '  "weather_task": "specific task for weather agent",\n'
                '  "attractions_task": "specific task for attractions agent",\n'
                '  "reasoning": "why these agents were selected",\n'
                '  "location": "the geographic location from the user\'s request such as **Austin** for the prompt \'what are good things to do in Austin\'"\n'
                "}\n\n"
                "If only one agent is needed, omit the unnecessary task field."
            )
        )
        
        # Final orchestrator for response synthesis
        self.final_agent = self.client.agents.create_agent(
            model=self.model,
            name="final-orchestrator",
            instructions=(
                "You are the final orchestrator. Combine the responses from specialist agents "
                "into a comprehensive, well-structured final answer. Present the information "
                "clearly and acknowledge the contributions from different agents."
                "Have the context to suggest attractions based on weather if both are present."
            )
        )
        
        print(f"Created orchestrator agent: {self.agent.id}")
        print(f"Created final orchestrator agent: {self.final_agent.id}")
    
    @property
    def id(self):
        """Get the main orchestrator agent ID"""
        return self.agent.id if self.agent else None
    
    @property
    def final_id(self):
        """Get the final orchestrator agent ID"""
        return self.final_agent.id if self.final_agent else None
    
    def process_request(self, user_message: str) -> Dict[str, Any]:
        """
        Complete multi-agent workflow: analyze task, run subagents, synthesize response
        """
        print(f"\n=== MULTI-AGENT WORKFLOW ===")
        
        # Step 1: Analyze task and decide which agents to use
        print(f"\n1. Orchestrator analyzing task...")
        agent_plan = self._analyze_task(user_message)
        
        print(f"   Orchestrator decision: {agent_plan.get('reasoning', 'No reasoning provided')}")
        print(f"   Agents selected: {agent_plan.get('agents_needed', [])}")
        print(f"   Location specified: {agent_plan.get('location', 'No location specified')}")
        
        # Step 2: Run selected subagents
        subagent_responses = self._run_subagents(agent_plan)
        
        # Step 3: Synthesize responses
        print(f"\n3. Orchestrator combining responses...")
        final_answer = self._synthesize_responses(user_message, subagent_responses)
        
        return {
            "final_answer": final_answer,
            "agents_used": agent_plan.get("agents_needed", []),
            "subagent_responses": subagent_responses
        }
    
    def _analyze_task(self, user_message: str) -> Dict[str, Any]:
        """Analyze a task and determine which agents are needed"""
        if not self.agent:
            raise ValueError("Orchestrator agent not initialized")
        
        # Create thread for task analysis
        thread = self.client.agents.threads.create()
        
        # Add message to thread
        message = self.client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Analyze this task and determine which agents are needed and for what location: {user_message}"
        )
        
        # Run the orchestrator
        run = self.client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self.agent.id
        )
        
        # Get orchestrator's decision
        messages = self.client.agents.messages.list(thread_id=thread.id)
        for msg in messages:
            if msg.role == "assistant":
                try:
                    agent_plan = json.loads(msg.content[0].text.value)
                    return agent_plan
                except (json.JSONDecodeError, KeyError):
                    print(f"   Orchestrator response: {msg.content[0].text.value}")
                    # Fallback: use both agents
                    return {
                        "agents_needed": ["weather-agent", "attractions-agent"],
                        "weather_task": user_message,
                        "attractions_task": user_message,
                        "location": "location not specified",
                        "reasoning": "Fallback to using both agents"
                    }
        
        # Ultimate fallback
        return {
            "agents_needed": ["weather-agent", "attractions-agent"],
            "weather_task": user_message,
            "attractions_task": user_message,
            "location": "location not specified",
            "reasoning": "Default fallback"
        }
    
    def _run_subagents(self, agent_plan: Dict[str, Any]) -> Dict[str, str]:
        """Run the selected subagents and collect their responses"""
        subagent_responses = {}
        
        # Extract location from the plan
        location = agent_plan.get("location", "")
        
        # Run weather agent if needed
        if ("weather-agent" in agent_plan.get("agents_needed", []) and 
            "weather_task" in agent_plan and 
            self.weather_agent):
            print(f"\n2a. Running weather agent...")
            # Prepare weather-specific task context
            weather_task = f"Location: {location}\n\nTask: {agent_plan['weather_task']}\n\nPlease use the weather tools with the location '{location}' to provide accurate weather information."
            subagent_responses["weather"] = self.weather_agent.process_task(weather_task)
            print(f"   Weather agent completed task")

        # Run attractions agent if needed
        if ("attractions-agent" in agent_plan.get("agents_needed", []) and 
            "attractions_task" in agent_plan and 
            self.attractions_agent):
            print(f"\n2b. Running attractions agent...")
            # Prepare attractions-specific task context
            attractions_task = f"Location: {location}\n\nTask: {agent_plan['attractions_task']}\n\nPlease use the attractions tools with the location '{location}' to provide accurate attraction information."
            subagent_responses["attractions"] = self.attractions_agent.process_task(attractions_task)
            print(f"   Attractions agent completed task")
        
        return subagent_responses
    
    def _synthesize_responses(self, user_message: str, subagent_responses: Dict[str, str]) -> str:
        """Combine subagent responses into a final answer"""
        if not self.final_agent:
            raise ValueError("Final orchestrator agent not initialized")
        
        # Create thread for synthesis
        thread = self.client.agents.threads.create()
        
        # Prepare the synthesis prompt
        synthesis_prompt = f"Original user question: {user_message}\n\n"
        synthesis_prompt += "Responses from specialist agents:\n\n"
        
        for agent_type, response in subagent_responses.items():
            synthesis_prompt += f"=== {agent_type.upper()} AGENT RESPONSE ===\n{response}\n\n"
        
        synthesis_prompt += "Please synthesize these responses into a comprehensive final answer."
        
        # Add message to thread
        message = self.client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=synthesis_prompt
        )
        
        # Run the final orchestrator
        run = self.client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self.final_agent.id
        )
        
        # Get synthesized response
        messages = self.client.agents.messages.list(thread_id=thread.id)
        for msg in messages:
            if msg.role == "assistant":
                return msg.content[0].text.value
        
        return "No response received from final orchestrator"
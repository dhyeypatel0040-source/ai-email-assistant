"""
AI Agent service using Composio MCP and LangChain.
"""
import os
import asyncio
from typing import Dict, Any
from composio import Composio
from composio_langchain import LangchainProvider
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

load_dotenv()

class EmailAssistantAgent:
    """AI Agent service for email assistance using LangChain and MCP."""
    
    def __init__(self):
        """Initialize the agent service."""
        self.composio = Composio(provider=LangchainProvider())
        self.model = init_chat_model("openai:gpt-5")
        self.auth_config_id = os.getenv('AUTH_CONFIG_ID', '')
        self.sessions: Dict[str, Any] = {}
        self.clients: Dict[str, MultiServerMCPClient] = {}
        self.graphs: Dict[str, Any] = {}

    async def create_session_for_user(self, user_id: str) -> str:
        """Create a new Composio session for a user"""
        if user_id in self.sessions:
            return self.sessions[user_id]["session_id"]
        

        session = self.composio.experimental.tool_router.create_session(
            user_id=user_id,
            toolkits=[
                {'toolkit': 'gmail', 'auth_config_id': self.auth_config_id}
            ],
        )
        
        self.sessions[user_id] = session
        return session["session_id"]

    async def setup_mcp_client(self, user_id: str):
        """Set up MCP client for a user"""
        if user_id in self.clients:
            return self.clients[user_id]
        
        session = self.sessions[user_id]
        
        client = MultiServerMCPClient(
            {
                "tool_router": {
                    "url": session["url"],
                    "transport": "streamable_http",
                }
            }
        )
        
        self.clients[user_id] = client
        return client

    async def create_agent_graph(self, user_id: str):
        """Create LangGraph agent for a user"""
        if user_id in self.graphs:
            return self.graphs[user_id]
        
        client = await self.setup_mcp_client(user_id)
        tools = await client.get_tools()
        
        model_with_tools = self.model.bind_tools(tools)
        tool_node = ToolNode(tools)

        def should_continue(state: MessagesState):
            messages = state["messages"]
            last_message = messages[-1]
            if last_message.tool_calls:
                return "tools"
            return END

        async def call_model(state: MessagesState):
            messages = state["messages"]
            response = await model_with_tools.ainvoke(messages)
            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("call_model", call_model)
        builder.add_node("tools", tool_node)

        builder.add_edge(START, "call_model")
        builder.add_conditional_edges(
            "call_model",
            should_continue,
        )
        builder.add_edge("tools", "call_model")

        graph = builder.compile()
        self.graphs[user_id] = graph
        return graph

    async def process_message(self, user_id: str, message: str) -> str:
        """Process a message from the frontend"""
        # Create session if it doesn't exist
        await self.create_session_for_user(user_id)
        
        # Get or create the agent graph for this user
        graph = await self.create_agent_graph(user_id)
        
        # Process the message
        response = await graph.ainvoke(
            {"messages": [{"role": "user", "content": message}]}
        )
        
        # Extract the assistant's response
        last_message = response["messages"][-1]
        return last_message.content

    async def cleanup_user_session(self, user_id: str):
        """Clean up resources for a user"""
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.clients:
            del self.clients[user_id]
        if user_id in self.graphs:
            del self.graphs[user_id]

# Global agent instance
agent = EmailAssistantAgent()

async def handle_frontend_request(user_id: str, message: str) -> str:
    """Main function to handle requests from frontend"""
    try:
        response = await agent.process_message(user_id, message)
        return response
    except Exception as e:
        return f"Error processing request: {str(e)}"
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from mcp import ClientSession, stdio_client
import asyncio
import os
from typing import Optional, Dict, Any
from omniflow.utils.config import settings
from omniflow.utils.prompts import get_system_prompt as robust_system_prompt

def get_llm():
    return ChatOpenAI(
        temperature=0,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=settings.OPENAI_API_KEY
    )

def get_system_prompt(role: str):
    return robust_system_prompt(role)

def get_chat_prompt(role: str):
    return ChatPromptTemplate.from_messages([
        ("system", get_system_prompt(role)),
        ("human", "{input}")
    ])

class MCPClientManager:
    """Manages MCP client connections for agents"""
    
    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._tools: Dict[str, Any] = {}
    
    async def connect_to_server(self, server_name: str, command: list) -> Optional[ClientSession]:
        """Connect to an MCP server"""
        try:
            server_params = stdio_client.get_server_parameters(command)
            session = await stdio_client.connect(server_params)
            await session.initialize()
            self._sessions[server_name] = session
            
            # Get available tools from the server
            tools_result = await session.list_tools()
            self._tools[server_name] = tools_result.tools
            
            return session
        except Exception as e:
            print(f"Failed to connect to MCP server {server_name}: {e}")
            return None
    
    def get_tools_for_server(self, server_name: str) -> list:
        """Get available tools for a specific server"""
        return self._tools.get(server_name, [])
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a tool on an MCP server"""
        session = self._sessions.get(server_name)
        if not session:
            raise ValueError(f"No active session for server: {server_name}")
        
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            print(f"Failed to call tool {tool_name} on {server_name}: {e}")
            raise

# Global MCP client manager
mcp_manager = MCPClientManager()

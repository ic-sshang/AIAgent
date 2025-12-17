from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
from agent import AIAgent
from datetime import datetime

from prompt import SYSTEM_PROMPT

app = FastAPI(
    title="AI Agent API",
    description="REST API for AI Agent with function calling capabilities",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active agent sessions (in production, use Redis or similar)
agent_sessions: Dict[str, AIAgent] = {}


# Request/Response Models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message/question")
    biller_id: int = Field(..., description="Biller ID for database connection")
    session_id: Optional[str] = Field(None, description="Session ID to maintain conversation history")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID for this conversation")
    timestamp: str = Field(..., description="Response timestamp")


class ResetRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to reset")


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class ToolsResponse(BaseModel):
    tools: List[str]
    count: int


# Helper function to get or create agent
def get_agent(biller_id: int, session_id: Optional[str] = None) -> tuple[AIAgent, str]:
    """Get existing agent or create new one"""
    if session_id and session_id in agent_sessions:
        return agent_sessions[session_id], session_id
    
    # Create new agent
    agent = AIAgent(biller_id)
    agent.add_system_message(SYSTEM_PROMPT.format(
        biller_id=agent.biller_id,
        current_date=datetime.now().strftime('%Y-%m-%d')
    ))
    
    # Generate session ID
    if not session_id:
        session_id = f"{biller_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    agent_sessions[session_id] = agent
    return agent, session_id


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent and get a response.
    
    - **message**: User's question or message
    - **biller_id**: Biller ID for database connection
    - **session_id**: Optional session ID to maintain conversation history
    """
    try:
        # Get or create agent
        agent, session_id = get_agent(request.biller_id, request.session_id)
        
        # Get response
        response = agent.chat(request.message)
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.post("/reset")
async def reset_conversation(request: ResetRequest):
    """
    Reset conversation history for a session.
    
    - **session_id**: Session ID to reset
    """
    if request.session_id in agent_sessions:
        agent_sessions[request.session_id].reset_conversation()
        return {"status": "success", "message": f"Conversation reset for session {request.session_id}"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and cleanup resources.
    
    - **session_id**: Session ID to delete
    """
    if session_id in agent_sessions:
        # Cleanup database connection
        agent = agent_sessions[session_id]
        if hasattr(agent, 'db_connection') and agent.db_connection:
            agent.db_connection.disconnect()
        
        del agent_sessions[session_id]
        return {"status": "success", "message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.get("/tools/{biller_id}", response_model=ToolsResponse)
async def get_available_tools(biller_id: int):
    """
    Get list of available tools for a biller.
    
    - **biller_id**: Biller ID
    """
    try:
        agent, session_id = get_agent(biller_id)
        tools = agent.tool_registry.list_tools()
        
        # Cleanup temporary agent
        if session_id in agent_sessions:
            del agent_sessions[session_id]
        
        return ToolsResponse(
            tools=tools,
            count=len(tools)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tools: {str(e)}")


@app.get("/sessions")
async def list_sessions():
    """Get list of active sessions"""
    return {
        "sessions": list(agent_sessions.keys()),
        "count": len(agent_sessions)
    }


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

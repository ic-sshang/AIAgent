from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
import os
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
    billerId: int = Field(..., description="Biller ID for database connection")
    sessionId: Optional[str] = Field(None, description="Session ID to maintain conversation history")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    sessionId: str = Field(..., description="Session ID for this conversation")
    timestamp: str = Field(..., description="Response timestamp")


class ResetRequest(BaseModel):
    sessionId: str = Field(..., description="Session ID to reset")


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
        agent, sessionId = get_agent(request.billerId, request.sessionId)
        # Get response
        response = agent.chat(request.message)
        return ChatResponse(
            response=response,
            sessionId=sessionId,
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
    if request.sessionId in agent_sessions:
        agent_sessions[request.sessionId].reset_conversation()
        return {"status": "success", "message": f"Conversation reset for session {request.sessionId}"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.delete("/session/{sessionId}")
async def delete_session(sessionId: str):
    """
    Delete a session and cleanup resources.
    
    - **session_id**: Session ID to delete
    """
    if sessionId in agent_sessions:
        # Cleanup database connection
        agent = agent_sessions[sessionId]
        if hasattr(agent, 'db_connection') and agent.db_connection:
            agent.db_connection.disconnect()
        
        del agent_sessions[sessionId]
        return {"status": "success", "message": f"Session {sessionId} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.get("/tools/{billerId}", response_model=ToolsResponse)
async def get_available_tools(billerId: int):
    """
    Get list of available tools for a biller.
    
    - **biller_id**: Biller ID
    """
    try:
        agent, sessionId = get_agent(billerId)
        tools = agent.tool_registry.list_tools()
        
        # Cleanup temporary agent
        if sessionId in agent_sessions:
            del agent_sessions[sessionId]
        
        return ToolsResponse(
            tools=tools,
            count=len(tools)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tools: {str(e)}")


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download an exported Excel file.
    
    - **filename**: Name of the file to download (e.g., 'export_data.xlsx')
    """
    file_path = os.path.join("exports", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


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

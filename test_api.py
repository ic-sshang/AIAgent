import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"


def chat(message: str, biller_id: int, session_id: str = None):
    """Send a chat message"""
    url = f"{BASE_URL}/chat"
    payload = {
        "message": message,
        "biller_id": biller_id,
        "session_id": session_id
    }
    
    response = requests.post(url, json=payload)
    return response.json()


def reset_conversation(session_id: str):
    """Reset conversation history"""
    url = f"{BASE_URL}/reset"
    payload = {"session_id": session_id}
    
    response = requests.post(url, json=payload)
    return response.json()


def delete_session(session_id: str):
    """Delete a session"""
    url = f"{BASE_URL}/session/{session_id}"
    response = requests.delete(url)
    return response.json()


def get_tools(biller_id: int):
    """Get available tools"""
    url = f"{BASE_URL}/tools/{biller_id}"
    response = requests.get(url)
    return response.json()


def list_sessions():
    """List active sessions"""
    url = f"{BASE_URL}/sessions"
    response = requests.get(url)
    return response.json()


def health_check():
    """Check API health"""
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    return response.json()


# Example usage
if __name__ == "__main__":
    biller_id = 1537
    
    print("Testing API...")
    print("\n1. Health check:")
    print(json.dumps(health_check(), indent=2))
    
    print("\n2. Get available tools:")
    print(json.dumps(get_tools(biller_id), indent=2))
    
    print("\n3. Chat - First message:")
    response1 = chat("I have a customer with account number IVRtest01, how many invoices does this customer have?", biller_id)
    print(json.dumps(response1, indent=2))
    session_id = response1['session_id']
    
    print("\n4. Chat - Follow-up message (same session):")
    response2 = chat("What is their email address?", biller_id, session_id)
    print(json.dumps(response2, indent=2))
    
    print("\n5. List active sessions:")
    print(json.dumps(list_sessions(), indent=2))
    
    print("\n6. Reset conversation:")
    print(json.dumps(reset_conversation(session_id), indent=2))
    
    print("\n7. Delete session:")
    print(json.dumps(delete_session(session_id), indent=2))

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

app = FastAPI(
    title="Columbus AI",
    description="AI-powered travel guide generation API",
    version="1.0.0"
)

class TravelGuideRequest(BaseModel):
    destination: str

@app.post("/generate_travel_guide")
def generate_travel_guide(request: TravelGuideRequest) -> Dict[str, str]:
    """
    Generate a travel guide for the specified destination.
    
    Args:
        request (TravelGuideRequest): The request containing the destination
        
    Returns:
        Dict[str, str]: A placeholder response with status and destination
    """
    return {
        "status": "received",
        "destination": request.destination
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
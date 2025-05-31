# Columbus AI

An AI-powered travel guide generation service.

## Backend Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Server

To start the development server:
```bash
cd backend
python main.py
```

The server will start at `http://localhost:8000`

### API Documentation

Once the server is running, you can access:
- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

### Testing the API

You can test the `/generate_travel_guide` endpoint using curl:
```bash
curl -X POST "http://localhost:8000/generate_travel_guide" \
     -H "Content-Type: application/json" \
     -d '{"destination": "Paris"}'
```

Expected response:
```json
{
    "status": "received",
    "destination": "Paris"
}
``` 
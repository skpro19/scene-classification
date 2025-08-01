# SVO Service

A FastAPI service for streaming SVO (Stereolabs Video Output) files to the frontend.

## Features

- **Status Check**: Verify if the server is running
- **SVO Streaming**: Stream SVO file images to the frontend in real-time
- **Stream Management**: Start, stop, and monitor streaming sessions

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have the ZED SDK installed for SVO processing.

## Running the Service

### Option 1: Using the run script
```bash
python run.py
```

### Option 2: Using uvicorn directly
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8000`

## API Endpoints

### 1. Status Check
- **URL**: `GET /status`
- **Description**: Check if the server is up and running
- **Response**:
```json
{
    "status": "healthy",
    "service": "svo-service",
    "version": "1.0.0"
}
```

### 2. Stream SVO
- **URL**: `POST /stream-svo`
- **Description**: Start streaming an SVO file to the frontend
- **Parameters**: 
  - `file`: The .svo file to stream (multipart form data)
- **Response**: Server-Sent Events stream of base64 encoded JPEG images
- **Headers**:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`

### 3. Stop Stream
- **URL**: `POST /stop-stream`
- **Description**: Stop the current SVO stream
- **Response**:
```json
{
    "message": "Stream stopped successfully"
}
```

### 4. Stream Status
- **URL**: `GET /stream-status`
- **Description**: Get the current streaming status
- **Response**:
```json
{
    "status": "streaming",
    "active": true
}
```

## API Documentation

Once the service is running, you can access:
- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

## Usage Example

### Frontend Integration

```javascript
// Start streaming an SVO file
const formData = new FormData();
formData.append('file', svoFile);

const response = await fetch('/stream-svo', {
    method: 'POST',
    body: formData
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const frameData = line.slice(6); // Remove 'data: ' prefix
            // Display the frame (base64 encoded JPEG)
            displayFrame(frameData);
        }
    }
}
```

## Error Handling

The service includes comprehensive error handling for:
- Invalid file types (non-SVO files)
- Missing SVO processor script
- File upload errors
- Streaming process failures

## Dependencies

- FastAPI: Web framework
- Uvicorn: ASGI server
- Python-multipart: File upload handling
- PyZED: ZED SDK Python wrapper
- OpenCV: Image processing
- NumPy: Numerical computing 
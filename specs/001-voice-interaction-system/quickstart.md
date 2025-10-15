# Quick Start Guide: Voice-Based AI Agent

**Date**: 2025-10-15 (Updated)  
**Feature**: Voice-enabled conversation system  
**Status**: ✅ Phase 2 Complete (80%) | ⏳ Phase 2E Planning (MCP Tools)

---

## ⚡ Current Implementation Status

**✅ What's Working Now (Phase 2 Complete)**:
- ✅ Text chat (non-streaming & streaming)
- ✅ Voice input (STT via iFlytek)
- ✅ Voice output (TTS via iFlytek, <500ms latency)
- ✅ Multiple streaming modes (SSE POST/GET, WebSocket)
- ✅ Session management & conversation history
- ✅ API Key authentication
- ✅ Conversation history API
- ✅ Chinese-localized codebase

**⏳ Coming Next (Phase 2E)**:
- 🚧 MCP tool integration (search, calculator, time tools)
- 🚧 Image generation & document analysis tools

**📋 Planned (Phase 3)**:
- 📋 Redis session storage
- � Docker containerization
- 📋 Production monitoring & metrics

---

## Prerequisites

**Required**:
- Python 3.11+
- OpenAI-compatible LLM API key
- iFlytek account (AppID, APIKey, APISecret) for voice features

**Optional**:
- Audio hardware (microphone/speakers) for voice testing
- Git for version control

## Installation

### 1. Clone and Setup

```powershell
# Clone repository
git clone <repository-url>
cd Ivan_happyWoods

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file from template:

```powershell
# Copy template
copy .env.example .env
```

Edit `.env` with your credentials:

```env
# Required: LLM Service
VOICE_AGENT_LLM__API_KEY=your_api_key_here
VOICE_AGENT_LLM__BASE_URL=https://api.openai-proxy.org/v1
VOICE_AGENT_LLM__MODELS__DEFAULT=gpt-5-mini

# Required: iFlytek Voice Services (register at https://www.xfyun.cn/)
IFLYTEK_APPID=your_appid
IFLYTEK_APIKEY=your_apikey
IFLYTEK_APISECRET=your_apisecret

# TTS Configuration
IFLYTEK_TTS_APPID=your_appid
IFLYTEK_TTS_APIKEY=your_apikey
IFLYTEK_TTS_APISECRET=your_apisecret

# Optional: API Authentication
API_KEY_ENABLED=true
API_KEYS=dev-test-key-123
```

## Running the System

### Start the Server

```powershell
# Option 1: Using provided script
python start_server.py

# Option 2: Direct uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify Installation

Open your browser: http://localhost:8000/docs  
You should see the FastAPI interactive documentation (Swagger UI).

Check health endpoint:
```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.2.0"
}
```

## Basic Usage (Current Features)

### 1. Text Chat (Non-Streaming)

```powershell
curl -X POST http://localhost:8000/api/conversation/send `
  -H "Content-Type: application/json" `
  -d '{"session_id": "test-123", "message": "你好"}'
```

Response:
```json
{
  "session_id": "test-123",
  "response": "你好!我能帮你什么吗?",
  "timestamp": "2025-10-15T..."
}
```

### 2. Streaming Chat (Server-Sent Events)

**POST with stream**:
```powershell
curl -X POST http://localhost:8000/api/conversation/send `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  -d '{"session_id": "test-123", "message": "讲个故事", "stream": true}'
```

**GET for EventSource**:
```
http://localhost:8000/api/conversation/stream?session_id=test-123&message=你好
```

Events received:
```
event: start
data: {"session_id":"test-123"}

event: delta
data: {"content":"从前"}

event: delta
data: {"content":"有一个"}

event: end
data: {"session_id":"test-123","complete":true}
```

### 3. Voice Input (Speech-to-Text)

```powershell
# Upload audio file for transcription
curl -X POST http://localhost:8000/api/voice/stt `
  -H "Content-Type: multipart/form-data" `
  -F "audio=@test_audio.wav" `
  -F "session_id=test-123"
```

Response:
```json
{
  "text": "你好，今天天气怎么样?",
  "confidence": 0.95,
  "session_id": "test-123"
}
```

### 4. Voice Output (Text-to-Speech)

```powershell
# Generate speech from text
curl -X POST http://localhost:8000/api/voice/tts `
  -H "Content-Type: application/json" `
  -d '{"text": "你好，欢迎使用语音助手", "voice": "x4_lingxiaoxuan_oral"}' `
  --output speech.mp3
```

### 5. Conversation History

```powershell
# Get conversation history
curl http://localhost:8000/api/conversation/history/test-123
```

Response:
```json
{
  "session_id": "test-123",
  "messages": [
    {
      "role": "user",
      "content": "你好",
      "timestamp": "2025-10-15T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "你好!我能帮你什么吗?",
      "timestamp": "2025-10-15T10:00:02Z"
    }
  ],
  "total": 2
}
```

### 6. Clear Conversation

```powershell
# Clear session history
curl -X DELETE http://localhost:8000/api/conversation/clear/test-123
```

### 7. WebSocket Chat (Bidirectional Streaming)

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/conversation/ws?session_id=test-123');

// Send message
ws.send(JSON.stringify({
  type: 'message',
  content: '解释一下量子物理',
  session_id: 'test-123'
}));

// Receive streaming response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type);  // start | delta | end | error
  
  if (data.type === 'delta') {
    console.log(data.content);  // Streaming content chunk
  } else if (data.type === 'end') {
    console.log('Stream complete');
  }
};
```

### 8. Model Selection

Switch between LLM models for different use cases:

```powershell
curl -X POST http://localhost:8000/api/conversation/send `
  -H "Content-Type: application/json" `
  -d '{"session_id": "test-123", "message": "快速回答", "model": "gpt-5-nano"}'
```

Available models:
- `gpt-5-mini`: Default balanced model
- `gpt-5-nano`: Fast responses
- `gpt-5-chat-latest`: Creative/advanced reasoning

## Phase 2E Features (Coming Soon)

### Tool Integration (Planned)

MCP protocol tools coming in Phase 2E:

```powershell
# Web search (planned)
curl -X POST http://localhost:8000/api/conversation/send `
  -d '{"message": "搜索最新的人工智能新闻", "enable_tools": true}'

# Calculator (planned)
curl -X POST http://localhost:8000/api/conversation/send `
  -d '{"message": "计算 250 的 15%"}'

# Image generation (planned)
curl -X POST http://localhost:8000/api/conversation/send `
  -d '{"message": "生成一张日落图片"}'
```

## Testing

### Run Tests

```powershell
# All tests
pytest

# With coverage
pytest --cov=src tests/

# Code quality
ruff check src/
```

### Manual Testing

```powershell
# Test conversation flow
python test_conversation.py

# Start dev server with reload
python start_server.py
```

## Troubleshooting

### Common Issues

**1. "Connection refused" on startup**
- Check if port 8000 is in use: `netstat -ano | findstr :8000`
- Try different port: `$env:VOICE_AGENT_API__PORT=8001; python start_server.py`

**2. "API key not found" error**
- Verify `.env` file exists: `Test-Path .env`
- Check API key: `$env:VOICE_AGENT_LLM__API_KEY`
- Reload environment: restart terminal or re-activate venv

**3. Voice features not working**
- Verify iFlytek credentials in `.env`
- Check audio file format (WAV, 16kHz, 16-bit recommended)
- Test TTS separately: `curl -X POST http://localhost:8000/api/voice/tts ...`

**4. "GPT-5 temperature parameter error"**
- This is expected for GPT-5 series models
- The system auto-handles this via `llm_compat.py`
- No action needed

**5. Session history lost after restart**
- This is expected (in-memory storage)
- Redis persistence coming in Phase 3
- Workaround: avoid server restarts during active sessions

### Debug Mode

Enable detailed logging:

```powershell
# Set log level
$env:VOICE_AGENT_LOG_LEVEL="DEBUG"
python start_server.py

# Or in .env file
# VOICE_AGENT_LOG_LEVEL=DEBUG
```

### Health Checks

```powershell
# System status
curl http://localhost:8000/health

# API documentation
Start-Process http://localhost:8000/docs

# Test conversation
python test_conversation.py
```

## Next Steps

1. **✅ Explore API docs**: Visit http://localhost:8000/docs
2. **✅ Test voice features**: Try STT and TTS endpoints
3. **✅ Build integration**: Use REST API or WebSocket in your app
4. **⏳ Await Phase 2E**: MCP tools coming soon
5. **📋 Production deployment**: Docker + monitoring in Phase 3

## Production Deployment (Phase 3 - Planned)

Coming features:
- Docker containerization (`docker-compose up`)
- Redis session storage (persistent sessions)
- Prometheus metrics (`/metrics` endpoint)
- Grafana dashboards
- CI/CD pipeline (GitHub Actions)
- API rate limiting
- Structured logging

## Additional Resources

- **Project Documentation**: [PROJECT.md](../../PROJECT.md)
- **Development Guide**: [DEVELOPMENT.md](../../DEVELOPMENT.md)
- **Progress Tracking**: [progress.md](./progress.md)
- **Achievement Reports**: [docs/achievements/INDEX.md](../../docs/achievements/INDEX.md)
- **Changelog**: [CHANGELOG.md](../../CHANGELOG.md)

---

**Questions or Issues?** Check logs or refer to [DEVELOPMENT.md](../../DEVELOPMENT.md)

**Current Version**: v0.2.0-beta (Phase 2 Complete)  
**Last Updated**: 2025-10-15

```bash
# Start search tool service
python -m src.mcp.tools.search

# Start image generation service  
python -m src.mcp.tools.image_gen

# Start document analysis service
python -m src.mcp.tools.doc_analysis
```

### 3. Verify Installation

Check API health:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "llm": "available",
    "tts": "available", 
    "stt": "available",
    "tools": ["search_tool", "calculator", "time_tool"]
  },
  "version": "1.0.0"
}
```

## Basic Usage

### 1. Create Session (REST API)

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "preferences": {
      "preferred_voice": "alloy",
      "speech_rate": 1.0,
      "language": "en-US"
    }
  }'
```

Response:
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "ACTIVE",
  "created_at": "2025-10-13T10:00:00Z",
  "websocket_url": "ws://localhost:8000/api/stream?session_id=123e4567-e89b-12d3-a456-426614174000"
}
```

### 2. Send Voice Message

```bash
# Upload audio file
curl -X POST http://localhost:8000/api/voice/upload \
  -H "X-API-Key: your-api-key" \
  -F "session_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "audio=@voice_message.wav" \
  -F "format=wav"
```

### 3. Text Chat (Fallback)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "message": "What is the weather like today?"
  }'
```

### 4. WebSocket Streaming (Advanced)

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/stream?session_id=YOUR_SESSION_ID');

// Send audio chunk
ws.send(JSON.stringify({
  type: 'audio_chunk',
  session_id: 'YOUR_SESSION_ID',
  data: base64AudioData,
  format: 'wav'
}));

// Receive responses
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'agent_response') {
    console.log('Agent response:', message.text);
    // Play audio: message.audio_data (base64)
  }
};
```

## Testing Voice Features

### 1. Basic Voice Test

Record a short audio message and test the voice pipeline:

```bash
# Record test message (using system recording tool)
# "Hello, what can you help me with today?"

# Upload and process
curl -X POST http://localhost:8000/api/voice/upload \
  -H "X-API-Key: your-api-key" \
  -F "session_id=YOUR_SESSION_ID" \
  -F "audio=@test_message.wav"
```

### 2. Tool Integration Test

```bash
# Test search functionality
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "message": "Search for recent news about artificial intelligence"
  }'

# Test calculation
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "session_id": "YOUR_SESSION_ID", 
    "message": "Calculate 15% of 250"
  }'
```

## Development Workflow

### 1. Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/

# Run with coverage
pytest --cov=src tests/
```

### 2. Code Quality

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

### 3. Development Server

```bash
# Run with auto-reload
uvicorn src.api.main:app --reload --log-level debug

# Run with specific configuration
python -m src.api.main --config config/development.yaml
```

## Troubleshooting

### Common Issues

1. **Audio not processing**: Check microphone permissions and audio format
2. **API key errors**: Verify API keys in configuration
3. **Tool failures**: Check tool service health endpoints
4. **WebSocket disconnections**: Verify session timeouts and network stability

### Debug Mode

Enable debug logging:

```yaml
# In config file
logging:
  level: "DEBUG"
  format: "detailed"
```

Or via environment:
```bash
export VOICE_AGENT_LOG_LEVEL="DEBUG"
```

### Health Checks

```bash
# Check overall system health
curl http://localhost:8000/health

# Check specific tool health
curl http://localhost:8000/api/tools/search_tool/health

# Check active sessions
curl http://localhost:8000/api/sessions \
  -H "X-API-Key: your-api-key"
```

## Production Deployment

### 1. Docker Deployment

```bash
# Build image
docker build -t voice-agent .

# Run container
docker run -p 8000:8000 \
  -e VOICE_AGENT_LLM_API_KEY="your-key" \
  -e VOICE_AGENT_LLM_BASE_URL="your-url" \
  voice-agent
```

### 2. Configuration for Production

- Use environment variables for all secrets
- Enable HTTPS with proper certificates
- Configure rate limiting and authentication
- Set up monitoring and logging
- Configure session persistence (Redis)

## Next Steps

1. **Integrate Frontend**: Build web or mobile client using WebSocket API
2. **Add Custom Tools**: Extend MCP tools for specific use cases
3. **Improve Performance**: Implement caching and optimization
4. **Add Security**: Implement user authentication and authorization
5. **Scale**: Deploy multiple instances with load balancing

## Support

For issues and questions:
- Check logs: `tail -f logs/voice-agent.log`
- Review API documentation: `http://localhost:8000/docs`
- Run health checks: `curl http://localhost:8000/health`
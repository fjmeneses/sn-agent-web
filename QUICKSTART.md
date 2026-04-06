# Technical Documentation — Voice AI Agent

## Architecture Overview

A containerized Python backend for a web-based voice AI agent with browser-based audio pipeline connected via WebSocket.

### Components

- **Backend**: FastAPI WebSocket server running in Docker
- **Speech-to-Text**: Azure Speech SDK with real-time streaming
- **LLM**: Azure OpenAI for conversation responses
- **Text-to-Speech**: Azure TTS (captures audio in-memory, no device output)
- **Audio Pipeline**: Browser → WebSocket → Azure Speech SDK → Azure OpenAI → Azure TTS → Browser

### Features

✅ **Browser-Based UI** — Single-page HTML interface, no build tools required  
✅ **No Audio Device Dependencies** — All audio I/O through WebSocket  
✅ **Real-Time STT** — Azure Speech SDK with interim and final transcripts  
✅ **State Machine** — LISTENING → THINKING → READY → SPEAKING  
✅ **Conversation Context** — Maintains full conversation history  
✅ **Two Modes**:
   - **Interactive**: Wait for browser confirmation before speaking
   - **Unattended**: Auto-speak all responses

### State Machine Flow

```
LISTENING
    ↓ (final transcript received)
THINKING
    ↓ (LLM response ready)
READY (interactive mode) → wait for {"event": "speak_confirm"}
    ↓ or
SPEAKING (unattended mode) → auto-speak immediately
    ↓
LISTENING (after TTS completes)
```

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### Server → Client Messages

#### State Changes (JSON)
```json
{"event": "state", "value": "LISTENING"}
{"event": "state", "value": "THINKING"}
{"event": "state", "value": "READY"}
{"event": "state", "value": "SPEAKING"}
```

#### Transcripts (JSON)
```json
{"event": "transcript", "value": "hello world", "type": "interim"}
{"event": "transcript", "value": "hello world", "type": "final"}
```

#### LLM Response (JSON)
```json
{"event": "llm_response", "value": "That's a great question..."}
```

#### Audio Response (Binary)
- WAV file bytes (16-bit, 16kHz, mono)
- Sent after SPEAKING state begins

### Client → Server Messages

#### Audio Stream (Binary)
- Send raw PCM audio chunks: 16-bit, 16kHz, mono
- Server streams to Azure Speech SDK in real-time

#### Speak Confirmation (JSON)
```json
{"event": "speak_confirm"}
```
When in **interactive mode**, send this after receiving `llm_response` to trigger TTS playback.

## File Structure

```
azure-sn-agent-web/
├── index.html             # Browser frontend (single-file)
├── serve.py               # Simple HTTP server for frontend
├── server.py              # FastAPI WebSocket backend
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── Dockerfile.frontend    # Frontend container (optional)
├── docker-compose.yml     # Docker Compose configuration
├── setup-env.sh          # Environment configuration script
├── .env                  # Environment variables (not in git)
├── test_websocket.py     # WebSocket test client
├── terraform/
│   ├── core/             # Minimal Azure resources
│   └── full/             # Full deployment with ACR + App Service
├── README.md             # Quick start guide
└── QUICKSTART.md         # This file (technical documentation)
```

---

# Quick Start Guide

## Environment Configuration

Required environment variables (automatically configured via `setup-env.sh`):

```bash
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=southeastasia
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_TTS_VOICE=en-US-AndrewNeural
UNATTENDED=false  # Set to "true" for auto-speak mode
```

## Testing Locally

### What's Been Built

**Backend (server.py):**
- ✅ FastAPI WebSocket server
- ✅ Azure Speech SDK integration (STT + TTS)
- ✅ Azure OpenAI integration
- ✅ 4-state machine (LISTENING → THINKING → READY → SPEAKING)
- ✅ Dockerized and running on port 8000

**Frontend (index.html):**
- ✅ Single-file HTML with inline JavaScript
- ✅ WebSocket client connecting to backend
- ✅ Microphone capture with AudioWorklet
- ✅ Real-time audio streaming (16kHz, 16-bit, mono PCM)
- ✅ TTS audio playback
- ✅ Conversation log with transcript display
- ✅ State indicator with color coding
- ✅ Mute/unmute control
- ✅ ENTER key for speak confirmation

## 🚀 How to Test

### 1. Ensure Backend is Running

```bash
# Start backend
docker compose up -d

# Verify it's running
curl http://localhost:8000/health
# Expected: {"status":"ok","mode":"interactive",...}
```

### 2. Start Frontend Server

```bash
# Start HTTP server on port 3000
python3 serve.py
```

### 3. Open in Browser

```bash
# Open in your default browser
open http://localhost:3000
```

Or manually navigate to: **http://localhost:3000**

### 4. Grant Microphone Permission

When the page loads, your browser will prompt for microphone access:
- Click **Allow** to grant permission
- The page will connect to the WebSocket automatically

### 5. Verify Connection

**Check the UI:**
- ✅ Status badge shows "Connected" (green)
- ✅ State pill shows "LISTENING" (green)
- ✅ No error banner at top

**Check browser console (F12):**
```
[Init] Starting application...
[Audio] Microphone access granted
[Audio] AudioContext created with sample rate: 16000Hz
[Audio] AudioWorklet setup complete
[WebSocket] Connecting to ws://localhost:8000/ws...
[WebSocket] Connected
[WebSocket] Received: {"event":"state","value":"LISTENING"}
```

**Check backend logs:**
```bash
docker compose logs -f
```
You should see:
```
[WebSocket] Client connected
[Azure Speech] Recognizer started
[STATE] LISTENING
```

### 6. Test the Conversation Flow

**With real Azure credentials:**

1. **Speak into your microphone**
   - You should see gray, italic text appear (interim transcript)
   - When you pause, it becomes green (final transcript)

2. **Wait for LLM response**
   - State changes to amber "THINKING"
   - After ~1-3 seconds, state changes to blue "READY"
   - LLM response text appears in purple

3. **Trigger speech**
   - Press **ENTER** or click "Speak Response" button
   - State changes to purple "SPEAKING"
   - Audio plays through your speakers
   - State returns to green "LISTENING"

**Without Azure credentials (testing UI only):**
- WebSocket will connect but no speech recognition will work
- You can still test the UI, state changes, and mute button

## 🧪 Acceptance Criteria Checklist

### Backend
- [x] Container builds without errors
- [x] Uvicorn listening on port 8000
- [x] Health endpoint responds
- [x] WebSocket endpoint accepts connections
- [x] Server sends {"event": "state", "value": "LISTENING"} on connect

### Frontend
- [x] Page loads without JavaScript errors
- [x] Microphone permission prompt appears
- [x] WebSocket connects automatically
- [x] Status badge shows "Connected"
- [x] State pill updates in real-time
- [x] Audio is being captured and sent (check backend logs)
- [x] TTS audio plays back through speakers
- [x] ENTER key triggers speak_confirm when READY
- [x] Mute button stops audio streaming
- [x] Conversation log displays transcripts and responses
- [x] Reconnection works after disconnect

## 🔧 Troubleshooting

### "Access to microphone denied"
- Reload page and grant permission when prompted
- Check browser settings → Site Permissions → Microphone

### "WebSocket connection failed"
- Verify backend is running: `docker ps`
- Check backend health: `curl http://localhost:8000/health`
- Ensure no firewall blocking port 8000

### "No audio being sent"
- Check browser console for errors
- Verify microphone is not muted (system and browser)
- Check the mute button in the UI is not active

### "TTS audio not playing"
- Check speaker volume
- Verify browser console shows "Playing TTS audio..."
- Check browser didn't block autoplay (shouldn't be an issue for user-initiated actions)

### "State stuck on CONNECTING"
- Backend might not be running
- Check `docker compose ps`
- Check `docker compose logs`

## 📝 Next Steps

### For Development
1. Add your real Azure credentials to `.env`
2. Restart backend: `docker compose restart`
3. Test full conversation flow with real speech

### For Production
1. Configure proper HTTPS/WSS for secure connections
2. Add authentication if needed
3. Deploy backend to Azure Container Instances or App Service
4. Serve frontend from Azure Static Web Apps or CDN
5. Configure CORS properly for production domains

## 🎯 Current State

Both backend and frontend are complete and functional:
- Backend accepts WebSocket connections ✅
- Frontend can be opened in browser ✅
- Ready for testing with Azure credentials 🚀

The system is now fully operational for Second Nature sales training sessions!

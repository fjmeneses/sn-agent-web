# Voice AI Agent — Containerized WebSocket Backend

A containerized Python backend for a web-based voice AI agent. This server replaces hardware audio dependencies (VB-Cable loopback) with a browser-based audio pipeline connected via WebSocket.

## Architecture

- **Backend**: FastAPI WebSocket server running in Docker
- **Speech-to-Text**: Azure Speech SDK with real-time streaming
- **LLM**: Azure OpenAI for conversation responses
- **Text-to-Speech**: Azure TTS (captures audio in-memory, no device output)
- **Audio Pipeline**: Browser → WebSocket → Azure Speech SDK → Azure OpenAI → Azure TTS → Browser

## Features

✅ **Browser-Based UI** — Single-page HTML interface, no build tools required  
✅ **No Audio Device Dependencies** — All audio I/O through WebSocket  
✅ **Real-Time STT** — Azure Speech SDK with interim and final transcripts  
✅ **State Machine** — LISTENING → THINKING → READY → SPEAKING  
✅ **Conversation Context** — Maintains full conversation history  
✅ **Two Modes**:
   - **Interactive**: Wait for browser confirmation before speaking
   - **Unattended**: Auto-speak all responses

## Prerequisites

- Docker and Docker Compose installed
- Azure account with:
  - Azure Speech Services (STT + TTS)
  - Azure OpenAI (GPT deployment)
- **Chrome browser** (recommended) or modern Chromium-based browser
  - AudioWorklet API support required
  - Microphone and speaker access

## Quick Start

### 1. Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Azure credentials
nano .env
```

Required environment variables:
```bash
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=southeastasia
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_TTS_VOICE=en-US-AndrewNeural
UNATTENDED=false  # Set to "true" for auto-speak mode
```

### 2. Build and Run

```bash
# Build the container
docker compose build

# Start the server
docker compose up
```

The server will start on `http://localhost:8000`.

### 3. Open Frontend

**Option A: Using included HTTP server (recommended):**
```bash
# Start simple HTTP server on port 3000
python3 serve.py

# Open in browser: http://localhost:3000
```

**Option B: Direct file access:**
```bash
# Open the HTML file directly
open index.html

# Or manually navigate to: file:///path/to/azure-sn-agent-web/index.html
```

> **Note**: Some browsers restrict WebSocket connections from `file://` URLs. If you see connection errors, use Option A.

**On first load:**
1. Browser will request microphone permission — **allow it**
2. Page automatically connects to `ws://localhost:8000/ws`
3. Status badge shows "Connected" when ready
4. State indicator shows "LISTENING" in green

### 4. Using the Frontend

**Interactive Mode (default):**
1. Speak into your microphone
2. Your speech appears as interim transcript (gray, italic)
3. Final transcript appears when you pause (green)
4. Agent responds with text (purple "Agent" message)
5. State changes to "READY" (blue) with a "Speak Response" button
6. Press **ENTER** or click "Speak Response"
7. Agent's voice plays through your speakers
8. Returns to "LISTENING" state

**Unattended Mode** (auto-speak):
- Set `UNATTENDED=true` in `.env`
- Restart: `docker compose restart`
- Agent automatically speaks all responses without waiting

**Mute Toggle:**
- Click "Mute Microphone" to stop audio streaming
- WebSocket stays connected; click "Unmute" to resume

### 5. Verify

```bash
# Health check
curl http://localhost:8000/health

# WebSocket test
python3 test_websocket.py
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
├── docker-compose.yml     # Docker Compose configuration
├── .dockerignore         # Docker build exclusions
├── .env                  # Environment variables (not in git)
├── .env.example          # Environment template
├── test_websocket.py     # WebSocket test client
└── README.md             # This file
```

## State Machine Flow

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

### Queuing Behavior

If transcripts arrive while the agent is **THINKING**, **READY**, or **SPEAKING**, they are queued and processed after returning to **LISTENING** state.

## Audio Format Requirements

### Frontend (Browser)

**Microphone Capture:**
- Automatically uses AudioContext with `sampleRate: 16000`
- AudioWorklet (preferred) or ScriptProcessorNode fallback
- Converts Float32 samples to Int16 PCM
- Streams continuously to WebSocket as binary frames

**TTS Playback:**
- Receives WAV bytes from server
- Uses `AudioContext.decodeAudioData()` to parse
- Plays via `AudioBufferSourceNode` to default audio output

### Client → Server (Microphone Input)
- **Format**: Raw PCM
- **Sample Rate**: 16kHz
- **Bit Depth**: 16-bit signed integer
- **Channels**: 1 (mono)
- **Encoding**: Little-endian

### Server → Client (TTS Output)
- **Format**: WAV file
- **Sample Rate**: 16kHz  
- **Bit Depth**: 16-bit signed integer
- **Channels**: 1 (mono)

## Logging

### Backend Console (Docker)
The backend uses color-coded console logging matching the reference implementation:

- **Gray**: Interim transcripts
- **Green**: Final transcripts, state transitions
- **Yellow**: LLM thinking, warnings
- **Magenta**: LLM responses
- **Cyan**: State changes
- **Red**: Errors
- **Blue**: Info messages

### Browser Console (F12)
Frontend logs all WebSocket events:
- Connection open/close
- State changes received
- Audio bytes sent/received
- Transcript updates
- Errors

Open DevTools → Console to monitor activity.

## Keyboard Shortcuts

- **ENTER** — Trigger speak confirmation (only in READY state)
- **F12** — Open browser DevTools for debugging

## UI States

| State | Color | Animation | Action |
|-------|-------|-----------|--------|
| LISTENING | Green | None | Microphone active, waiting for speech |
| THINKING | Amber | Pulsing | LLM processing transcript |
| READY | Blue | None | Response ready, press ENTER or click Speak |
| SPEAKING | Purple | Pulsing | TTS audio playing |

## Docker Commands

```bash
# Build container
docker compose build

# Start in foreground
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop container
docker compose down

# Rebuild and restart
docker compose up --build
```

## Troubleshooting

### Container Won't Start
- Check `.env` file exists and has valid Azure credentials
- Verify Docker daemon is running
- Check logs: `docker compose logs`

### WebSocket Connection Fails
- Verify container is running: `docker ps`
- Check health endpoint: `curl http://localhost:8000/health`
- Ensure port 8000 is not already in use

### Microphone Not Working
- Check browser console (F12) for errors
- Verify microphone permission was granted
- Try reloading the page and granting permission again
- Test microphone in browser settings

### No Audio Playback
- Check speaker volume and output device
- Verify browser console shows "Playing TTS audio..."
- Test audio with other applications
- Check browser doesn't have media autoplay blocked

### Frontend Shows "Disconnected"
- Backend must be running: `docker compose ps`
- Check for CORS or WebSocket errors in browser console
- Verify WebSocket URL matches backend: `ws://localhost:8000/ws`
- Clear browser cache and reload

### State Stuck on "THINKING"
- Check Docker logs: `docker compose logs -f`
- Verify Azure OpenAI credentials in `.env`
- Check Azure OpenAI deployment quota/availability

### Azure Speech Errors
- Verify `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` are correct
- Check Azure portal for quota/rate limits
- Ensure Speech Services resource is active

### Azure OpenAI Errors
- Verify `AZURE_OPENAI_ENDPOINT` format (must end with `/`)
- Check `AZURE_OPENAI_DEPLOYMENT` matches deployment name exactly
- Verify API key is valid and not expired
- Ensure deployment has sufficient quota

### Session Rejected
- Only one WebSocket session allowed at a time
- Close existing connection before opening new one
- Server responds with `{"event": "error", "value": "session_active"}`

## Development

### Local Testing Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Run server directly
python server.py
```

### Modifying the System Prompt

Edit `SYSTEM_PROMPT` in [server.py](server.py) line 61 to customize the AI agent's personality and behavior.

## License

MIT

## Credits

Based on the [azure-sn-agent](https://github.com/egubi/azure-sn-agent) CLI reference implementation.

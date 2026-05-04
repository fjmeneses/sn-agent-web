#!/usr/bin/env python3
"""
Real-time voice AI agent backend - WebSocket server.
Replaces hardware audio I/O with browser-based audio pipeline.
"""

import asyncio
import json
import os
import struct
import threading
from enum import Enum
from typing import Optional
import wave
import io

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from openai import AzureOpenAI
import uvicorn

# Load environment variables
load_dotenv()

# ============================================================================
# Global Configuration
# ============================================================================
AZURE_SAMPLE_RATE = 16000  # Browser sends 16kHz PCM
CHANNELS = 1  # Mono
BITS_PER_SAMPLE = 16

# Azure AI Services / Speech Configuration
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "southeastasia")
AZURE_SPEECH_ENDPOINT = os.getenv("AZURE_SPEECH_ENDPOINT")
AZURE_AI_SERVICES_RESOURCE_ID = os.getenv("AZURE_AI_SERVICES_RESOURCE_ID")

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Azure TTS Configuration
AZURE_TTS_VOICE = os.getenv("AZURE_TTS_VOICE", "en-US-AndrewNeural")

# Mode configuration
UNATTENDED_MODE = os.getenv("UNATTENDED", "false").lower() == "true"

# In Azure App Service this resolves to the system-assigned managed identity.
# Locally, DefaultAzureCredential can use Azure CLI or developer-tool sign-in.
AZURE_CREDENTIAL = DefaultAzureCredential()
AZURE_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"

# System prompt for the LLM
SYSTEM_PROMPT = """You are talking to Darcy a Senior Decision Maker for an Airline Company. 
You are playing the role of an Solution Engineer for Azure Infra. 
When the he says something, respond naturally as a competent but learning sales rep would. 
Highlight how Azure would help them and also keep it enggaging and ask the right question back.
Keep responses concise - 2-3 sentences max. Push the conversation for next steps and thanks her for the time.
Sound human and conversational, not robotic."""

# ============================================================================
# ANSI Color Codes
# ============================================================================
COLOR_INTERIM = "\033[90m"  # Gray
COLOR_FINAL = "\033[92m"  # Green
COLOR_ERROR = "\033[91m"  # Red
COLOR_INFO = "\033[94m"  # Blue
COLOR_LLM = "\033[95m"  # Magenta
COLOR_LLM_THINKING = "\033[93m"  # Yellow
COLOR_STATE = "\033[96m"  # Cyan
COLOR_READY = "\033[92m\033[1m"  # Bright green
COLOR_WARNING = "\033[93m"  # Yellow
COLOR_RESET = "\033[0m"


# ============================================================================
# State Machine
# ============================================================================
class AgentState(Enum):
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    READY = "READY"
    SPEAKING = "SPEAKING"


# ============================================================================
# FastAPI App
# ============================================================================
app = FastAPI(title="SecondNatureAgent Agent Backend")


@app.get("/")
async def frontend():
    """Serve the browser client from the same Azure App Service as the API."""
    return FileResponse("index.html")

# Global session state (single session at a time)
active_websocket: Optional[WebSocket] = None
active_session_lock = threading.Lock()


# ============================================================================
# Session Handler
# ============================================================================
class VoiceAgentSession:
    """Manages a single WebSocket session with Azure Speech SDK integration."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.loop = asyncio.get_event_loop()
        
        # State machine
        self.current_state = AgentState.LISTENING
        self.state_lock = threading.Lock()
        
        # Azure Speech SDK
        self.push_stream: Optional[speechsdk.audio.PushAudioInputStream] = None
        self.recognizer: Optional[speechsdk.SpeechRecognizer] = None
        
        # OpenAI client
        self.openai_client: Optional[AzureOpenAI] = None
        if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT:
            token_provider = get_bearer_token_provider(AZURE_CREDENTIAL, AZURE_TOKEN_SCOPE)
            self.openai_client = AzureOpenAI(
                api_version=AZURE_OPENAI_API_VERSION,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider
            )
        
        # Conversation history
        self.conversation_history = []
        
        # System prompt (can be overridden by client)
        self.system_prompt = SYSTEM_PROMPT
        
        # Unattended mode (can be overridden by client)
        self.unattended_mode = UNATTENDED_MODE
        
        # Pending state
        self.pending_response: Optional[str] = None
        self.pending_transcripts = asyncio.Queue()
        self.tts_playback_lock = threading.Lock()
        self.tts_pending_lock = threading.Lock()
        self.tts_pending_count = 0
        
        # Running flag
        self.running = True
    
    def set_state(self, new_state: AgentState):
        """Change agent state and notify client."""
        with self.state_lock:
            if self.current_state != new_state:
                self.current_state = new_state
                print(f"{COLOR_STATE}[STATE] {new_state.value}{COLOR_RESET}")
                # Send state notification to client
                asyncio.run_coroutine_threadsafe(
                    self.send_json({"event": "state", "value": new_state.value}),
                    self.loop
                )
    
    def get_state(self) -> AgentState:
        """Get current agent state (thread-safe)."""
        with self.state_lock:
            return self.current_state
    
    async def send_json(self, data: dict):
        """Send JSON message to client."""
        try:
            await self.websocket.send_text(json.dumps(data))
        except Exception as e:
            print(f"{COLOR_ERROR}[WebSocket Error] Failed to send JSON: {e}{COLOR_RESET}")
    
    async def send_binary(self, data: bytes):
        """Send binary message to client."""
        try:
            await self.websocket.send_bytes(data)
        except Exception as e:
            print(f"{COLOR_ERROR}[WebSocket Error] Failed to send binary: {e}{COLOR_RESET}")
    
    def setup_azure_speech(self):
        """Set up Azure Speech recognizer with PushAudioInputStream."""
        if not AZURE_SPEECH_ENDPOINT:
            raise RuntimeError("AZURE_SPEECH_ENDPOINT is required for Entra-authenticated Speech SDK access")

        # Create push audio stream
        self.push_stream = speechsdk.audio.PushAudioInputStream()
        
        # Create audio configuration from push stream
        audio_config = speechsdk.audio.AudioConfig(stream=self.push_stream)
        
        # Create speech configuration
        speech_config = speechsdk.SpeechConfig(
            token_credential=AZURE_CREDENTIAL,
            endpoint=AZURE_SPEECH_ENDPOINT
        )
        speech_config.speech_recognition_language = "en-US"
        
        # Create recognizer
        self.recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # Wire up event handlers
        self.recognizer.recognizing.connect(self._recognizing_callback)
        self.recognizer.recognized.connect(self._recognized_callback)
        self.recognizer.canceled.connect(self._canceled_callback)
        
        # Start continuous recognition
        self.recognizer.start_continuous_recognition_async()
        
        print(f"{COLOR_INFO}[Azure Speech] Recognizer started{COLOR_RESET}")
    
    def _recognizing_callback(self, evt):
        """Handle interim recognition results."""
        if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
            print(f"\r{COLOR_INTERIM}[Interim] {evt.result.text}{COLOR_RESET}", end='', flush=True)
            # Send interim transcript to client
            asyncio.run_coroutine_threadsafe(
                self.send_json({
                    "event": "transcript",
                    "value": evt.result.text,
                    "type": "interim"
                }),
                self.loop
            )
    
    def _recognized_callback(self, evt):
        """Handle final recognition results."""
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            if evt.result.text:
                # Clear interim line
                print(f"\r{' ' * 80}\r{COLOR_FINAL}[Final] {evt.result.text}{COLOR_RESET}")
                
                # Send final transcript to client
                asyncio.run_coroutine_threadsafe(
                    self.send_json({
                        "event": "transcript",
                        "value": evt.result.text,
                        "type": "final"
                    }),
                    self.loop
                )
                
                # Check current state
                state = self.get_state()
                
                if state == AgentState.LISTENING:
                    # Ready to process - trigger LLM response
                    if self.openai_client:
                        self.set_state(AgentState.THINKING)
                        # Run LLM in background thread
                        threading.Thread(
                            target=self._get_llm_response,
                            args=(evt.result.text,),
                            daemon=True
                        ).start()
                else:
                    # Busy - queue the transcript
                    print(f"{COLOR_WARNING}[WARNING] Transcript received while {state.value} — queuing{COLOR_RESET}")
                    asyncio.run_coroutine_threadsafe(
                        self.pending_transcripts.put(evt.result.text),
                        self.loop
                    )
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print(f"\r{' ' * 80}\r", end='')
    
    def _canceled_callback(self, evt):
        """Handle cancellation/error events."""
        print(f"\n{COLOR_ERROR}[Error] Recognition canceled: {evt.cancellation_details.reason}{COLOR_RESET}")
        if evt.cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"{COLOR_ERROR}[Error] Details: {evt.cancellation_details.error_details}{COLOR_RESET}")
    
    def _get_llm_response(self, user_message: str):
        """Call Azure OpenAI to get a response (runs in thread)."""
        if not self.openai_client:
            print(f"{COLOR_ERROR}[LLM] OpenAI client not configured{COLOR_RESET}")
            self.set_state(AgentState.LISTENING)
            return
        
        try:
            print(f"{COLOR_LLM_THINKING}[LLM Thinking...]{COLOR_RESET}")
            
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Build messages for API call
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            # Call Azure OpenAI
            print(f"{COLOR_INFO}[LLM] Calling Azure OpenAI... (deployment: {AZURE_OPENAI_DEPLOYMENT}){COLOR_RESET}")
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                max_completion_tokens=2000,
                timeout=30.0
            )
            print(f"{COLOR_INFO}[LLM] API call completed{COLOR_RESET}")
            
            # Extract response
            assistant_message = response.choices[0].message.content
            
            if not assistant_message:
                print(f"{COLOR_ERROR}[LLM] Empty response received{COLOR_RESET}")
                self.set_state(AgentState.LISTENING)
                return
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            print(f"{COLOR_LLM}[LLM Response] {assistant_message}{COLOR_RESET}")
            
            # Store pending response
            self.pending_response = assistant_message
            
            # Send LLM response to client
            asyncio.run_coroutine_threadsafe(
                self.send_json({
                    "event": "llm_response",
                    "value": assistant_message
                }),
                self.loop
            )
            
            # Check mode
            if self.unattended_mode:
                print(f"{COLOR_INFO}[Unattended Mode] Auto-speaking...{COLOR_RESET}")
                self.queue_speech(assistant_message)
                self.pending_response = None
            else:
                # Wait for client confirmation
                self.set_state(AgentState.READY)
        
        except Exception as e:
            print(f"{COLOR_ERROR}[LLM Error] {type(e).__name__}: {str(e)}{COLOR_RESET}")
            import traceback
            traceback.print_exc()
            self.set_state(AgentState.LISTENING)

    def queue_speech(self, text: str):
        """Queue a response for serialized TTS playback."""
        if not text:
            return

        with self.tts_pending_lock:
            self.tts_pending_count += 1
            queue_position = self.tts_pending_count

        print(f"{COLOR_INFO}[TTS] Queued response for playback (position: {queue_position}){COLOR_RESET}")
        self.set_state(AgentState.SPEAKING)
        threading.Thread(
            target=self._speak_response,
            args=(text,),
            daemon=True
        ).start()
    
    def _speak_response(self, text: str):
        """Use Azure TTS to synthesize speech (runs in thread)."""
        if not text:
            return
        
        try:
            with self.tts_playback_lock:
                self.set_state(AgentState.SPEAKING)
                print(f"{COLOR_INFO}[TTS] Synthesizing speech...{COLOR_RESET}")
                print(f"{COLOR_INFO}[TTS] Text length: {len(text)} chars{COLOR_RESET}")
                
                # Create speech config
                print(f"{COLOR_INFO}[TTS] Creating speech config...{COLOR_RESET}")
                if not AZURE_AI_SERVICES_RESOURCE_ID:
                    raise RuntimeError("AZURE_AI_SERVICES_RESOURCE_ID is required for Entra-authenticated Speech synthesis")

                aad_token = AZURE_CREDENTIAL.get_token(AZURE_TOKEN_SCOPE).token
                speech_authorization_token = f"aad#{AZURE_AI_SERVICES_RESOURCE_ID}#{aad_token}"
                speech_config = speechsdk.SpeechConfig(
                    auth_token=speech_authorization_token,
                    region=AZURE_SPEECH_REGION
                )
                speech_config.speech_synthesis_voice_name = AZURE_TTS_VOICE
                print(f"{COLOR_INFO}[TTS] Speech config created{COLOR_RESET}")
                
                # Use None for audio_config to get raw audio data without automatic playback
                print(f"{COLOR_INFO}[TTS] Creating synthesizer...{COLOR_RESET}")
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=None
                )
                print(f"{COLOR_INFO}[TTS] Synthesizer created{COLOR_RESET}")
                
                # Synthesize with timeout
                print(f"{COLOR_INFO}[TTS] Calling Azure TTS API...{COLOR_RESET}")
                future = synthesizer.speak_text_async(text)
                result = future.get()
                print(f"{COLOR_INFO}[TTS] API call completed, reason: {result.reason}{COLOR_RESET}")
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # Get audio data directly from result (already in WAV format)
                    audio_data = bytes(result.audio_data)
                    
                    print(f"{COLOR_INFO}[TTS] Synthesized {len(audio_data)} bytes{COLOR_RESET}")
                    
                    # Send audio to client (already in WAV format, no need to wrap)
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.send_binary(audio_data),
                            self.loop
                        ).result(timeout=5.0)  # Wait up to 5 seconds
                        print(f"{COLOR_INFO}[TTS] Audio sent to client{COLOR_RESET}")
                    except Exception as e:
                        print(f"{COLOR_ERROR}[TTS] Failed to send audio: {e}{COLOR_RESET}")
                    
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation = result.cancellation_details
                    print(f"{COLOR_ERROR}[TTS Error] Canceled: {cancellation.reason}{COLOR_RESET}")
                    if cancellation.error_details:
                        print(f"{COLOR_ERROR}[TTS Error] Details: {cancellation.error_details}{COLOR_RESET}")
        
        except Exception as e:
            print(f"{COLOR_ERROR}[TTS Error] {type(e).__name__}: {str(e)}{COLOR_RESET}")
            import traceback
            traceback.print_exc()
        
        finally:
            with self.tts_pending_lock:
                self.tts_pending_count = max(0, self.tts_pending_count - 1)
                has_more_speech = self.tts_pending_count > 0

            if has_more_speech:
                print(f"{COLOR_INFO}[TTS] Waiting for next queued response{COLOR_RESET}")
                self.set_state(AgentState.SPEAKING)
            else:
                self.set_state(AgentState.LISTENING)
                asyncio.run_coroutine_threadsafe(
                    self._process_queued_transcripts(),
                    self.loop
                )
    
    def _create_wav(self, pcm_data: bytes) -> bytes:
        """Wrap PCM data in WAV header (16kHz, 16-bit, mono)."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(BITS_PER_SAMPLE // 8)
            wav_file.setframerate(AZURE_SAMPLE_RATE)
            wav_file.writeframes(pcm_data)
        return wav_buffer.getvalue()
    
    async def _process_queued_transcripts(self):
        """Process any queued transcripts."""
        if not self.pending_transcripts.empty():
            try:
                queued_text = await self.pending_transcripts.get()
                print(f"{COLOR_INFO}[Processing queued] {queued_text}{COLOR_RESET}")
                
                if self.openai_client and self.get_state() == AgentState.LISTENING:
                    self.set_state(AgentState.THINKING)
                    threading.Thread(
                        target=self._get_llm_response,
                        args=(queued_text,),
                        daemon=True
                    ).start()
            except Exception as e:
                print(f"{COLOR_ERROR}[Queue Error] {e}{COLOR_RESET}")
    
    def push_audio(self, audio_data: bytes):
        """Push audio data to Azure Speech SDK."""
        if self.push_stream and self.running:
            self.push_stream.write(audio_data)
    
    async def handle_client_message(self, data):
        """Handle text messages from client."""
        try:
            msg = json.loads(data)
            event = msg.get("event")
            
            if event == "speak_confirm":
                # Client confirmed - speak the pending response
                if self.pending_response and self.get_state() == AgentState.READY:
                    print(f"{COLOR_INFO}[Client] Speak confirmed{COLOR_RESET}")
                    self.queue_speech(self.pending_response)
                    self.pending_response = None
            
            elif event == "set_system_prompt":
                # Client sent custom system prompt
                new_prompt = msg.get("value", "").strip()
                if new_prompt:
                    self.system_prompt = new_prompt
                    print(f"{COLOR_INFO}[Session] System prompt updated ({len(new_prompt)} chars){COLOR_RESET}")
            
            elif event == "set_unattended":
                # Client sent unattended mode setting
                self.unattended_mode = bool(msg.get("value", False))
                mode_label = "UNATTENDED" if self.unattended_mode else "INTERACTIVE"
                print(f"{COLOR_INFO}[Session] Mode set to {mode_label}{COLOR_RESET}")
            
            else:
                print(f"{COLOR_WARNING}[Client] Unknown event: {event}{COLOR_RESET}")
        
        except json.JSONDecodeError:
            print(f"{COLOR_ERROR}[Client] Invalid JSON received{COLOR_RESET}")
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        
        if self.recognizer:
            self.recognizer.stop_continuous_recognition_async()
        
        if self.push_stream:
            self.push_stream.close()
        
        print(f"{COLOR_INFO}[Session] Cleaned up{COLOR_RESET}")


# ============================================================================
# WebSocket Endpoint
# ============================================================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global active_websocket
    
    # Check if session is already active
    with active_session_lock:
        if active_websocket is not None:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "event": "error",
                "value": "session_active"
            }))
            await websocket.close()
            print(f"{COLOR_WARNING}[WebSocket] Rejected connection - session active{COLOR_RESET}")
            return
        
        active_websocket = websocket
    
    await websocket.accept()
    print(f"{COLOR_INFO}[WebSocket] Client connected{COLOR_RESET}")
    
    # Create session
    session = VoiceAgentSession(websocket)
    
    try:
        # Set up Azure Speech
        session.setup_azure_speech()
        
        # Send initial state
        await session.send_json({"event": "state", "value": "LISTENING"})
        
        # Message loop
        while session.running:
            data = await websocket.receive()
            
            if "bytes" in data:
                # Binary audio data
                audio_bytes = data["bytes"]
                session.push_audio(audio_bytes)
            
            elif "text" in data:
                # JSON message
                await session.handle_client_message(data["text"])
    
    except WebSocketDisconnect:
        print(f"{COLOR_INFO}[WebSocket] Client disconnected{COLOR_RESET}")
    
    except Exception as e:
        print(f"{COLOR_ERROR}[WebSocket Error] {e}{COLOR_RESET}")
    
    finally:
        # Cleanup
        session.cleanup()
        
        with active_session_lock:
            active_websocket = None
        
        print(f"{COLOR_INFO}[Session] Ended{COLOR_RESET}")


# ============================================================================
# Health Check
# ============================================================================
@app.get("/health")
async def health_check():
    return JSONResponse(content={
        "status": "ok",
        "mode": "unattended" if UNATTENDED_MODE else "interactive",
        "azure_speech": "configured" if AZURE_SPEECH_ENDPOINT and AZURE_AI_SERVICES_RESOURCE_ID else "missing",
        "azure_openai": "configured" if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT else "missing",
        "auth": "entra_id"
    })


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    print(f"{COLOR_INFO}{'='*80}{COLOR_RESET}")
    print(f"{COLOR_INFO}SecondNatureAgent Agent Backend Server{COLOR_RESET}")
    print(f"{COLOR_INFO}{'='*80}{COLOR_RESET}")
    print(f"{COLOR_INFO}Mode: {'UNATTENDED' if UNATTENDED_MODE else 'INTERACTIVE'}{COLOR_RESET}")
    print(f"{COLOR_INFO}Azure Speech: {'OK' if AZURE_SPEECH_ENDPOINT and AZURE_AI_SERVICES_RESOURCE_ID else 'MISSING'}{COLOR_RESET}")
    print(f"{COLOR_INFO}Azure OpenAI: {'OK' if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT else 'MISSING'}{COLOR_RESET}")
    print(f"{COLOR_INFO}Authentication: Microsoft Entra ID{COLOR_RESET}")
    print(f"{COLOR_INFO}{'='*80}{COLOR_RESET}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

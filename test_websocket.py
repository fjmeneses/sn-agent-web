#!/usr/bin/env python3
"""
Simple WebSocket test client for the Voice AI Agent backend.
This script connects to the WebSocket endpoint and verifies basic connectivity.
"""

import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully!")
            
            # Wait for initial state message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✓ Received initial state: {data}")
            
            if data.get("event") == "state" and data.get("value") == "LISTENING":
                print("✓ Server is in LISTENING state")
                print("\n✅ All acceptance criteria met:")
                print("   - Container started without errors")
                print("   - Uvicorn listening on port 8000")
                print("   - WebSocket connection established")
                print("   - Received initial LISTENING state")
                return True
            else:
                print("✗ Unexpected initial message")
                return False
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket())
    exit(0 if success else 1)

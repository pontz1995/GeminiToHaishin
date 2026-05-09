import asyncio
import os
import json
from dotenv import load_dotenv

import websockets
from google import genai
from google.genai import types


load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(".env に GOOGLE_API_KEY が設定されていません")

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-3.1-flash-live-preview"

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription=types.AudioTranscriptionConfig(),
    system_instruction=types.Content(
        role="system",
        parts=[
            types.Part(text="あなたは、優秀なAIアシスタントです。日本語で回答してください。")
        ],
    ),
)


async def ws_server(websocket):
    print("[LOG] Client connected")

    try:
        async with client.aio.live.connect(
            model=MODEL,
            config=config,
        ) as session:
            print("[LOG] Connected to Gemini Live API")

            async for text in websocket:
                print(f"[CLIENT] {text}")

                await session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=text)],
                    ),
                    turn_complete=True,
                )

                async for message in session.receive():
                    if message.server_content:
                        if message.server_content.output_transcription:
                            print("[Gemini]: ", message.server_content.output_transcription.text)
                            await websocket.send(json.dumps({"serverContent": {"modelTurn": {"parts": [{"text": message.server_content.output_transcription.text}]}}}))

                    server_content = getattr(message, "server_content", None)

                    if server_content:
                        if getattr(server_content, "generation_complete", False):
                            print("[LOG] Generation complete")

                        if getattr(server_content, "turn_complete", False):
                            await websocket.send(
                                json.dumps({"serverContent": {"turnComplete": True}})
                            )
                            print("[LOG] Turn complete")
                            break

    except websockets.exceptions.ConnectionClosed as e:
        print("[LOG] Client disconnected code={e.code} reason={e.reason}")

    except Exception as e:
        print(f"[ERROR] {e}")
        try:
            await websocket.send(json.dumps({"serverContent": {"error": f"[ERROR] {e}"}}))
            await websocket.send(json.dumps({"serverContent": {"generationComplete": True}}))
            await websocket.send(json.dumps({"serverContent": {"turnComplete": True}}))
        except Exception:
            pass


async def main():
    print("[LOG] WebSocket server started: ws://localhost:8000")

    async with websockets.serve(ws_server, "localhost", 8000, ping_interval=20, ping_timeout=None):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
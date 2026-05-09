import asyncio
import json
import os
import websockets

WS_URL = "ws://localhost:8000"


async def ws_client():
    async with websockets.connect(
        WS_URL,
        ping_interval=20,
        ping_timeout=None
    ) as websocket:
        print("[LOG] Connected")

        while True:
            text = input("\nYou: ")

            if text.lower() in ["exit", "quit"]:
                break

            message = {
                "realtimeInput": {
                    "text": text
                }
            }

            await websocket.send(json.dumps(message))

            print("Gemini: ", end="")

            async for response_text in websocket:
                response = json.loads(response_text)

                if "serverContent" in response:
                    server_content = response["serverContent"]

                    if "modelTurn" in server_content:
                        parts = server_content["modelTurn"].get("parts", [])
                        for part in parts:
                            if "text" in part:
                                print(part["text"], end="", flush=True)

                    if server_content.get("turnComplete"):
                        break

            print()


if __name__ == "__main__":
    asyncio.run(ws_client())
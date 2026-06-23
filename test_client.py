import asyncio
import websockets

async def test_client():
    uri = "ws://localhost:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for greeting audio...")
            while True:
                data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if isinstance(data, bytes):
                    print(f"Received audio chunk of size {len(data)} bytes")
                else:
                    print(f"Received text: {data}")
    except asyncio.TimeoutError:
        print("Timeout waiting for data.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())

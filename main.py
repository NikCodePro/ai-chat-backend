import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        # Send WS ping every 20s and close if pong not received within 20s.
        # Prevents silent TCP drops on mobile cellular/WiFi switches.
        ws_ping_interval=20,
        ws_ping_timeout=20,
        # 8 MB max WS message — accommodates base64-encoded audio chunks safely.
        ws_max_size=8_388_608,
    )

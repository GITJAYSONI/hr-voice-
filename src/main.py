from contextlib import asynccontextmanager
import os
import signal
import subprocess
import sys
from uuid import UUID
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.interface.api.router import api_router

class BotManager:
    """Manages the lifecycle of the Pipecat background subprocess"""
    def __init__(self):
        self.bot_process = None

    def kill_port_owner(self, port: int):
        """Force kills any process holding the target port (Windows specific)"""
        try:
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            for line in output.strip().split('\n'):
                parts = [p for p in line.split() if p]
                if len(parts) >= 5:
                    addr = parts[1]
                    if addr.split(':')[-1] == str(port):
                        pid = int(parts[4])
                        if pid > 0:
                            # Send termination signal gracefully
                            os.kill(pid, signal.SIGTERM)
                            print(f"[System] Terminated background process {pid} holding port {port}")
        except Exception:
            pass

    def start_bot(self, interview_id: UUID):
        print("\n[System] Freeing port 8765…")
        self.kill_port_owner(8765)
        if self.bot_process:
            self.stop_bot()
            
        # Robustly detect virtual environment python if it exists
        python_exe = sys.executable
        venv_path = os.path.join(os.getcwd(), "venv")
        if os.path.exists(venv_path):
            candidate_exe = os.path.join(venv_path, "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(venv_path, "bin", "python")
            if os.path.exists(candidate_exe):
                python_exe = candidate_exe
                print(f"[System] Spawning bot using virtual environment: {python_exe}")
            else:
                print(f"[System] Spawning bot using current python: {python_exe}")
        else:
            print(f"[System] Spawning bot using current python: {python_exe}")
            
        print(f"[System] Starting Pipecat Voice Server for interview {interview_id}…")
        self.bot_process = subprocess.Popen(
            [python_exe, "bot.py", str(interview_id)],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

    def stop_bot(self):
        if self.bot_process:
            print("[System] Sending termination signal to Pipecat Voice Server…")
            try:
                # Use terminate() on all platforms to prevent signal bubbling on Windows
                self.bot_process.terminate()
                try:
                    self.bot_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    print("[System] Bot process did not exit in time, forcing kill…")
                    self.bot_process.kill()
            except Exception as e:
                print(f"[System] Error shutting down bot process: {e}")
            finally:
                self.bot_process = None

bot_manager = BotManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # FastAPI teardown – ensure the background bot is stopped cleanly
    print("\n[System] ASGI application shutdown – cleaning up bot process…")
    try:
        bot_manager.stop_bot()
    except Exception as e:
        print(f"[System] Exception during bot cleanup: {e}")

def create_app() -> FastAPI:
    app = FastAPI(
        title="HR Voice + Vision Interview Platform",
        description="Backend API for the autonomous technical recruiter platform.",
        version="1.0.0",
        lifespan=lifespan,
    )
    # CORS – allow all origins for local dev (restrict in prod)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Register routers
    app.include_router(api_router, prefix="/api/v1")

    @app.post("/api/v1/interviews/{interview_id}/start")
    async def start_interview_bot(interview_id: UUID):
        bot_manager.start_bot(interview_id)
        return {"status": "started", "interview_id": interview_id}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app()

if __name__ == "__main__":
    # Local dev entry point – suppress noisy CancelledError traces
    try:
        # In production you typically disable reload to avoid a subprocess which prints tracebacks on Ctrl+C.
        uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        # Graceful shutdown on manual interrupt
        print("\n[System] Server interrupted by user – shutting down cleanly.")
    except Exception as e:
        # Suppress CancelledError that can bubble up from uvicorn internals
        if type(e).__name__ == "CancelledError":
            print("\n[System] Server cancelled during shutdown (clean exit).")
        else:
            raise

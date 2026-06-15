import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run(cmd, desc):
    print(f"\n{'='*54}\n>>> {desc}\n{'='*54}")
    subprocess.run(cmd, shell=True)

print("""
╔══════════════════════════════════════════════════════╗
║       LegalEase India v4 — SETUP & LAUNCH            ║
║  Fixed: All intents · Voice · News TTS · 3 languages ║
║  Standalone: Works without backend too!              ║
╚══════════════════════════════════════════════════════╝
""")

run(f"{sys.executable} -m pip install fastapi uvicorn pydantic python-multipart -q",
    "Installing dependencies...")

print(f"""
{'='*54}
Launching on PORT 8001
{'='*54}
  App      :  http://localhost:8001
  API Docs :  http://localhost:8001/api/docs
  Press Ctrl+C to stop
""")
os.system(f"{sys.executable} -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8001")

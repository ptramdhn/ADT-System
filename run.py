import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("\n" + "="*65)
    print(" [>] MEMULAI SISTEM OPERASIONAL & KEUANGAN PT ANUGRAH DJAYA TUNGGAL")
    print("="*65)
    print(" [*] Web Dashboard : http://localhost:8000")
    print(" [*] Dokumentasi API: http://localhost:8000/docs")
    print(" [*] Database      : MySQL (localhost:3306 / adt_system)")
    from app.core.config import settings
    print(f" [*] AI Agent      : Mistral AI ({settings.MISTRAL_MODEL} + Multi-Model Fallback)")
    print("="*65 + "\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

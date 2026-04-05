import threading
import webbrowser
import uvicorn
import os
import time


def open_browser():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    # 🔥 SOLO abrir browser en proceso principal real
    if os.environ.get("RUN_MAIN") != "true":
        threading.Thread(target=open_browser).start()

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )

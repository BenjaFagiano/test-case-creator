import threading
import webbrowser
import time
import uvicorn

chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
webbrowser.get(chrome_path).open("http://127.0.0.1:8000")

def open_browser():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)

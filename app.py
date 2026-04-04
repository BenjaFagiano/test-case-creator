import json
import os
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from datetime import datetime
from fastapi import UploadFile, File
import shutil

from main import get_jira_issue, call_ai, parse_response, create_excel, MODEL_NAME

app = FastAPI()

templates = Jinja2Templates(directory="templates")
HISTORY_FILE = "history.json"
EXECUTION_LOG_FILE = "execution_log.json"
STYLE_FOLDER = "style_uploads"
STYLE_PROFILE_FILE = "style_profile.json"


def log_execution(issue_key, priority, model_name, file_path, cases_count):
    if not os.path.exists(EXECUTION_LOG_FILE):
        with open(EXECUTION_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(EXECUTION_LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    logs.insert(0, {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "issue": issue_key,
        "priority": priority,
        "model": model_name,
        "file": file_path,
        "cases_generated": cases_count
    })

    logs = logs[:20]  # mantener solo últimas 20 ejecuciones

    with open(EXECUTION_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_issues": []}, f)
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("last_issues", [])

def save_issue_to_history(issue_key):
    history = load_history()
    
    if issue_key in history:
        history.remove(issue_key)
    
    history.insert(0, issue_key)
    
    history = history[:5]  # solo últimas 5
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_issues": history}, f, indent=2)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    history = load_history()
    execution_log = load_execution_log()

    return templates.TemplateResponse(
    "index.html",
    {
        "request": request,
        "history": history,
        "execution_log": execution_log
    }
)


@app.post("/generate", response_class=HTMLResponse)
async def generate(request: Request, issue_key: str = Form(...)):

    try:
        title, description, priority = get_jira_issue(issue_key)

        with open("prompts/base_prompt.txt", "r", encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            title=title,
            description=description,
            acceptance="Incluido en descripción"
        )

        response = call_ai(prompt)

        csv_text, gherkin_text = parse_response(response)

        create_excel(issue_key, csv_text, gherkin_text)

        lines = csv_text.strip().split("\n")
        cases_count = max(len(lines) - 1, 0)

        file_path = f"outputs/{issue_key}_testcases.xlsx"

        log_execution(
            issue_key,
            priority,
            MODEL_NAME,
            file_path,
            cases_count
        )

        save_issue_to_history(issue_key)

        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{issue_key}_testcases.xlsx"
        )

    except Exception as e:
        history = load_history()
        execution_log = load_execution_log()

        error_text = str(e)

        # Intentar limpiar mensaje si viene de Jira
        if "errorMessages" in error_text:
            try:
                parsed = json.loads(error_text.split("Error al obtener issue: ")[-1])
                error_text = parsed["errorMessages"][0]
            except:
                pass

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "history": history,
                "execution_log": execution_log,
                "error_message": error_text,
                "issue_key": issue_key
            }
        )

def load_execution_log():
    if not os.path.exists(EXECUTION_LOG_FILE):
        return []

    try:
        with open(EXECUTION_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        return []


os.makedirs(STYLE_FOLDER, exist_ok=True)


@app.get("/style", response_class=HTMLResponse)
async def style_page(request: Request):

    uploaded_files = os.listdir(STYLE_FOLDER)

    active_profile = None

    if os.path.exists(STYLE_PROFILE_FILE):
        try:
            with open(STYLE_PROFILE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    active_profile = json.loads(content)
        except:
            active_profile = None

    return templates.TemplateResponse(
        "style.html",
        {
            "request": request,
            "files": uploaded_files,
            "active_profile": active_profile
        }
    )


@app.post("/style/upload")
async def upload_style(file: UploadFile = File(...)):

    file_path = os.path.join(STYLE_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "File uploaded successfully"}

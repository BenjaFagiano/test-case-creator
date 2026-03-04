import os
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from main import get_jira_issue, call_ai, parse_response, create_excel

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate(issue_key: str = Form(...)):

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

    file_path = f"outputs/{issue_key}_testcases.xlsx"

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{issue_key}_testcases.xlsx"
    )

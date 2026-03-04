import os
import sys
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from openpyxl import Workbook
from openai import OpenAI
from dotenv import load_dotenv

# ==============================
# CARGA DE VARIABLES .ENV
# ==============================

load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not OPENAI_API_KEY:
    raise ValueError("Falta OPENAI_API_KEY en .env")

if not JIRA_BASE_URL or not JIRA_EMAIL or not JIRA_API_TOKEN:
    raise ValueError("Faltan variables de Jira en .env")

print("DEBUG:")
print("JIRA_BASE_URL:", JIRA_BASE_URL)
print("JIRA_EMAIL:", JIRA_EMAIL)
print("JIRA_API_TOKEN:", "OK" if JIRA_API_TOKEN else "MISSING")
# ==============================
# FUNCIONES JIRA
# ==============================

def extract_description(description_field):
    """
    Jira Cloud usa Atlassian Document Format (ADF).
    Esto convierte el JSON en texto plano.
    """
    if not description_field:
        return ""

    if isinstance(description_field, dict):
        content = []

        def parse_content(node):
            if "text" in node:
                content.append(node["text"])
            if "content" in node:
                for child in node["content"]:
                    parse_content(child)

        parse_content(description_field)
        return "\n".join(content)

    return str(description_field)


def get_jira_issue(issue_key):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        raise Exception(f"Error al obtener issue: {response.text}")

    data = response.json()
    fields = data["fields"]

    title = fields.get("summary", "")
    description = extract_description(fields.get("description"))
    priority = fields.get("priority", {}).get("name", "Media")

    return title, description, priority


# ==============================
# IA
# ==============================

def call_ai(prompt):
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content


def parse_response(response):
    parts = response.split("===GHERKIN===")

    csv_part = parts[0].replace("===CASOS_CSV===", "").strip()
    gherkin_part = parts[1].strip() if len(parts) > 1 else ""

    return csv_part, gherkin_part


# ==============================
# EXCEL
# ==============================

def create_excel(issue_key, csv_text, gherkin_text):

    wb = Workbook()
    ws = wb.active
    ws.title = "Casos Manuales"

    headers = [
        "Fecha", "ID", "Descripción", "Prioridad", "Tipo de Caso",
        "Precondiciones", "Pasos de prueba", "Resultado Esperado",
        "Estado", "Resultado Actual", "Observaciones"
    ]

    ws.append(headers)

    today = datetime.now().strftime("%d/%m/%Y")

    for line in csv_text.split("\n"):
        cols = [c.strip() for c in line.split(",")]

        if len(cols) < 7:
            continue  # evita errores si la IA devuelve línea vacía

        row = [
            today,
            cols[0],  # ID
            cols[1],  # Descripción
            cols[2],  # Prioridad
            cols[3],  # Tipo
            cols[4],  # Precondiciones
            cols[5],  # Pasos
            cols[6],  # Resultado esperado
            "Pendiente",
            "",
            ""
        ]

        ws.append(row)

    # Hoja Gherkin
    ws2 = wb.create_sheet("Gherkin")

    for line in gherkin_text.split("\n"):
        ws2.append([line])

    os.makedirs("outputs", exist_ok=True)
    wb.save(f"outputs/{issue_key}_testcases.xlsx")


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Uso: python main.py QM-1486")
        sys.exit(1)

    issue_key = sys.argv[1]

    print(f"Buscando issue {issue_key} en Jira...")

    title, description, priority = get_jira_issue(issue_key)

    print("Generando casos con IA...")

    with open("prompts/base_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()

    prompt = template.format(
        title=title,
        description=description,
        acceptance="Incluido en descripción si aplica"
    )

    response = call_ai(prompt)

    csv_text, gherkin_text = parse_response(response)

    create_excel(issue_key, csv_text, gherkin_text)

    print(f"Excel generado correctamente para {issue_key}")

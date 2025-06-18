import sqlite3
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import re
import PyPDF2

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = "store.db"
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class QueryRequest(BaseModel):
    question: str

def adaptar_sql_para_sqlite(sql_query: str) -> str:
    # Reemplaza SELECT TOP N ... por SELECT ... LIMIT N
    import re
    # Detecta SELECT TOP N ... FROM ...
    top_match = re.match(r'(SELECT)\s+TOP\s+(\d+)\s+(.*?FROM\s+.+)', sql_query, re.IGNORECASE)
    if top_match:
        select, top_n, rest = top_match.groups()
        # Quita TOP N y agrega LIMIT N al final
        sql_query = f"{select} {rest} LIMIT {top_n}"
    # Reemplaza YEAR(Fecha) por strftime('%Y', Fecha)
    sql_query = re.sub(r'YEAR\(([^)]+)\)', r"strftime('%Y', \1)", sql_query, flags=re.IGNORECASE)
    # Reemplaza comillas simples dobles por simples
    sql_query = sql_query.replace("''", "'")
    return sql_query

def extract_text_from_pdfs(upload_dir="uploads"):
    text = ""
    for fname in os.listdir(upload_dir):
        if fname.lower().endswith(".pdf"):
            try:
                with open(os.path.join(upload_dir, fname), "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or ""
            except Exception as e:
                text += f"\n[Error leyendo {fname}: {e}]\n"
    return text

def format_pdf_response(question, pdf_answer, pdf_text):
    # Separar interpretación y fuente si el modelo las mezcla
    # Buscar sección 'Fuente (PDF):' o similar en la respuesta del modelo
    fuente = ""
    interpretacion = pdf_answer
    fuente_match = re.search(r'Fuente ?\(PDF\)?:?\s*([\s\S]+)', pdf_answer, re.IGNORECASE)
    if fuente_match:
        interpretacion = pdf_answer[:fuente_match.start()].strip()
        fuente = fuente_match.group(1).strip()
    return (
        f"<div style='margin-bottom:18px;'><b>Interpretación:</b><br>{interpretacion}</div>"
        f"<div class='small' style='margin-top:18px; color:#555;'><b>Fuente (PDF):</b><br><code style='font-size:0.95em'>{fuente}</code></div>"
    )

@app.post("/ask")
def ask_question(req: QueryRequest):
    question = req.question
    # Palabras clave que fuerzan búsqueda SQL
    sql_keywords = [
        "sql", "venta", "ventas", "producto", "productos", "distribuidor", "distribuidores", "costo", "precio", "unidades", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "catálogo", "catalogo", "descuento", "participación", "participacion", "promedio", "total", "tabla", "query"
    ]
    # Si la pregunta contiene palabras clave SQL, priorizar SQL
    if any(k in question.lower() for k in sql_keywords):
        goto_sql = True
    else:
        goto_sql = False
    # 1. Buscar primero en PDFs (solo si no se fuerza SQL)
    if not goto_sql:
        pdf_text = extract_text_from_pdfs()
        if pdf_text.strip():
            prompt_pdf = (
                f"Eres un asistente experto en análisis de documentos PDF. Si puedes responder la siguiente pregunta usando solo el contenido de los PDFs cargados, hazlo. Si no encuentras información relevante en los PDFs, responde solo con la palabra: __NO_PDF__\n\n"
                f"Contenido de los PDFs:\n{pdf_text[:3000]}\n\nPregunta: {question}\n\nFormato de respuesta:\nInterpretación:\n<interpretación en texto>\n\nFuente (PDF):\n<fragmento relevante del PDF>"
            )
            response_pdf = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_pdf}]
            )
            pdf_answer = response_pdf.choices[0].message.content.strip()
            if not pdf_answer.startswith("__NO_PDF__"):
                return {"response": format_pdf_response(question, pdf_answer, pdf_text)}
    # 2. Si no hay respuesta relevante en PDF o se fuerza SQL, pasar a SQL
    with open("prompt.txt", "r", encoding="utf-8") as f:
        prompt_base = f.read()
    prompt = prompt_base.replace("{question}", question)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content
    sql_blocks = re.findall(r'```sql\s*([\s\S]+?)\s*```', result, re.IGNORECASE)
    sql_query = None
    if sql_blocks:
        for block in sql_blocks:
            if re.search(r'\bSELECT\b|\bUPDATE\b|\bDELETE\b|\bINSERT\b', block, re.IGNORECASE):
                sql_query = block.strip()
                break
        if not sql_query:
            sql_query = sql_blocks[0].strip()
    else:
        lines = result.splitlines()
        for line in lines:
            if re.match(r'\s*(SELECT|UPDATE|DELETE|INSERT) ', line, re.IGNORECASE):
                sql_query = line.strip()
                break
    if sql_query:
        sql_query = adaptar_sql_para_sqlite(sql_query)
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()
        except Exception as e:
            return {"response": f"Error al ejecutar el query SQL: {e}"}
        table_html = '<table border="1"><tr>' + ''.join(f'<th>{col}</th>' for col in columns) + '</tr>'
        for row in rows:
            table_html += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
        table_html += '</table>'
        interp_match = re.search(r'Interpretaci[oó]n:\s*(.*?)\n(Resultados:|Query:|$)', result, re.DOTALL)
        interpretacion = interp_match.group(1).strip() if interp_match else ""
        interpretacion = interpretacion.split('Query:')[0].strip()
        respuesta = (
            f"<div style='margin-bottom:18px;'><b>Interpretación:</b><br>{interpretacion}</div>"
            f"<div style='margin-bottom:18px; text-align:center;'>{table_html}</div>"
            f"<div class='small' style='margin-top:18px; color:#555;'><b>Query SQL generado:</b><br><code style='font-size:0.95em'>{sql_query}</code></div>"
        )
        return {"response": respuesta}
    interp_match = re.search(r'Interpretaci[oó]n:\s*(.*?)\n(Resultados:|Query:|$)', result, re.DOTALL)
    interpretacion = interp_match.group(1).strip() if interp_match else result.strip()
    respuesta = (
        f"<div style='margin-bottom:18px;'><b>Interpretación:</b><br>{interpretacion}</div>"
    )
    return {"response": respuesta}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        return JSONResponse(content={"error": "Solo se permiten archivos PDF."}, status_code=400)
    save_path = os.path.join("uploads", file.filename)
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"filename": file.filename, "message": "Archivo subido correctamente."}
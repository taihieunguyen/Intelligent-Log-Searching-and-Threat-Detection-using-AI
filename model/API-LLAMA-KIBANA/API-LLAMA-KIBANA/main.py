from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import urllib.parse
import re

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def form(request: Request):
    return templates.TemplateResponse("form_result.html", {"request": request})
# Xử lý truy vấn tiếng Việt
@app.post("/search")
async def search(request: Request, prompt: str = Form(...)):
    system_prompt = "Bạn là trợ lý cho Kibana. Hãy chuyển câu hỏi tiếng Việt thành truy vấn KQL (Kibana Query Language) đúng cú pháp, chỉ trả về chuỗi KQL, không trả về bất kỳ ký tự đặc biệt, markdown hoặc giải thích nào."
    full_prompt = f"{system_prompt}\n\nNgười dùng hỏi: {prompt}"

    # Gửi prompt tới Ollama
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:latest",  # hoặc model phù hợp với RAM của bạn
            "prompt": full_prompt,
            "stream": False
        }
    )
    result = r.json()
    kql = result.get("response", "").strip()


    # Remove backticks and code block markers
    kql = re.sub(r"[`]+", "", kql)
    kql = kql.replace('KQL:', '').replace('kql:', '').strip()

    # Extract content inside {} if present (e.g. search logs {agent: "Chrome"})
    match = re.search(r"\{(.+?)\}", kql)
    if match:
        kql = match.group(1).strip()

    # Remove leading 'search', 'log', 'logs', ':', etc.
    kql = re.sub(r"^(search\s*)?(logs?|log)?\s*:?(\s*)", "", kql, flags=re.IGNORECASE).strip()

    # Final clean: remove any trailing or leading unwanted characters
    kql = kql.strip(';')

    # Chuyển hướng sang Kibana Discover với KQL
    kibana_url = f"http://localhost:5601/app/discover#/?_a=(query:(language:kuery,query:'{urllib.parse.quote(kql)}'))"
    return templates.TemplateResponse("form_result.html", {
        "request": request,
        "kql": kql,
        "kibana_url": kibana_url,
        "prompt": prompt
    })


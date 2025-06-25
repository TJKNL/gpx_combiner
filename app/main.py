from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from .gpx_utils import combine_gpx_files, fit_to_gpx_xml
import io
import datetime

app = FastAPI(title="GPX Combiner Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nAllow: /"

@app.get("/sitemap.xml")
def sitemap():
    # In a real app, you would generate this dynamically
    # and include the actual domain
    today = datetime.date.today().isoformat()
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://your-domain.com/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"""
    return Response(content=xml_content, media_type="application/xml")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_gpx(files: list[UploadFile] = File(...)):
    # Validate file types and size
    file_contents = []
    for file in files:
        if not (file.filename.lower().endswith('.gpx') or file.filename.lower().endswith('.fit')):
            return {"error": f"Invalid file type: {file.filename}"}
        content = await file.read()
        if len(content) > 2 * 1024 * 1024:  # 2MB per file limit
            return {"error": f"File too large: {file.filename}"}
        file_contents.append((file.filename, content))
    try:
        combined_gpx = combine_gpx_files(file_contents)
    except Exception as e:
        return {"error": str(e)}
    return StreamingResponse(io.BytesIO(combined_gpx.encode('utf-8')), media_type='application/gpx+xml', headers={"Content-Disposition": "attachment; filename=combined.gpx"})

@app.post("/convert-fit", response_class=PlainTextResponse)
async def convert_fit(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.fit'):
        return PlainTextResponse("Invalid file type", status_code=400)
    content = await file.read()
    try:
        gpx_xml = fit_to_gpx_xml(content)
    except Exception as e:
        return PlainTextResponse(f"Error converting FIT: {str(e)}", status_code=400)
    return gpx_xml 
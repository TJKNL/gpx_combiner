from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, PlainTextResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from .gpx_utils import combine_gpx_files, fit_to_gpx_xml
import io
import datetime
import logging
import sys
from sqlalchemy.orm import Session
from . import database

# Configure logging to output to stdout for containerized environments like Railway
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="GPX Combiner Web App")

# Add compression middleware for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

@app.get("/styles.css", response_class=PlainTextResponse)
def get_styles():
    """Serve CSS directly as fallback"""
    css_path = os.path.join(BASE_DIR, "static", "styles.css")
    try:
        with open(css_path, 'r') as f:
            css_content = f.read()
        response = PlainTextResponse(css_content, media_type="text/css")
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    except FileNotFoundError:
        return PlainTextResponse("/* CSS file not found */", status_code=404)

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    response = PlainTextResponse("User-agent: *\\nAllow: /")
    response.headers["Cache-Control"] = "public, max-age=86400"  # Cache for 1 day
    return response

@app.get("/sitemap.xml")
def sitemap(request: Request):
    """Generates a sitemap.xml using the APP_DOMAIN environment variable."""
    app_domain = os.getenv("APP_DOMAIN", f"{request.url.scheme}://{request.url.netloc}")
    today = datetime.date.today().isoformat()
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{app_domain}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"""
    response = Response(content=xml_content, media_type="application/xml")
    response.headers["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
    return response

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    app_domain = os.getenv("APP_DOMAIN", f"{request.url.scheme}://{request.url.netloc}")
    response = templates.TemplateResponse("index.html", {"request": request, "app_domain": app_domain})
    # Add performance and security headers
    response.headers["Cache-Control"] = "public, max-age=3600"  # Cache for 1 hour
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

@app.post("/upload")
async def upload_gpx(request: Request, files: list[UploadFile] = File(...), db: Session = Depends(database.get_db)):
    # Validate file types and size
    file_contents = []
    for file in files:
        if not (file.filename.lower().endswith('.gpx') or file.filename.lower().endswith('.fit')):
            return JSONResponse(status_code=400, content={"error": f"Invalid file type: {file.filename}"})
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:  # 20MB per file limit
            return JSONResponse(status_code=400, content={"error": f"File too large: {file.filename}"})
        file_contents.append((file.filename, content))
    
    try:
        combined_gpx = combine_gpx_files(file_contents)

        # Log the download after successful combination
        logger.info(f"Logging anonymous download event for IP: {request.client.host}")
        log_entry = database.DownloadLog(ip_address=None, ip_hash=database.anonymise_ip(request.client.host))
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(f"Successfully logged download event with ID: {log_entry.id}")
        
        return StreamingResponse(
            io.BytesIO(combined_gpx.encode('utf-8')),
            media_type='application/gpx+xml',
            headers={"Content-Disposition": "attachment; filename=combined.gpx"}
        )
    except Exception as e:
        logger.error(f"Failed during file combination or logging: {e}", exc_info=True)
        # Check if the exception is from the database and provide a more specific error
        if "database" in str(e).lower():
             return JSONResponse(status_code=500, content={"error": "A database error occurred."})
        return JSONResponse(status_code=400, content={"error": str(e)})

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

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    app_domain = os.getenv("APP_DOMAIN", f"{request.url.scheme}://{request.url.netloc}")
    return templates.TemplateResponse("404.html", {"request": request, "app_domain": app_domain}, status_code=404) 
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

from core.models import HealthResult
from core.github import GITHUB_TOKEN, http_client
from core.ai import GEMINI_API_KEY, GROQ_API_KEY
from core.utils import validate_username
from core import github

from routers import users, projects, ai, exports

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the global HTTP client
    github.http_client = httpx.AsyncClient(timeout=15.0, headers=github.HEADERS)
    log.info("HTTP client pool started.")
    yield
    await github.http_client.aclose()
    log.info("HTTP client pool closed.")

app = FastAPI(
    title="GitPulse: GitHub Talent Finder",
    description="Search, analyse, and export GitHub developer profiles with extreme speed and AI.",
    version="2.0.0",
    lifespan=lifespan,
)

# Eco-Friendly Optimization: Compress all outgoing data > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Include Modular Routers
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(ai.router)
app.include_router(exports.router)

# ---------------------------------------------------------------------------
# Routes — pages
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/analyze/{username}", response_class=HTMLResponse)
async def analyze_page(request: Request, username: str):
    validate_username(username)
    return templates.TemplateResponse("analyze.html", {"request": request, "username": username})

@app.get("/jd-match", response_class=HTMLResponse)
async def jd_match_page(request: Request):
    return templates.TemplateResponse("jd_match.html", {"request": request})

@app.get("/market-trends", response_class=HTMLResponse)
async def market_trends_page(request: Request):
    return templates.TemplateResponse("market_trends.html", {"request": request})

@app.get("/role-analyzer", response_class=HTMLResponse)
async def role_analyzer_page(request: Request):
    return templates.TemplateResponse("role_analyzer.html", {"request": request})

@app.get("/health", response_model=HealthResult)
async def health():
    return {
        "status": "ok",
        "github_token": bool(GITHUB_TOKEN),
        "gemini_key": bool(GEMINI_API_KEY),
        "groq_key": bool(GROQ_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

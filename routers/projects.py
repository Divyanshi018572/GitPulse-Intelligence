from typing import Optional
import asyncio
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import ORJSONResponse

from core.models import ProjectSearchResult, RigorResult
from core.cache import cache_get, cache_set
from core.github import get_github_data, GITHUB_API
from core.utils import validate_username, validate_param

router = APIRouter(default_response_class=ORJSONResponse)

@router.get("/api/search_projects", response_model=ProjectSearchResult)
async def search_projects(topic: str, language: Optional[str] = None, page: int = 1, x_github_token: str = Header(None)):
    topic = validate_param(topic, "topic")
    query = topic
    if language and language.strip():
        query += f' language:"{validate_param(language, "language")}"'

    cache_key = f"projects:{query}:{page}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    params = {"q": query, "per_page": 12, "page": page, "sort": "stars", "order": "desc"}
    res = await get_github_data(f"{GITHUB_API}/search/repositories", params=params, user_token=x_github_token)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="GitHub API error")

    data = res.json()
    projects = [
        {
            "repo_name": item.get("full_name"),
            "description": item.get("description"),
            "stars": item.get("stargazers_count"),
            "primary_language": item.get("language"),
            "topics": item.get("topics", []),
            "url": item.get("html_url"),
        }
        for item in data.get("items", [])
    ]
    result = {"total_count": data.get("total_count", 0), "projects": projects, "page": page}
    cache_set(cache_key, result, ttl=60)
    return result

@router.get("/api/project_rigor/{owner}/{repo}", response_model=RigorResult)
async def project_rigor(owner: str, repo: str, x_github_token: str = Header(None)):
    validate_username(owner)
    validate_param(repo, "repo")

    res = await get_github_data(f"{GITHUB_API}/repos/{owner}/{repo}", user_token=x_github_token)
    if res.status_code != 200:
        return {"grade": "N/A", "raw_score": 0.0}

    data = res.json()
    score = min(100.0, data.get("stargazers_count", 0) * 0.5 + data.get("forks_count", 0) * 2.0)
    grade = "🟢 A+" if score > 80 else ("🟡 B" if score > 40 else "🔴 C")
    return {"grade": grade, "raw_score": round(score, 2)}

@router.get("/api/project_preview/{owner}/{repo}")
async def project_preview(owner: str, repo: str, x_github_token: str = Header(None)):
    validate_username(owner)
    validate_param(repo, "repo")

    cached = cache_get(f"preview:{owner}/{repo}")
    if cached:
        return cached

    res = await get_github_data(f"{GITHUB_API}/repos/{owner}/{repo}", user_token=x_github_token)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not fetch repo info.")

    data      = res.json()
    homepage  = (data.get("homepage") or "").strip()
    has_pages = data.get("has_pages", False)

    site_url = None
    if homepage and homepage.startswith("http"):
        site_url = homepage
    elif has_pages:
        site_url = f"https://{owner}.github.io/{repo}/"

    result = {
        "site_url":  site_url,
        "has_pages": has_pages,
        "homepage":  homepage or None,
        "repo_url":  data.get("html_url"),
        "name":      data.get("full_name"),
    }
    cache_set(f"preview:{owner}/{repo}", result, ttl=300)
    return result

@router.get("/api/heatmap/{username}")
async def contribution_heatmap(username: str, x_github_token: str = Header(None)):
    validate_username(username)

    cached = cache_get(f"heatmap:{username}")
    if cached:
        return cached

    res = await get_github_data(
        f"{GITHUB_API}/users/{username}/events/public",
        params={"per_page": 100},
        user_token=x_github_token
    )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not fetch events.")

    events = res.json()
    from collections import defaultdict
    from datetime import datetime, timedelta

    counts: dict = defaultdict(int)
    for e in events:
        if e.get("type") == "PushEvent":
            day = (e.get("created_at") or "")[:10]
            if day:
                commits = len(e.get("payload", {}).get("commits", []))
                counts[day] += max(commits, 1)

    today = datetime.utcnow().date()
    start = today - timedelta(weeks=52)
    grid  = []
    d     = start
    while d <= today:
        ds = d.isoformat()
        grid.append({"date": ds, "count": counts.get(ds, 0)})
        d += timedelta(days=1)

    result = {"grid": grid, "total_contributions": sum(counts.values())}
    cache_set(f"heatmap:{username}", result, ttl=300)
    return result

@router.get("/api/market_trends")
async def market_trends(x_github_token: str = Header(None)):
    cached = cache_get("trends_v2")
    if cached:
        return cached

    categories = {
        "languages":    ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "Swift"],
        "frameworks":   ["React", "Next.js", "FastAPI", "Django", "Vue", "Flutter"],
        "cloud":        ["AWS", "Docker", "Kubernetes", "Terraform", "Azure", "GCP"],
        "ml_ecosystem": ["PyTorch", "TensorFlow", "Hugging Face", "LangChain", "scikit-learn"]
    }
    
    trends = {cat: {} for cat in categories}
    
    async def fetch_count(cat, topic):
        try:
            # Using broader search for more realistic "market presence" counts
            res = await get_github_data(
                f"{GITHUB_API}/search/repositories",
                params={"q": f"{topic} in:readme,description", "per_page": 1},
                user_token=x_github_token
            )
            if res.status_code == 200:
                count = res.json().get("total_count", 0)
                return cat, topic, count
        except Exception:
            pass
        return cat, topic, 0

    tasks = []
    for cat, topics in categories.items():
        for t in topics:
            tasks.append(fetch_count(cat, t))

    results = await asyncio.gather(*tasks)
    for cat, topic, count in results:
        trends[cat][topic] = count

    result = {"trends": trends, "last_updated": asyncio.get_event_loop().time()}
    cache_set("trends_v2", result, ttl=3600) # Cache for 1 hour
    return result

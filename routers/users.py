import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import ORJSONResponse

from core.models import UserSearchResult
from core.cache import cache_get, cache_set
from core.github import get_github_data, GITHUB_API, http_client
from core.utils import validate_username, validate_param

router = APIRouter(default_response_class=ORJSONResponse)

@router.get("/api/user/{username}")
async def get_user_profile(username: str, x_github_token: str = Header(None)):
    validate_username(username)

    cached = cache_get(f"user:{username}")
    if cached:
        return cached

    res = await get_github_data(f"{GITHUB_API}/users/{username}", user_token=x_github_token)
    if res.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="GitHub API error.")

    data = res.json()
    cache_set(f"user:{username}", data, ttl=300)
    return data

@router.get("/api/search", response_model=UserSearchResult)
async def search_users(
    roles: List[str] = Query(None),
    location: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    x_github_token: str = Header(None)
):
    if not roles:
        raise HTTPException(status_code=400, detail="Please select at least one role.")

    role_query = " OR ".join([f'"{r}"' for r in roles])
    query = f"{role_query} in:bio"
    if location:
        loc = validate_param(location, "location")
        query += f' location:"{loc}"'

    params: dict = {"q": query, "per_page": 12, "page": page}
    if sort in ("followers", "repositories", "joined"):
        params["sort"] = sort
        params["order"] = "desc"

    cache_key = f"search:{query}:{page}:{sort}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    res = await get_github_data(f"{GITHUB_API}/search/users", params=params, user_token=x_github_token)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail=res.json().get("message", "GitHub API error"))

    data = res.json()
    items = data.get("items", [])

    # Parallel detail fetch
    async def fetch_detail(item):
        try:
            # We use the generic wrapper mapped to the user token
            r = await get_github_data(item["url"], user_token=x_github_token)
            return r.json() if r.status_code == 200 else item
        except Exception:
            return item

    users = await asyncio.gather(*[fetch_detail(item) for item in items])
    result = {"total_count": data.get("total_count", 0), "users": list(users), "page": page}
    cache_set(cache_key, result, ttl=60)
    return result

@router.get("/api/similar_candidates/{username}")
async def similar_candidates(username: str, x_github_token: str = Header(None)):
    validate_username(username)

    res = await get_github_data(f"{GITHUB_API}/users/{username}/repos?per_page=10", user_token=x_github_token)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not fetch repos.")

    langs: dict = {}
    for r in res.json():
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    top_lang = max(langs, key=langs.get) if langs else "Python"

    s_res = await get_github_data(
        f"{GITHUB_API}/search/users",
        params={"q": f"language:{top_lang}", "per_page": 5},
        user_token=x_github_token
    )
    if s_res.status_code != 200:
        raise HTTPException(status_code=502, detail="Similar candidate search failed.")

    items = s_res.json().get("items", [])
    similar = [i for i in items if i["login"].lower() != username.lower()][:4]
    return {"top_language": top_lang, "similar_users": similar}

@router.get("/api/repos/{username}")
async def get_repos(username: str, x_github_token: str = Header(None)):
    validate_username(username)
    cached = cache_get(f"repos:{username}")
    if cached:
        return cached

    res = await get_github_data(
        f"{GITHUB_API}/users/{username}/repos",
        params={"per_page": 9, "sort": "updated"},
        user_token=x_github_token
    )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not fetch repos.")

    repos = [
        {
            "name":        r.get("name"),
            "description": r.get("description") or "",
            "stars":       r.get("stargazers_count", 0),
            "forks":       r.get("forks_count", 0),
            "language":    r.get("language") or "",
            "url":         r.get("html_url"),
            "updated":     (r.get("updated_at") or "")[:10],
        }
        for r in res.json()
    ]
    result = {"repos": repos}
    cache_set(f"repos:{username}", result, ttl=300)
    return result

@router.get("/api/skill_radar/{username}")
async def skill_radar(username: str, x_github_token: str = Header(None)):
    validate_username(username)
    cached = cache_get(f"radar:{username}")
    if cached:
        return cached

    res = await get_github_data(
        f"{GITHUB_API}/users/{username}/repos",
        params={"per_page": 50, "sort": "updated"},
        user_token=x_github_token
    )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not fetch repos for radar.")

    repos = res.json()
    scores = {"Frontend": 0, "Backend": 0, "ML/AI": 0, "Data": 0, "DevOps": 0, "Mobile": 0}
    topics_list = []

    for r in repos:
        lang = str(r.get("language") or "").lower()
        topics = [str(t).lower() for t in r.get("topics") or []]
        all_terms = [lang] + topics
        topics_list.extend(topics)

        # Basic heuristic mapping
        if any(t in all_terms for t in ["javascript", "typescript", "react", "vue", "css", "html", "svelte", "frontend"]):
            scores["Frontend"] += 1
        if any(t in all_terms for t in ["python", "java", "go", "ruby", "c#", "php", "backend", "nodejs", "express"]):
            scores["Backend"] += 1
        if any(t in all_terms for t in ["pytorch", "tensorflow", "keras", "machine-learning", "ai", "deep-learning", "nlp"]):
            scores["ML/AI"] += 1
        if any(t in all_terms for t in ["sql", "data-science", "pandas", "numpy", "database", "analytics", "hadoop"]):
            scores["Data"] += 1
        if any(t in all_terms for t in ["docker", "kubernetes", "aws", "terraform", "ci-cd", "devops", "bash"]):
            scores["DevOps"] += 1
        if any(t in all_terms for t in ["swift", "kotlin", "android", "ios", "flutter", "react-native"]):
            scores["Mobile"] += 1

    # Normalize max score to 100 for visual appeal
    max_score = max(scores.values()) if max(scores.values()) > 0 else 1
    scores = {k: int((v / max_score) * 100) for k, v in scores.items()}
    
    # Generate simple summary based on top skill
    top_skill = max(scores, key=scores.get) if max(scores.values()) > 0 else "Generalist"
    summary = f"Highly proficient in {top_skill} driven by recent project activity."

    result = {"scores": scores, "summary": summary}
    cache_set(f"radar:{username}", result, ttl=600)
    return result

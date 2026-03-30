import json
import re
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import ORJSONResponse, StreamingResponse

log = logging.getLogger(__name__)

from core.models import AISummaryResult, PersonaResult
from core.cache import cache_get, cache_set
from core.github import get_github_data, GITHUB_API, http_client
from core.utils import validate_username, validate_param
from core.ai import gemini_client, groq_client
from core import github

router = APIRouter(default_response_class=ORJSONResponse)

@router.get("/api/ai_summary/{username}")
async def ai_summary(username: str, x_github_token: str = Header(None)):
    """Uses Groq (Llama 3) for blazing fast, streamed summary generation."""
    validate_username(username)

    if not groq_client and not gemini_client:
        return {"ai_summary": "⚠️ API keys not found for AI features."}

    # Fetch data
    user_res, repos_res = await asyncio.gather(
        get_github_data(f"{GITHUB_API}/users/{username}", user_token=x_github_token),
        get_github_data(f"{GITHUB_API}/users/{username}/repos?per_page=5&sort=updated", user_token=x_github_token),
    )

    if user_res.status_code != 200:
        raise HTTPException(status_code=404, detail="Could not fetch GitHub user for AI analysis.")

    user_data = user_res.json()
    repos_data = repos_res.json() if repos_res.status_code == 200 else []

    prompt = (
        f"Analyze this GitHub developer profile and write a concise, high-impact professional summary "
        f"in exactly 2-3 sentences. Highlight key strengths and engineering potential.\n\n"
        f"Username: {user_data.get('login')}\n"
        f"Name: {user_data.get('name')}\n"
        f"Bio: {user_data.get('bio')}\n"
        f"Location: {user_data.get('location')}\n"
        f"Public repos: {user_data.get('public_repos')}\n"
        f"Followers: {user_data.get('followers')}\n"
        f"Recent projects: {', '.join(r.get('name', '') for r in repos_data)}"
    )

    # Groq Streaming logic
    if groq_client:
        async def stream_groq():
            try:
                stream = await groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                yield " [Groq Error - Rate Limited or Down]"
        
        return StreamingResponse(stream_groq(), media_type="text/plain")
        
    # Gemini Fallback Backup
    elif gemini_client:
        try:
            response = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            summary = response.text.strip()
            return {"ai_summary": summary}
        except Exception:
            return {"ai_summary": "AI feature temporarily unavailable."}

@router.get("/api/analyze_persona/{username}", response_model=PersonaResult)
async def analyze_persona(username: str, x_github_token: str = Header(None)):
    validate_username(username)

    cached = cache_get(f"persona:{username}")
    if cached:
        return cached

    res = await get_github_data(f"{GITHUB_API}/users/{username}/events/public", user_token=x_github_token)
    if res.status_code != 200:
        return {"persona": "💻 The Coder", "icon": "💻"}

    events = res.json()
    commits = [
        msg.lower()
        for e in events
        if e.get("type") == "PushEvent"
        for msg in (c.get("message", "") for c in e["payload"].get("commits", []))
    ]

    if not commits:
        return {"persona": "💻 The Coder", "icon": "💻"}

    text = " ".join(commits)
    counts = {
        "exterminator": len(re.findall(r"\b(fix|patch|bug|resolve|issue)\b", text)),
        "documenter":   len(re.findall(r"\b(doc|docs|readme|clean|format)\b", text)),
        "architect":    len(re.findall(r"\b(init|structure|arch|refactor|setup)\b", text)),
    }
    shipper_count = len(commits)

    if shipper_count > 20:
        result = {"persona": "🚀 The Shipper", "icon": "🚀"}
    elif max(counts.values()) == 0:
        result = {"persona": "💻 The Coder", "icon": "💻"}
    else:
        personas = {
            "exterminator": "🐛 The Exterminator",
            "documenter":   "📚 The Documenter",
            "architect":    "🏛️ The Architect",
        }
        top = max(counts, key=counts.get)
        result = {"persona": personas[top], "icon": personas[top][:2]}

    cache_set(f"persona:{username}", result, ttl=300)
    return result

@router.get("/api/draft_email/{username}")
async def draft_email(username: str, x_github_token: str = Header(None)):
    validate_username(username)

    if not groq_client and not gemini_client:
        return {"email": "⚠️ API keys not set for email drafting."}

    cached = cache_get(f"email:{username}")
    if cached:
        return {"email": cached}

    user_res, repos_res = await asyncio.gather(
        get_github_data(f"{GITHUB_API}/users/{username}", user_token=x_github_token),
        get_github_data(f"{GITHUB_API}/users/{username}/repos?per_page=5&sort=updated", user_token=x_github_token),
    )
    if user_res.status_code != 200:
        raise HTTPException(status_code=404, detail="User not found.")

    u = user_res.json()
    repos = repos_res.json() if repos_res.status_code == 200 else []
    repo_names = ", ".join(r.get("name", "") for r in repos[:4])

    prompt = (
        f"Write a short, professional recruiter cold email to a developer for a software engineering role. "
        f"Personalise it using their real GitHub data below. Keep it under 150 words. "
        f"Do not use placeholders like [Company Name] — write it as if from a tech startup.\n\n"
        f"Developer: {u.get('name') or u.get('login')}\n"
        f"Bio: {u.get('bio') or 'Not provided'}\n"
        f"Location: {u.get('location') or 'Not provided'}\n"
        f"Recent projects: {repo_names or 'Not available'}\n"
        f"GitHub: {u.get('html_url')}"
    )

    try:
        # Use Groq for speed!
        if groq_client:
            response = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile"
            )
            email_text = response.choices[0].message.content.strip()
        else:
            response = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            email_text = response.text.strip()
            
        cache_set(f"email:{username}", email_text, ttl=600)
        return {"email": email_text}
    except Exception as e:
        log.error("AI email draft error for %s: %s", username, str(e))
        raise HTTPException(status_code=500, detail="Email draft failed.")

@router.get("/api/architecture/{owner}/{repo}")
async def project_architecture(owner: str, repo: str, x_github_token: str = Header(None)):
    validate_username(owner)
    validate_param(repo, "repo")

    if not gemini_client:
        return {"error": "GEMINI_API_KEY not set."}

    cached = cache_get(f"arch:{owner}/{repo}")
    if cached:
        return cached

    repo_res, readme_res, langs_res = await asyncio.gather(
        get_github_data(f"{GITHUB_API}/repos/{owner}/{repo}", user_token=x_github_token),
        github.http_client.get(f"{GITHUB_API}/repos/{owner}/{repo}/readme",
                        headers={"Accept": "application/vnd.github.raw"}),
        get_github_data(f"{GITHUB_API}/repos/{owner}/{repo}/languages", user_token=x_github_token),
    )

    if repo_res.status_code != 200:
        raise HTTPException(status_code=404, detail="Repo not found.")

    repo_data   = repo_res.json()
    readme_text = readme_res.text[:3000] if readme_res.status_code == 200 else "Not available"
    languages   = list((langs_res.json() if langs_res.status_code == 200 else {}).keys())

    prompt = f"""
You are a senior software architect. Analyse the following GitHub repository and return a detailed JSON object describing its project pipeline and architecture.
Identify the primary components and group them into logical stages (e.g. Data Ingestion, Processing, Training, Backend, Frontend, Infrastructure).

Repository: {repo_data.get('full_name')}
Description: {repo_data.get('description') or 'Not provided'}
Primary language: {repo_data.get('language') or 'Unknown'}
All languages: {', '.join(languages) or 'Unknown'}
README (first 3000 chars):
{readme_text}

Return ONLY a valid JSON object matching this schema:
{{
  "stages": [
    {{
      "nodes": [
        {{
          "type": "input", // or "process", "model", "output", "infra"
          "icon": "📝",
          "layer": "Data Source",
          "title": "Module name",
          "description": "Short explanation",
          "tools": ["Python", "Docker"]
        }}
      ]
    }}
  ],
  "summary": "High level architecture overview.",
  "tech_stack": ["Python", "Docker"]
}}
"""
    try:
        if groq_client:
            response = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)
        else:
            response  = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            raw       = response.text.strip()
            raw       = raw.replace("```json", "").replace("```", "").strip()
            result    = json.loads(raw)
            
        cache_set(f"arch:{owner}/{repo}", result, ttl=600)
        return result
    except Exception as e:
        log.error("Architecture AI error for %s/%s: %s", owner, repo, str(e))
        fallback = {"stages": [], "summary": "Architecture analysis could not be completed. The AI may have struggled to parse the repository data.", "tech_stack": languages}
        return fallback

@router.post("/api/jd_match")
async def jd_match(payload: dict, x_github_token: str = Header(None)):
    jd       = (payload.get("jd") or "").strip()
    roles    = payload.get("roles", ["software engineer"])
    location = payload.get("location", "")

    if not jd:
        raise HTTPException(status_code=400, detail="Job description is required.")
    if not gemini_client:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not set.")

    role_query = " OR ".join([f'"{r}"' for r in roles[:4]])
    query = f"{role_query} in:bio"
    if location:
        query += f' location:"{location}"'

    log.info("Starting JD Match for: %s", jd[:50])
    
    # Cache Check
    cache_key = f"jd_match:{jd}:{','.join(roles)}:{location}"
    cached = cache_get(cache_key)
    if cached:
        log.info("Returning CACHED JD Match results.")
        return cached

    res = await get_github_data(f"{GITHUB_API}/search/users", params={"q": query, "per_page": 8, "sort": "followers", "order": "desc"}, user_token=x_github_token)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="GitHub search failed.")

    items = res.json().get("items", [])
    log.info("Found %d items, downloading user details concurrently...", len(items))

    async def fetch_user(item):
        try:
            r = await get_github_data(item["url"], user_token=x_github_token)
            return r.json() if r.status_code == 200 else item
        except Exception:
            return item

    users = await asyncio.gather(*[fetch_user(i) for i in items])
    log.info("Users downloaded. Generating candidates text...")
    candidates_text = "\n".join([f"- {u.get('login')}: bio={u.get('bio')}" for u in users])

    prompt = f"You are a tech recruiter. Score 0-100 against JD.\nJD: {jd[:2000]}\nCANDIDATES: {candidates_text}\nReturn ONLY a valid JSON object matching this schema: {{\"results\": [{{\"login\":\"...\", \"score\":<int>, \"match_reason\":\"...\", \"gap\":\"...\"}}] }}"

    try:
        log.info("Sending prompt to AI...")
        if groq_client:
            log.info("Using Groq API...")
            response = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            log.info("Groq raw completion received. Length: %d", len(raw))
            parsed = json.loads(raw)
            scores = parsed.get("results", []) if isinstance(parsed, dict) else parsed
        else:
            log.info("Using Gemini API...")
            response = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            raw      = response.text.strip().replace("```json","").replace("```","").strip()
            log.info("Gemini raw completion received. Length: %d", len(raw))
            parsed   = json.loads(raw)
            scores   = parsed.get("results", []) if isinstance(parsed, dict) else parsed
            
        score_map = {s["login"]: s for s in scores if isinstance(s, dict) and "login" in s}
        
        results = []
        for u in users:
            login = u.get("login","")
            s = score_map.get(login, {"score":0,"match_reason":"","gap":""})
            results.append({**u, "ai_score": s.get("score",0), "match_reason": s.get("match_reason",""), "gap": s.get("gap","")})
        results.sort(key=lambda x: x["ai_score"], reverse=True)
        final_res = {"candidates": results, "total": len(results)}
        cache_set(cache_key, final_res, ttl=3600)
        return final_res
    except Exception as e:
        log.error("JD Matching error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"JD matching failed: {e}")

@router.post("/api/analyze_for_role")
async def analyze_for_role(payload: dict, x_github_token: str = Header(None)):
    url = (payload.get("url") or "").strip()
    role = (payload.get("role") or "").strip()
    stack = (payload.get("stack") or "").strip()

    if not url or not role:
        raise HTTPException(status_code=400, detail="URL and role are required.")
    
    # Check Cache
    cache_key = f"role_analysis:{url}:{role}:{stack}"
    cached = cache_get(cache_key)
    if cached:
        log.info("Returning CACHED role analysis for %s", url)
        return cached

    # Parse URL 
    url_tag = url.rstrip("/")
    parts = url_tag.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
    
    if len(parts) == 0 or not parts[0]:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL.")
    
    owner = parts[0]
    repo = parts[1] if len(parts) > 1 else None

    # Fetch data
    context = ""
    if repo:
        repo_res, readme_res = await asyncio.gather(
            github.get_github_data(f"{GITHUB_API}/repos/{owner}/{repo}", user_token=x_github_token),
            github.http_client.get(f"{GITHUB_API}/repos/{owner}/{repo}/readme", headers={"Accept": "application/vnd.github.raw"})
        )
        if repo_res.status_code != 200:
            raise HTTPException(status_code=404, detail="Repository not found.")
        repo_data = repo_res.json()
        readme = readme_res.text[:3000] if readme_res.status_code == 200 else "No README available"
        context = f"Repository: {repo_data.get('full_name')}\nDescription: {repo_data.get('description')}\nLanguage: {repo_data.get('language')}\nStars: {repo_data.get('stargazers_count')}\nREADME snippet:\n{readme}"
    else:
        user_res, repos_res = await asyncio.gather(
            github.get_github_data(f"{GITHUB_API}/users/{owner}", user_token=x_github_token),
            github.get_github_data(f"{GITHUB_API}/users/{owner}/repos?per_page=10&sort=updated", user_token=x_github_token)
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found.")
        user_data = user_res.json()
        repos_data = repos_res.json() if repos_res.status_code == 200 else []
        repo_names = ", ".join([r.get('name', '') for r in repos_data])
        context = f"Developer: {user_data.get('login')}\nBio: {user_data.get('bio')}\nPublic Repos: {user_data.get('public_repos')}\nFollowers: {user_data.get('followers')}\nRecent Repos: {repo_names}"

    stack_context = f"\nTarget Company Stack: {stack}" if stack else ""
    
    prompt = f"""
You are an expert technical recruiter and senior engineering manager.
Analyze the following GitHub {'repository' if repo else 'profile'} to determine its professional score specifically for the role of '{role}'.
{stack_context}

Focus on:
1. Technical depth and original contributions.
2. Alignment with '{role}' and the target company stack.
3. Code quality and documentation signals.

Return ONLY a valid JSON object matching this schema:
{{
  "score": <int between 0 and 100>,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "summary": "High-level professional assessment"
}}
"""
    
    try:
        log.info("Sending role analysis prompt to AI for %s...", url)
        if groq_client:
            response = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
        else:
            response = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            raw = response.text.strip().replace("```json","").replace("```","").strip()
            parsed = json.loads(raw)
        
        cache_set(cache_key, parsed, ttl=86400) # Cache for 24 hours
        return parsed
    except Exception as e:
        log.error("Role Analysis Matching error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

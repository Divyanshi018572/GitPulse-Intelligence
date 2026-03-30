import os
import logging
import asyncio
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# We will initialize this in the main.py lifespan
http_client: httpx.AsyncClient = None  # type: ignore

async def get_github_data(url: str, params: dict = None, user_token: str = None):
    """
    Core function to fetch data from GitHub.
    It automatically handles:
    1. BYOK (Bring Your Own Key) if the user provides one in the frontend.
    2. Automatic retries if hitting a 429 Rate Limit.
    """
    headers = HEADERS.copy()
    
    # Priority 1: User's provided token (BYOK)
    # Priority 2: Server's .env token
    token_to_use = user_token if user_token else GITHUB_TOKEN
    if token_to_use:
        headers["Authorization"] = f"Bearer {token_to_use}"
        
    for attempt in range(3):
        res = await http_client.get(url, params=params, headers=headers)
        
        if res.status_code == 429:
            log.warning(f"GitHub Rate limit hit. Waiting 2 seconds (Attempt {attempt + 1}/3)")
            await asyncio.sleep(2)
            continue
            
        return res
        
    raise HTTPException(status_code=429, detail="GitHub API rate limit reached. Please add your own token in Settings.")

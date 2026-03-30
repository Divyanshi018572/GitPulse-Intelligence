import re
from fastapi import HTTPException

_SAFE_USERNAME = re.compile(r"^[a-zA-Z0-9\-]{1,39}$")
_SAFE_PARAM    = re.compile(r"^[\w\s\-\.]{1,80}$")

def validate_username(username: str) -> str:
    """Raises 400 if username looks unsafe."""
    if not _SAFE_USERNAME.match(username):
        raise HTTPException(status_code=400, detail="Invalid GitHub username.")
    return username

def validate_param(value: str, field: str = "parameter") -> str:
    if not _SAFE_PARAM.match(value.strip()):
        raise HTTPException(status_code=400, detail=f"Invalid {field}.")
    return value.strip()

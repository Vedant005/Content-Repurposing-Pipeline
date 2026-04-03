import re
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

SESSION_COOKIE = "rsid"          # repurpose session id
SESSION_MAX_AGE = 60 * 60 * 24 * 90  # 90 days
SESSION_ID_RE = re.compile(r'^[a-f0-9]{32}$') 

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        raw = request.cookies.get(SESSION_COOKIE)
        session_id = raw if raw and SESSION_ID_RE.match(raw) else uuid.uuid4().hex
        if not session_id:
            session_id = uuid.uuid4().hex  

        request.state.session_id = session_id

        response = await call_next(request)

        if not request.cookies.get(SESSION_COOKIE):
            response.set_cookie(
                key=SESSION_COOKIE,
                value=session_id,
                max_age=SESSION_MAX_AGE,
                httponly=True,   
                samesite="none",  
                secure=True,
            )
        return response
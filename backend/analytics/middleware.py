from .tracking import SESSION_COOKIE, new_session_id


class SessionIdMiddleware:
    """Anonymous session cookie `tk_sid` (UUID, one year)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        sid = request.COOKIES.get(SESSION_COOKIE)
        created = not sid
        if created:
            sid = new_session_id()
        request.tk_sid = sid
        response = self.get_response(request)
        if created:
            response.set_cookie(
                SESSION_COOKIE, sid, max_age=365 * 24 * 3600, samesite="Lax", httponly=True
            )
        return response

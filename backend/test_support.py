from http.cookies import SimpleCookie
from fastapi.testclient import TestClient


class BrowserClient(TestClient):
    """Existing API regression tests send the same cookies/CSRF as the UI."""
    def request(self, method, url, **kwargs):
        if method.upper() not in {"GET", "HEAD", "OPTIONS"} and str(url) != "/billing/webhook":
            headers = dict(kwargs.get("headers") or {})
            if "Cookie" in headers:
                cookies = SimpleCookie(headers["Cookie"])
                csrf = cookies["mh_csrf"].value if "mh_csrf" in cookies else ""
            else:
                csrf = self.get("/auth/csrf").json()["csrf"]
            headers.setdefault("X-CSRF-Token", csrf)
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def session_headers(client):
    csrf = client.cookies.get("mh_csrf")
    session = client.cookies.get("mh_session")
    return {"Cookie": f"mh_session={session}; mh_csrf={csrf}", "X-CSRF-Token": csrf}

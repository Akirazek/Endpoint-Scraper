"""Utility functions."""

from urllib.parse import urlparse


def categorize(url):
    """Categorize URL based on its path."""
    path = urlparse(url).path.lower()
    if any(x in path for x in ["/api/", "/v1/", "/v2/", "/graphql", ".json", "/rest/"]):
        return "api"
    if any(x in path for x in ["/profile", "/user", "/account", "/me/", "/member"]):
        return "user"
    if any(x in path for x in ["/search", "/find", "/query", "/filter", "/browse"]):
        return "search"
    if any(
        x in path for x in ["/login", "/signup", "/register", "/auth", "/oauth", "/logout"]
    ):
        return "auth"
    if any(x in path for x in ["/admin", "/dashboard", "/panel", "/manage", "/cms"]):
        return "admin"
    if any(
        x in path for x in ["/download", "/uploads", "/files", "/mods", "/submissions"]
    ):
        return "content"
    return "page"

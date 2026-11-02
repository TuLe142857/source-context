from app.route_extractor.normalizer import canonicalize_url_path


def is_segment_match(call_path: str, route_path: str) -> bool:
    """Segment-wise comparison between client call path and server route template.

    Example:
        - '/api/v1/products/prod_123' matches '/api/v1/products/{}' -> True
        - '/api/v1/users/usr_1/status' matches '/api/v1/users/{}/status' -> True
        - '/api/v1/orders' matches '/api/v1/products' -> False
    """
    c_norm = canonicalize_url_path(call_path)
    r_norm = canonicalize_url_path(route_path)

    c_segs = [s for s in c_norm.strip("/").split("/") if s]
    r_segs = [s for s in r_norm.strip("/").split("/") if s]

    if len(c_segs) != len(r_segs):
        return False

    for c, r in zip(c_segs, r_segs):
        if r == "{}" or c == "{}":
            continue
        if c != r:
            return False
    return True


def is_method_match(call_method: str, route_method: str) -> bool:
    """Check if caller's HTTP method matches the route's method."""
    c = (call_method or "ANY").upper()
    r = (route_method or "ANY").upper()
    return c == r or c == "ANY" or r == "ANY"


def determine_rule_level(call_path: str, route_path: str) -> str:
    """Categorize the difficulty level of the matched cross-repo link."""
    c_norm = canonicalize_url_path(call_path)
    r_norm = canonicalize_url_path(route_path)

    if "{}" not in c_norm and "{}" not in r_norm:
        return "exact_match"
    return "param_pattern"

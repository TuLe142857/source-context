from app.cross_repo.matcher import is_segment_match, is_method_match, determine_rule_level


def test_is_segment_match_exact():
    assert is_segment_match("/api/v1/orders", "/api/v1/orders") is True
    assert is_segment_match("/api/v1/orders/", "/api/v1/orders") is True
    assert is_segment_match("/api/v1/orders", "/api/v1/products") is False


def test_is_segment_match_parameters():
    # Call with ID argument matches parameterized route template
    assert is_segment_match("/api/v1/billing/inv_9988", "/api/v1/billing/{}") is True
    assert is_segment_match("/api/v1/billing/{}", "/api/v1/billing/{invoice_id}") is True
    assert is_segment_match("/api/v1/users/42/status", "/api/v1/users/{user_id}/status") is True
    assert is_segment_match("/api/v1/users/42/status", "/api/v1/users/{}/status") is True


def test_is_segment_match_length_mismatch():
    assert is_segment_match("/api/v1/orders", "/api/v1/orders/items") is False
    assert is_segment_match("/api/v1/orders/123", "/api/v1/orders") is False


def test_is_method_match():
    assert is_method_match("GET", "GET") is True
    assert is_method_match("get", "GET") is True
    assert is_method_match("ANY", "POST") is True
    assert is_method_match("POST", "ANY") is True
    assert is_method_match("GET", "POST") is False


def test_determine_rule_level():
    assert determine_rule_level("/api/v1/orders", "/api/v1/orders") == "exact_match"
    assert determine_rule_level("/api/v1/billing/{}", "/api/v1/billing/inv_1") == "param_pattern"
    assert determine_rule_level("/api/v1/products/123", "/api/v1/products/{id}") == "param_pattern"

from app.engine.graph.model import ApiCallNodeModel, ApiEndpointNodeModel

from .api_handler import ApiHandler


class SseApiHandler(ApiHandler):
    """Server-sent events. Placeholder: no model classes nor detectors yet (see the plan, §11.4)."""

    def match_api(
        self, endpoint: ApiEndpointNodeModel, call: ApiCallNodeModel
    ) -> tuple[str, float] | None:
        return None

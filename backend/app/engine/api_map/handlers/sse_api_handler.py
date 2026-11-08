from .api_handler import ApiHandler

class SseApiHandler(ApiHandler):
    def match_api(self, api_endpoint, api_call) -> float:
        return 0
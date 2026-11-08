from .api_handler import ApiHandler

class WebsocketApiHandler(ApiHandler):
    def match_api(self, api_endpoint, api_call) -> float:
        return 0
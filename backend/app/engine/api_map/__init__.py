"""API map: endpoints a project serves, calls it makes, and which call reaches which endpoint.

Design and algorithms: plans/api_map_detection_plan.md.
"""

from .api_registry import ApiRegistry as ApiRegistry
from .build import build_api_map_for_project as build_api_map_for_project
from .build import detect_apis as detect_apis
from .context import ApiMapContext as ApiMapContext
from .handlers import ApiHandler as ApiHandler
from .link import link_api_map as link_api_map

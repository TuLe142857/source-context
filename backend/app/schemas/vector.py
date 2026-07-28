from pydantic import BaseModel


class SearchReponse(BaseModel):
    source_text: str
    function_name: str
    file_path: str


class SearchRequest(BaseModel):
    query: str
    repository_id: int
    branch_name: str

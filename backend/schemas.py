from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.preprocessing.normalizer import normalize_text

Language = Literal["en", "hi", "te", "ta"]
Method = Literal["tfidf", "bm25", "semantic"]
Strategy = Literal["direct", "translate"]


class RequestSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["auto", "en", "hi", "te", "ta"] = "auto"
    retrieval_method: Method = "semantic"
    multilingual_strategy: Strategy = "translate"
    top_k: int = Field(default=3, ge=1, le=5, strict=True)


class AskRequest(RequestSettings):
    query: str = Field(min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def meaningful_question(cls, value: str) -> str:
        if not normalize_text(value):
            raise ValueError("Please enter a question.")
        return value.strip()

    @model_validator(mode="after")
    def compatible_settings(self):
        if self.multilingual_strategy == "direct" and self.retrieval_method != "semantic":
            raise ValueError("Direct multilingual retrieval requires Semantic. Choose translate-then-retrieve for TF-IDF or BM25.")
        return self


class AskResponse(BaseModel):
    # Names match src.qa.response_generator.build_response exactly.
    query: str
    detected_language: Language
    selected_language: Language
    retrieval_strategy: str
    english_query: str
    answer: str
    translated_answer: str
    category: str
    source: str
    source_url: str
    similarity_score: float = Field(allow_inf_nan=False)
    related_questions: list[str]
    document_id: str
    translation_warning: str | None = None
    status: Literal['success'] = 'success'
    retrieved_question: str = ''
    retrieval_query: str = ''
    validation: dict[str, Any] = Field(default_factory=dict)


class AbstentionResponse(BaseModel):
    status: Literal['out_of_scope', 'insufficient_evidence', 'clarification_needed']
    query: str
    selected_language: Language
    detected_language: Language
    reason: str
    message: str
    validation: dict[str, Any] = Field(default_factory=dict)
    candidate: dict[str, Any] | None = None


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=4000)
    language: Literal['auto', 'en', 'hi', 'te', 'ta'] = 'auto'
    top_k: int = Field(default=3, ge=1, le=5, strict=True)

    @field_validator('query')
    @classmethod
    def meaningful_question(cls, value):
        return AskRequest.meaningful_question(value)


class ComparisonResponse(BaseModel):
    query: str
    selected_language: Language
    retrieval_method: Literal['semantic'] = 'semantic'
    top_k: int
    equivalent: bool = False
    explanation: str
    direct: AskResponse | AbstentionResponse
    translate: AskResponse | AbstentionResponse


class Choice(BaseModel):
    value: str
    label: str


class OptionsResponse(BaseModel):
    languages: list[Choice]
    retrieval_methods: list[Choice]
    multilingual_strategies: list[Choice]
    defaults: RequestSettings
    top_k_min: int = 1
    top_k_max: int = 5
    direct_requires: Literal["semantic"] = "semantic"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    code: str
    message: str

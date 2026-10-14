from pydantic import BaseModel, ConfigDict, Field, field_validator


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    appliance: str | None = None
    question: str = Field(min_length=1, max_length=2000)

    @field_validator('question')
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError('Please enter a question.')
        return value.strip()


class Source(BaseModel):
    filename: str
    page: int
    appliance: str
    model: str
    text: str
    kind: str = 'semantic match'
    chunk_ids: list[str] = Field(default_factory=list)
    url: str


class Answer(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    status: str = 'answered'

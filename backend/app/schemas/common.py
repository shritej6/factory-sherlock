from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Base for response models: reads ORM attributes and forbids unknown fields on input."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Shape of every error body produced by ``app.api.errors``."""

    error: str
    message: str
    details: dict[str, object] = {}
    request_id: str

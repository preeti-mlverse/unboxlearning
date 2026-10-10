"""The lesson block registry. A block is {block_type, config}; each type has a schema here and a renderer in the
web app (apps/web/src/components/blocks). Foundation ships `text` and `image`. Later waves register more types
(explanation, process_flow, mcq, simulation, tutor…) without changing the tables or the editor's plumbing."""
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from ..errors import bad_request


class TextBlock(BaseModel):
    heading: str | None = Field(default=None, max_length=200)
    # light Markdown: paragraphs, **bold**, *italic*, lists, links. Rendered safely (no raw HTML) by the app.
    body: str = Field(default="", max_length=20000)


class ImageBlock(BaseModel):
    document_id: str = Field(min_length=4, max_length=40)  # an uploaded image (purpose=asset) in the same workspace
    alt: str = Field(min_length=1, max_length=300, description="Describes the image for people who can't see it")
    caption: str | None = Field(default=None, max_length=300)
    size: Literal["small", "medium", "full"] = "full"

    @field_validator("alt")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("Describe the image")
        return v.strip()


REGISTRY: dict[str, type[BaseModel]] = {"text": TextBlock, "image": ImageBlock}


def validate(block_type: str, config: dict) -> dict:
    model = REGISTRY.get(block_type)
    if model is None:
        raise bad_request("UNKNOWN_BLOCK_TYPE", f"'{block_type}' isn't a supported block type.",
                          {"supported": sorted(REGISTRY)})
    try:
        return model.model_validate(config).model_dump()
    except ValidationError as e:
        fields = {".".join(str(p) for p in err["loc"]) or "config": err["msg"].removeprefix("Value error, ")
                  for err in e.errors()}
        raise bad_request("INVALID_BLOCK", "This block has fields that need attention.", {"fields": fields})


def is_empty(block_type: str, config: dict) -> bool:
    if block_type == "text":
        return not (config.get("body") or "").strip() and not (config.get("heading") or "").strip()
    return False

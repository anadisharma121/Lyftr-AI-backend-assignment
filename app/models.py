from pydantic import BaseModel, Field

INIT_SCRIPT = """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    from_msisdn TEXT NOT NULL,
    to_msisdn TEXT NOT NULL,
    ts TEXT NOT NULL,
    text TEXT,
    created_at TEXT NOT NULL
);
"""


class WebhookPayload(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from", pattern=r"^\+\d+$")
    to: str = Field(..., pattern=r"^\+\d+$")
    ts: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    text: str = Field(default="", max_length=4096)
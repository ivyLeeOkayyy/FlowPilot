from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"] = "ok"
    service: Literal["flowpilot"] = "flowpilot"
    version: Literal["0.1.0"] = "0.1.0"

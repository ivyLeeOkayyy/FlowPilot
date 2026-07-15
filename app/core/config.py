from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_name: str = "flowpilot"
    app_title: str = "FlowPilot"
    app_version: str = "0.1.0"
    app_description: str = (
        "FlowPilot is a lightweight AI-assisted automation builder created as a "
        "hackathon demo."
    )
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int = 15


settings = Settings()

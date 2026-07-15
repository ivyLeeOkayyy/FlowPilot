from app.core.config import llm_config_diagnostics


def main() -> None:
    diagnostics = llm_config_diagnostics()
    print(f"configured LLM provider: {diagnostics['llm_provider']}")
    print(f"DeepSeek base URL: {diagnostics['deepseek_base_url']}")
    print(f"DeepSeek model: {diagnostics['deepseek_model']}")
    print(f"timeout seconds: {diagnostics['llm_timeout_seconds']}")
    print(
        "DeepSeek API key configured: "
        f"{diagnostics['deepseek_api_key_configured']}"
    )


if __name__ == "__main__":
    main()

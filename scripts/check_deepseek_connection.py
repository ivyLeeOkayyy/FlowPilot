from app.services.providers import DeepSeekProvider, GenerationProviderError


def main() -> None:
    provider = DeepSeekProvider()
    prompt = (
        "Create a simple workflow that starts when a customer requests an "
        "appointment, asks for their preferred date, and ends after recording "
        "the request."
    )

    print(f"endpoint: {provider.endpoint}")
    print(f"requested model: {provider.model_name}")

    try:
        provider.generate(prompt)
        error_code = None
        error_message = None
    except GenerationProviderError as exc:
        error_code = exc.code
        error_message = exc.message
    except Exception as exc:  # defensive diagnostic only
        error_code = "UNEXPECTED_ERROR"
        error_message = exc.__class__.__name__

    diagnostics = provider.last_diagnostics
    print(f"returned provider model: {diagnostics.get('provider_model')}")
    print(f"HTTP status: {diagnostics.get('http_status')}")
    print(f"choices present: {diagnostics.get('choices_present')}")
    print(f"message present: {diagnostics.get('message_present')}")
    print(f"content present: {diagnostics.get('content_present')}")
    print(f"content parsed as JSON: {diagnostics.get('content_json_valid')}")
    print(f"content validated as AutomationFlow: {diagnostics.get('automation_flow_valid')}")
    print(f"sanitized error code: {error_code or diagnostics.get('error_code')}")
    print(f"sanitized error detail: {error_message or diagnostics.get('error_message')}")


if __name__ == "__main__":
    main()

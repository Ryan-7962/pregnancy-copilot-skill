import sys

from pregnancy_copilot.llm import CommandLLMProvider, LLMProvider, NullLLMProvider


def test_null_llm_provider_keeps_model_binding_external():
    provider: LLMProvider = NullLLMProvider()

    response = provider.generate("hello")

    assert response == ""
    assert not hasattr(provider, "model")


def test_command_llm_provider_sends_prompt_to_stdin_and_returns_stdout():
    provider = CommandLLMProvider(
        [
            sys.executable,
            "-c",
            "import sys; prompt=sys.stdin.read(); print('seen:' + prompt)",
        ]
    )

    assert provider.generate("hello").strip() == "seen:hello"


def test_command_llm_provider_returns_empty_on_failure():
    provider = CommandLLMProvider([sys.executable, "-c", "raise SystemExit(2)"])

    assert provider.generate("hello") == ""

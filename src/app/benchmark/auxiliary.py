"""Route original OpenAI judge SDK clients through the shared provider owner."""

import ssl
from contextlib import contextmanager

import httpx


@contextmanager
def judge_clients(context):
    import openai

    original = {name: getattr(openai, name) for name in ("OpenAI", "AsyncOpenAI")}
    clients = []

    def create(name, asynchronous, **kwargs):
        if any(k in kwargs for k in ("api_key", "base_url", "http_client", "max_retries")):
            raise RuntimeError("UNENROLLED_JUDGE_CLIENT_OVERRIDE")
        transport = (httpx.AsyncClient if asynchronous else httpx.Client)(
            verify=ssl.create_default_context(cafile=context["ca_file"]),
            trust_env=False,
            timeout=120,
        )
        client = original[name](
            api_key=context["judge_token"],
            base_url=context["provider_url"] + "/v1",
            max_retries=0,
            http_client=transport,
            **kwargs,
        )
        clients.append((client, asynchronous))
        return client

    openai.OpenAI = lambda **kwargs: create("OpenAI", False, **kwargs)
    openai.AsyncOpenAI = lambda **kwargs: create("AsyncOpenAI", True, **kwargs)
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(openai, name, value)
        for client, asynchronous in clients:
            if not asynchronous:
                client.close()
        # Async judge clients are scoped to the worker process. Their owning
        # async loop closes on task completion; never share clients across tasks.

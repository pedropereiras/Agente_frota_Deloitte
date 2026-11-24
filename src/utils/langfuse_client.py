import os
from typing import Any
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()


def get_langfuse_handler():
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    from copy import deepcopy
    from langchain_core.outputs import LLMResult
    from langfuse.langchain import CallbackHandler

    class ApplicationCallbackHandler(CallbackHandler):
        @classmethod
        def _sanitize_trace_value(cls, value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    key: cls._sanitize_trace_value(item)
                    for key, item in value.items()
                    if key != "reasoning_content"
                }
            if isinstance(value, list):
                return [cls._sanitize_trace_value(item) for item in value]
            if isinstance(value, tuple):
                return tuple(cls._sanitize_trace_value(item) for item in value)

            additional_kwargs = getattr(value, "additional_kwargs", None)
            if isinstance(additional_kwargs, dict):
                sanitized_kwargs = cls._sanitize_trace_value(additional_kwargs)
                if sanitized_kwargs != additional_kwargs:
                    value = deepcopy(value)
                    value.additional_kwargs = sanitized_kwargs
            return value

        def on_chain_start(
            self,
            serialized: dict[str, Any] | None,
            inputs: Any,
            *,
            run_id: UUID,
            parent_run_id: UUID | None = None,
            tags: list[str] | None = None,
            metadata: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> Any:
            return super().on_chain_start(
                serialized,
                self._sanitize_trace_value(inputs),
                run_id=run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=metadata,
                **kwargs,
            )

        def on_chain_end(
            self,
            outputs: dict[str, Any],
            *,
            run_id: UUID,
            parent_run_id: UUID | None = None,
            **kwargs: Any,
        ) -> Any:
            outputs = self._sanitize_trace_value(outputs)
            if parent_run_id is None:
                outputs = (
                    {"resultado": outputs["resultado"]}
                    if isinstance(outputs, dict) and "resultado" in outputs
                    else {"output_keys": sorted(outputs)}
                )
            return super().on_chain_end(
                outputs,
                run_id=run_id,
                parent_run_id=parent_run_id,
                **kwargs,
            )

        def on_chat_model_start(
            self,
            serialized: dict[str, Any] | None,
            messages: list[list[Any]],
            *,
            run_id: UUID,
            parent_run_id: UUID | None = None,
            tags: list[str] | None = None,
            metadata: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> Any:
            return super().on_chat_model_start(
                serialized,
                self._sanitize_trace_value(messages),
                run_id=run_id,
                parent_run_id=parent_run_id,
                tags=tags,
                metadata=metadata,
                **kwargs,
            )

        def on_llm_end(
            self,
            response: LLMResult,
            *,
            run_id: UUID,
            parent_run_id: UUID | None = None,
            **kwargs: Any,
        ) -> Any:
            response_for_trace = deepcopy(response)
            for generations in response_for_trace.generations:
                for generation in generations:
                    message = getattr(generation, "message", None)
                    additional_kwargs = getattr(message, "additional_kwargs", None)
                    if isinstance(additional_kwargs, dict):
                        additional_kwargs.pop("reasoning_content", None)
            return super().on_llm_end(
                response_for_trace,
                run_id=run_id,
                parent_run_id=parent_run_id,
                **kwargs,
            )

    return ApplicationCallbackHandler()


def run_config(
    *,
    trace_name: str = "porto-alfa",
    tags: tuple[str, ...] = ("porto-alfa",),
    **extra,
) -> dict[str, Any]:
    handler = get_langfuse_handler()
    config = (
        {
            "callbacks": [handler],
            "run_name": trace_name,
            "metadata": {"langfuse_tags": list(tags)},
        }
        if handler
        else {}
    )
    config.update(extra)
    return config


def flush() -> None:
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        from langfuse import get_client

        get_client().flush()

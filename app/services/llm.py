import logging
import os

from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from app.config import config

logger = logging.getLogger(__name__)


def configure_models() -> None:
    """
    Configure the shared LlamaIndex models.
    """

    # Make the API key available to the OpenAI SDK
    os.environ["OPENAI_API_KEY"] = config.openai_api_key

    if config.model_provider.lower() != "openai":
        raise ValueError(
            f"Unsupported MODEL_PROVIDER: {config.model_provider}"
        )

    logger.info("LLM Model: %s", config.llm_model)
    logger.info("Embedding Model: %s", config.embedding_model)

    Settings.llm = OpenAI(
        model=config.llm_model,
        temperature=0.1,
    )

    Settings.embed_model = OpenAIEmbedding(
        model=config.embedding_model,
    )
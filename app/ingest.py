from pathlib import Path

from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter

from app.config import config
from app.services.llm import configure_models

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


def build_index() -> None:
    configure_models()

    data_path = Path(config.data_dir)
    storage_path = Path(config.storage_dir)

    storage_path.mkdir(parents=True, exist_ok=True)

    try:
        documents = SimpleDirectoryReader(
            str(data_path),
            recursive=True,
        ).load_data()
    except ValueError as exc:
        raise RuntimeError(
            f"No documents found in the data directory: {data_path}"
        ) from exc

    if not documents:
        raise RuntimeError(
            "No documents found in the data directory."
        )

    for document in documents:
        file_name = document.metadata.get("file_name", "unknown")
        document.metadata["source_type"] = Path(file_name).suffix.lower()
        document.metadata["collection"] = "judo_knowledge"

    splitter = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    nodes = splitter.get_nodes_from_documents(documents)

    index = VectorStoreIndex(
        nodes,
        show_progress=True,
    )

    index.storage_context.persist(
        persist_dir=str(storage_path)
    )

    print("=" * 50)
    print("Index built successfully.")
    print(f"Indexed {len(documents)} document(s).")
    print(f"Saved to: {storage_path}")
    print("=" * 50)


if __name__ == "__main__":
    build_index()
import os
import vertexai
from vertexai.preview import rag


def consult_herbal_corpus(query: str) -> str:
    """Search Culpeper's Complete Herbal corpus for medicinal plants, herbs, ailments, and natural remedies.

    Args:
        query: What to look up (a plant name, ailment, symptom, or herbal remedy).

    Returns:
        Matched passages from the herbal corpus, or a message if none found.
    """
    corpus_name = os.getenv("RAG_CORPUS_NAME", "")
    if not corpus_name:
        return "Error: RAG_CORPUS_NAME environment variable is not set."

    try:
        # Parse location from corpus_name e.g. projects/.../locations/asia-east1/...
        loc = "asia-east1"
        if "/locations/" in corpus_name:
            loc = corpus_name.split("/locations/")[1].split("/")[0]

        vertexai.init(project="qwiklabs-gcp-01-597eb0775984", location=loc)
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        return "\n\n---\n\n".join(passages) or "No relevant herbal passages found."
    except Exception as e:
        return f"Retrieval query failed: {e}"

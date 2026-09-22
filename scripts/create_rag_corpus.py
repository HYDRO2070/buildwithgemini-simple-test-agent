import sys
import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-01-597eb0775984"
LOCATION = "us-central1"
GCS_PATH = "gs://simple-test-agent-assets-597eb/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, medicinal herbs, plants, and remedies described in this text. "
    "Ignore and omit all boilerplate and license text. "
    "Output clean, self-contained prose."
)

print(f"Initializing Vertex AI for project={PROJECT_ID}, location={LOCATION}...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

print("1. Updating RAG Engine config to serverless mode...")
cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
try:
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=cfg,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
        )
    )
    print("Updated RAG engine config to serverless mode.")
except Exception as e:
    print(f"Note on RAG Engine config update: {e}")

print("2. Creating RAG Corpus...")
corpus = rag.create_corpus(
    display_name="complete-herbal-corpus",
    embedding_model_config=rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    ),
)
print("Created corpus:", corpus.name)

print("3. Importing files into corpus...")
resp = rag.import_files(
    corpus_name=corpus.name,
    paths=[GCS_PATH],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
    ),
    llm_parser=rag.LlmParserConfig(
        model_name="gemini-2.5-flash",
        custom_parsing_prompt=PARSING_PROMPT,
    ),
)
print(f"Import complete. Imported files count: {resp.imported_rag_files_count}")

# Append corpus name to .env
with open(".env", "a") as f:
    f.write(f"\nRAG_CORPUS_NAME={corpus.name}\n")

print("Appended RAG_CORPUS_NAME to .env file.")

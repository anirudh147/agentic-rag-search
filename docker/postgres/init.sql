-- Enables pgvector. LlamaIndex's PGVectorStore also issues this on first
-- connect (CREATE EXTENSION IF NOT EXISTS vector), but declaring it here
-- keeps the requirement explicit and makes a fresh DB usable even before
-- the backend's first ingestion run.
CREATE EXTENSION IF NOT EXISTS vector;

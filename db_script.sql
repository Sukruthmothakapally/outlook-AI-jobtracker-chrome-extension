CREATE TABLE applied_companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    company_website VARCHAR(255),
    job_position VARCHAR(255),
    applied_date TIMESTAMP WITH TIME ZONE NOT NULL,
    application_status text,
    UNIQUE (company_name, job_position)
);


CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE applied_companies_embeddings (
    vector_id SERIAL PRIMARY KEY,
    applied_company_id INT REFERENCES applied_companies(id) ON DELETE CASCADE, -- Foreign key to applied_companies table
    company_embeddings VECTOR(768) -- SBERT embeddings typically have a dimension of 768
);

-- Create an index on the embeddings column for cosine similarity
CREATE INDEX ON applied_companies_embeddings
USING ivfflat (company_embeddings vector_cosine_ops) WITH (lists = 50);


REINDEX INDEX applied_companies_embeddings_embedding_idx;
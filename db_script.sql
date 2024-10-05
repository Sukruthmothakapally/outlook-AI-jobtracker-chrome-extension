CREATE TABLE applied_companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    company_website VARCHAR(255),
    job_position VARCHAR(255),
    applied_date TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (company_name, job_position)
);

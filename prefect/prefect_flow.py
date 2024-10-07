import os
from prefect import flow, task
from datetime import timedelta

# Get the absolute path to the pipeline directory
PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline")

# Set the TOKEN_FILE environment variable to point to the correct location
os.environ['TOKEN_FILE'] = os.path.join(PIPELINE_DIR, "token_cache.json")

# Import functions from existing files
from pipeline.outlookapi import fetch_emails_last_24_hours
from pipeline.gpt_processing_emails import extract_job_application_emails
from pipeline.insert_to_db import process_and_insert_applications

@task(name="Fetch Emails", retries=3, retry_delay_seconds=60)
def fetch_emails_task():
    """Task to fetch emails from Outlook"""
    print(f"Current working directory: {os.getcwd()}")
    print(f"Pipeline directory: {PIPELINE_DIR}")
    print(f"Token file location: {os.environ['TOKEN_FILE']}")
    return fetch_emails_last_24_hours()

@task(name="Process Emails with GPT")
def process_emails_task(email_context):
    """Task to process emails with GPT"""
    if email_context:
        return extract_job_application_emails(email_context)
    return None

@task(name="Insert to Database")
def insert_to_db_task(email_context):
    """Task to insert processed data into database"""
    if email_context:
        process_and_insert_applications(email_context)

@flow(name="Job Applications Processing Flow")
def job_applications_flow():
    # Execute tasks in sequence
    email_data = fetch_emails_task()
    processed_data = process_emails_task(email_data)
    insert_to_db_task(processed_data)

if __name__ == "__main__":
    # Verify token file exists before starting
    token_file = os.path.join(PIPELINE_DIR, "token_cache.json")
    if not os.path.exists(token_file):
        raise FileNotFoundError(f"Token file not found at {token_file}")
        
    job_applications_flow.serve(
        name="job-applications-deployment",
        interval=timedelta(hours=24),
        tags=["job-applications"]
    )
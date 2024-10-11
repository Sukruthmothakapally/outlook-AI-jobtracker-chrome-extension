import os
import sys
import logging
from prefect import flow, task, get_run_logger
from datetime import timedelta
import json

# Add the project root to sys.path to allow importing assistant.py from the root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # This points to the project root
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO)
global_logger = logging.getLogger(__name__)

PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline")

os.environ['TOKEN_FILE'] = os.path.join(PIPELINE_DIR, "token_cache.json")

from pipeline.outlookapi import fetch_emails_last_24_hours
from pipeline.gpt_processing_emails import extract_job_application_emails
from pipeline.insert_to_db import process_and_insert_applications

@task(name="Fetch Emails", retries=3, retry_delay_seconds=60)
def fetch_emails_task():
    """Task to fetch emails from Outlook"""
    logger = get_run_logger()
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Pipeline directory: {PIPELINE_DIR}")
    logger.info(f"Token file location: {os.environ['TOKEN_FILE']}")

    try:
        logger.info("Fetching emails from Outlook for the last 24 hours.")
        emails = fetch_emails_last_24_hours()
        logger.info(f"Successfully fetched emails.")
        return emails
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        raise

@task(name="Process Emails with LLM")
def process_emails_task(email_context):
    """Task to process emails with LLM"""
    logger = get_run_logger()

    if email_context:
        try:
            logger.info(f"Processing emails with LLM.")
            processed_emails = extract_job_application_emails(email_context)
            logger.info(f"Successfully processed emails with LLM")
            return processed_emails
        except Exception as e:
            logger.error(f"Failed to process emails: {e}")
            raise
    else:
        logger.warning("No emails to process.")
    return None

@task(name="Insert to Postgres DB")
def insert_to_db_task(processed_emails):
    """Task to insert processed data into the database"""
    logger = get_run_logger()

    if processed_emails:
        try:
            # Log the processed data before inserting it
            logger.info("Logging processed data before insertion.")
            
            # If data size is manageable, log the entire data in JSON format
            logger.debug(f"Processed Data: {json.dumps(processed_emails, indent=4)}")

            # Insert data into the database
            logger.info(f"Inserting processed applications into the database.")
            process_and_insert_applications(processed_emails)
            logger.info("Successfully inserted processed applications into the database.")
        except Exception as e:
            logger.error(f"Failed to insert data into the database: {e}")
            raise
    else:
        logger.warning("No data to insert into the database.")

@flow(name="Outlook Job Applications Processing Flow")
def job_applications_flow():
    # Execute tasks in sequence
    logger = get_run_logger()
    logger.info("Starting Job Applications Processing Flow.")

    email_data = fetch_emails_task()
    processed_emails = process_emails_task(email_data)
    insert_to_db_task(processed_emails)

    logger.info("Job Applications Processing Flow completed.")

if __name__ == "__main__":
    # Verify token file exists before starting
    token_file = os.path.join(PIPELINE_DIR, "token_cache.json")
    
    if not os.path.exists(token_file):
        global_logger.error(f"Token file not found at {token_file}")
        raise FileNotFoundError(f"Token file not found at {token_file}")
        
    global_logger.info(f"Token file found at {token_file}. Starting the flow.")

    job_applications_flow.serve(
        name="Outlook-job-applications-deployment",
        interval=timedelta(hours=24),
        tags=["Outlook-job-applications"]
    )

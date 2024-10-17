import os
import sys
import logging
from prefect import flow, task
from prefect.logging import get_run_logger
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
from pipeline.insert_to_db import process_applications, process_embeddings, get_db_connection

# Task 1: Fetch Emails Task
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
        if not emails:  # Raise exception if no emails were fetched
            raise ValueError("No emails were fetched from Outlook.")
        logger.info("Successfully fetched emails.")
        return emails
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        raise  # Ensure the task fails

# Task 2: Process Emails Task
@task(name="Process Emails with LLM")
def process_emails_task(email_context):
    """Task to process emails with LLM"""
    logger = get_run_logger()

    if email_context:
        try:
            logger.info("Processing emails with LLM.")
            processed_emails = extract_job_application_emails(email_context)
            if not processed_emails:  # Raise exception if no processed emails
                raise ValueError("No processed emails to work with.")
            logger.info("Successfully processed emails with LLM.")
            return processed_emails
        except Exception as e:
            logger.error(f"Failed to process emails: {e}")
            raise  # Ensure the task fails
    else:
        logger.error("No email context provided for processing.")
        raise ValueError("No email context provided for processing.")  # Raise an exception if no context

# Task 3: Insert to Postgres DB Task
@task(name="Insert to Postgres DB")
def insert_to_db_task(processed_emails):
    """Task to insert processed data into the database"""
    logger = get_run_logger()

    if processed_emails:
        try:
            logger.info("Logging processed data before insertion.")
            logger.debug(f"Processed Data: {json.dumps(processed_emails, indent=4)}")

            conn = get_db_connection()

            if conn:
                logger.info("Inserting processed applications into the database.")
                company_data_list = process_applications(conn, processed_emails)
                conn.commit()
                conn.close()

                logger.info("Successfully inserted processed applications into the database.")
                return company_data_list
            else:
                logger.error("Failed to connect to the database.")
                raise ConnectionError("Database connection failed.")  # Ensure the task fails
        except Exception as e:
            logger.error(f"Failed to insert data into the database: {e}")
            raise  # Ensure the task fails
    else:
        logger.error("No processed emails available for insertion.")
        raise ValueError("No processed emails available for insertion.")  # Raise an exception for empty data

# Task 4: Insert Embeddings Task
@task(name="Insert Embeddings")
def insert_embeddings_task(company_data_list):
    """Task to insert embeddings into the database"""
    logger = get_run_logger()

    if company_data_list:
        try:
            conn = get_db_connection()

            if conn:
                logger.info("Inserting embeddings for companies into the database.")
                process_embeddings(conn, company_data_list)
                conn.commit()
                conn.close()

                logger.info("Successfully inserted embeddings into the database.")
            else:
                logger.error("Failed to connect to the database for embedding insertion.")
                raise ConnectionError("Database connection failed.")  # Ensure the task fails
        except Exception as e:
            logger.error(f"Failed to insert embeddings into the database: {e}")
            raise  # Ensure the task fails
    else:
        logger.error("No company data found for inserting embeddings.")
        raise ValueError("No company data found for inserting embeddings.")  # Raise an exception for empty data

# Main Flow: Job Applications Processing Flow
@flow(name="Outlook Job Applications Processing Flow")
def job_applications_flow():
    logger = get_run_logger()
    logger.info("Starting Job Applications Processing Flow.")

    # Fetch emails from Outlook
    email_data_state = fetch_emails_task(return_state=True)
    
    if email_data_state.is_completed():
        email_data = email_data_state.result()
        if email_data:
            # Process the fetched emails using LLM
            processed_emails_state = process_emails_task(email_data, return_state=True)
            
            if processed_emails_state.is_completed():
                processed_emails = processed_emails_state.result()
                if processed_emails:
                    # Insert applications into the database and get company data
                    company_data_list_state = insert_to_db_task(processed_emails, return_state=True)
                    
                    if company_data_list_state.is_completed():
                        company_data_list = company_data_list_state.result()
                        if company_data_list:
                            # Insert embeddings for the companies
                            insert_embeddings_task(company_data_list)
                        else:
                            logger.error("No company data to process for embeddings.")
                            raise ValueError("No company data to process for embeddings.")  # Raise an exception for empty data
                    else:
                        logger.error("Failed to insert data into the database.")
                else:
                    logger.error("No processed emails to insert into the database.")
                    raise ValueError("No processed emails to insert into the database.")  # Raise an exception for empty data
            else:
                logger.error("Failed to process emails with LLM.")
        else:
            logger.error("No emails fetched to process.")
            raise ValueError("No emails fetched to process.")  # Raise an exception for empty data
    else:
        logger.error("Failed to fetch emails.")

    logger.info("Job Applications Processing Flow completed.")

if __name__ == "__main__":
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

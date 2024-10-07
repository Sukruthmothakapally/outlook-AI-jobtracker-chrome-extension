import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

from pipeline.gpt_processing_emails import extract_job_application_emails
from pipeline.outlookapi import fetch_emails_last_24_hours

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters
DB_HOST_NAME = os.getenv('DB_HOST_NAME')
MAINTENANCE_DB = os.getenv('MAINTENANCE_DB')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def insert_applied_company(company_name, company_website, job_position, applied_date):
    """Insert applied company data into the PostgreSQL database."""
    try:
        # Connect to the PostgreSQL database
        with psycopg2.connect(
            host=DB_HOST_NAME,
            database=MAINTENANCE_DB,
            user=DB_USERNAME,
            password=DB_PASSWORD
        ) as conn:
            with conn.cursor() as cursor:
                insert_query = sql.SQL("""
                    INSERT INTO applied_companies (company_name, company_website, job_position, applied_date)
                    VALUES (%s, %s, %s, %s)
                """)
                cursor.execute(insert_query, (company_name, company_website, job_position, applied_date))
                conn.commit()  # Commit the transaction
                print(f"Inserted: {company_name}, {company_website}, {job_position}, {applied_date}")
    except Exception as e:
        print("Error inserting data:", e)

def process_and_insert_applications(email_context):
    """Process and insert job application data into the database."""
    # Fetch the job application details using GPT
    extracted_data = extract_job_application_emails(email_context)

    if extracted_data and 'applications' in extracted_data:
        # Iterate over each application in the returned JSON and insert it into the database
        for application in extracted_data['applications']:
            company_name = application.get('company_name')
            company_website = application.get('company_website')
            job_position = application.get('applied_position')
            applied_date = application.get('applied_timestamp')
            insert_applied_company(company_name, company_website, job_position, applied_date)
        print('All applications successfully inserted.')
    else:
        print("No valid application data found or extracted.")

if __name__ == "__main__":
    # Fetch the email context from GPT processing (this should return JSON from gpt_processing_emails.py)
    email_context = fetch_emails_last_24_hours()  # Fetch the emails from the last 24 hours

    if email_context:
        # Process and insert the job application data into the database
        process_and_insert_applications(email_context)
    else:
        print("No email data retrieved.")

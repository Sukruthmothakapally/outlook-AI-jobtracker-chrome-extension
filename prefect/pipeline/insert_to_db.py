import os
import sys
import psycopg2
from psycopg2 import sql, Error
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import logging

from pipeline.gpt_processing_emails import extract_job_application_emails
from pipeline.outlookapi import fetch_emails_last_24_hours

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters
DB_HOST_NAME = os.getenv('DB_HOST_NAME')
MAINTENANCE_DB = os.getenv('MAINTENANCE_DB')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

model = SentenceTransformer('thenlper/gte-small')

def get_db_connection():
    """Create and return a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST_NAME,
            database=MAINTENANCE_DB,
            user=DB_USERNAME,
            password=DB_PASSWORD
        )
        logging.info("Successfully connected to the database.")
        return conn
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        return None

def insert_applied_company(cursor, company_name, company_website, job_position, applied_date, application_status):
    """Insert applied company data into the PostgreSQL database."""
    try:
        insert_query = sql.SQL("""
            INSERT INTO applied_companies (company_name, company_website, job_position, applied_date, application_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """)
        cursor.execute(insert_query, (company_name, company_website, job_position, applied_date, application_status))
        company_id = cursor.fetchone()[0]
        logging.info(f"Inserted: {company_name}, {company_website}, {job_position}, {applied_date}, {application_status} with ID: {company_id}")

        return company_id
    
    except Exception as e:
        logging.error(f"Error inserting data: {e}")

def generate_embedding(company_name, company_website, job_position, applied_date, application_status):
    """Generate an embedding for the given company data."""
    try:
        text_to_embed = f"{company_name} {company_website} {job_position} Applied on: {applied_date} Status: {application_status}"
        embedding = model.encode([text_to_embed])[0]  # Model returns a list, get the first item
        logging.info(f"Generated embedding for: {company_name}")
        return embedding
    except Exception as e:
        logging.error(f"Error generating embedding: {e}")
        return None

def insert_embedding(cursor, applied_company_id, embedding):
    """Insert the embedding into the applied_companies_embeddings table."""
    try:
        insert_query = sql.SQL("""
            INSERT INTO applied_companies_embeddings (applied_company_id, company_embeddings)
            VALUES (%s, %s)
        """)
        # Convert embedding to list for insertion
        cursor.execute(insert_query, (applied_company_id, embedding.tolist()))
        logging.info(f"Inserted embedding for company ID: {applied_company_id}")
    except (Exception, Error) as e:
        logging.error(f"Error inserting embedding for company ID {applied_company_id}: {e}")

def process_applications(conn, email_context):
    """Process and insert job application data into the database."""
    extracted_data = extract_job_application_emails(email_context)
   
    if extracted_data and 'applications' in extracted_data:
        with conn.cursor() as cursor:
            company_data_list = []
            for application in extracted_data['applications']:
                company_name = application.get('company_name')
                company_website = application.get('company_website')
                job_position = application.get('applied_position')
                applied_date = application.get('applied_timestamp')
                application_status = application.get('application_status')

                # Insert the company data
                company_id = insert_applied_company(cursor, company_name, company_website, job_position, applied_date, application_status)

                if company_id:
                    # Collect company data for further embedding generation
                    company_data_list.append({
                        'company_id': company_id,
                        'company_name': company_name,
                        'company_website': company_website,
                        'job_position': job_position,
                        'applied_date': applied_date,
                        'application_status': application_status
                    })
            
            conn.commit()  # Commit after all companies have been inserted
            logging.info("All applications successfully inserted.")
            return company_data_list  # Return company data
    else:
        logging.warning("No valid application data found or extracted.")
        return []

def process_embeddings(conn, company_data_list):
    """Process and insert embeddings for a list of companies."""
    if company_data_list:
        with conn.cursor() as cursor:
            for company_data in company_data_list:
                company_id = company_data['company_id']
                company_name = company_data['company_name']
                company_website = company_data['company_website']
                job_position = company_data['job_position']
                applied_date = company_data['applied_date']
                application_status = company_data['application_status']

                # Generate the embedding for the company
                embedding = generate_embedding(company_name, company_website, job_position, applied_date, application_status)

                if embedding is not None:
                    # Insert the embedding
                    insert_embedding(cursor, company_id, embedding)

            conn.commit()  # Commit after all embeddings have been inserted
            logging.info("All embeddings successfully inserted.")
    else:
        logging.warning("No companies found for embedding.")

if __name__ == "__main__":
    # Fetch the email context from GPT processing (this should return JSON from gpt_processing_emails.py)
    email_context = fetch_emails_last_24_hours()  # Fetch the emails from the last 24 hours

    if email_context:
        # Process and insert the job application data into the database
        conn = get_db_connection()
        try:
            # Step 1: Insert application data
            company_data_list = process_applications(conn, email_context)
            
            # Step 2: Insert embeddings separately
            process_embeddings(conn, company_data_list)
        finally:
            # Always close the connection
            conn.close()
    else:
        logging.warning("No email data retrieved")
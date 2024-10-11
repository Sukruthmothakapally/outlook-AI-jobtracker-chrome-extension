import os
import psycopg2
from psycopg2 import sql, Error  # Import Error for better exception handling
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters
DB_HOST_NAME = os.getenv('DB_HOST_NAME')
MAINTENANCE_DB = os.getenv('MAINTENANCE_DB')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Load the GTE-Large model from Hugging Face
model = SentenceTransformer('thenlper/gte-small')

def connect_to_postgres():
    """Create a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST_NAME,
            database=MAINTENANCE_DB,
            user=DB_USERNAME,
            password=DB_PASSWORD
        )
        logging.info("Successfully connected to the database")
        return conn
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        return None

def fetch_applied_companies(conn):
    """Fetch all rows from applied_companies table including the applied_date."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, company_name, job_position, applied_date FROM applied_companies")
            rows = cursor.fetchall()
            logging.info(f"Fetched {len(rows)} rows from applied_companies table.")
            return rows
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return []

def insert_embedding(conn, applied_company_id, embedding):
    """Insert the embedding into the applied_companies_embeddings table."""
    try:
        with conn.cursor() as cursor:
            insert_query = sql.SQL("""
                INSERT INTO applied_companies_embeddings (applied_company_id, company_embeddings)
                VALUES (%s, %s)
            """)
            # Convert embedding to list for insertion
            cursor.execute(insert_query, (applied_company_id, embedding.tolist()))
            conn.commit()
            logging.info(f"Inserted embedding for company ID: {applied_company_id}")
    except (Exception, Error) as e:
        conn.rollback()  # Roll back the transaction to recover from errors
        logging.error(f"Error inserting embedding for company ID {applied_company_id}: {e}")

def process_and_insert_embeddings():
    """Main function to process each company and insert embeddings into the database."""
    # Connect to the database
    conn = connect_to_postgres()
    
    if conn is None:
        logging.error("Could not connect to the database.")
        return
    
    try:
        # Fetch the applied companies data
        applied_companies = fetch_applied_companies(conn)
        
        if not applied_companies:
            logging.warning("No data found in the applied_companies table.")
            return
        
        # Loop through each row and generate embeddings
        for company in applied_companies:
            applied_company_id, company_name, job_position, applied_date = company
            logging.info(f"Processing company ID {applied_company_id}: {company_name}, {job_position}")
            
            # Option 1: Use applied_date directly
            text_to_embed = f"{company_name} {job_position} Applied on: {applied_date}"
            
            # Generate the embedding using GTE-Large
            try:
                embedding = model.encode([text_to_embed])[0]  # Encode returns a list, take the first element
                logging.info(f"Generated embedding for company ID {applied_company_id}")
            except Exception as e:
                logging.error(f"Error generating embedding for company ID {applied_company_id}: {e}")
                continue  # Skip this record and proceed with the next
            
            # Insert the embedding into the applied_companies_embeddings table
            insert_embedding(conn, applied_company_id, embedding)
    
    except Exception as e:
        logging.error(f"Error in processing: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    process_and_insert_embeddings()

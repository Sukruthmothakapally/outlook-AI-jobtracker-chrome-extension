import os
import psycopg2
from psycopg2 import sql, Error
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

# Load the GTE-Small model from Hugging Face
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

def perform_similarity_search(conn, query):
    """Perform a vector similarity search based on a user query."""
    try:
        # Step 1: Encode the user query into a vector
        logging.info(f"Encoding the user query: {query}")
        query_vector = model.encode([query])[0]  # Get the embedding for the query
        
        # Convert the vector to a proper string format with square brackets for PostgreSQL
        query_vector_str = '[' + ','.join(map(str, query_vector)) + ']'

        # Step 2: Perform the vector similarity search in PostgreSQL
        with conn.cursor() as cursor:
            search_query = sql.SQL("""
                SELECT ac.id, ac.company_name, ac.job_position, ac.applied_date, ace.company_embeddings <-> %s::vector AS similarity
                FROM applied_companies ac
                JOIN applied_companies_embeddings ace ON ac.id = ace.applied_company_id
                ORDER BY similarity
                LIMIT 1;
            """)
            cursor.execute(search_query, (query_vector_str,))
            result = cursor.fetchone()
            
            if result:
                logging.info(f"Most similar company found: {result}")
                return result
            else:
                logging.warning("No similar company found.")
                return None
    except (Exception, Error) as e:
        logging.error(f"Error during similarity search: {e}")
        return None

def main():
    """Main function to execute the similarity search."""
    conn = connect_to_postgres()
    
    if conn is None:
        logging.error("Could not connect to the database.")
        return
    
    try:
        # Example user query
        user_query = "uber"
        result = perform_similarity_search(conn, user_query)
        
        if result:
            id, company_name, job_position, applied_date, similarity = result
            print(f"Most similar company to '{user_query}':")
            print(f"Company Name: {company_name}")
            print(f"Job Position: {job_position}")
            print(f"Applied Date: {applied_date}")
            print(f"Similarity Score: {similarity}")
        else:
            print(f"No similar company found for query '{user_query}'.")
    
    except Exception as e:
        logging.error(f"Error in main function: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    main()

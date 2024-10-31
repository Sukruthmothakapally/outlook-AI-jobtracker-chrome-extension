import os
import psycopg2
from psycopg2 import sql, Error
from sentence_transformers import SentenceTransformer
import openai
from dotenv import load_dotenv
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters
DB_HOST_NAME = os.getenv('DB_HOST_NAME')
MAINTENANCE_DB = os.getenv('MAINTENANCE_DB')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')

if not openai_api_key:
    raise ValueError("OpenAI API key not found. Make sure it is set in the .env file.")

# Load the embedding model from Hugging Face
model = SentenceTransformer('thenlper/gte-small')

# Initialize OpenAI API
client = openai.OpenAI(
    api_key=openai_api_key,
)


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
    """Perform a vector similarity search based on a user query using cosine similarity."""
    try:
        # Step 1: Encode the user query into a vector
        logging.info(f"Encoding the user query: {query}")
        query_vector = model.encode([query])[0]  # Get the embedding for the query
        
        # Convert the vector to a proper string format with square brackets for PostgreSQL
        query_vector_str = '[' + ','.join(map(str, query_vector)) + ']'

        # Step 2: Perform the vector similarity search in PostgreSQL
        with conn.cursor() as cursor:
            search_query = sql.SQL("""
                SELECT ac.id, ac.company_name, ac.company_website, ac.job_position, ac.applied_date, ac.application_status,
                       ace.company_embeddings <-> %s::vector AS similarity
                FROM applied_companies ac
                JOIN applied_companies_embeddings ace ON ac.id = ace.applied_company_id
                ORDER BY ace.company_embeddings <-> %s::vector -- Ensure cosine distance is used
                LIMIT 1;
            """)
            cursor.execute(search_query, (query_vector_str, query_vector_str))
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


async def generate_openai_response(user_query: str, company_details) -> AsyncGenerator[str, None]:
    """Generate a response using OpenAI's GPT-3.5-turbo model based on user query and company details."""
    company_name = company_details[1]
    company_website = company_details[2]
    job_position = company_details[3]
    applied_date = company_details[4]
    application_status = company_details[5]
    
    prompt = f"""
            You are a helpful assistant. The user asked the following query: '{user_query}'.

            The most relevant match found in the database is as follows:
            - Company Name: {company_name}
            - Company Website: {company_website}
            - Job Position: {job_position}
            - Applied Date: {applied_date}
            - Application Status:
              {application_status}

            Here are the rules to guide your response:

            1. **If the user's query contains the company name '{company_name}',** provide a concise and accurate response based **only** on the above context. 

            2. **If the company name mentioned in the user's query is different from '{company_name}',** inform them that they haven't applied to that company yet.
            For example: If the user's query contains "Company X" and the company name in context is "Company Y". Your response would be: "You haven't applied to company X yet.

            3. **If the user's query doesn't contain any company name,** inform them that their query is irrelevant and encourage them to ask a question about a specific company.
            For example: "Use's query: "What can you do?" Your response: Please provide a company name in your query so I can check whether you applied to it or not along with providing useful stats."

            Do not generate or assume any information beyond the provided context. Ensure your response remains strictly within the data provided.
            """
    
    client = AsyncOpenAI()

    try:
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.1,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logging.error(f"Error during OpenAI request: {e}")
        yield "There was an error processing your request. Please try again later."


def main():
    """Main function to execute the similarity search and get a response from OpenAI."""
    conn = connect_to_postgres()
    
    if conn is None:
        logging.error("Could not connect to the database.")
        return
    
    try:
        # User input
        user_query = input("Enter your query: ")
        
        # Step 1: Perform similarity search
        result = perform_similarity_search(conn, user_query)
        
        if result:
            # Step 2: Generate OpenAI response
            openai_response = generate_openai_response(user_query, result)
            logging.info(f"Response from OpenAI: {openai_response}")
        else:
            logging.info(f"No similar company found for query '{user_query}'.")

    
    except Exception as e:
        logging.error(f"Error in main function: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")


if __name__ == "__main__":
    main()

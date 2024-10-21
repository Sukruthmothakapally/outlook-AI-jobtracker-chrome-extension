import os
import psycopg2
from psycopg2 import Error
import openai
from dotenv import load_dotenv
import logging
import openai
import json
import pandas as pd

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

def generate_sql_query(user_query: str) -> str:

    """Generate an SQL query using OpenAI's GPT-3.5-turbo model based on user query."""
    prompt = f"""
    You are an AI assistant skilled in converting natural language queries to SQL.
    The database has a table named 'applied_companies' with the following structure:

    CREATE TABLE applied_companies (
        id SERIAL PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        company_website VARCHAR(255),
        job_position VARCHAR(255),
        applied_date TIMESTAMP WITH TIME ZONE NOT NULL,
        application_status VARCHAR(255),
        UNIQUE (company_name, job_position)
    );

    Please follow these constraints:
    1. Understand the user's intention based on their question and use the given table structure to create a grammatically correct SQL query.
    2. Generate one SQL query for every question the user provides.
    3. Always limit the query to a maximum of 5 results using 'LIMIT 5' unless the user specifies a different number.
    4. Select at most 5 fields for each SQL query. For example, instead of 'SELECT * FROM applied_companies', use 'SELECT company_name, job_position, applied_date, application_status FROM applied_companies'.
    5. Ensure that all fields used in the query exist in the provided table structure.
    6. Check the correctness of the SQL and optimize query performance where possible.

    User query: {user_query}

    Respond according to the following JSON format:
    {{
        "sql": "SQL Query to run"
    }}

    Ensure the response is correct JSON and can be parsed by Python json.loads.

    Examples:
    1. User query: "Show me the latest 5 job applications"
    Response: {{
        "sql": "SELECT company_name, job_position, applied_date, application_status FROM applied_companies ORDER BY applied_date DESC LIMIT 5"
    }}

    2. User query: "How many companies have I applied to?"
    Response: {{
        "sql": "SELECT COUNT(DISTINCT company_name) AS company_count FROM applied_companies LIMIT 5"
    }}

    JSON response:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates SQL queries in JSON format"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0,
            response_format={"type": "json_object"}
        )
        sql_query = response.choices[0].message.content.strip()
        logging.info(f"Generated SQL query: {sql_query}")

         # Parse the response as JSON
        try:
            json_output = json.loads(sql_query)
            return json_output
        except json.JSONDecodeError:
            logging.error("Failed to parse GPT response as JSON. Here is the raw output:\n%s", sql_query)
            return None
    
    except openai.APIError as e:
        # Handle any OpenAI API errors
        logging.error(f"OpenAI API error occurred: {e}")
        return None
    except Exception as e:
        # Catch all other exceptions
        logging.error(f"An error occurred: {e}")
        return None

def execute_sql_query(conn, sql_query):
    """Execute the SQL query and return the results along with column names."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            result = cursor.fetchall()

            # Fetch column names from cursor description
            column_names = [desc[0] for desc in cursor.description]

            logging.info(f"Query executed successfully. Result: {result}")
            logging.info(f"Column names: {column_names}")

            return column_names, result  # Return both column names and result
    except (Exception, Error) as e:
        logging.error(f"Error executing SQL query: {e}")
        return None, None  # Return None for both if an error occurs

def visualize_sql_result(result, headers):
    """
    Convert SQL query result into a table format and display.
    
    :param result: List of tuples containing SQL query result
    :param headers: List of strings for the table headers
    :return: Formatted table as string (if needed)
    """
    
    # Create a pandas DataFrame from the result
    df = pd.DataFrame(result, columns=headers)
    
    # Return or print the DataFrame for visual representation
    return df

def main():
    """Main function to execute the text-to-SQL query process."""
    conn = connect_to_postgres()
    
    if conn is None:
        logging.error("Could not connect to the database.")
        return
    
    try:
        # User input
        user_query = input("Enter your question about the database: ")
        
        # Generate SQL query
        json_response = generate_sql_query(user_query)
        
        if json_response and 'sql' in json_response:
            sql_query = json_response['sql']
            
            print(f"Generated SQL query: {sql_query}")
            
            # Execute SQL query
            headers, result = execute_sql_query(conn, sql_query)
                
            # Visualize result
            table = visualize_sql_result(result, headers)
            print(table)  # Display the table
        
        else:
            print("Failed to generate SQL query.")
    
    except Exception as e:
        logging.error(f"Error in main function: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    main()
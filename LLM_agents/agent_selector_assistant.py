import openai
import json
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI API
client = openai.OpenAI(
    api_key=openai_api_key,
)


def generate_prompt(user_query: str) -> str:
    """
    Generate the prompt that will guide GPT-4 to choose the correct agent or return 'invalid question'.
    """
    prompt = f"""
    You are a helpful assistant tasked with choosing between two agent functions: 'vector_search_agent' and 'text_to_sql_agent', or returning 'invalid question' if the query is irrelevant, based on the user's query.

    The user may ask about companies they have applied to. The relevant table schema for these tasks is as follows:

    CREATE TABLE applied_companies (
        id SERIAL PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        company_website VARCHAR(255),
        job_position VARCHAR(255),
        applied_date TIMESTAMP WITH TIME ZONE NOT NULL,
        application_status text,
        UNIQUE (company_name, job_position)
    );

    Here are the rules to guide your decision:
    1. **If the query mentions a specific company**, you must return the 'vector_search_agent'.
    2. **If the query is generic or refers to multiple companies without mentioning a specific company name**, return the 'text_to_sql_agent'.
    3. **If the query doesn't ask questions about a specific company or companies in general**, return 'invalid question'.

    Consider the following examples for guidance:
    - Example 1:
      User query: "What is the status of my application at Google?"
      Expected response: {{"agent": "vector_search_agent"}}

    - Example 2:
      User query: "Show me all the companies I've applied to in the last month."
      Expected response: {{"agent": "text_to_sql_agent"}}

    - Example 3:
      User query: "How many companies have I applied to?"
      Expected response: {{"agent": "text_to_sql_agent"}}

    - Example 4:
      User query: "Did I apply to Apple? and when?"
      Expected response: {{"agent": "vector_search_agent"}}

    - Example 5:
      User query: "What's the weather like?"
      Expected response: {{"error": "invalid question"}}

    Based on these rules, return the appropriate response in a valid JSON format.

    Here is the user query:
    {user_query}

    JSON response:
    """
    return prompt

def select_agent(user_query: str):
    """
    Interact with GPT-4 model to choose the appropriate agent function.
    """

    if not openai_api_key:
        raise ValueError("OpenAI API key not found. Make sure it is set in the .env file.")

    if not client:
        logging.error("OpenAI client initialization failed.")
        raise ValueError("OpenAI client could not be initialized. Check API key or client configuration.")
    
    # Generate the prompt
    prompt = generate_prompt(user_query)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates SQL queries in JSON format"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0,
            response_format={"type": "json_object"}
        )

        # Extract the response text
        response_text = response.choices[0].message.content.strip()

        # Parse the response text to extract the agent or error message
        try:
            json_output = json.loads(response_text)
            if "agent" in json_output:
                return json_output["agent"]
            elif "error" in json_output:
                return json_output["error"] 
        except json.JSONDecodeError:
            logging.error("Failed to parse GPT response as JSON. Here is the raw output:\n%s", response_text)
            return "invalid question"

    except openai.APIError as e:
        # Handle any OpenAI API errors
        logging.error(f"OpenAI API error occurred: {e}")
        return "invalid question"
    except Exception as e:
        # Catch all other exceptions
        logging.error(f"An error occurred: {e}")
        return "invalid question"

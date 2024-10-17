import json
from pipeline.outlookapi import fetch_emails_last_24_hours
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from LLM_agents.email_assistant import get_job_application_details

# Define token limits for gpt-3.5
MODEL_TOTAL_TOKEN_LIMIT = 4096
INPUT_TOKEN_LIMIT = 3500  # Limit for the input (email_context)
OUTPUT_TOKEN_ALLOCATION = MODEL_TOTAL_TOKEN_LIMIT - INPUT_TOKEN_LIMIT

# For gpt-4o -> token limit is 30k. So input=29k and output-1k ideal

# Function to estimate the number of tokens in the text (rough estimation)
def estimate_token_count(text):
    # A rough estimation: assume each word is approximately 1.3 tokens
    return int(len(text.split()) * 1.3)

# Function to trim the email context if it exceeds the token limit
def trim_email_context(email_context, token_limit):
    """Trim the email context if it exceeds the token limit."""
    tokens = estimate_token_count(email_context)

    if tokens <= token_limit:
        return email_context

    # If it exceeds the limit, start trimming from the end
    logging.info(f"Email context exceeds token limit. Trimming to {token_limit} tokens.")
    words = email_context.split()

    # Estimate the number of words that can fit within the token limit
    trimmed_word_count = int(token_limit / 1.3)

    # Join only the number of words that fit within the token limit
    trimmed_email_context = ' '.join(words[:trimmed_word_count])

    return trimmed_email_context

def extract_job_application_emails(email_context: str):
    """
    Main function to extract job application details from email context.
    This function will call assistant.py to handle the model interaction.
    """
    try:
        # Call the function in assistant.py to extract the details
        extracted_applications = get_job_application_details(email_context)
        return extracted_applications
    
    except Exception as e:
        # Catch any errors and log them
        logging.error(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    # Fetch the email data from the last 24 hours
    email_context = fetch_emails_last_24_hours()

    if email_context:
        # Check and trim email context if necessary (limit to 3500 tokens)
        email_context = trim_email_context(email_context, INPUT_TOKEN_LIMIT)

        # Call the GPT function with the fetched email data and enforce JSON output
        result = extract_job_application_emails(email_context)

        # Log the result
        if result:
            logging.info("Job application details extracted successfully.")
            logging.info(json.dumps(result, indent=4))
        else:
            logging.warning("No valid job application data found or an error occurred.")
    else:
        logging.warning("No emails fetched or an error occurred while fetching emails.")

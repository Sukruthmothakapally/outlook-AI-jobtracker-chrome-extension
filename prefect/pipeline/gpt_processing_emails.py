import openai
import os
from dotenv import load_dotenv
import json
from pipeline.outlookapi import fetch_emails_last_24_hours  # Importing the function from outlookapi.py

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OpenAI API key not found. Make sure it is set in the .env file.")

# Initialize OpenAI API
client = openai.OpenAI(
    api_key=openai_api_key,
)

# Define token limits for gpt-3.5
MODEL_TOTAL_TOKEN_LIMIT = 4096
INPUT_TOKEN_LIMIT = 3500  # Limit for the input (email_context)
OUTPUT_TOKEN_ALLOCATION = MODEL_TOTAL_TOKEN_LIMIT - INPUT_TOKEN_LIMIT 

#for gpt-4o -> token limit is 30k. so input=29k and output-1k ideal

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
    print(f"Email context exceeds token limit. Trimming to {token_limit} tokens.")
    words = email_context.split()

    # Estimate the number of words that can fit within the token limit
    trimmed_word_count = int(token_limit / 1.3)

    # Join only the number of words that fit within the token limit
    trimmed_email_context = ' '.join(words[:trimmed_word_count])

    return trimmed_email_context

def extract_job_application_emails(email_context: str):
    try:
        # Define the prompt to filter emails and extract data
        prompt = f"""
        The following is a series of emails. Some of these emails contain acknowledgement messages or thank you notes after a job application. Your task is to extract and return the relevant job application details strictly in JSON format. 

        The output should be a valid JSON object with the following keys:
        - company_name
        - company_website
        - applied_position
        - applied_timestamp

        If no emails match the requirement, return an empty JSON object like this: {{"applications": []}}.

        The output must be a valid JSON object. Do not include any additional text outside of the JSON object.

        Here is the email context:
        {email_context}
        """

        # Call the GPT-4 model using the new `client.chat.completions.create` method
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        # Extract and return the JSON response from GPT-4
        response_text = response.choices[0].message.content.strip()

        # Attempt to parse the response as JSON
        try:
            json_output = json.loads(response_text)
            return json_output
        except json.JSONDecodeError:
            raise ValueError("Failed to parse GPT response as JSON. Here is the raw output:\n" + response_text)

    except openai.APIError as e:
        # Handle any OpenAI API errors
        print(f"OpenAI API error occurred: {e}")
        return None
    except Exception as e:
        # Catch all other exceptions
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    # Fetch the email data from the last 24 hours
    email_context = fetch_emails_last_24_hours()

    if email_context:

        # Check and trim email context if necessary (limit to 3500 tokens)
        email_context = trim_email_context(email_context, INPUT_TOKEN_LIMIT)

        # Call the GPT function with the fetched email data and enforce JSON output
        result = extract_job_application_emails(email_context)

        # Print the result
        if result:
            print(json.dumps(result, indent=4))
        else:
            print("No valid job application data found or an error occurred.")
    else:
        print("No emails fetched or an error occurred while fetching emails.")

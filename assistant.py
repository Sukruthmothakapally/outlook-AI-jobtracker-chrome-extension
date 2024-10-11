import openai
import json
import os
from dotenv import load_dotenv

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

def generate_email_prompt(email_context: str) -> str:
    """
    Function to generate the prompt for extracting job application details from emails.
    """
    prompt = f"""
    The following is a series of emails. These emails may contain job application updates, acknowledgements, or thank you messages related to a job application. 
    Your task is to extract and return the relevant job application details strictly in JSON format.

    The output should be a valid JSON object with the following keys:
    - company_name
    - company_website
    - applied_position (this should be **exactly** as stated in the email without any modifications)
    - applied_timestamp
    - application_status

    The "applied_position" should be extracted exactly as it appears in the email and should not be altered in any way. Do not modify capitalization, spacing, or wording in the "applied_position". It should reflect exactly what is mentioned in the email.

    The "application_status" should be determined based on the content of the email. Below are specific examples of common phrases that might appear in the email and how to map them to the "application_status":

    1. **Acknowledgement of Application (application_status = "applied")**:
        - If the email contains phrases like:
          - "Thank you for applying to Company XYZ"
          - "We have received your application"
          - "Your application has been received"
        - These emails acknowledge the receipt of your job application and should have the "application_status" set to "applied".

    2. **Rejection (application_status = "rejected")**:
        - If the email contains phrases like:
          - "Unfortunately, we have decided to move forward with other candidates"
          - "We regret to inform you that you have not been selected"
          - "After careful consideration, we are unable to offer you the position"
        - These emails are rejections, and the "application_status" should be set to "rejected".

    3. **Moving Forward (application_status = "next steps")**:
        - If the email indicates that you are advancing to the next stage, such as:
          - "Congratulations, you have been shortlisted for the next round"
          - "We would like to invite you for an interview"
          - "You have been selected for the next round of interviews"
        - These emails indicate progress in the application process, and the "application_status" should be set to "next steps".

    4. **Interview Scheduled or Offer Received (custom application_status)**:
        - If the email communicates additional updates about interviews or offers, you can customize the "application_status":
          - "Your interview has been scheduled" -> application_status = "interview scheduled"
          - "We are pleased to offer you the position" -> application_status = "offer received"

    **Important Note**: 
    - Use the above examples and keywords to determine the correct "application_status".
    - If none of the categories fit, set "application_status" according to the email's context (e.g., "interview scheduled", "offer received", etc.).

    **Exclusion Criteria**:
    - Do not include generic or promotional emails, such as job alerts, mass job opportunity emails, or advertisements. 
    - Emails with the following phrases should be ignored:
      - "There's an opening at"
      - "Check out this opportunity"
      - "Job alert"
      - "Exciting opportunity at"
    - These emails are generic notifications or advertisements and should be omitted from the JSON output.

    If no emails match the requirement, return an empty JSON object like this: {{"applications": []}}.

    The output must be a valid JSON object. Do not include any additional text outside of the JSON object.

    Here is the email context:
    {email_context}
    """
    return prompt


def get_job_application_details(email_context: str):
    """
    Function to interact with GPT-4 model to extract job application details from email context.
    """
    # Generate the prompt
    prompt = generate_email_prompt(email_context)
    
    try:
        # Call the GPT-4 model
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

        # Parse the response as JSON
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
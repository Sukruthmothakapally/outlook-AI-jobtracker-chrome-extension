import os
import json
import requests
from msal import PublicClientApplication
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import ast

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters
app_id = os.getenv('app_id')
SCOPES = os.getenv('SCOPES')
TOKEN_FILE = os.getenv('TOKEN_FILE')

if isinstance(SCOPES, str):
    try:
        # Safely evaluate the string to convert it into a Python list
        SCOPES = ast.literal_eval(SCOPES)
    except ValueError:
        # Fallback to splitting by comma in case the SCOPES are comma-separated
        SCOPES = SCOPES.split(",")

client = PublicClientApplication(
    client_id=app_id
)

def get_stored_tokens():
    """Retrieve tokens from the token cache file if available."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def store_tokens(token_data):
    """Store tokens to the token cache file."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)

def get_access_token():
    """Retrieve a valid access token, refresh if needed."""
    tokens = get_stored_tokens()
    
    if tokens:
        # Check if the token has expired or is near expiration, and refresh it
        accounts = client.get_accounts()
        result = client.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
        
        if result:
            return result['access_token']
        
        # If token silent acquisition fails, use the refresh token to get a new access token
        if 'refresh_token' in tokens:
            result = client.acquire_token_by_refresh_token(refresh_token=tokens['refresh_token'], scopes=SCOPES)
            if 'access_token' in result:
                store_tokens(result)
                return result['access_token']
    
    # If no valid tokens, prompt user to log in and get new tokens
    print("Fetching new authorization code... Visit this URL:")
    authorization_url = client.get_authorization_request_url(SCOPES)
    print(authorization_url)

    authorization_code = input("Enter the authorization code from the URL: ")

    # Acquire tokens using the authorization code
    result = client.acquire_token_by_authorization_code(code=authorization_code, scopes=SCOPES)
    
    if 'access_token' in result:
        store_tokens(result)
        return result['access_token']
    
    raise Exception(f"Error acquiring access token: {result.get('error_description', 'Unknown error')}")


def fetch_emails_last_24_hours():
    """Fetch and store up to 50 emails from the last 24 hours in a text file, with a counter."""
    access_token = get_access_token()
    if access_token:
        # Calculate the timestamp for 24 hours ago in the correct format for Microsoft Graph
        time_24_hours_ago = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        endpoint = f"https://graph.microsoft.com/v1.0/me/messages?$filter=receivedDateTime ge {time_24_hours_ago}&$orderby=receivedDateTime desc&$top=50"  # Fetch up to 50 emails from the last 24 hours
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Make the GET request to fetch the emails
        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            emails = response.json()  # Parse the JSON response
            email_count = len(emails.get('value', []))  # Count the number of emails fetched

            email_text_data = f"Total Emails Fetched: {email_count}\n"
            email_text_data += "-" * 50 + "\n"  # Separator for the email count

            # Write the email data to a text file and simultaneously store it in a string
            with open("emails_last_24_hours.txt", "w", encoding="utf-8") as file:
                file.write(email_text_data)
                for email in emails.get('value', []):  # Iterate over each email in the 'value' field
                    email_details = (
                        f"Subject: {email.get('subject', 'No Subject')}\n"
                        f"From: {email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')}\n"
                        f"Received: {email.get('receivedDateTime', 'Unknown')}\n"
                        f"Body Preview: {email.get('bodyPreview', 'No Preview')}\n"
                        + "-" * 50 + "\n"  # Separator for each email
                    )
                    file.write(email_details)
                    email_text_data += email_details

            return email_text_data
            
        else:
            print("Error:", response.status_code, response.json())  # Print error details
    else:
        print("Error: Could not acquire an access token.")

if __name__ == "__main__":
    print(fetch_emails_last_24_hours())
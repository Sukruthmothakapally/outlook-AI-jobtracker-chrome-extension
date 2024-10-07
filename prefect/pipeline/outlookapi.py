import os
import json
import requests
from msal import PublicClientApplication
from datetime import datetime, timedelta
from dotenv import load_dotenv
import ast

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# PostgreSQL connection parameters
app_id = os.getenv('app_id')
SCOPES = os.getenv('SCOPES')

# Set TOKEN_FILE path relative to this script's location if not set in environment
TOKEN_FILE = os.getenv('TOKEN_FILE') or os.path.join(SCRIPT_DIR, 'token_cache.json')

# Print debug information
print(f"Script directory: {SCRIPT_DIR}")
print(f"Token file path: {TOKEN_FILE}")
print(f"Token file exists: {os.path.exists(TOKEN_FILE)}")

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
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading token file: {e}")
        print(f"Attempted to read from: {TOKEN_FILE}")
    return None

def store_tokens(token_data):
    """Store tokens to the token cache file."""
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
    except Exception as e:
        print(f"Error writing token file: {e}")
        print(f"Attempted to write to: {TOKEN_FILE}")

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
    """Fetch and store up to 50 emails from the last 24 hours and return as a string with a counter."""
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

            # Store the email data in a string
            for email in emails.get('value', []):  # Iterate over each email in the 'value' field
                email_details = (
                    f"Subject: {email.get('subject', 'No Subject')}\n"
                    f"From: {email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')}\n"
                    f"Received: {email.get('receivedDateTime', 'Unknown')}\n"
                    f"Body Preview: {email.get('bodyPreview', 'No Preview')}\n"
                    + "-" * 50 + "\n"  # Separator for each email
                )
                email_text_data += email_details

            return email_text_data
            
        else:
            return f"Error: {response.status_code}, {response.json()}"  # Return error details
    else:
        return "Error: Could not acquire an access token."

if __name__ == "__main__":
    print(fetch_emails_last_24_hours())

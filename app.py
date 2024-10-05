from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# PostgreSQL connection parameters
DB_HOST_NAME = os.getenv('DB_HOST_NAME')
MAINTENANCE_DB = os.getenv('MAINTENANCE_DB')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
print(f"DB Connection - Host: {DB_HOST_NAME}, DB: {MAINTENANCE_DB}, Username: {DB_USERNAME}")

app = FastAPI()

class URLRequest(BaseModel):
    url: str

def clean_website_url(url):
    # If the URL doesn't have a scheme (http/https), prepend 'https://'
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed_url = urlparse(url)
    scheme = parsed_url.scheme  # Extract scheme (http/https)
    netloc = parsed_url.netloc  # Extract domain (including subdomain if any)
    
    # Remove 'www.' if present in the domain
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Return the cleaned base URL (protocol + domain)
    cleaned_url = f"{scheme}://{netloc}"
    print(f"Cleaned URL: {cleaned_url}")
    return cleaned_url

def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST_NAME,
            database=MAINTENANCE_DB,
            user=DB_USERNAME,
            password=DB_PASSWORD
        )
        print("Database connection successful.")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def format_applied_date(applied_date):
    # If applied_date is already a datetime object, just format it directly
    if isinstance(applied_date, datetime):
        return applied_date.strftime("%B %d, %Y, %I:%M %p")
    
    # If applied_date is a string, try to parse it
    if isinstance(applied_date, str):
        try:
            parsed_date = datetime.fromisoformat(applied_date)
            return parsed_date.strftime("%B %d, %Y, %I:%M %p")
        except ValueError:
            # If the string is not in ISO format, return it as is or handle it
            return applied_date
    
    # If applied_date is None or unrecognized, return a default message
    return "Unknown date"

@app.post("/check-url")
async def check_url(request: URLRequest):
    print(f"Received URL: {request.url}")
    cleaned_url = clean_website_url(request.url)  # Clean the input URL
    company_website = urlparse(cleaned_url).netloc  # Extract the domain

    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to the database.")
        raise HTTPException(status_code=500, detail="Unable to connect to the database.")

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT company_name, job_position, applied_date 
            FROM applied_companies 
            WHERE company_website = %s
            ORDER BY applied_date DESC;
            """
            print(f"Executing query for: {cleaned_url}")
            cursor.execute(query, (cleaned_url,))
            results = cursor.fetchall()  # Fetch all matching rows

        if results:
            # Build a response with multiple rows
            response_data = {
                "message": "Applied for the following positions:",
                "company_website": company_website,
                "applications": []
            }

            # Add each row to the applications list and format the date
            for row in results:
                formatted_date = format_applied_date(row[2])  # Convert the date to a readable format
                response_data["applications"].append({
                    "job_position": row[1],
                    "applied_date": formatted_date
                })

            return response_data
        else:
            # Return the company website even if no matching applications are found
            return {
                "message": f"Not yet applied to {company_website}",
                "company_website": company_website
            }
    except Exception as e:
        print(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e}")
    finally:
        conn.close()

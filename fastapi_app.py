from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse,JSONResponse, FileResponse, Response
from pydantic import BaseModel
from urllib.parse import urlparse
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
import pandas as pd
import matplotlib.pyplot as plt
import io
from LLM_agents.vector_search_agent import perform_similarity_search, generate_openai_response, connect_to_postgres
from LLM_agents.text_to_sql_agent import generate_sql_query, execute_sql_query, visualize_sql_result
from LLM_agents.agent_selector_assistant import select_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# PostgreSQL connection parameters
DB_HOST_NAME = os.getenv('DB_HOST_NAME')
MAINTENANCE_DB = os.getenv('MAINTENANCE_DB')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
logging.info(f"DB Connection - Host: {DB_HOST_NAME}, DB: {MAINTENANCE_DB}, Username: {DB_USERNAME}")

app = FastAPI()

class URLRequest(BaseModel):
    url: str

class UserQueryRequest(BaseModel):
    query: str

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
    logging.info(f"Cleaned URL: {cleaned_url}")
    return cleaned_url

def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST_NAME,
            database=MAINTENANCE_DB,
            user=DB_USERNAME,
            password=DB_PASSWORD
        )
        logging.info("Database connection successful.")
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
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
    logging.info(f"Received URL: {request.url}")
    cleaned_url = clean_website_url(request.url)  # Clean the input URL
    company_website = urlparse(cleaned_url).netloc  # Extract the domain

    conn = connect_to_db()
    if conn is None:
        logging.error("Failed to connect to the database.")
        raise HTTPException(status_code=500, detail="Unable to connect to the database.")

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT company_name, job_position, applied_date 
            FROM applied_companies 
            WHERE company_website = %s
            ORDER BY applied_date DESC;
            """
            logging.info(f"Executing query for: {cleaned_url}")
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
        logging.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e}")
    finally:
        conn.close()

@app.post("/get_user_query")
async def get_user_query(request: UserQueryRequest):
    user_query = request.query
    logging.info(f"Received user query: {user_query}")

    try:
        agent = select_agent(user_query)
        logging.info(f"Selected Agent is: {agent}")
        
        if agent=='invalid question':
            response = "Please ask relevant questions about a company!!!!"

            return StreamingResponse(iter([response]), media_type="text/plain")
        
        elif agent=='vector_search_agent':

            # Step 1: Connect to the database
            conn = connect_to_postgres()
            if conn is None:
                raise HTTPException(status_code=500, detail="Unable to connect to the database.")

            try:
                # Step 2: Perform similarity search
                result = perform_similarity_search(conn, user_query)
                
                if result:
                    # Step 3: Generate a streaming response using OpenAI GPT-3.5
                    return StreamingResponse(generate_openai_response(user_query, result), media_type="text/plain")
                else:
                    return {"message": "No similar company found for the query."}
                
            except Exception as e:
                logging.error(f"Error in handling query: {e}")
                raise HTTPException(status_code=500, detail=f"Error processing the query: {e}")
            
            finally:
                if conn:
                    conn.close()
                    logging.info("Database connection closed.")

        elif agent=='text_to_sql_agent':

            # Step 1: Connect to the database
            conn = connect_to_postgres()
            if conn is None:
                raise HTTPException(status_code=500, detail="Unable to connect to the database.")
            
            try:
                # Step 2: Generate SQL query and chart type
                json_response = generate_sql_query(user_query)
                
                if not json_response or 'sql' not in json_response:
                    return {"message": "Failed to generate SQL query or chart."}
                    
                sql_query = json_response['sql']
                chart_type = json_response.get('chart_type', 'Null')
                
                # Step 3: Execute the SQL query
                headers, result = execute_sql_query(conn, sql_query)
                
                # Step 4: Process and return results
                if chart_type == 'Null':
                    # Convert result to DataFrame and handle datetime serialization
                    table = pd.DataFrame(result, columns=headers)
                    
                    # Convert all datetime columns to ISO format strings
                    for column in table.columns:
                        if isinstance(table[column].iloc[0], (datetime, pd.Timestamp)):
                            table[column] = table[column].apply(lambda x: x.isoformat() if x else None)
                    
                    return JSONResponse(content=table.to_dict(orient='records'))
                else:
                    # Generate visualization
                    buffer = io.BytesIO()
                    visualize_sql_result(result, headers, chart_type)
                    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)
                    plt.close()
                    
                    buffer.seek(0)
                    image_bytes = buffer.getvalue()
                    buffer.close()
                    
                    return Response(
                        content=image_bytes,
                        media_type="image/png",
                        headers={
                            "Content-Disposition": "inline",
                            "Cache-Control": "no-cache"
                        }
                    )
                    
            except Exception as e:
                logging.error(f"Error in handling query: {e}")
                raise HTTPException(status_code=500, detail=str(e))
            
            finally:
                if conn:
                    conn.close()
                    logging.info("Database connection closed.")

    except Exception as e:
        logging.error(f"Error in handling query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing the query: {e}")
    


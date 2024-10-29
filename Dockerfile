# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the requirements files
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV PREFECT_API_URL=http://54.183.74.135:4200

# Expose the ports
EXPOSE 8000
EXPOSE 4200

# Start the Prefect server and FastAPI
CMD ["sh", "-c", "nohup prefect server start --host 0.0.0.0 & nohup python prefect/prefect_flow.py & python -m uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload"]


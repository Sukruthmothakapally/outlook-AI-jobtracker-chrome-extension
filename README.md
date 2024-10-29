# AI-Powered Outlook Job Tracker

## Overview
The **AI-Powered Outlook Job Tracker** is a Chrome extension integrated with a FastAPI backend that helps users keep track of job applications seamlessly. It notifies users when they land on a company's website if they’ve already applied to that company and displays relevant application details like job position and application date. Additionally, the extension features a query interface where users can ask specific questions about their job applications, leveraging LLM-powered text-to-SQL and text-to-graph functionalities for data insights.

## Key Features

### Chrome Extension:
- Triggers when users visit a company website and checks if the user has applied to that company.
- Displays application details such as position applied for and the application date.
- Provides a query text box for users to ask questions about their applications, like "Did I apply to JP Morgan?" or "How many jobs did I apply for last month?"
- Graphical and statistical insights on job applications using text-to-graph and text-to-SQL capabilities.

### Backend:
- FastAPI backend, with endpoints that the Chrome extension communicates with to fetch company data from the PostgreSQL database.
- Two AI agents:
  - **Agent 1**: Handles queries related to specific companies using vector embeddings (e.g., "When did I apply to company X?").
  - **Agent 2**: Converts user queries into SQL or visual queries for data retrieval and visualization.

### Automated Workflow:
- A Prefect scheduler automates workflows every 24 hours to fetch, clean, and process job application data from Outlook.
- The data is loaded into PostgreSQL and vector embeddings are created for enhanced query performance.

## Tech Stack
- **Backend**: FastAPI, Python, Postgres, Docker, AWS
- **Frontend**: JavaScript, HTML (Chrome Extension)
- **AI Integration**: OpenAI GPT-4 (LLM-powered agents for query processing)
- **Database**: PostgreSQL with pgvector for embeddings
- **Automation**: Prefect (for scheduled workflows and ETL processes)
- **CI/CD**: GitHub Actions for continuous integration and deployment

## Work in Progress
This project has been completed and currently working on Continuous Integration and Continuous Deployment (CI/CD). Stay tuned for updates!
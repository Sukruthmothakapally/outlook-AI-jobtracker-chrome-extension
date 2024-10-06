# email_processing_dag.py
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from pipeline.outlookapi import fetch_emails_last_24_hours
from pipeline.gpt_processing_emails import extract_job_application_emails, trim_email_context
from pipeline.insert_to_db import process_and_insert_applications
from datetime import timedelta

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Initialize the DAG
with DAG(
    'email_processing_dag',
    default_args=default_args,
    description='Fetch, process, and insert job application emails into PostgreSQL',
    schedule_interval='*/15 * * * *',  # Run every 15 minutes
    start_date=days_ago(1),
    catchup=False,
) as dag:

    # Task 1: Fetch the emails from the last 24 hours
    def fetch_emails_task(**kwargs):
        emails = fetch_emails_last_24_hours()
        if emails:
            # Push the fetched email data to the next task using XCom
            kwargs['ti'].xcom_push(key='email_context', value=emails)

    fetch_emails = PythonOperator(
        task_id='fetch_emails_from_outlook',  # Updated task_id
        python_callable=fetch_emails_task,
        provide_context=True,
    )

    # Task 2: Process the fetched emails using GPT to filter job applications
    def process_emails_task(**kwargs):
        # Retrieve email context from the previous task (Task 1)
        email_context = kwargs['ti'].xcom_pull(task_ids='fetch_emails_from_outlook', key='email_context')  # Updated task_id reference
        if email_context:
            trimmed_email_context = trim_email_context(email_context, 3500)  # Trim email context for GPT input
            filtered_data = extract_job_application_emails(trimmed_email_context)
            # Push the filtered email data to the next task
            kwargs['ti'].xcom_push(key='filtered_data', value=filtered_data)

    process_emails = PythonOperator(
        task_id='clean_and_preprocess_emails_using_llm',  # Updated task_id
        python_callable=process_emails_task,
        provide_context=True,
    )

    # Task 3: Insert the filtered job applications into PostgreSQL
    def insert_to_db_task(**kwargs):
        # Retrieve the filtered data from Task 2
        filtered_data = kwargs['ti'].xcom_pull(task_ids='clean_and_preprocess_emails_using_llm', key='filtered_data')  # Updated task_id reference
        if filtered_data:
            process_and_insert_applications(filtered_data)

    insert_to_db = PythonOperator(
        task_id='insert_to_postgres',  # Updated task_id
        python_callable=insert_to_db_task,
        provide_context=True,
    )

    # Define task dependencies
    fetch_emails >> process_emails >> insert_to_db

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python

with Diagram("Architecture_diagram", show=False, direction="LR"):
    # Frontend Section
    with Cluster("Frontend"):
        frontend = Custom("", "./html_css_js.png")
        user = Custom("User", "./user.png")
        google = Custom("Google Search", "./google_search.png")
        extension = Custom("Chrome Extension", "./chrome_extension.jpg")
        
        user >> google >> extension

    # Backend Section
    with Cluster("Backend"):
        python = Python("Python")
        
        with Cluster("OpenAI Agents"):
            router = Custom("Router Agent", "./routing_agent.png")
            vector_search = Custom("Vector Search Agent", "./vector_agent.png")
            text_to_sql = Custom("Text-to-SQL/\nGraph Agent", "./text_to_sql.png")
            openai = Custom("OpenAI", "./openai.png")
            
            router >> vector_search
            router >> text_to_sql

        with Cluster("FastAPI Services"):
            api = FastAPI("FastAPI")
        
        db = PostgreSQL("PostgreSQL")

        # Prefect Data Pipeline
        outlook = Custom("Outlook", "./outlook.png")
        prefect = Custom("Prefect", "./prefect.png")
        
        etl = Custom("Extract Emails\nAI Processing\nGenerate Embeddings", "./etl.jpg")
        
        # Connections in the data pipeline
        outlook >> Edge(color="darkgreen") >> prefect
        prefect >> Edge(color="darkgreen") >> etl
        etl >> Edge(color="darkgreen") >> db

    # Infrastructure
    with Cluster("Infrastructure"):
        with Cluster("CI/CD"):
            git = Custom("Git", "./git.png")
            actions = Custom("GitHub Actions", "./github_actions.png")
            
            git >> actions

        with Cluster("AWS"):
            aws = Custom("AWS", "./aws.png")
            ec2 = EC2("EC2")
            rds = RDS("RDS")
            
            aws - ec2
            aws - rds

        docker = Docker("Docker")
        
        actions >> docker
        docker >> aws

    # Connections
    extension >> Edge(color="darkgreen") >> api
    api >> Edge(color="darkgreen") >> extension  

    api << Edge(color="darkgreen") >> openai  
    
    api >> Edge(color="darkgreen") >> db  
    db >> Edge(color="darkgreen") >> api  
    
    # Docker connections
    docker >> api  # FastAPI runs in Docker
    docker >> db   # PostgreSQL runs in Docker

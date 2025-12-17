import os
from dotenv import load_dotenv

# Load secrets from .env file
load_dotenv()

# CONFIGURATION (No more hardcoding!)
SERVER_NAME = os.getenv("DB_SERVER")
DATABASE_NAME = os.getenv("DB_NAME")
AWS_LLM_IP = os.getenv("AWS_LLM_IP")
AWS_URL = f"http://{AWS_LLM_IP}:{os.getenv('AWS_LLM_PORT')}/api/chat"
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import pyodbc
import requests
import re
import json

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SERVER_NAME = r'localhost\SQLEXPRESS'
DATABASE_NAME = 'pqFirstVerifyProduction'
AWS_LLM_IP = "15.207.85.212"  # <--- VERIFY IP
AWS_URL = f"http://{AWS_LLM_IP}:11434/api/chat"

app = FastAPI(title="FirstVerify AI Agent (Production)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all connections (for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------


class QuestionRequest(BaseModel):
    extraction_id: int
    question: str


# ==============================================================================
# GOLD STANDARD DICTIONARY (Safety Net)
# ==============================================================================
CORE_OVERRIDE = {
    "Producer Name": 55,
    "Insurer Name": 104,
    "GL Occurrence Limit": 19,
    "GL Aggregate Limit": 18,
    "Auto Combined Limit": 20,
    "Umbrella Limit": 21,
    "Workers Comp Limit": 22
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def get_hybrid_context():
    context_data = {}
    # 1. DB Fetch
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        query = "SELECT Q.QuestionText, A.QuestionBankId FROM AIMapping A JOIN Questions Q ON A.QuestionBankId = Q.QuestionBankId"
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                clean_name = row.QuestionText[:50].replace('\n', ' ').strip()
                context_data[clean_name] = row.QuestionBankId
        conn.close()
    except:
        pass

    # 2. Apply Overrides
    for name, id_val in CORE_OVERRIDE.items():
        context_data[name] = id_val
    return context_data


def call_llama_for_ids(prompt):
    payload = {
        "model": "llama3.2:1b",
        "messages": [{"role": "system", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0}
    }
    try:
        response = requests.post(AWS_URL, json=payload, timeout=90)
        if response.status_code == 200:
            return response.json()['message']['content']
        return ""
    except:
        return ""


def construct_sql_query(ai_text, extraction_id, context_map):
    """
    PRODUCTION UPGRADE:
    1. Extract IDs found by AI.
    2. Reverse-Lookup the ID in 'context_map' to find the Official Name.
    3. Generate SQL with human-readable Aliases (AS [Producer_Name]).
    """
    # 1. Extract numbers using Regex
    found_ids = re.findall(r'\b\d+\b', ai_text)

    # Filter out extraction_id to avoid confusion
    clean_ids = list(set([int(id)
                     for id in found_ids if id != str(extraction_id)]))

    if not clean_ids:
        return "-- ERROR: AI could not identify any valid data fields."

    # 2. Build the SQL Columns with Aliases
    sql_parts = []

    # Create a Reverse Dictionary: ID -> Name (e.g., 55 -> "Producer Name")
    # This ensures we use the OFFICIAL name from our DB/Config, not the AI's hallucination.
    id_to_name_map = {v: k for k, v in context_map.items()}

    for q_id in clean_ids:
        # Look up the name. If not found, fallback to Field_ID
        raw_name = id_to_name_map.get(q_id, f"Field_{q_id}")

        # Sanitize Name for SQL (Remove spaces, special chars)
        safe_alias = re.sub(r'[^a-zA-Z0-9]', '_', raw_name)

        # Remove trailing underscores if any
        safe_alias = safe_alias.strip('_')

        sql_parts.append(
            f"MAX(CASE WHEN QuestionBankId = {q_id} THEN ExtractedValue END) AS [{safe_alias}]")

    columns_sql = ",\n  ".join(sql_parts)

    final_sql = f"""SELECT 
  {columns_sql}
FROM ExtractedDataDetail
WHERE ExtractionId = {extraction_id};"""

    return final_sql

# ==============================================================================
# API ENDPOINT
# ==============================================================================


@app.post("/generate_sql")
def generate_sql(request: QuestionRequest):
    # 1. Context
    full_context_map = get_hybrid_context()

    # 2. Filter Rules
    user_words = request.question.lower().split()
    relevant_rules = ""
    for name, id_val in full_context_map.items():
        if any(word in name.lower() for word in user_words if len(word) > 2):
            relevant_rules += f"Field: '{name}' -> ID {id_val}\n"

    if not relevant_rules:
        for name, id_val in CORE_OVERRIDE.items():
            relevant_rules += f"Field: '{name}' -> ID {id_val}\n"

    # 3. Agent Prompt
    system_prompt = f"""
    You are a Data Retrieval Assistant.
    TASK: Identify which IDs the user is asking for.
    Output ONLY the matching IDs from the list below.
    
    ### DATA LIST ###
    {relevant_rules}
    
    ### EXAMPLE ###
    Data: 'Producer' -> ID 55, 'Insurer' -> ID 104
    User: "Who is the Producer?"
    Output: ID 55
    
    User Question: "{request.question}"
    Output (IDs only):
    """

    # 4. Call AI
    print(f"DEBUG: Asking AI to map concepts...")
    ai_response = call_llama_for_ids(system_prompt)
    print(f"DEBUG: AI said: {ai_response}")

    # 5. Python Builds the SQL (Passing context_map for naming)
    generated_sql = construct_sql_query(
        ai_response, request.extraction_id, full_context_map)

    return {
        "extraction_id": request.extraction_id,
        "original_question": request.question,
        "ai_identified_ids": ai_response,
        "generated_sql": generated_sql
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

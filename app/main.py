import os
from dotenv import load_dotenv
load_dotenv()

# Grabs everything from your .env file
SERVER_NAME = os.getenv("DB_SERVER", r'localhost\SQLEXPRESS')
DATABASE_NAME = os.getenv("DB_NAME", 'pqFirstVerifyProduction')
AWS_LLM_IP = os.getenv("AWS_LLM_IP")
AWS_URL = f"http://{AWS_LLM_IP}:11434/api/chat"

print(f"🚀 Service starting using LLM at: {AWS_URL}")

# print(f"🚀 Service starting using LLM at: {AWS_URL}")
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import pyodbc
import requests
import re
import json



app = FastAPI(title="FirstVerify AI Agent (Production)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all connections (for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------


# 1. Models for the Request and Feedback
class QuestionRequest(BaseModel):
    extraction_id: int
    question: str


class FeedbackRequest(BaseModel):
    question: str
    sql_generated: str
    is_positive: bool  # True for 👍, False for 👎


# 2. Updated GOLD STANDARD (Now including Static fields)
# Note: Static_ fields tell our logic to look at the 'Document' or 'Organization' tables
CORE_OVERRIDE = {
    "GST Number": "Static_GST",
    "PAN": "Static_PAN",
    "Company Name": "Static_OrgName",
    "Document Name": "Static_DocName",
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
           
            raw_text = response.json()['message']['content']
            # This removes <|start_header_id|>assistant<|end_header_id|> and other junk
            clean_text = re.sub(r'<\|.*?\|>', '', raw_text).strip()
            return clean_text
        else:
            print(f"❌ LLM API Error: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        # This will show the REAL error
        print(f"❌ Connection Error to LLM: {e}")
        return ""


def construct_sql_query(ai_text, extraction_id, context_map):
    # 1. Extract numbers using Regex
    found_ids = re.findall(r'\b\d+\b', ai_text)

    # --- ADD THIS LOGIC TO REMOVE JUNK ---
    # Convert to set to remove duplicates, and remove '0' and the extraction_id
    clean_ids = sorted(list(
        set([int(id) for id in found_ids if int(id) > 0 and id != str(extraction_id)])))
    # -------------------------------------

    if not clean_ids:
        # Check for static fields as a backup
        static_fields = []
        if "Static_GST" in ai_text:
            static_fields.append("D.DocumentId as GST_Number")
        if "Static_OrgName" in ai_text:
            static_fields.append("H.DocumentName as Company_Name")

        if not static_fields:
            return "-- ERROR: AI could not identify any valid data fields."

        select_clause = ",\n  ".join(static_fields)
    else:
        # Build dynamic columns
        id_to_name_map = {v: k for k, v in context_map.items()}
        sql_parts = []
        for q_id in clean_ids:
            raw_name = id_to_name_map.get(q_id, f"Field_{q_id}")
            safe_alias = re.sub(r'[^a-zA-Z0-9]', '_', raw_name).strip('_')
            sql_parts.append(
                f"MAX(CASE WHEN QuestionBankId = {q_id} THEN ExtractedValue END) AS [{safe_alias}]")

        select_clause = ",\n  ".join(sql_parts)

    final_sql = f"""SELECT 
  {select_clause}
FROM ExtractionHeader H
JOIN ExtractedDataDetail D ON H.ExtractionId = D.ExtractionId
WHERE H.ExtractionId = {extraction_id}
GROUP BY H.DocumentName, H.DocumentId;"""

    return final_sql
# ==============================================================================
# API ENDPOINT
# ==============================================================================


@app.get("/")
def home():
    return {"status": "Online", "service": "FirstVerify AI Agent"}
# -------------------------------------

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


    system_prompt = f"""
    [INST] You are a logic-only extraction engine.
    Match keywords from the User Question to the Knowledge Base.
    Output ONLY the ID numbers or Static_ tags separated by commas.
    DO NOT write SQL. DO NOT say "Here is the query." 
    If no match, output '0'.

    KNOWLEDGE BASE:
    {relevant_rules}

    User Question: "{request.question}"
    [/INST]
    Output (IDs only):"""
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


@app.post("/feedback")
def save_feedback(feedback: FeedbackRequest):
    print(
        f"📝 FEEDBACK RECEIVED: {feedback.question} -> {'👍' if feedback.is_positive else '👎'}")

    # In a real setup, we would save this to a SQL table 'AIFeedbackLogs'
    # For your demo, we will just log it to a file.
    with open("logs/feedback_loop.log", "a") as f:
        status = "GOLDEN" if feedback.is_positive else "FAILED"
        f.write(
            f"[{status}] Question: {feedback.question} | SQL: {feedback.sql_generated}\n")

    return {"status": "Feedback Saved"}


@app.post("/run_report")
def run_report(request: dict):
    sql_query = request.get("sql")
    if not sql_query or "-- ERROR" in sql_query:
        return {"error": "Invalid SQL query"}

    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute(sql_query)

        # Get column names for the table header
        columns = [column[0] for column in cursor.description]

        # Get all rows
        rows = cursor.fetchall()

        # Convert rows to a list of dicts for the frontend
        data = []
        for row in rows:
            data.append(dict(zip(columns, row)))

        conn.close()
        return {"columns": columns, "data": data}
    except Exception as e:
        return {"error": f"Database Error: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

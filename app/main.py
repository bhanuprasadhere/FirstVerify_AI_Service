import json
import re
import requests
import pyodbc
from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
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


# THE BROAD VIEW: FIXED RELATIONSHIP GRAPH
DB_RELATIONS = {
    "base": "ExtractionHeader H",
    "joins": [
        "JOIN ExtractedDataDetail D ON H.ExtractionId = D.ExtractionId",
        "JOIN Prequalification P ON H.PQID = P.PrequalificationId",
        "JOIN dbo.Organizations O ON P.VendorId = O.OrganizationID"
    ]
}


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
    "Tax ID": "Static_TaxID",
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
    # 1. Extract IDs and Static Keywords
    found_ids = re.findall(r'\b\d+\b', ai_text)
    clean_ids = sorted(list(
        set([int(id) for id in found_ids if int(id) > 0 and id != str(extraction_id)])))

    # 2. Identify Static fields
    static_fields = []
    if "Static_TaxID" in ai_text:
        static_fields.append("O.TaxID as Tax_Identification_Number")
    if "Static_OrgName" in ai_text:
        static_fields.append("O.Name as Company_Name")

    if not clean_ids and not static_fields:
        return "-- ERROR: AI could not identify any valid data fields."

    # 3. Build the dynamic columns
    id_to_name_map = {v: k for k, v in context_map.items()}
    dynamic_parts = []
    for q_id in clean_ids:
        raw_name = id_to_name_map.get(q_id, f"Field_{q_id}")
        safe_alias = re.sub(r'[^a-zA-Z0-9]', '_', raw_name).strip('_')
        dynamic_parts.append(
            f"MAX(CASE WHEN QuestionBankId = {q_id} THEN ExtractedValue END) AS [{safe_alias}]")

    select_clause = ",\n  ".join(static_fields + dynamic_parts)

    # 4. FINAL CORRECTED JOIN (Using VendorId as verified by your SSMS result)
    final_sql = f"""
SELECT 
  {select_clause}
FROM ExtractionHeader H
JOIN ExtractedDataDetail D ON H.ExtractionId = D.ExtractionId
JOIN Prequalification P ON H.PQID = P.PrequalificationId
JOIN dbo.Organizations O ON P.VendorId = O.OrganizationID
WHERE H.ExtractionId = {extraction_id}
GROUP BY O.Name, O.TaxID;"""

    return final_sql


# ==============================================================================
# API ENDPOINT
# ==============================================================================


@app.get("/")
def home():
    return {"status": "Online", "service": "FirstVerify AI Agent"}
# -------------------------------------


# --- THE FINAL ALIGNED SAFETY REPORT TEMPLATE ---
SAFETY_REPORT_TEMPLATE = """
SELECT Vendor, EMRStatsYear, emrVal AS EMR,
       [Number of days away from work: (total from Column K on your OSHA Form)] AS DaysAwayFromWork,
       [Number of fatalities: (total from Column G on your OSHA Form)] AS Fatalities,
       [Number of job transfer or restricted work day cases: (total from Column I on your OSHA Form)] AS jobTransfer,
       [Number of lost work day cases: (total from Column H on your OSHA Form)] AS LostWorkDay,
       [Number of other recordable cases: (total from Column J on your OSHA Form)] AS OtherRecordableCases,
       [Total Recordable Incident Rate (TRIR): (total from columns G, H, I, J) x 200,000 / Total employee hours] AS TRIRCases,
       [Total hours worked by all employees last year: (from your OSHA Form)] AS TotalHoursWorked
FROM (
    SELECT o.Name AS Vendor, pesv.QuestionColumnIdValue, pesy.EMRStatsYear, q.QuestionText, emr.emrVal
    FROM Prequalification p 
    JOIN Organizations o ON o.OrganizationID = p.VendorId 
    JOIN PrequalificationEMRStatsYears pesy ON pesy.PrequalificationId = p.PrequalificationId 
    JOIN PrequalificationEMRStatsValues pesv ON pesy.PrequalEMRStatsYearId = pesv.PrequalEMRStatsYearId 
    LEFT JOIN (
        SELECT PreQualificationId, MAX(UserInput) AS emrVal 
        FROM PrequalificationUserInput ui
        JOIN QuestionColumnDetails qcol ON qcol.QuestionColumnId = ui.QuestionColumnId
        JOIN Questions q ON q.QuestionID = qcol.QuestionId 
        WHERE q.QuestionText LIKE 'EMR%'
        GROUP BY PreQualificationId
    ) emr ON emr.PreQualificationId = p.PrequalificationId
    JOIN QuestionColumnDetails qd ON qd.QuestionColumnId = pesv.QuestionColumnId 
    JOIN Questions q ON q.QuestionID = qd.QuestionId 
    WHERE ISNUMERIC(pesy.EMRStatsYear) = 1 
      {WHERE_CLAUSE} 
) AS p 
PIVOT (
    MAX(QuestionColumnIdValue) FOR QuestionText IN (
        [Number of days away from work: (total from Column K on your OSHA Form)],
        [Number of fatalities: (total from Column G on your OSHA Form)],
        [Number of job transfer or restricted work day cases: (total from Column I on your OSHA Form)],
        [Number of lost work day cases: (total from Column H on your OSHA Form)],
        [Number of other recordable cases: (total from Column J on your OSHA Form)],
        [Total Recordable Incident Rate (TRIR): (total from columns G, H, I, J) x 200,000 / Total employee hours],
        [Total hours worked by all employees last year: (from your OSHA Form)]
    )
) AS piv 
WHERE CAST(EMRStatsYear AS DECIMAL(18,2)) > 2012 
ORDER BY Vendor, EMRStatsYear;
"""

@app.post("/generate_sql")
def generate_sql(request: QuestionRequest):
    question_lower = request.question.lower()

    # Recognize if the user wants safety stats (Dynamic Report)
    if any(word in question_lower for word in ["safety", "osha", "emr", "fatality", "rir", "dart"]):
        # Build the dynamic report SQL using Kiran's PIVOT template
        sql = SAFETY_REPORT_TEMPLATE.format(
            WHERE_CLAUSE=f"AND p.PrequalificationId = (SELECT PQID FROM ExtractionHeader WHERE ExtractionId = {request.extraction_id})"
        )
        return {
            "extraction_id": request.extraction_id,
            "original_question": request.question,
            "ai_identified_ids": "SAFETY_PIVOT_MODE",
            "generated_sql": sql
        }

    # Standard ID mapping logic for other questions
    full_context_map = get_hybrid_context()
    user_words = question_lower.split()
    relevant_rules = ""
    for name, id_val in full_context_map.items():
        if any(word in name.lower() for word in user_words if len(word) > 2):
            relevant_rules += f"Field: '{name}' -> ID {id_val}\n"

    if not relevant_rules:
        for name, id_val in CORE_OVERRIDE.items():
            relevant_rules += f"Field: '{name}' -> ID {id_val}\n"

    system_prompt = f"""
    [INST] You are a logic-only extraction engine. Output ONLY ID numbers or Static_ tags.
    KNOWLEDGE BASE:
    {relevant_rules}
    User Question: "{request.question}"
    [/INST]
    Output (IDs only):"""

    print(f"DEBUG: Asking AI to map concepts...")
    ai_response = call_llama_for_ids(system_prompt)
    print(f"DEBUG: AI said: {ai_response}")

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

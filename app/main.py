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

# 1. SETUP & ENVIRONMENT
load_dotenv()
SERVER_NAME = os.getenv("DB_SERVER", r'localhost\SQLEXPRESS')
DATABASE_NAME = os.getenv("DB_NAME", 'pqFirstVerifyProduction')
AWS_LLM_IP = os.getenv("AWS_LLM_IP")
AWS_URL = f"http://{AWS_LLM_IP}:11434/api/chat"

print(f"🚀 Service starting using LLM at: {AWS_URL}")

app = FastAPI(title="FirstVerify AI Agent (Production V7)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. MODELS


class QuestionRequest(BaseModel):
    extraction_id: int
    question: str


class FeedbackRequest(BaseModel):
    question: str
    sql_generated: str
    is_positive: bool


# 3. KNOWLEDGE BASE OVERRIDES
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
# HELPER FUNCTIONS (The "Discovery Engine")
# ==============================================================================


def get_dynamic_safety_sql(extraction_id=None):
    """
    METADATA DISCOVERY ENGINE: Fetches current safety questions from the DB 
    and builds the PIVOT query automatically.
    """
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Step A: Discover what safety columns exist in the DB right now
        cursor.execute("""
            SELECT DISTINCT q.QuestionText 
            FROM QuestionColumnDetails qd 
            JOIN Questions q ON q.QuestionID = qd.QuestionId 
            WHERE q.QuestionText LIKE '%OSHA%' OR q.QuestionText LIKE '%Recordable%' 
               OR q.QuestionText LIKE '%fatalit%' OR q.QuestionText LIKE '%Work Day%'
               OR q.QuestionText LIKE '%TRIR%'
        """)
        rows = cursor.fetchall()
        col_names = [f"[{row.QuestionText}]" for row in rows]

        if not col_names:
            return None, "No safety questions found in database."

        pivot_cols = ", ".join(col_names)

        # Step B: Build the PIVOT query
        where_filter = ""
        if extraction_id and extraction_id > 0:
            where_filter = f"AND p.PrequalificationId = (SELECT PQID FROM ExtractionHeader WHERE ExtractionId = {extraction_id})"

        query = f"""
        SELECT Vendor, EMRStatsYear, emrVal AS EMR, {pivot_cols}
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
            {where_filter}
        ) AS p 
        PIVOT (
            MAX(QuestionColumnIdValue) FOR QuestionText IN ({pivot_cols})
        ) AS piv 
        WHERE CAST(EMRStatsYear AS DECIMAL(18,2)) > 2012 
        ORDER BY Vendor, EMRStatsYear;
        """
        conn.close()
        return query, None
    except Exception as e:
        return None, str(e)


def get_hybrid_context():
    context_data = {}
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Q.QuestionText, A.QuestionBankId FROM AIMapping A JOIN Questions Q ON A.QuestionBankId = Q.QuestionBankId")
        for row in cursor.fetchall():
            context_data[row.QuestionText[:50]] = row.QuestionBankId
        conn.close()
    except:
        pass
    for name, id_val in CORE_OVERRIDE.items():
        context_data[name] = id_val
    return context_data


def call_llama_for_ids(prompt):
    payload = {"model": "llama3.2:1b", "messages": [
        {"role": "system", "content": prompt}], "stream": False, "options": {"temperature": 0.0}}
    try:
        response = requests.post(AWS_URL, json=payload, timeout=90)
        if response.status_code == 200:
            return re.sub(r'<\|.*?\|>', '', response.json()['message']['content']).strip()
    except:
        return ""


def construct_sql_query(ai_text, extraction_id, context_map):
    found_ids = re.findall(r'\b\d+\b', ai_text)
    clean_ids = sorted(list(
        set([int(id) for id in found_ids if int(id) > 0 and id != str(extraction_id)])))
    static_fields = []
    if "Static_TaxID" in ai_text:
        static_fields.append("O.TaxID as Tax_Identification_Number")
    if "Static_OrgName" in ai_text:
        static_fields.append("O.Name as Company_Name")

    id_to_name_map = {v: k for k, v in context_map.items()}
    dynamic_parts = [
        f"MAX(CASE WHEN QuestionBankId = {q_id} THEN ExtractedValue END) AS [{re.sub(r'[^a-zA-Z0-9]', '_', id_to_name_map.get(q_id, 'Field')).strip('_')}]" for q_id in clean_ids]

    select_clause = ",\n  ".join(static_fields + dynamic_parts)
    return f"SELECT \n  {select_clause}\nFROM ExtractionHeader H\nJOIN ExtractedDataDetail D ON H.ExtractionId = D.ExtractionId\nJOIN Prequalification P ON H.PQID = P.PrequalificationId\nJOIN dbo.Organizations O ON P.VendorId = O.OrganizationID\nWHERE H.ExtractionId = {extraction_id}\nGROUP BY O.Name, O.TaxID;"

# ==============================================================================
# API ENDPOINTS
# ==============================================================================


@app.get("/")
def home():
    return {"status": "Online", "service": "FirstVerify AI Agent"}


@app.get("/api/reports/safety_stats")
def get_safety_stats_report(extraction_id: int = None):
    sql, error = get_dynamic_safety_sql(extraction_id)
    if error:
        return {"status": "error", "message": error}
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return {"status": "success", "columns": columns, "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/generate_sql")
def generate_sql(request: QuestionRequest):
    question_lower = request.question.lower()
    if any(word in question_lower for word in ["safety", "osha", "emr", "fatality", "rir", "trir", "dart"]):
        sql, _ = get_dynamic_safety_sql(request.extraction_id)
        return {"extraction_id": request.extraction_id, "original_question": request.question, "ai_identified_ids": "SAFETY_PIVOT_MODE", "generated_sql": sql}
    full_context_map = get_hybrid_context()
    system_prompt = f"[INST] Match keywords to IDs. Output ONLY IDs. KNOWLEDGE BASE: {full_context_map} User Question: '{request.question}' [/INST]"
    ai_response = call_llama_for_ids(system_prompt)
    generated_sql = construct_sql_query(
        ai_response, request.extraction_id, full_context_map)
    return {"extraction_id": request.extraction_id, "original_question": request.question, "ai_identified_ids": ai_response, "generated_sql": generated_sql}


@app.post("/run_report")
def run_report(request: dict):
    sql_query = request.get("sql")
    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return {"columns": columns, "data": data}
    except Exception as e:
        return {"error": f"Database Error: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

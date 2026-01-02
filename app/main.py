import json
import re
import requests
import pyodbc
import os
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
SERVER_NAME = os.getenv("DB_SERVER", r'localhost\SQLEXPRESS')
DATABASE_NAME = os.getenv("DB_NAME", 'pqFirstVerifyProduction')
AWS_LLM_IP = os.getenv("AWS_LLM_IP", "13.232.17.234")
AWS_URL = f"http://{AWS_LLM_IP}:11434/api/chat"

app = FastAPI(title="FirstVerify AI Agent V8.2 - Enterprise Fixed")
app.add_middleware(CORSMiddleware, allow_origins=[
                   "*"], allow_methods=["*"], allow_headers=["*"])

# --- EXTENDED HEADER ALIASES ---
HEADER_ALIASES = {
    "Number of fatalities: (total from Column G on your OSHA Form)": "Fatalities",
    "Number of days away from work: (total from Column K on your OSHA Form)": "Days Away",
    "Total Recordable Incident Rate (TRIR): (total from columns G, H, I, J) x 200,000 / Total employee hours": "TRIR",
    "Total hours worked by all employees last year: (from your OSHA Form)": "Total Hours",
    "Number of lost work day cases: (total from Column H on your OSHA Form)": "Lost Work Days",
    "Number of job transfer or restricted work day cases: (total from Column I on your OSHA Form)": "Job Transfers",
    "Number of other recordable cases: (total from Column J on your OSHA Form)": "Other Recordables",
    "What is your company's total annual revenue?": "Annual Revenue",
    "What is your company's current net worth?": "Net Worth"
}


def get_pivot_sql(subject="Safety", extraction_id=None):
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;')
        cursor = conn.cursor()

        # Use broader keywords to ensure discovery doesn't return empty
        if subject == "Safety":
            keywords = "LIKE '%OSHA%' OR q.QuestionText LIKE '%TRIR%' OR q.QuestionText LIKE '%Recordable%'"
        else:
            keywords = "LIKE '%Revenue%' OR q.QuestionText LIKE '%Worth%' OR q.QuestionText LIKE '%Financial%'"

        # 1. Column Discovery
        cursor.execute(f"""
            SELECT DISTINCT q.QuestionText FROM QuestionColumnDetails qd 
            JOIN Questions q ON q.QuestionID = qd.QuestionId 
            JOIN PrequalificationEMRStatsValues pesv ON pesv.QuestionColumnId = qd.QuestionColumnId
            WHERE (q.QuestionText {keywords}) AND q.QuestionText NOT LIKE '%personnel approving%'
        """)
        rows = cursor.fetchall()
        if not rows:
            return None, f"No {subject} metadata found in the EMR stats table."

        col_names = [f"[{row.QuestionText}]" for row in rows]
        pivot_cols = ", ".join(col_names)
        where_clause = f"AND p.PrequalificationId = (SELECT PQID FROM ExtractionHeader WHERE ExtractionId = {extraction_id})" if extraction_id else ""

        query = f"""
        SELECT TOP 2000 Vendor, EMRStatsYear, emrVal AS EMR, {pivot_cols}
        FROM (
            SELECT o.Name AS Vendor, pesv.QuestionColumnIdValue, pesy.EMRStatsYear, q.QuestionText, emr.emrVal
            FROM Prequalification p 
            JOIN Organizations o ON o.OrganizationID = p.VendorId 
            JOIN PrequalificationEMRStatsYears pesy ON pesy.PrequalificationId = p.PrequalificationId 
            JOIN PrequalificationEMRStatsValues pesv ON pesy.PrequalEMRStatsYearId = pesv.PrequalEMRStatsYearId 
            LEFT JOIN (SELECT PreQualificationId, MAX(UserInput) AS emrVal FROM PrequalificationUserInput ui JOIN QuestionColumnDetails qcol ON qcol.QuestionColumnId = ui.QuestionColumnId JOIN Questions q ON q.QuestionID = qcol.QuestionId WHERE q.QuestionText LIKE 'EMR%' GROUP BY PreQualificationId) emr ON emr.PreQualificationId = p.PrequalificationId
            JOIN QuestionColumnDetails qd ON qd.QuestionColumnId = pesv.QuestionColumnId JOIN Questions q ON q.QuestionID = qcol.QuestionId 
            WHERE ISNUMERIC(pesy.EMRStatsYear) = 1 {where_clause}
        ) AS p PIVOT (MAX(QuestionColumnIdValue) FOR QuestionText IN ({pivot_cols})) AS piv 
        WHERE EMRStatsYear > '2012' ORDER BY Vendor, EMRStatsYear;
        """
        conn.close()
        return query, None
    except Exception as e:
        return None, str(e)

# --- API ENDPOINTS ---


class QuestionRequest(BaseModel):
    extraction_id: int
    question: str


@app.post("/generate_sql")
def generate_sql(request: QuestionRequest):
    q_low = request.question.lower()
    # FIXED: Corrected iteration variable name mismatch
    subject = "Financials" if any(key in q_low for key in [
                                  "revenue", "worth", "financial"]) else "Safety"
    sql, error = get_pivot_sql(subject, request.extraction_id)
    if error:
        return {"error": error}
    return {"generated_sql": sql, "ai_identified_ids": f"{subject.upper()}_PIVOT_MODE"}


@app.post("/run_report")
def run_report(request: dict):
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;')
        cursor = conn.cursor()
        cursor.execute(request.get("sql"))
        # Header translation happens here for both Dashboards and AI Search
        cols = [HEADER_ALIASES.get(c[0], c[0]) for c in cursor.description]
        data = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return {"columns": cols, "data": data}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/reports/paginated")
def get_paginated_report(subject: str = "Safety"):
    sql, error = get_pivot_sql(subject)
    if error:
        return {"status": "error", "message": error}
    res = run_report({"sql": sql})
    return {"status": "success", "columns": res["columns"], "data": res["data"]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

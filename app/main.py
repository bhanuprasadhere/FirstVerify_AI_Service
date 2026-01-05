import json
import re
import requests
import pyodbc
import os
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
SERVER_NAME = os.getenv("DB_SERVER", r'localhost\SQLEXPRESS')
DATABASE_NAME = os.getenv("DB_NAME", 'pqFirstVerifyProduction')
AWS_LLM_IP = os.getenv("AWS_LLM_IP", "13.232.17.234")
AWS_URL = f"http://{AWS_LLM_IP}:11434/api/chat"

app = FastAPI(title="FirstVerify AI Agent V8.4 - Production")
app.add_middleware(CORSMiddleware, allow_origins=[
                   "*"], allow_methods=["*"], allow_headers=["*"])

# --- COMPREHENSIVE HEADER ALIASES (30+ ENTRIES) ---
# Map database question text to short, clean column names
HEADER_ALIASES = {
    # === OSHA FATALITIES ===
    "Number of fatalities: (total from Column G on your OSHA Form)": "Fatalities",
    "Number of Fatalities:": "Fatalities",
    "Fatalities (from Column G):": "Fatalities",
    "Total fatalities": "Fatalities",

    # === OSHA DAYS AWAY ===
    "Number of days away from work: (total from Column K on your OSHA Form)": "Days Away",
    "Number of Days Away:": "Days Away",
    "Days Away from Work (Column K):": "Days Away",
    "Total days away": "Days Away",

    # === TRIR (TOTAL RECORDABLE INCIDENT RATE) ===
    "Total Recordable Incident Rate (TRIR): (total from columns G, H, I, J) x 200,000 / Total employee hours": "TRIR",
    "TRIR": "TRIR",
    "Total Recordable Incident Rate:": "TRIR",
    "TRIR (All Recordable Cases)": "TRIR",
    "Total Recordable Incidents per 200,000 hours": "TRIR",

    # === RIFR (RECORDABLE INCIDENT FREQUENCY RATE) ===
    "Recordable Incident Frequency Rate: # recordable cases (total from columns G, H, I, J) x 200,000 Total employee hours wo": "RIFR",
    "Recordable Incident Frequency Rate:": "RIFR",
    "RIFR": "RIFR",

    # === TOTAL HOURS WORKED ===
    "Total hours worked by all employees last year: (from your OSHA Form)": "Total Hours",
    "Total Hours Worked:": "Total Hours",
    "Annual Total Hours Worked": "Total Hours",
    "Hours Worked (Denominator)": "Total Hours",

    # === LOST WORK DAY CASES ===
    "Number of lost work day cases: (total from Column H on your OSHA Form)": "Lost Work Days",
    "Number of Lost Work Day Cases:": "Lost Work Days",
    "Lost Work Day Cases (Column H):": "Lost Work Days",
    "Total Lost Work Day Cases": "Lost Work Days",

    # === DART RATE (DAYS AWAY, RESTRICTED, OR TRANSFERRED) ===
    "DART: # of DART incidents (total from columns H and I) x 200,000 / Total employee hours worked last year": "DART Rate",
    "Days Away, Restrictions or Transfers Rate (DART)": "DART Rate",
    "DART Rate:": "DART Rate",
    "DART Cases per 200,000 hours": "DART Rate",
    "DART:": "DART",

    # === LOST WORK DAY RATE ===
    "Lost Work Day Case Rate: # lost work day cases (total from column H) x 200,000 / Total employee hours worked last year": "Lost Work Day Rate",
    "Lost Work Day Case Rate:": "Lost Work Day Rate",
    "LWDC Rate": "Lost Work Day Rate",

    # === JOB TRANSFER/RESTRICTED WORK ===
    "Number of job transfer or restricted work day cases: (total from Column I on your OSHA Form)": "Job Transfer/Restricted",
    "Job Transfer/Restricted (Column I):": "Job Transfer/Restricted",
    "Restricted Work Day Cases:": "Restricted Work Days",

    # === OTHER RECORDABLE CASES ===
    "Number of other recordable cases: (total from Column J on your OSHA Form)": "Other Recordable Cases",
    "Other Recordable Cases (Column J):": "Other Recordable Cases",
    "Medical Treatment Only Cases:": "Medical Treatment Only",

    # === EMR (EXPERIENCE MODIFICATION RATE) ===
    "EMR": "EMR Rating",
    "Experience Modification Rate:": "EMR Rating",
    "EMR Rating": "EMR Rating",

    # === FINANCIAL METRICS ===
    "Insurance Carrier(s):": "Insurance Carrier",
    "Insurance Carrier:": "Insurance Carrier",
    "Current Insurance Carrier": "Insurance Carrier",

    "General Liability – General Aggregate Limit Amount:": "GL Aggregate Limit",
    "GL Aggregate Limit:": "GL Aggregate Limit",
    "General Liability Aggregate": "GL Aggregate Limit",

    "Estimated Annual Premium:": "Est Annual Premium",
    "Annual Premium:": "Est Annual Premium",
    "Workers Comp Premium": "Est Annual Premium",

    "Do you only work in a limited geographic area?": "Limited Geographic Area",
    "Limited Geographic Area:": "Limited Geographic Area",
    "Geographic Coverage:": "Geographic Coverage",

    "Bodily Injury Liability per Incident:": "BI Liability/Incident",
    "Property Damage Liability per Incident:": "PD Liability/Incident",
}


def get_pivot_sql(subject="Safety", extraction_id=None):
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;ConnectionTimeout=30;')
        cursor = conn.cursor()

        # KEYWORD MATCHING FOR INTENT DETECTION
        if subject == "Safety":
            # Comprehensive safety keywords: OSHA metrics, incident rates, EMR
            kw = "LIKE '%OSHA%' OR q.QuestionText LIKE '%TRIR%' OR q.QuestionText LIKE '%Recordable%' OR q.QuestionText LIKE '%Fatalit%' OR q.QuestionText LIKE '%Work Day%' OR q.QuestionText LIKE '%EMR%' OR q.QuestionText LIKE '%DART%' OR q.QuestionText LIKE '%Lost%' OR q.QuestionText LIKE '%Restricted%'"
        else:
            # Financials - Must match ACTUAL column names in database (validated against real data)
            kw = "LIKE '%Insurance%' OR q.QuestionText LIKE '%Liability%' OR q.QuestionText LIKE '%Premium%' OR q.QuestionText LIKE '%Coverage%' OR q.QuestionText LIKE '%Aggregate%' OR q.QuestionText LIKE '%Bodily%' OR q.QuestionText LIKE '%Property Damage%'"

        # 1. Column Discovery with 120-char truncation to prevent SQL Error 42000
        cursor.execute(f"""
            SELECT DISTINCT LEFT(q.QuestionText, 120) as QuestionText 
            FROM QuestionColumnDetails qd 
            JOIN Questions q ON q.QuestionID = qd.QuestionId 
            JOIN PrequalificationEMRStatsValues pesv ON pesv.QuestionColumnId = qd.QuestionColumnId
            WHERE (q.QuestionText {kw}) AND q.QuestionText NOT LIKE '%personnel approving%'
        """)
        rows = cursor.fetchall()
        if not rows:
            return None, f"❌ No {subject} data found in database. The system may not have {subject} records configured."

        pivot_cols = ", ".join([f"[{r[0][:120]}]" for r in rows])
        where = f"AND p.PrequalificationId = (SELECT PQID FROM ExtractionHeader WHERE ExtractionId = {extraction_id})" if extraction_id else ""

        query = f"""
        SELECT TOP 100 Vendor, EMRStatsYear, emrVal AS EMR, {pivot_cols}
        FROM (
            SELECT o.Name AS Vendor, pesv.QuestionColumnIdValue, pesy.EMRStatsYear, LEFT(q.QuestionText, 120) as QuestionText, emr.emrVal
            FROM Prequalification p 
            JOIN Organizations o ON o.OrganizationID = p.VendorId 
            JOIN PrequalificationEMRStatsYears pesy ON pesy.PrequalificationId = p.PrequalificationId 
            JOIN PrequalificationEMRStatsValues pesv ON pesy.PrequalEMRStatsYearId = pesv.PrequalEMRStatsYearId 
            LEFT JOIN (SELECT PreQualificationId, MAX(UserInput) AS emrVal FROM PrequalificationUserInput ui JOIN QuestionColumnDetails qcol ON qcol.QuestionColumnId = ui.QuestionColumnId JOIN Questions q ON q.QuestionID = qcol.QuestionId WHERE q.QuestionText LIKE 'EMR%' GROUP BY PreQualificationId) emr ON emr.PreQualificationId = p.PrequalificationId
            JOIN QuestionColumnDetails qd ON qd.QuestionColumnId = pesv.QuestionColumnId JOIN Questions q ON q.QuestionID = qd.QuestionId 
            WHERE ISNUMERIC(pesy.EMRStatsYear) = 1 {where}
        ) AS p PIVOT (MAX(QuestionColumnIdValue) FOR QuestionText IN ({pivot_cols})) AS piv 
        WHERE EMRStatsYear > '2012' ORDER BY Vendor, EMRStatsYear;
        """
        conn.close()
        return query, None
    except Exception as e:
        return None, str(e)


@app.get("/api/reports/paginated")
def get_paginated_report(subject: str = "Safety"):
    # Input validation
    if subject not in ["Safety", "Financials"]:
        return {"status": "error", "message": f"Invalid subject '{subject}'. Must be 'Safety' or 'Financials'.", "data": [], "columns": []}

    sql, error = get_pivot_sql(subject)
    if error:
        return {"status": "error", "message": error, "data": [], "columns": []}
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;ConnectionTimeout=30;')
        cursor = conn.cursor()
        cursor.execute(sql)

        # Generate clean headers with fallback aliasing
        cols = []
        for column in cursor.description:
            col_text = column[0]
            # Try exact match first
            if col_text in HEADER_ALIASES:
                cols.append(HEADER_ALIASES[col_text])
            # Try prefix match for truncated columns
            else:
                for alias_key, alias_value in HEADER_ALIASES.items():
                    if alias_key.startswith(col_text[:50]):
                        cols.append(alias_value)
                        break
                else:
                    # Fallback: create readable name from question text
                    # Take first part before colon or parenthesis
                    readable = col_text.split(':')[0].split('(')[0].strip()
                    if len(readable) > 50:
                        readable = readable[:47] + "..."
                    cols.append(readable if readable else col_text)

        data = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()

        # Return success with metadata
        return {
            "status": "success",
            "columns": cols,
            "data": data,
            "record_count": len(data),
            "max_records": 100,
            "message": f"Loaded {len(data)} {subject} records (showing first 100 - optimized for performance)"
        }
    except Exception as e:
        return {"status": "error", "message": f"Database query failed: {str(e)}", "data": [], "columns": []}


class QuestionRequest(BaseModel):
    extraction_id: int
    question: str


@app.post("/generate_sql")
def generate_sql(request: QuestionRequest):
    # Input validation
    if not request.extraction_id or request.extraction_id <= 0:
        return {"status": "error", "error": "Invalid extraction_id. Must be a positive integer.", "generated_sql": None}
    if not request.question or len(request.question.strip()) == 0:
        return {"status": "error", "error": "Question cannot be empty.", "generated_sql": None}

    q_low = request.question.lower()
    # Enhanced financial keywords for better intent detection
    financial_keywords = ["revenue", "worth", "financial", "limit", "aggregate",
                          "insurance", "liability", "premium", "net", "annual",
                          "bodily", "property", "coverage", "carrier", "benefit"]
    sub = "Financials" if any(
        k in q_low for k in financial_keywords) else "Safety"

    sql, error = get_pivot_sql(sub, request.extraction_id)
    if error:
        return {"status": "error", "error": error, "generated_sql": None, "detected_subject": sub}

    return {
        "status": "success",
        "generated_sql": sql,
        "detected_subject": sub,
        "message": f"Generated {sub} report for extraction ID {request.extraction_id}"
    }


@app.post("/run_report")
def run_report(request: dict):
    # Input validation
    sql = request.get("sql")
    if not sql or len(sql.strip()) == 0:
        return {"status": "error", "error": "SQL query cannot be empty.", "data": [], "columns": []}

    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;ConnectionTimeout=30;')
        cursor = conn.cursor()
        cursor.execute(sql)

        # Generate clean headers with same logic as paginated endpoint
        cols = []
        for column in cursor.description:
            col_text = column[0]
            if col_text in HEADER_ALIASES:
                cols.append(HEADER_ALIASES[col_text])
            else:
                for alias_key, alias_value in HEADER_ALIASES.items():
                    if alias_key.startswith(col_text[:50]):
                        cols.append(alias_value)
                        break
                else:
                    readable = col_text.split(':')[0].split('(')[0].strip()
                    if len(readable) > 50:
                        readable = readable[:47] + "..."
                    cols.append(readable if readable else col_text)

        data = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()

        return {
            "status": "success",
            "columns": cols,
            "data": data,
            "record_count": len(data),
            "message": f"Successfully returned {len(data)} records"
        }
    except Exception as e:
        return {"status": "error", "error": f"Query execution failed: {str(e)}", "data": [], "columns": []}


# Mount static files LAST (after all API routes are defined)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

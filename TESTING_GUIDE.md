# FirstVerify Hybrid AI Reporting Engine - Complete Testing & Verification Guide

## Overview
This guide explains how to verify each component of the FirstVerify system works correctly.

---

## 1. ENVIRONMENT & PREREQUISITES CHECK

### 1.1 Python Virtual Environment
```powershell
# Navigate to project root
cd d:\AhaApps\FirstVerify_AI_Service

# Check if venv exists (look for venv folder)
dir venv

# If venv doesn't exist, create it:
python -m venv venv

# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again

# Verify Python is active
python --version
# Should show Python 3.x.x
```

### 1.2 Install Required Packages
```powershell
# Ensure venv is activated first
pip install fastapi uvicorn pyodbc pydantic python-dotenv requests

# Verify installations
pip list
# You should see:
#   - fastapi
#   - uvicorn
#   - pyodbc
#   - pydantic
#   - python-dotenv
#   - requests
```

### 1.3 Environment Variables (.env file)
Create a `.env` file in `d:\AhaApps\FirstVerify_AI_Service\`:
```
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=pqFirstVerifyProduction
AWS_LLM_IP=13.232.17.234
```

---

## 2. DATABASE CONNECTIVITY TEST

### 2.1 Test SQL Server Connection
```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Create a test script: test_db_connection.py
```

Create `d:\AhaApps\FirstVerify_AI_Service\test_db_connection.py`:
```python
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()
SERVER = os.getenv("DB_SERVER", r'localhost\SQLEXPRESS')
DATABASE = os.getenv("DB_NAME", 'pqFirstVerifyProduction')

print(f"Attempting to connect to: {SERVER} | Database: {DATABASE}")

try:
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
    
    # Test 1: Check if Questions table exists
    cursor.execute("SELECT COUNT(*) FROM Questions")
    count = cursor.fetchone()[0]
    print(f"✅ Database connected! Total questions in DB: {count}")
    
    # Test 2: Sample Safety keywords
    cursor.execute("""
        SELECT TOP 5 QuestionID, QuestionText 
        FROM Questions 
        WHERE QuestionText LIKE '%OSHA%'
    """)
    print("\n📋 Sample OSHA questions found:")
    for row in cursor.fetchall():
        print(f"  - {row.QuestionText[:80]}...")
    
    # Test 3: Check PrequalificationEMRStatsValues exists
    cursor.execute("SELECT COUNT(*) FROM PrequalificationEMRStatsValues")
    stat_count = cursor.fetchone()[0]
    print(f"\n✅ EMR Stats Values records: {stat_count}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Connection Failed: {e}")
```

Run it:
```powershell
python test_db_connection.py
```

**Expected Output:**
- ✅ Database connected message
- 📋 Sample OSHA questions listed
- ✅ EMR stats count displayed

---

## 3. BACKEND API TESTING

### 3.1 Start the FastAPI Server
```powershell
# From project root with venv activated
cd d:\AhaApps\FirstVerify_AI_Service

# Start server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

Keep this terminal open. The `--reload` flag restarts the server when you change code.

### 3.2 Test Endpoint 1: `/api/reports/paginated` (Safety)
Open a new PowerShell terminal:
```powershell
# Test Safety Dashboard
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/reports/paginated?subject=Safety" -Method Get | ConvertFrom-Json
$response.status
# Should print: "success"

$response.columns | Select-Object -First 5
# Should show column names like: Vendor, EMRStatsYear, EMR, Fatalities, Days Away, etc.

$response.data | Measure-Object
# Should show the count of records (up to 2000)
```

### 3.3 Test Endpoint 2: `/api/reports/paginated` (Financials)
```powershell
# Test Financials Dashboard
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/reports/paginated?subject=Financials" -Method Get | ConvertFrom-Json
$response.status
# Should print: "success" (if Financial questions exist in DB)
```

**Troubleshooting Financials:**
If you get "Metadata for Financials not found", the Keywords need adjustment. Check your Questions table:
```powershell
# In another PowerShell, run Python to check keywords
python -c "
import pyodbc
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=pqFirstVerifyProduction;Trusted_Connection=yes;')
cursor = conn.cursor()
cursor.execute(\"SELECT DISTINCT TOP 10 QuestionText FROM Questions WHERE QuestionText NOT LIKE '%OSHA%'\")
for row in cursor.fetchall():
    print(row[0][:100])
"
```

### 3.4 Test Endpoint 3: `/generate_sql` (Intent Detection)

**Test 3a: Safety Intent**
```powershell
$body = @{
    extraction_id = 3053
    question = "Show me TRIR and fatalities data"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/generate_sql" -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertFrom-Json | Select-Object -Property ai_identified_ids
# Should print: SAFETY_PIVOT_MODE
```

**Test 3b: Financials Intent**
```powershell
$body = @{
    extraction_id = 3053
    question = "What is the revenue limit and insurance coverage?"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/generate_sql" -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertFrom-Json | Select-Object -Property ai_identified_ids
# Should print: FINANCIALS_PIVOT_MODE
```

### 3.5 Test Endpoint 4: `/run_report` (Execute SQL)
```powershell
# First get a SQL query from generate_sql
$genBody = @{
    extraction_id = 3053
    question = "Show OSHA metrics"
} | ConvertTo-Json

$genRes = Invoke-WebRequest -Uri "http://127.0.0.1:8000/generate_sql" -Method Post `
  -ContentType "application/json" -Body $genBody | ConvertFrom-Json

$runBody = @{
    sql = $genRes.generated_sql
} | ConvertTo-Json

$runRes = Invoke-WebRequest -Uri "http://127.0.0.1:8000/run_report" -Method Post `
  -ContentType "application/json" -Body $runBody | ConvertFrom-Json

$runRes.columns | Head -5
# Should show column names

$runRes.data | Measure-Object
# Should show record count
```

---

## 4. FRONTEND TESTING

### 4.1 Start Frontend
Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

Wait - FastAPI doesn't serve static files by default. Update [app/main.py](app/main.py) to add:

```python
from fastapi.staticfiles import StaticFiles

# Add this AFTER creating the app:
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

Then restart the server. Now visit:
```
http://127.0.0.1:8000/
```

### 4.2 Test Frontend UI Elements

**Test 4a: Button Clicks Work**
1. Open Developer Console: Press `F12`
2. Go to **Network** tab
3. Click **Safety** button
4. You should see: `GET /api/reports/paginated?subject=Safety` request
5. Verify response status is `200`

**Test 4b: Data Loads in Table**
1. Click **Safety** button
2. Table should populate with rows
3. Check the pagination controls at bottom (Prev, Page numbers, Next)
4. Check the stats display: "Page 1 of X (Records: Y)"

**Test 4c: AI Search Button**
1. Enter Extraction ID: `3053`
2. Enter Question: `Show me safety metrics`
3. Click **AI Search**
4. In Developer Console Network tab, verify these requests fire:
   - `POST /generate_sql` (status 200)
   - `POST /run_report` (status 200)
5. Table should populate with results

**Test 4d: Pagination Navigation**
1. Load Safety dashboard
2. Click page numbers
3. Table rows should change
4. Stats display should update: "Page X of Y"

**Test 4e: Empty Data Handling**
1. Enter impossible search criteria
2. Pagination controls should disappear
3. Stats should show: "No records found."
4. Table area should stay hidden

### 4.3 Browser Console Debugging

While running, open Developer Console (`F12`) and check:
- **Console tab**: No JavaScript errors (red messages)
- **Network tab**: All requests return `200` or `201` status
- **Application tab** → Storage → Local Storage: Check if any state is stored

---

## 5. PERFORMANCE TESTING

### 5.1 Test Pagination Performance (Client-Side)
1. Click Safety to load 2,000 records
2. Click through pages rapidly (1→2→3→2→1)
3. Should respond instantly (< 100ms per page change)
4. Browser should NOT freeze

### 5.2 Test SQL Query Performance
```powershell
# Add timing to test
Measure-Command {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/reports/paginated?subject=Safety"
}
```

**Expected Timing:**
- Database query: < 2 seconds
- Total response: < 3 seconds

If slower, check SQL Server performance:
```powershell
# In SQL Server Management Studio:
# Enable Execution Plan (Ctrl+L)
# Run the query from the backend

SELECT TOP 2000 Vendor, EMRStatsYear, emrVal AS EMR
FROM (
    SELECT o.Name AS Vendor, pesv.QuestionColumnIdValue, pesy.EMRStatsYear, 
           LEFT(q.QuestionText, 120) as QuestionText, emr.emrVal
    FROM Prequalification p 
    -- ... rest of query
)
```

---

## 6. ERROR HANDLING & EDGE CASES

### 6.1 Test Database Timeout
```powershell
# Simulate by stopping SQL Server, then try API call
# Expected: Error message in response, no crash
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/reports/paginated?subject=Safety"
# Should return: {"status": "error", "message": "...connection failed..."}
```

### 6.2 Test Invalid Extraction ID
```powershell
$body = @{
    extraction_id = 999999
    question = "Show data"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/generate_sql" -Method Post `
  -ContentType "application/json" -Body $body | ConvertFrom-Json
# Should handle gracefully (return empty data, not crash)
```

### 6.3 Test Special Characters in Questions
```powershell
$body = @{
    extraction_id = 3053
    question = "Show data for O'Reilly & Co. (OSHA)"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/generate_sql" -Method Post `
  -ContentType "application/json" -Body $body | ConvertFrom-Json
# Should not throw SQL injection error
```

---

## 7. DEPLOYMENT CHECKLIST

Before deploying to production:

- [ ] Environment variables (.env) set correctly
- [ ] Database server is accessible
- [ ] All Python packages installed (`pip list` shows all deps)
- [ ] Safety dashboard returns data
- [ ] Financials dashboard returns data (or is configured to skip if N/A)
- [ ] AI Search button works (clicking fires `/generate_sql` request)
- [ ] Pagination works (can navigate pages)
- [ ] No JavaScript errors in browser console
- [ ] API responds within 3 seconds for 2,000 records
- [ ] Empty data is handled (no "Page 1 of 0" shown)

---

## 8. QUICK START VERIFICATION SCRIPT

Run this PowerShell script to verify everything:

```powershell
# Quick Test Script
Write-Host "🔍 FirstVerify System Verification" -ForegroundColor Cyan

# Test 1: Environment
Write-Host "`n1️⃣  Checking Python..."
python --version

# Test 2: Packages
Write-Host "`n2️⃣  Checking packages..."
pip list | Select-String "fastapi|uvicorn|pyodbc|pydantic"

# Test 3: Database
Write-Host "`n3️⃣  Testing database connection..."
python test_db_connection.py

# Test 4: API Health
Write-Host "`n4️⃣  Testing API endpoint..."
try {
    $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/reports/paginated?subject=Safety" -TimeoutSec 10
    if ($res.StatusCode -eq 200) {
        Write-Host "✅ API is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ API is not responding. Make sure uvicorn server is running." -ForegroundColor Red
}

Write-Host "`n✨ Verification complete!" -ForegroundColor Cyan
```

Save as `verify.ps1` and run:
```powershell
.\verify.ps1
```

---

## 9. COMMON ISSUES & SOLUTIONS

| Issue | Cause | Solution |
|-------|-------|----------|
| "Failed to Fetch" | CORS blocked or API not running | Check API is running on port 8000; verify CORS is enabled |
| "Page 1 of 0" | Empty dataset | Check filters; verify database has data for that subject |
| Button click doesn't work | HTML ID mismatch | Verify input IDs match JS selectors (extraction_id, user_question) |
| "SQL Error 42000" | Column name too long | Truncation to 120 chars should prevent this; check query |
| "Metadata not found" | Keywords don't match DB | Check actual question text in DB; add more keyword variants |
| Financials dashboard empty | Financial questions missing | Run query to see what financial question text exists in DB |

---

## 10. NEXT STEPS (PRODUCTION)

1. **Configure AWS LLM Integration** (if using Llama 3.2-1B):
   - Verify AWS EC2 instance is running on port 11434
   - Implement `/api/chat` endpoint integration in `generate_sql`

2. **Add Authentication**:
   - Add JWT tokens for API security
   - Require auth headers for sensitive endpoints

3. **Add Logging**:
   - Log all SQL queries to audit.log
   - Log API errors for debugging

4. **Optimize SQL**:
   - Add indexes to Questions, Organizations, Prequalification
   - Archive old data (> 5 years)

5. **Monitor Performance**:
   - Set up Application Insights in Azure
   - Alert if API response > 5 seconds

---

## Support
For issues, check:
1. Browser Console (F12) for JavaScript errors
2. Server logs (Uvicorn terminal) for Python errors
3. SQL Server Logs for database connection errors

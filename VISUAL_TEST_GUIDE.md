# FirstVerify - Visual Testing & Verification Guide

## 🎯 Visual Checklist - What You Should See

### Step 1️⃣: Database Verification
```
Run: python test_db_connection.py

EXPECTED OUTPUT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FirstVerify Database Connection Test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Server: localhost\SQLEXPRESS
Database: pqFirstVerifyProduction

✅ Connection established!

📋 TEST 1: Questions Table
   Total questions: [number > 0]

🔒 TEST 2: Safety Questions (OSHA)
   1. Number of fatalities: (total from Column G...)
   2. Number of days away from work: (total from Column K...)
   3. Total Recordable Incident Rate (TRIR)...

💰 TEST 3: Financial Questions
   [Should show results or ⚠️ No financial questions found]

📊 TEST 4: EMR Stats Values
   Total EMR stat records: [number > 0]

🏢 TEST 5: Organizations
   Total vendors/organizations: [number > 0]

🔎 TEST 6: Sample Extraction Data
   Extraction ID: [number], Prequalification ID: [number]

✂️  TEST 7: Question Text Length Check
   Length: [number] chars - Sample: [text]...

⚠️  TEST 8: SQL Column Name Limit Check
   Max question text length in DB: [number] chars
   ✅ All questions fit within 120-char limit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All tests completed successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PASS
```

---

### Step 2️⃣: Start Backend Server
```
Run: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

EXPECTED OUTPUT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ Server is ready. Leave this terminal open.

✅ PASS - Server Running
```

---

### Step 3️⃣: API Endpoint Testing
```
Run: python test_api.py

EXPECTED OUTPUT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FirstVerify API Endpoint Tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Testing: http://127.0.0.1:8000

📋 TEST 1: Safety Dashboard (/api/reports/paginated?subject=Safety)
────────────────────────────────────────────────────────────────────────
✅ Status: success
   Response time: 1.23s
   Columns: 9 found
     Sample: Vendor, EMRStatsYear, EMR, Fatalities, Days Away
   Records: 2000 returned
   First vendor: Acme Corp

💰 TEST 2: Financials Dashboard (/api/reports/paginated?subject=Financials)
────────────────────────────────────────────────────────────────────────
✅ Status: success
   Response time: 0.95s
   Records: 1500 returned

🔒 TEST 3: Generate SQL - Safety Intent (/generate_sql)
────────────────────────────────────────────────────────────────────────
✅ Intent detected: SAFETY_PIVOT_MODE
   Response time: 0.34s
   SQL Generated: Yes
   Query preview: SELECT TOP 2000 Vendor, EMRStatsYear, emrVal AS EMR...

💰 TEST 4: Generate SQL - Financials Intent (/generate_sql)
────────────────────────────────────────────────────────────────────────
✅ Intent detected: FINANCIALS_PIVOT_MODE
   Response time: 0.31s

📊 TEST 5: Run Report (/run_report)
────────────────────────────────────────────────────────────────────────
✅ Report executed successfully
   Response time: 1.45s
   Columns: 9 found
   Records: 2000 returned

🔍 TEST 6: Error Handling - Invalid Extraction ID
────────────────────────────────────────────────────────────────────────
✅ Error handled gracefully: [Error message]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ API Testing Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ALL 6 TESTS PASS
```

---

### Step 4️⃣: Frontend Browser Test
```
Open: http://127.0.0.1:8000/

EXPECTED SCREEN:
┌──────────────────────────────────────────────────────────────────┐
│                    FirstVerify AI V8.2 Enterprise                │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Extraction ID: [3053           ]                                │
│  Ask a Question: [Search safety, financials, or limits...  ]     │
│  [AI Search] [Safety] [Financials]                               │
│                                                                   │
│  System Ready.                                                    │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│  ✅ Page 1 of 40 (Records: 2000)  [Prev] [1] [2] [3] [Next]      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Vendor        EMRStatsYear  EMR   Fatalities  Days Away         │
│  ──────────────────────────────────────────────────────────      │
│  Acme Corp     2023          5.2   2           45                │
│  Baker Inc     2023          4.8   1           38                │
│  Charlie Ltd   2023          6.1   3           52                │
│  Delta Tech    2023          5.5   2           41                │
│  Echo Group    2023          4.9   1           35                │
│  ...                                                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

✅ PASS - Frontend Loaded
```

---

### Step 5️⃣: Button Click Tests

#### Test 5A: Click "Safety" Button
```
Action: Click the "Safety" button

EXPECTED:
✅ Table fills with data
✅ Shows vendors (Acme, Baker, etc.)
✅ Shows years (2023, 2024, etc.)
✅ Shows metrics (Fatalities, Days Away, TRIR, etc.)
✅ Pagination controls appear: [Prev] [1] [2] [3] [4] [5] [Next]
✅ Status shows: "Page 1 of 40 (Records: 2000)"

F12 Network Tab:
✅ GET /api/reports/paginated?subject=Safety
✅ Status: 200
✅ Response time: < 3 seconds

✅ PASS
```

#### Test 5B: Click "Financials" Button
```
Action: Click the "Financials" button

EXPECTED:
✅ Table fills with financial data OR
✅ Shows error message: "Metadata for Financials not found"
   (This is OK - means no financial questions in DB)

F12 Network Tab:
✅ GET /api/reports/paginated?subject=Financials
✅ Status: 200

✅ PASS
```

#### Test 5C: Click "AI Search" Button
```
Action: 
1. Enter Extraction ID: 3053
2. Enter Question: "Show OSHA TRIR metrics"
3. Click "AI Search"

EXPECTED:
✅ Status shows: "🤖 Analyzing..."
✅ Table fills with results
✅ Shows vendor data related to TRIR

F12 Network Tab:
✅ POST /generate_sql
   Status: 200
   Request: {"extraction_id": 3053, "question": "Show OSHA TRIR metrics"}
   
✅ POST /run_report
   Status: 200
   Request: {"sql": "[actual SQL query]"}

F12 Console:
✅ No red error messages

✅ PASS
```

---

### Step 6️⃣: Pagination Test

#### Test 6A: Click Page Numbers
```
Action:
1. Click "Safety" to load data
2. Click page number "2"
3. Click page number "3"
4. Click "Prev" to go back

EXPECTED:
✅ Rows change instantly (< 100ms)
✅ Stats update: "Page 2 of 40 (Records: 2000)"
✅ Different vendors/data shown per page
✅ No loading delay

F12 Console:
✅ No JavaScript errors

✅ PASS - Instant Client-Side Pagination
```

#### Test 6B: Navigate to Last Page
```
Action:
1. Click "Safety"
2. Click page "5" (last page)

EXPECTED:
✅ Shows page 5 data
✅ "Next" button disabled (grayed out)
✅ Fewer rows (< 50) on last page
✅ Stats shows correct page

✅ PASS
```

---

### Step 7️⃣: Edge Cases & Error Handling

#### Test 7A: Empty Result
```
Action:
1. Enter Question: "xyz123impossible"
2. Click "AI Search"

EXPECTED:
✅ Status: "No data returned"
✅ Pagination controls disappear (NOT shown)
✅ Table area stays hidden
✅ No "Page 1 of 0" message
✅ No JavaScript errors

F12 Console:
✅ No red errors

✅ PASS - Graceful Empty State
```

#### Test 7B: Special Characters
```
Action:
1. Enter Question: "O'Reilly & Co. (OSHA) 'damages'"
2. Click "AI Search"

EXPECTED:
✅ No SQL injection errors
✅ Either returns data or graceful error message
✅ No 500 error

F12 Network Tab:
✅ POST /generate_sql returns 200 (not 500)

✅ PASS - Safe SQL Handling
```

#### Test 7C: Server Error (Intentional)
```
Action:
1. Stop the backend server (kill the uvicorn process)
2. Click "Safety" button in browser

EXPECTED:
✅ Status: "Failed to Fetch" or similar error
✅ Table doesn't populate
✅ No blank screen
✅ Error message shown

✅ PASS - Error Handling
```

---

## 🎨 UI Element Checklist

### Header Section
- [ ] Title: "FirstVerify AI V8.2 Enterprise"
- [ ] Badge: "V8.2 Enterprise" shown in blue

### Control Panel
- [ ] Label: "Extraction ID"
- [ ] Input field: Contains "3053"
- [ ] Label: "Ask a Question"
- [ ] Input field: Contains placeholder "Search safety..."
- [ ] Button: "AI Search" (blue, clickable)
- [ ] Button: "Safety" (green, clickable)
- [ ] Button: "Financials" (yellow, clickable)
- [ ] Status text: "System Ready." or current status

### Pagination Section
- [ ] Prev button (disabled if page 1)
- [ ] Page number buttons (1, 2, 3, etc.)
- [ ] Next button (disabled if last page)
- [ ] Stats display: "Page X of Y (Records: Z)"

### Data Table
- [ ] Header row: Column names visible
- [ ] Data rows: 50 per page
- [ ] Striped styling: Alternating row colors
- [ ] Hover effect: Rows highlight on hover
- [ ] Data cells: Numbers formatted correctly

---

## 🔴 Red Flags ⚠️

### If You See These - Something is Wrong ❌

| Issue | What's Broken | Fix |
|-------|---------------|-----|
| "Page 1 of 0" | Pagination edge case | Should be fixed in renderPaginationUI() |
| No data in table | API not responding | Check uvicorn server running |
| "Failed to Fetch" | Backend not running | Run `uvicorn app.main:app --reload` |
| Red errors in F12 | JavaScript errors | Check [static/index.html](static/index.html) |
| Empty Financials | No financial questions | Check keywords in get_pivot_sql() |
| SQL Error 42000 | Column name too long | Check LEFT() truncation is 120 chars |
| Button doesn't work | ID mismatch | Check extraction_id, user_question IDs |

---

## ✅ Success Criteria

### All Tests Pass If:

1. **Database** ✅
   - `test_db_connection.py` shows all tests passing
   - Questions table has > 0 rows
   - EMR stats table has > 0 rows

2. **API** ✅
   - `test_api.py` shows 6/6 tests passing
   - All endpoints respond with 200 status
   - Response times < 3 seconds

3. **Frontend** ✅
   - Page loads at http://127.0.0.1:8000/
   - Safety button populates table
   - Financials button populates table (or shows error)
   - AI Search works with sample questions
   - Pagination works (click pages, stats update)

4. **No Errors** ✅
   - F12 Console has no red messages
   - F12 Network shows all 200 status codes
   - Browser doesn't freeze or crash
   - No blank screens or "Page 1 of 0"

---

## 📊 Performance Benchmarks

| Operation | Target | Acceptable | Check |
|-----------|--------|-----------|-------|
| DB Query | < 2s | < 3s | `test_api.py` output |
| API Response | < 3s | < 4s | F12 Network tab |
| Page Navigation | < 100ms | < 500ms | Click page number |
| Browser Load | < 500ms | < 1s | F12 Performance tab |

---

## 🎓 Interpreting Test Output

### ✅ This is Good
```
✅ Status: success
✅ Intent detected: SAFETY_PIVOT_MODE
✅ All tests completed successfully
Response time: 1.23s
```

### ⚠️ This Might Be OK
```
⚠️ No financial questions found
⚠️ No metadata found for Financials
```
(Means no financial questions in your DB - acceptable)

### ❌ This is Bad
```
❌ Connection Failed
❌ SQL Error 42000
❌ Failed to Fetch
No tests completed
```

---

## 🚀 Timeline

| Step | Action | Time | Status |
|------|--------|------|--------|
| 1 | Run `test_db_connection.py` | 2 min | ✅ |
| 2 | Start `uvicorn` server | 1 min | ✅ |
| 3 | Run `test_api.py` | 2 min | ✅ |
| 4 | Open browser, click Safety | 1 min | ✅ |
| 5 | Test AI Search | 2 min | ✅ |
| 6 | Test pagination | 2 min | ✅ |
| 7 | Test edge cases | 3 min | ✅ |

**Total: ~15 minutes for complete verification**

---

## 📞 Quick Help

### "How do I know if it's working?"
1. Database: `python test_db_connection.py` → All ✅
2. API: `python test_api.py` → All ✅
3. Frontend: Browser loads, buttons work, tables fill
4. No red errors in F12 Console

### "What if a test fails?"
1. Read the error message carefully
2. Check [BUG_FIXES.md](BUG_FIXES.md) for what was fixed
3. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for troubleshooting
4. Verify dependencies are installed: `pip list`

### "How do I restart the server?"
1. Press `Ctrl+C` in uvicorn terminal
2. Run: `uvicorn app.main:app --reload`
3. Refresh browser: `F5` or `Ctrl+R`

---

**Status: ✅ READY FOR TESTING**

Follow this guide in order. Each step should show the expected output. If any step shows something different, refer to troubleshooting in [TESTING_GUIDE.md](TESTING_GUIDE.md).

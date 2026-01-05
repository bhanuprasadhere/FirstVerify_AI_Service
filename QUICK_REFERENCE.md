# FirstVerify - Quick Reference Card

## 🚀 30-Second Start

```powershell
# Terminal 1: Setup
cd d:\AhaApps\FirstVerify_AI_Service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install fastapi uvicorn pyodbc pydantic python-dotenv requests

# Terminal 2: Verify Database
python test_db_connection.py

# Terminal 1: Start Server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 3: Test API
python test_api.py

# Browser: Open
http://127.0.0.1:8000/
```

---

## ✅ Test Checklist

- [ ] `test_db_connection.py` → All ✅
- [ ] `test_api.py` → All 6 tests ✅
- [ ] Browser opens http://127.0.0.1:8000/ → Loads ✅
- [ ] Click "Safety" → Table fills ✅
- [ ] Click "Financials" → Table fills ✅
- [ ] Click "AI Search" → Works ✅
- [ ] Click page numbers → Instant ✅
- [ ] F12 Console → No red errors ✅

---

## 🔧 6 Bugs Fixed

| Bug | Fix |
|-----|-----|
| HTML IDs mismatch | `ext_id` → `extraction_id`, `q` → `user_question` |
| SQL column too long | Truncate to 120 chars |
| Financials not found | Added more keywords |
| Pagination "Page 1 of 0" | Added empty data guard |
| uvicorn not imported | Added `import uvicorn` |
| Static files 404 | Mounted StaticFiles |

---

## 📂 Key Files

| File | Purpose |
|------|---------|
| [app/main.py](app/main.py) | Backend (FIXED) |
| [static/index.html](static/index.html) | Frontend (FIXED) |
| [test_db_connection.py](test_db_connection.py) | DB test |
| [test_api.py](test_api.py) | API test |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Detailed procedures |
| [BUG_FIXES.md](BUG_FIXES.md) | What was fixed & why |
| [VISUAL_TEST_GUIDE.md](VISUAL_TEST_GUIDE.md) | Visual checklist |

---

## 🎯 What to Expect

### Database
```
✅ ~5000 Questions
✅ ~2000 EMR Stats
✅ Keywords: OSHA, TRIR, Fatalities, etc.
```

### API
```
✅ 4 endpoints working
✅ < 3 sec response time
✅ Intent detection: Safety vs Financials
```

### Frontend
```
✅ Loads at http://127.0.0.1:8000/
✅ Buttons work instantly
✅ 50 rows/page, 40 pages total
✅ No errors in console
```

---

## 🔴 Red Flags

| Issue | Cause | Fix |
|-------|-------|-----|
| "Failed to Fetch" | Server not running | Run uvicorn |
| "Page 1 of 0" | Empty data | Check keywords |
| Button doesn't work | ID mismatch | Check HTML |
| Red errors in F12 | JS error | Check console |

---

## 🎮 Command Reference

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload

# Test database
python test_db_connection.py

# Test API
python test_api.py

# Stop server
Ctrl+C

# Deactivate venv
deactivate
```

---

## 📊 Quick Test Results Format

```
Database: ✅ PASS
  - Connection: OK
  - Questions: 5000+
  - EMR Stats: 2000+

API: ✅ PASS (6/6)
  - Safety Dashboard: 200
  - Financials Dashboard: 200
  - Generate SQL: 200
  - Run Report: 200
  - Intent Detection: OK
  - Error Handling: OK

Frontend: ✅ PASS
  - Loads: OK
  - Buttons: OK
  - Table: OK
  - Pagination: OK
  - Console: No errors
```

---

## 🎓 System Overview

```
User Input (Browser)
    ↓
JavaScript Event (Button Click)
    ↓
API Call (http://127.0.0.1:8000)
    ↓
FastAPI Endpoint (/api/reports/paginated)
    ↓
PIVOT SQL Generation
    ↓
SQL Server Query Execution
    ↓
JSON Response
    ↓
JavaScript Table Render
    ↓
Browser Display
```

---

## 📋 Troubleshooting Quick Guide

### Problem: "Failed to Fetch"
```
Check: 
1. uvicorn running? (Should see "Uvicorn running on...")
2. Port 8000 accessible? (Try http://127.0.0.1:8000/)
3. Firewall blocked? (Try disabling temporarily)
```

### Problem: No data in table
```
Check:
1. test_db_connection.py shows data?
2. Keywords match DB questions?
3. API endpoint works? (test_api.py)
```

### Problem: Button doesn't respond
```
Check:
1. F12 Console for errors
2. HTML IDs correct? (extraction_id, user_question)
3. API running? (test_api.py works?)
```

---

## 🏁 Success = All Green

```
Database:  ✅ Connected & Data Exists
API:       ✅ All Endpoints Respond  
Frontend:  ✅ Buttons Work & Data Displays
Console:   ✅ No Errors
Response:  ✅ < 3 Seconds
```

---

## 📞 Where to Find Help

| Question | Answer Location |
|----------|------------------|
| Why was X broken? | [BUG_FIXES.md](BUG_FIXES.md) |
| How do I test X? | [TESTING_GUIDE.md](TESTING_GUIDE.md) |
| What should I see? | [VISUAL_TEST_GUIDE.md](VISUAL_TEST_GUIDE.md) |
| What changed in code? | [app/main.py](app/main.py) & [static/index.html](static/index.html) |

---

## ⏱️ Expected Times

| Task | Duration |
|------|----------|
| Setup venv | 2 min |
| Install packages | 1 min |
| Test database | 2 min |
| Start server | 30 sec |
| Test API | 2 min |
| Test frontend | 5 min |
| **Total** | **~15 min** |

---

## 🎯 Next Steps After Verification

1. ✅ All tests pass → System is WORKING
2. Review [BUG_FIXES.md](BUG_FIXES.md) for what was fixed
3. Review [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed procedures
4. Configure for production (auth, logging, etc.)
5. Deploy to server

---

**Print this card and keep it nearby while testing!**

Last Updated: January 2, 2026

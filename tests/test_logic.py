from main import app, construct_sql_query
import sys
import os
from fastapi.testclient import TestClient

# --- FIX: Add the parent directory to the system path ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now it will find 'main' because we added the parent folder to the path

client = TestClient(app)

# ... (rest of your code stays the same)

# TEST 1: Check if API is alive


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "Online"

# TEST 2: Test the SQL Construction Logic (Pure Python)
# We mock the AI response to ensure Python builds SQL correctly


def test_sql_construction_producer():
    # Scenario: AI found ID 55
    ai_response = "I found ID 55 in the list."
    extraction_id = 100
    # Mock Context map
    context_map = {"Producer Name": 55}

    sql = construct_sql_query(ai_response, extraction_id, context_map)

    expected_snippet = "MAX(CASE WHEN QuestionBankId = 55 THEN ExtractedValue END) AS [Producer_Name]"
    assert expected_snippet in sql
    assert "WHERE ExtractionId = 100" in sql

# TEST 3: Test SQL Construction with Multiple IDs


def test_sql_construction_multiple():
    # Scenario: AI found 55 and 19
    ai_response = "IDs 55 and 19"
    extraction_id = 501
    context_map = {"Producer Name": 55, "GL Occurrence Limit": 19}

    sql = construct_sql_query(ai_response, extraction_id, context_map)

    assert "[Producer_Name]" in sql
    assert "[GL_Occurrence_Limit]" in sql

# TEST 4: Test SQL Safety (Empty/Garbage AI Response)


def test_sql_garbage_input():
    ai_response = "I couldn't find any relevant IDs."
    extraction_id = 999
    context_map = {}

    sql = construct_sql_query(ai_response, extraction_id, context_map)

    assert "-- ERROR: AI could not identify" in sql

from app.main import app, construct_sql_query
import sys
import os
from fastapi.testclient import TestClient

# ==============================================================================
# SETUP: Fix Python Path to find 'app' folder
# ==============================================================================
# Get the directory of this test file
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (FirstVerify_AI_Service root)
parent_dir = os.path.dirname(current_dir)
# Add root to sys.path so we can import 'app'
sys.path.append(parent_dir)

# --- THE FIX IS HERE ---
# Since main.py is inside the 'app' folder, we import from app.main

client = TestClient(app)

# ==============================================================================
# TESTS
# ==============================================================================


def test_home():
    response = client.get("/")
    assert response.status_code == 200


def test_sql_construction_producer():
    ai_response = "I found ID 55."
    extraction_id = 100
    context_map = {"Producer Name": 55}

    # We pass the context_map correctly now
    sql = construct_sql_query(ai_response, extraction_id, context_map)

    assert "AS [Producer_Name]" in sql
    assert "WHERE ExtractionId = 100" in sql


def test_sql_garbage_input():
    ai_response = "No IDs found."
    extraction_id = 999
    context_map = {}

    sql = construct_sql_query(ai_response, extraction_id, context_map)
    assert "-- ERROR" in sql

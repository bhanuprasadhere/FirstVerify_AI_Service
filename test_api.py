"""
API Endpoint Testing Script
Tests all FirstVerify API endpoints
Run AFTER uvicorn server is started
"""
import requests
import json
import io
import sys
from time import time

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://127.0.0.1:8000"


def test_api():
    print("=" * 80)
    print("FirstVerify API Endpoint Tests")
    print("=" * 80)
    print(f"Testing: {API_URL}\n")

    # Test 1: Safety Dashboard
    print("📋 TEST 1: Safety Dashboard (/api/reports/paginated?subject=Safety)")
    print("-" * 80)
    try:
        start = time()
        response = requests.get(
            f"{API_URL}/api/reports/paginated?subject=Safety", timeout=60)
        elapsed = time() - start

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data.get('status')}")
            print(f"   Response time: {elapsed:.2f}s")
            print(f"   Columns: {len(data.get('columns', []))} found")
            if data.get('columns'):
                print(f"     Sample: {', '.join(data.get('columns', [])[:5])}")
            print(f"   Records: {len(data.get('data', []))} returned")
            if data.get('data'):
                print(
                    f"   First vendor: {data['data'][0].get('Vendor', 'N/A')}")
        else:
            print(f"❌ Status Code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 2: Financials Dashboard
    print("💰 TEST 2: Financials Dashboard (/api/reports/paginated?subject=Financials)")
    print("-" * 80)
    try:
        start = time()
        response = requests.get(
            f"{API_URL}/api/reports/paginated?subject=Financials", timeout=10)
        elapsed = time() - start

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'error':
                print(f"⚠️  No data: {data.get('message')}")
            else:
                print(f"✅ Status: {data.get('status')}")
                print(f"   Response time: {elapsed:.2f}s")
                print(f"   Records: {len(data.get('data', []))} returned")
        else:
            print(f"❌ Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 3: Generate SQL - Safety Intent
    print("🔒 TEST 3: Generate SQL - Safety Intent (/generate_sql)")
    print("-" * 80)
    try:
        payload = {
            "extraction_id": 3053,
            "question": "Show me TRIR and fatalities data"
        }
        start = time()
        response = requests.post(
            f"{API_URL}/generate_sql", json=payload, timeout=10)
        elapsed = time() - start

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Intent detected: {data.get('ai_identified_ids')}")
            print(f"   Response time: {elapsed:.2f}s")
            print(
                f"   SQL Generated: {'Yes' if data.get('generated_sql') else 'No'}")
            if data.get('generated_sql'):
                sql = data['generated_sql'][:100] + \
                    "..." if len(data['generated_sql']
                                 ) > 100 else data['generated_sql']
                print(f"   Query preview: {sql}")
        else:
            print(f"❌ Status Code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 4: Generate SQL - Financials Intent
    print("💰 TEST 4: Generate SQL - Financials Intent (/generate_sql)")
    print("-" * 80)
    try:
        payload = {
            "extraction_id": 3053,
            "question": "What is the annual revenue limit and insurance premium?"
        }
        start = time()
        response = requests.post(
            f"{API_URL}/generate_sql", json=payload, timeout=10)
        elapsed = time() - start

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Intent detected: {data.get('ai_identified_ids')}")
            print(f"   Response time: {elapsed:.2f}s")
        else:
            print(f"❌ Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 5: Run Report
    print("📊 TEST 5: Run Report (/run_report)")
    print("-" * 80)
    try:
        # First get a SQL query
        gen_payload = {
            "extraction_id": 3053,
            "question": "OSHA safety metrics"
        }
        gen_response = requests.post(
            f"{API_URL}/generate_sql", json=gen_payload, timeout=10)

        if gen_response.status_code == 200:
            gen_data = gen_response.json()
            sql = gen_data.get('generated_sql')

            if sql:
                run_payload = {"sql": sql}
                start = time()
                run_response = requests.post(
                    f"{API_URL}/run_report", json=run_payload, timeout=10)
                elapsed = time() - start

                if run_response.status_code == 200:
                    run_data = run_response.json()
                    if 'error' in run_data:
                        print(f"❌ SQL Error: {run_data.get('error')[:200]}")
                    else:
                        print(f"✅ Report executed successfully")
                        print(f"   Response time: {elapsed:.2f}s")
                        print(
                            f"   Columns: {len(run_data.get('columns', []))} found")
                        print(
                            f"   Records: {len(run_data.get('data', []))} returned")
                else:
                    print(f"❌ Status Code: {run_response.status_code}")
            else:
                print("⚠️  No SQL generated")
        else:
            print(f"❌ Could not generate SQL")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 6: Error Handling - Invalid Extraction ID
    print("🔍 TEST 6: Error Handling - Invalid Extraction ID")
    print("-" * 80)
    try:
        payload = {
            "extraction_id": 999999999,
            "question": "Show data"
        }
        response = requests.post(
            f"{API_URL}/generate_sql", json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'error' in data:
                print(
                    f"✅ Error handled gracefully: {data.get('error')[:100]}...")
            else:
                print(f"⚠️  No error returned for invalid ID")
        else:
            print(f"⚠️  HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    print("=" * 80)
    print("✅ API Testing Complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_api()

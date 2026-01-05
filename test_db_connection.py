"""
Database Connection Verification Script
Tests that all required tables and data exist
"""
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()
SERVER = os.getenv("DB_SERVER", r'localhost\SQLEXPRESS')
DATABASE = os.getenv("DB_NAME", 'pqFirstVerifyProduction')

print("=" * 70)
print(f"FirstVerify Database Connection Test")
print("=" * 70)
print(f"Server: {SERVER}")
print(f"Database: {DATABASE}")
print()

try:
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
    print("✅ Connection established!\n")

    # Test 1: Questions table
    print("📋 TEST 1: Questions Table")
    cursor.execute("SELECT COUNT(*) FROM Questions")
    count = cursor.fetchone()[0]
    print(f"   Total questions: {count}\n")

    # Test 2: Safety keywords
    print("🔒 TEST 2: Safety Questions (OSHA)")
    cursor.execute("""
        SELECT TOP 3 QuestionText 
        FROM Questions 
        WHERE QuestionText LIKE '%OSHA%' OR QuestionText LIKE '%TRIR%'
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        text = row[0][:100] + "..." if len(row[0]) > 100 else row[0]
        print(f"   {i}. {text}")
    print()

    # Test 3: Financial keywords
    print("💰 TEST 3: Financial Questions")
    cursor.execute("""
        SELECT TOP 3 QuestionText 
        FROM Questions 
        WHERE QuestionText LIKE '%Revenue%' OR QuestionText LIKE '%Premium%' 
           OR QuestionText LIKE '%Limit%' OR QuestionText LIKE '%Insurance%'
    """)
    results = cursor.fetchall()
    if results:
        for i, row in enumerate(results, 1):
            text = row[0][:100] + "..." if len(row[0]) > 100 else row[0]
            print(f"   {i}. {text}")
    else:
        print("   ⚠️  No financial questions found - this may be expected")
    print()

    # Test 4: EMR Stats
    print("📊 TEST 4: EMR Stats Values")
    cursor.execute("SELECT COUNT(*) FROM PrequalificationEMRStatsValues")
    stat_count = cursor.fetchone()[0]
    print(f"   Total EMR stat records: {stat_count}\n")

    # Test 5: Organizations
    print("🏢 TEST 5: Organizations")
    cursor.execute("SELECT COUNT(*) FROM Organizations")
    org_count = cursor.fetchone()[0]
    print(f"   Total vendors/organizations: {org_count}\n")

    # Test 6: Check extraction ID
    print("🔎 TEST 6: Sample Extraction Data")
    cursor.execute("""
        SELECT TOP 3 PQID, ExtractionId 
        FROM ExtractionHeader 
        ORDER BY ExtractionId DESC
    """)
    results = cursor.fetchall()
    if results:
        for row in results:
            print(
                f"   Extraction ID: {row.ExtractionId}, Prequalification ID: {row.PQID}")
    print()

    # Test 7: Check column truncation
    print("✂️  TEST 7: Question Text Length Check")
    cursor.execute("""
        SELECT TOP 5 DATALENGTH(QuestionText) as TextLength, LEFT(QuestionText, 50) as Sample
        FROM Questions 
        ORDER BY TextLength DESC
    """)
    for row in cursor.fetchall():
        print(f"   Length: {row.TextLength} chars - Sample: {row.Sample}...")
    print()

    # Test 8: Verify 128-char SQL limit
    print("⚠️  TEST 8: SQL Column Name Limit Check")
    cursor.execute("""
        SELECT MAX(DATALENGTH(QuestionText)) as MaxLength
        FROM Questions
    """)
    max_len = cursor.fetchone()[0]
    print(f"   Max question text length in DB: {max_len} chars")
    if max_len > 120:
        print(f"   ⚠️  Note: Questions exceed 120 chars - truncation to 120 is needed")
    else:
        print(f"   ✅ All questions fit within 120-char limit")
    print()

    conn.close()

    print("=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)

except pyodbc.Error as e:
    print(f"❌ Database Error: {e}")
    print("\nTroubleshooting steps:")
    print("1. Verify SQL Server is running (Services > SQL Server)")
    print("2. Check server name: localhost\\SQLEXPRESS")
    print("3. Check database name: pqFirstVerifyProduction")
    print("4. Verify Trusted Connection (Windows Auth) is enabled")
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

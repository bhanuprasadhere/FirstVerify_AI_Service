import pyodbc
import requests
import json

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# 1. DATABASE DETAILS
SERVER_NAME = r'localhost\SQLEXPRESS'
DATABASE_NAME = 'pqFirstVerifyProduction'

# 2. AWS LLM SERVER DETAILS
# ⚠️ IMPORTANT: Check your AWS Console! This IP changes if you stop/start the server.
AWS_LLM_IP = "15.207.85.212"  # <--- REPLACE THIS WITH YOUR CURRENT PUBLIC IP
AWS_URL = f"http://{AWS_LLM_IP}:11434/api/chat"

# ==============================================================================
# FUNCTION 1: GET DYNAMIC CONTEXT (The "Knowledge")
# ==============================================================================


def get_db_context():
    """
    Connects to SQL, joins AIMapping with Questions to get readable names.
    Returns a dictionary: {'GL Limit': 19, 'Producer': 55}
    """
    context_data = {}
    print("🔌 Connecting to Database to build Context...")

    try:
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # We try to join with the Questions table to get human-readable names
        # If this returns empty, we will use the fallback hardcoded list below
        query = """
        SELECT Q.QuestionText, A.QuestionBankId 
        FROM AIMapping A 
        JOIN Questions Q ON A.QuestionBankId = Q.QuestionBankId
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        if rows:
            print(f"✅ Found {len(rows)} dynamic rules in database.")
            for row in rows:
                # Clean up the text (take first 30 chars) so it's not too long
                clean_name = row.QuestionText[:40].replace('\n', ' ').strip()
                context_data[clean_name] = row.QuestionBankId
        else:
            print("⚠️ Database returned no rows. Using Fallback Context.")
            # FALLBACK: If DB join is empty, use the list we know works
            context_data = {
                "GL Occurrence Limit": 19,
                "GL Aggregate Limit": 18,
                "Auto Combined Limit": 20,
                "Umbrella Limit": 21,
                "Producer Name": 55,
                "Insurer Name": 104
            }

        conn.close()

    except Exception as e:
        print(f"❌ DB Error: {e}")
        # Even if DB fails, we want the AI to work for the demo
        context_data = {"GL Occurrence Limit": 19, "Producer Name": 55}

    return context_data

# ==============================================================================
# FUNCTION 2: CALL THE AI (The "Brain")
# ==============================================================================


def ask_ai_to_write_sql(user_question, context_map):
    print(f"\n🚀 Sending Question to Llama 3.2: '{user_question}'...")

    # 1. Build the Dynamic Dictionary String
    context_str = ""
    for name, id_val in context_map.items():
        context_str += f"- '{name}' = ID {id_val}\n"

    # 2. Construct the "Few-Shot" System Prompt
    system_prompt = f"""
    You are a SQL Generator. Output ONLY SQL.

    Table: ExtractedDataDetail (DetailId, ExtractionId, QuestionBankId, ExtractedValue)

    DATA DICTIONARY:
    {context_str}

    ### EXAMPLE 1 (Copy this pattern!) ###
    User: Get the Producer Name and Insurer Name for ExtractionId 100.
    SQL: 
    SELECT 
      MAX(CASE WHEN QuestionBankId = 55 THEN ExtractedValue END) as Producer_Name,
      MAX(CASE WHEN QuestionBankId = 104 THEN ExtractedValue END) as Insurer_Name
    FROM ExtractedDataDetail
    WHERE ExtractionId = 100;
    ### END EXAMPLES ###

    Instructions:
    1. Use the DATA DICTIONARY to find the ID for the requested fields.
    2. Use the 'MAX(CASE WHEN...)' pattern from Example 1.
    3. Do not invent columns.
    """

    # 3. Send the Request
    payload = {
        "model": "llama3.2:1b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        "stream": False,
        "options": {"temperature": 0.0}
    }

    try:
        response = requests.post(AWS_URL, json=payload, timeout=30)

        if response.status_code == 200:
            ai_text = response.json()['message']['content']
            print("\n🤖 AI RESPONSE (Generated SQL):")
            print("-" * 50)
            print(ai_text.strip())
            print("-" * 50)
            return ai_text
        else:
            print(f"❌ AWS Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Tip: Check if your EC2 instance is running and the IP is correct!")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    # Step 1: Get the Knowledge
    my_context = get_db_context()

    # Step 2: Ask a Question
    # You can change this question to test different things!
    my_question = "Get the GL Occurrence Limit and Producer Name for ExtractionId 501."

    # Step 3: Run
    ask_ai_to_write_sql(my_question, my_context)

import pyodbc

# CONFIGURATION
# Update these to match your local SQL Server details
# CONFIGURATION
SERVER_NAME = r'localhost\SQLEXPRESS'  # The 'r' handles the backslash safely
DATABASE_NAME = 'pqFirstVerifyProduction'


def get_db_connection():
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER_NAME};'
        f'DATABASE={DATABASE_NAME};'
        f'Trusted_Connection=yes;'  # Uses your Windows Login
    )
    return pyodbc.connect(conn_str)


def get_ai_mappings():
    print("🔌 Connecting to Database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # We query the mapping table you created!
        query = "SELECT AI_Internal_Name, QuestionBankId FROM AIMapping"
        cursor.execute(query)

        rows = cursor.fetchall()

        print(f"✅ Success! Found {len(rows)} mapping rules.")

        # Convert to a Dictionary for our Context Builder
        # Logic: We are building the "Look up list" for the AI
        mapping_dict = {}
        for row in rows:
            # We map the AI Name (e.g., 'GL_Limit') to the ID (e.g., 19)
            # Just printing them for now to prove it works
            print(
                f"   - Map: {row.AI_Internal_Name} -> ID {row.QuestionBankId}")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")


# RUN IT
if __name__ == "__main__":
    get_ai_mappings()

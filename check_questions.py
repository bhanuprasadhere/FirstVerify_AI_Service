import pyodbc

conn_str = 'Driver={ODBC Driver 17 for SQL Server};Server=AAAAA-0F3D05;Database=FirstVerify;Trusted_Connection=yes;'
try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dbo.Questions")
    total = cursor.fetchone()[0]
    print(f'Total Questions: {total}')

    # Check what financial keywords exist
    financial_keywords = ['Revenue', 'Net Worth', 'Annual', 'Sales',
                          'Financial', 'Insurance', 'Liability', 'Premium', 'Coverage', 'Aggregate']

    print('\nFinancial Keyword Matches:')
    for kw in financial_keywords:
        cursor.execute(
            f"SELECT COUNT(*) FROM dbo.Questions WHERE QuestionText LIKE '%{kw}%'")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f'  {kw}: {count} questions')
            cursor.execute(
                f"SELECT TOP 2 QuestionText FROM dbo.Questions WHERE QuestionText LIKE '%{kw}%'")
            for row in cursor.fetchall():
                print(f'    -> {row[0][:70]}...' if len(row[0])
                      > 70 else f'    -> {row[0]}')

    conn.close()
except Exception as e:
    print(f'Error: {e}')

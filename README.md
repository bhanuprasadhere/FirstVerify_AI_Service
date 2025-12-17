# FirstVerify Hybrid AI SQL Engine (v7.0)

## 🚀 Executive Summary
A production-grade microservice that translates natural language queries into optimized T-SQL for the FirstVerify Normalized Database (EAV Architecture). 

Unlike standard "Text-to-SQL" solutions which are prone to syntax hallucinations, this system utilizes a **Hybrid Neuro-Symbolic Architecture**:
1.  **AI Layer (Llama 3.2):** Restricted solely to *Intent Extraction* (mapping concepts to Database IDs).
2.  **Logic Layer (Python):** Deterministically constructs SQL queries, ensuring 100% syntax compliance and SQL Injection immunity.

## 🏗️ Architecture
- **Backend:** Python FastAPI (Async)
- **AI Model:** Self-Hosted Llama 3.2-1B (AWS EC2)
- **Database:** SQL Server (ODBC) via Dynamic Context Mapping
- **Frontend:** Lightweight HTML5/JS Control Center

## ⚙️ Setup & Installation
1.  **Environment:** Ensure Python 3.13+ is installed.
2.  **Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configuration:**
    Create a `.env` file with your credentials:
    ```ini
    DB_SERVER=localhost\SQLEXPRESS
    DB_NAME=pqFirstVerifyProduction
    AWS_LLM_HOST=15.207.85.212
    ```
4.  **Run Service:**
    ```bash
    uvicorn app.main:app --reload
    ```

## 🛡️ Security Features
- **Gold Standard Override:** Critical fields (Producer, GL Limit) are hardcoded in the application layer to override potential DB inconsistencies.
- **Input Sanitization:** All AI outputs are scrubbed via Regex before SQL construction.
- **Logging:** Full audit trail available in `/logs/service.log`.
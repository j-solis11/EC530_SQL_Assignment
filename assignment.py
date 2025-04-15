import sqlite3
import pandas as pd
import os
import time
import openai
import re

DB_FILE = "chat_sheet.db"
ERROR_LOG = "error_log.txt"
API_KEY = "API_KEY_HERE"

def infer_schema_and_create_table(csv_file: str, table_name: str):
    print(f"infer_schema_and_create_table({csv_file}, {table_name})")
    df = pd.read_csv(csv_file)
    conn = sqlite3.connect(DB_FILE)
    dtype_map = {
        "object": "TEXT",
        "int64": "INTEGER",
        "float64": "REAL",
        "bool": "INTEGER",
        "datetime64": "TEXT"
    }
    columns = []
    for col in df.columns:
        print(f"Column: {col} | dtype: {df[col].dtype}")
        dtype = str(df[col].dtype)
        col_type = dtype_map.get(dtype, "TEXT")  # fallback to TEXT
        columns.append(f'"{col}" {col_type}')

    create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)});"
    print(f"🛠️ CREATE STMT: {create_stmt}")
    
    try:
        conn.execute(create_stmt)
        df.to_sql(table_name, conn, if_exists='append', index=False)
        conn.commit()
        print(f"Table '{table_name}' created from '{csv_file}'.")
    except Exception as e:
        log_error("Error")
    finally:
        conn.close()

def validate_and_handle_conflicts(table_name: str):
    print(f"validate_and_handle_conflicts({table_name})")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    print(tables)
    if table_name in tables:
        action = input(f"Table '{table_name}' exists. Overwrite (o), Rename (r), or Skip (s)? ").lower()
        if action == "o":
            conn = sqlite3.connect(DB_FILE)
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            conn.close()
            return table_name
        elif action == "r":
            return input("Enter new table name: ")
        elif action == "s":
            return None
    return table_name

def cli_assistant():
    print("Welcome to ChatSheet! Run commands with database.")
    while True:
        cmd = input(">> ").strip().lower()
        if cmd == "exit":
            print("Exiting ChatSheet...")
            break
        elif cmd.startswith("load "):
            parts = cmd.split()
            if len(parts) != 3:
                print("Usage: load <csv_file> <table_name>")
                continue
        
            csv_file, table_name = parts[1], parts[2]

            if not os.path.exists(csv_file):
                print(f"CSV file '{csv_file}' not found.")
                continue

            try:
                df = pd.read_csv(csv_file)
                if df.empty:
                    print(f"CSV file '{csv_file}' is empty.")
                    continue
            except Exception as e:
                print(f"Failed to read CSV: {e}")
                continue

            new_name = validate_and_handle_conflicts(table_name)
            if new_name:
                infer_schema_and_create_table(csv_file, new_name)
        elif cmd == "tables":
            #list_tables()
            get_table_schemas()
        run_response(cmd)
        '''
        elif cmd.startswith("query "):
            run_query(cmd[6:])
        elif cmd == "run":
            run_response()
        
        elif cmd == "help":
            print("Commands:\n  load <csv> <table>\n  query <sql>\n  tables\n  exit")
        else:
            print("Unknown command. Try 'help'.")
        '''

def list_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for t in tables:
        print("🗂", t[0])
    conn.close()

def get_table_schemas():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    schema_strings = []
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        col_defs = [f"{col[1]} {col[2]}" for col in columns]  # (cid, name, type, notnull, dflt_value, pk)
        schema_strings.append(f"- {table_name} ({', '.join(col_defs)})")

    conn.close()
    print(schema_strings)
    return "\n".join(schema_strings)

def run_query(query: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]
        print("\t".join(col_names))
        for row in results:
            print("\t".join(str(r) for r in row))
        conn.close()
    except Exception as e:
        log_error(str(e))
        print(f"Error: {e}")

def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{time.ctime()}] {msg}\n")

def run_llm_query(user_prompt: str):
    openai.api_key = API_KEY
    table_schemas = get_table_schemas()
    prompt = f"""
    You are an AI assistant tasked with converting user queries into SQL statements. 
    The database uses SQLite and contains the following tables:\n{table_schemas}\n
    User Query: "{user_prompt}"
    
    Please respond with the SQL query wrapped in a code block as follows:

    ```sql
    -- SQL query here
    ```

    Then respond with the explanation wrapped in a block as follows:
    '''explanation
    === explanation here
    '''
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    print(response['choices'][0]['message']['content'])

def run_response(full_response):
    match = re.search(r"```sql\s*(.*?)```", full_response, re.DOTALL)
    if not match:
        match = re.search(r"SQL Query:\s*(.*)", full_response)
    
    sql_query = match.group(1).strip() if match else None

    explanation_match = re.search(r"'''explanation\s*(.*?)\s*'''", full_response, re.DOTALL)
    
    explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided."

    # Output the explanation to the user
    print("\nExplanation:")
    print(explanation)

    if sql_query:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            results = cursor.fetchall()
            col_names = [description[0] for description in cursor.description] if cursor.description else []
            conn.close()

            print("\nQuery Results:")
            if col_names:
                print(" | ".join(col_names))
                for row in results:
                    print(" | ".join(str(cell) for cell in row))
            else:
                print("No result returned (e.g. DDL or update statement).")

        except Exception as e:
            print(f"\nError executing SQL: {e}")
    else:
        print("\nNo SQL query found in the response.")

if __name__ == "__main__":
    cli_assistant()
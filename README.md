# SQLite Query Assistant

A Python-based tool that allows you to interact with an SQLite database using natural language queries. It sends your query to OpenAI's API, retrieves the SQL query, and executes it on your SQLite database. The tool also provides an explanation of the query and outputs the results in the terminal.

## Features:
- Interact with SQLite database using natural language queries.
- Receive the SQL query that corresponds to your natural language prompt.
- Get an explanation of the SQL query.
- View the results of the query in a user-friendly format.
- Option to load CSV data into an SQLite table.
- List existing tables in the database.
- Command-line interface with an interactive prompt.

## Usage:
Start program with: python assignment.py

Commands Available:
  - exit: Exit the program
  - load <csv_filepath> <table_name>: Loads data from csv file into the   
    db with the name of the table
  - tables: Lists all of the table schemas in the terminal

If no commands are found in the user input, will send the input as a prompt with the existing table schemas.

## Requirements:
- Python 3.x
- Required Python libraries:
  - `sqlite3` (included in Python standard library)
  - `pandas`
  - `openai`


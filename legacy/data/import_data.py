import os
import json
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters using environment variables
db_params = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
}

def insert_data_from_json(json_file):
    # Connect to the database
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # Open and process each line in the JSON file
    with open(json_file, "r", encoding="utf-16") as file:
        for line in file:
            data = json.loads(line)

            source = data["source"]
            target = data["target"]

            # Insert into OriginalText
            cursor.execute(
                "INSERT INTO OriginalText (lang, text) VALUES (%s, %s) RETURNING text_id;",
                (source["lang"], source["text"]),
            )
            source_text_id = cursor.fetchone()[0]

            # Insert into Translation for the target
            cursor.execute(
                "INSERT INTO Translation (original_text_id, user_id, lang, text) VALUES (%s, %s, %s, %s) RETURNING translation_id;",
                (
                    source_text_id,
                    1,
                    target["lang"],
                    target["text"],
                ),  # Adding user_id as 1 to denote that original text is from echopod
            )
            translation_id = cursor.fetchone()[0]
            print(
                f"Inserted translation {translation_id} for source text {source_text_id}"
            )

    # Commit the transaction
    conn.commit()

    # Close the connection
    cursor.close()
    conn.close()

    print("Data inserted successfully.")


# Path to your JSON file
json_file_path = "/unicode_processed.json"
insert_data_from_json(json_file_path)

"""
Functions to handle redeployment of the bot on Heroku.
"""

import os
import psycopg2
import datetime
import subprocess


def clear_tables() -> None:
    # Clears all the data within all the tables in Heroku.
    DATABASE_URL = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute(
            "TRUNCATE TABLE credentials, invalid_sheets, default_links RESTART IDENTITY CASCADE;"
        )
        conn.commit()
        print("Tables cleared successfully.")
    except Exception as e:
        print("Failed to clear tables:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def restart_heroku() -> None:
    # Redeploys the app in Heroku.
    app_name = os.environ["HEROKU_APP_NAME"]
    subprocess.run(["heroku", "ps:restart", "--app", app_name], check=True)


def main() -> None:
    # Initiates redeployment once a week.
    if datetime.datetime.now().weekday() == 6:
        clear_tables()
        restart_heroku()


if __name__ == "__main__":
    main()

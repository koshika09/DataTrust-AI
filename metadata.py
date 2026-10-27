
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "Data" / "datatrust.db"


@contextmanager
def _database_connection():
    """Open a project-local SQLite connection with safe transaction handling."""
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection


def initialize_database():
    with _database_connection() as connection:
        connection.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_time TEXT NOT NULL,
            total_rows INTEGER NOT NULL,
            valid_rows INTEGER NOT NULL,
            quarantined_rows INTEGER NOT NULL
        )
        """)

        connection.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_lineage (
            lineage_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            source_file TEXT NOT NULL,
            transformation TEXT NOT NULL,
            output_file TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
        )
        """)


def save_pipeline_run(total_rows, valid_rows, quarantined_rows):
    with _database_connection() as connection:
        cursor = connection.execute("""
        INSERT INTO pipeline_runs (
            run_time,
            total_rows,
            valid_rows,
            quarantined_rows
        )
        VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            total_rows,
            valid_rows,
            quarantined_rows
        ))
        run_id = cursor.lastrowid

    print("Pipeline run saved to database. Run ID:", run_id)

    return run_id
def show_pipeline_runs():
    with _database_connection() as connection:
        cursor = connection.execute("""
        SELECT run_id, run_time, total_rows,
               valid_rows, quarantined_rows
        FROM pipeline_runs
        ORDER BY run_id DESC
        """)
        rows = cursor.fetchall()

    print("\n--- PIPELINE RUN HISTORY ---")

    for row in rows:
        print(row)


def save_lineage(run_id, source_file, transformation, output_file):
    with _database_connection() as connection:
        connection.execute("""
        INSERT INTO pipeline_lineage (
            run_id,
            source_file,
            transformation,
            output_file
        )
        VALUES (?, ?, ?, ?)
        """, (
            run_id,
            source_file,
            transformation,
            output_file
        ))

    print("Data lineage saved successfully.")


def show_lineage():
    with _database_connection() as connection:
        rows = connection.execute("""
        SELECT run_id, source_file, transformation, output_file
        FROM pipeline_lineage
        ORDER BY lineage_id DESC
        """).fetchall()

    print("\n--- DATA LINEAGE HISTORY ---")

    for row in rows:
        print(row)


def save_pipeline_run_with_lineage(
    total_rows, valid_rows, quarantined_rows, lineage_entries
):
    """Save a run and all its lineage rows as one transaction."""
    with _database_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO pipeline_runs (
                run_time, total_rows, valid_rows, quarantined_rows
            ) VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            total_rows,
            valid_rows,
            quarantined_rows
        ))
        run_id = cursor.lastrowid
        connection.executemany("""
            INSERT INTO pipeline_lineage (
                run_id, source_file, transformation, output_file
            ) VALUES (?, ?, ?, ?)
        """, [
            (run_id, source_file, transformation, output_file)
            for source_file, transformation, output_file in lineage_entries
        ])
    print("Pipeline run and lineage saved to database. Run ID:", run_id)
    return run_id




if __name__ == "__main__":
    initialize_database()
    print("DataTrust AI metadata database initialized successfully!")
    show_pipeline_runs()
    show_lineage()
    

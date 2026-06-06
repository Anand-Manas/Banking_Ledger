import os
import subprocess
import sys


def main():
    print("=== Railway Startup Debug ===", flush=True)
    port = os.environ.get("PORT", "8000")
    db_url = os.environ.get("DATABASE_URL", "NOT SET")
    print(f"PORT={port}", flush=True)
    print(f"DATABASE_URL={'YES' if db_url != 'NOT SET' else 'NO'}", flush=True)
    if db_url != "NOT SET":
        print(f"DATABASE_URL prefix={db_url[:60]}...", flush=True)

    # Run migrations with timeout (don't block forever)
    print("=== Running Alembic ===", flush=True)
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            print("Migrations OK", flush=True)
        else:
            print(f"Migrations stderr: {result.stderr}", flush=True)
            print(f"Migrations stdout: {result.stdout}", flush=True)
    except subprocess.TimeoutExpired:
        print("Migrations timed out after 15s", flush=True)
    except Exception as e:
        print(f"Migrations error: {e}", flush=True)

    # Start Uvicorn (exec replaces this process)
    print(f"=== Starting Uvicorn on port {port} ===", flush=True)
    os.execvp(
        "uvicorn",
        ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", port],
    )


if __name__ == "__main__":
    main()
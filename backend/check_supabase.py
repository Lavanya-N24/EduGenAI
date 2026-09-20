"""
EduGenAI - Supabase Database Check
Run: python check_supabase.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

async def main():
    print("=" * 55)
    print("  EduGenAI - Supabase Database Check")
    print("=" * 55)

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL not set in .env")
        sys.exit(1)

    print(f"\nConnecting to: {DATABASE_URL[:45]}...")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
    except ImportError:
        print("[ERROR] sqlalchemy not installed. Run: pip install sqlalchemy asyncpg")
        sys.exit(1)

    try:
        engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": "require"})
        async with engine.connect() as conn:
            print("[OK] Connected to Supabase PostgreSQL!\n")

            # List tables in public schema
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = [r[0] for r in result.fetchall()]

            if not tables:
                print("[INFO] No tables found yet.")
                print("       The backend creates tables on first startup.")
                print("       Make sure you ran the backend at least once.")
            else:
                print(f"Tables in Supabase ({len(tables)} found):")
                print("-" * 40)
                for t in tables:
                    r = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                    count = r.scalar()
                    status = "EMPTY" if count == 0 else f"{count} rows"
                    print(f"  {t:<20} : {status}")

                # Show latest video record if exists
                if "video_records" in tables:
                    r = await conn.execute(text(
                        "SELECT title, language, created_at FROM video_records "
                        "ORDER BY created_at DESC LIMIT 3"
                    ))
                    rows = r.fetchall()
                    if rows:
                        print("\nLatest video records:")
                        for row in rows:
                            print(f"  - {row[0]} ({row[1]}) at {row[2]}")

                # Show latest quiz attempts if exists
                if "quiz_attempts" in tables:
                    r = await conn.execute(text(
                        "SELECT topic, score, difficulty, created_at FROM quiz_attempts "
                        "ORDER BY created_at DESC LIMIT 3"
                    ))
                    rows = r.fetchall()
                    if rows:
                        print("\nLatest quiz attempts:")
                        for row in rows:
                            print(f"  - {row[0]} | score={row[1]} | {row[2]} | {row[3]}")

        await engine.dispose()
        print("\n[DONE] Check complete.")

    except Exception as e:
        print(f"[ERROR] Could not connect: {e}")
        print("\nPossible causes:")
        print("  1. DATABASE_URL is wrong in .env")
        print("  2. Supabase project is paused (check dashboard)")
        print("  3. IP not whitelisted (Supabase allows all IPs by default)")
        sys.exit(1)

asyncio.run(main())

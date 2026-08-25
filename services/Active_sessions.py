import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path


# AWS server par application ke andar local database file
DB_PATH = Path(__file__).resolve().parent.parent / "active_sessions.db"

# Isko apne existing auto-logout timeout ke barabar rakhein
SESSION_TIMEOUT_MINUTES = 15


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
        check_same_thread=False,
    )
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def initialize_session_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS active_sessions (
            username TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            employee_id TEXT,
            employee_name TEXT,
            login_time TEXT NOT NULL,
            last_activity TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def cleanup_expired_sessions():
    """Remove sessions which have been inactive beyond timeout."""

    cutoff = datetime.now() - timedelta(
        minutes=SESSION_TIMEOUT_MINUTES
    )

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM active_sessions
        WHERE last_activity < ?
        """,
        (cutoff.isoformat(),),
    )

    conn.commit()
    conn.close()


def create_session(username, employee_id, employee_name):
    """
    Create one active session for a user.

    Returns:
        (True, session_id)  -> login allowed
        (False, None)       -> already logged in
    """

    initialize_session_db()
    cleanup_expired_sessions()

    username = username.strip().lower()
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn = get_connection()

    try:
        # Atomic insert. Username is PRIMARY KEY,
        # therefore only one active session can exist.
        conn.execute(
            """
            INSERT INTO active_sessions
            (
                username,
                session_id,
                employee_id,
                employee_name,
                login_time,
                last_activity
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                session_id,
                str(employee_id),
                employee_name,
                now,
                now,
            ),
        )

        conn.commit()

        return True, session_id

    except sqlite3.IntegrityError:
        # User already has an active session
        return False, None

    finally:
        conn.close()


def update_activity(username, session_id):
    """Update last activity of the current session."""

    username = username.strip().lower()

    conn = get_connection()

    conn.execute(
        """
        UPDATE active_sessions
        SET last_activity = ?
        WHERE username = ?
          AND session_id = ?
        """,
        (
            datetime.now().isoformat(),
            username,
            session_id,
        ),
    )

    conn.commit()
    conn.close()


def logout_session(username, session_id):
    """Remove the current user's active session."""

    username = username.strip().lower()

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM active_sessions
        WHERE username = ?
          AND session_id = ?
        """,
        (
            username,
            session_id,
        ),
    )

    conn.commit()
    conn.close()


def get_active_users():
    """Return currently active users."""

    initialize_session_db()
    cleanup_expired_sessions()

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            username,
            employee_id,
            employee_name,
            login_time,
            last_activity
        FROM active_sessions
        ORDER BY login_time DESC
        """
    ).fetchall()

    conn.close()

    return rows


def get_active_user_count():
    """Return number of active users."""

    initialize_session_db()
    cleanup_expired_sessions()

    conn = get_connection()

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM active_sessions
        """
    ).fetchone()[0]

    conn.close()

    return count

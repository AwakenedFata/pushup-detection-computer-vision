"""
MySQL database layer for pushup session history.

Requires: pip install mysql-connector-python

Database : db_pushUpCv
Table    : sessions
Columns  :
  id              INT AUTO_INCREMENT PRIMARY KEY
  start_time      DATETIME NOT NULL
  end_time        DATETIME NOT NULL
  total_reps      INT NOT NULL DEFAULT 0
  correct_reps    INT NOT NULL DEFAULT 0
  incorrect_reps  INT NOT NULL DEFAULT 0
  duration_sec    FLOAT NOT NULL DEFAULT 0
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

import os

_DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST", "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "db_pushUpCv"),
}

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    start_time      DATETIME     NOT NULL,
    end_time        DATETIME     NOT NULL,
    total_reps      INT          NOT NULL DEFAULT 0,
    correct_reps    INT          NOT NULL DEFAULT 0,
    incorrect_reps  INT          NOT NULL DEFAULT 0,
    duration_sec    FLOAT        NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _get_connection():
    import mysql.connector  # lazy import — avoids hard crash if not installed
    return mysql.connector.connect(**_DB_CONFIG)


def ensure_table() -> bool:
    """Create the sessions table if it does not exist. Returns True on success."""
    try:
        conn = _get_connection()
        cur  = conn.cursor()
        cur.execute(_DDL)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.warning("DB: could not ensure table — %s", e)
        return False


def save_session(
    start_time:     datetime,
    end_time:       datetime,
    total_reps:     int,
    correct_reps:   int,
    incorrect_reps: int,
) -> int | None:
    """
    Insert one session row and return the new row id.
    Returns None if the insert fails (DB not available).
    """
    duration_sec = (end_time - start_time).total_seconds()
    sql = """
        INSERT INTO sessions
            (start_time, end_time, total_reps, correct_reps, incorrect_reps, duration_sec)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        conn = _get_connection()
        cur  = conn.cursor()
        cur.execute(sql, (
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
            total_reps,
            correct_reps,
            incorrect_reps,
            round(duration_sec, 2),
        ))
        conn.commit()
        row_id = cur.lastrowid
        cur.close()
        conn.close()
        logger.info("DB: session %d saved (reps=%d, correct=%d, wrong=%d)",
                    row_id, total_reps, correct_reps, incorrect_reps)
        return row_id
    except Exception as e:
        logger.warning("DB: failed to save session — %s", e)
        return None


def get_sessions(limit: int = 50) -> list[dict]:
    """Return the most recent sessions ordered by newest first."""
    sql = """
        SELECT id, start_time, end_time, total_reps,
               correct_reps, incorrect_reps, duration_sec
        FROM sessions
        ORDER BY start_time DESC
        LIMIT %s
    """
    try:
        conn = _get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Serialise datetime → ISO string for JSON
        for row in rows:
            row["start_time"] = row["start_time"].isoformat()
            row["end_time"]   = row["end_time"].isoformat()
        return rows
    except Exception as e:
        logger.warning("DB: failed to fetch sessions — %s", e)
        return []

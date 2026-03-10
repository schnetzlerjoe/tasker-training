#!/usr/bin/env python3
"""
mine_tasker_db.py — Extract recovery training pairs from Tasker's SQLite database.

Finds two recovery pattern types:
  1. explicit_failure — a step that failed (success=0) immediately followed by a
                        successful step (the agent recovered)
  2. backtrack        — a successful navigation step immediately followed by go_back
                        (the agent realised it went the wrong way)

Outputs: tasker_recovery_pairs.jsonl
  Each line is a JSON object with:
    type, task, workflow_name,
    failed_tool, failed_params, failed_error, failed_screenshot,
    recovery_tool, recovery_params, recovery_screenshot

Screenshots are base64 JPEG strings (same format Tasker stores them).
They can be fed directly into the notebook's convert_recovery_sample().

Usage:
    python mine_tasker_db.py
    python mine_tasker_db.py --db /custom/path/runs.db --out my_pairs.jsonl
"""

import argparse
import json
import sqlite3
from pathlib import Path

DB_PATH  = Path.home() / ".local" / "share" / "com.tasker.app" / "runs.db"
OUT_PATH = Path("tasker_recovery_pairs.jsonl")

NAVIGATION_TOOLS = {
    "click_element",
    "input_text",
    "go_to_url",
    "select_dropdown_option",
    "send_keys",
    "scroll_down",
    "scroll_up",
}


def get_explicit_recoveries(conn: sqlite3.Connection) -> list:
    """Failed step immediately followed by a successful step."""
    return conn.execute(
        """
        SELECT
            r.task_description,
            r.workflow_name,
            s1.tool_name    AS failed_tool,
            s1.params       AS failed_params,
            s1.error        AS failed_error,
            s1.screenshot   AS failed_screenshot,
            s2.tool_name    AS recovery_tool,
            s2.params       AS recovery_params,
            s2.screenshot   AS recovery_screenshot
        FROM run_steps s1
        JOIN run_steps s2
            ON  s1.run_id      = s2.run_id
            AND s2.step_number = s1.step_number + 1
        JOIN runs r ON s1.run_id = r.id
        WHERE s1.success = 0
          AND s2.success = 1
          AND s1.tool_name != 'done'
          AND s2.tool_name != 'done'
        ORDER BY s1.timestamp DESC
        """
    ).fetchall()


def get_backtrack_recoveries(conn: sqlite3.Connection) -> list:
    """Successful navigation step immediately followed by go_back."""
    return conn.execute(
        """
        SELECT
            r.task_description,
            r.workflow_name,
            s1.tool_name    AS prev_tool,
            s1.params       AS prev_params,
            NULL            AS prev_error,
            s1.screenshot   AS prev_screenshot,
            s2.tool_name    AS recovery_tool,
            s2.params       AS recovery_params,
            s2.screenshot   AS recovery_screenshot
        FROM run_steps s1
        JOIN run_steps s2
            ON  s1.run_id      = s2.run_id
            AND s2.step_number = s1.step_number + 1
        JOIN runs r ON s1.run_id = r.id
        WHERE s2.tool_name = 'go_back'
          AND s1.tool_name IN ('click_element', 'input_text', 'go_to_url')
          AND s1.success = 1
        ORDER BY s1.timestamp DESC
        """
    ).fetchall()


def row_to_dict(row: tuple, recovery_type: str) -> dict:
    def parse_json(s):
        try:
            return json.loads(s or "{}")
        except Exception:
            return {}

    return {
        "type":                recovery_type,
        "task":                row[0] or "",
        "workflow_name":       row[1] or "",
        "failed_tool":         row[2] or "",
        "failed_params":       parse_json(row[3]),
        "failed_error":        row[4] or "",
        "failed_screenshot":   row[5],          # base64 JPEG string or None
        "recovery_tool":       row[6] or "",
        "recovery_params":     parse_json(row[7]),
        "recovery_screenshot": row[8],
    }


def main():
    parser = argparse.ArgumentParser(description="Mine Tasker DB for recovery pairs")
    parser.add_argument("--db",  default=str(DB_PATH), help="Path to runs.db")
    parser.add_argument("--out", default=str(OUT_PATH), help="Output JSONL path")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        print("Run Tasker at least once so the database is created.")
        return

    # Open read-only to avoid touching the live DB
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    explicit   = get_explicit_recoveries(conn)
    backtracks = get_backtrack_recoveries(conn)
    conn.close()

    print(f"Explicit failures → recovery : {len(explicit)}")
    print(f"Backtrack (go_back) patterns : {len(backtracks)}")

    out_path = Path(args.out)
    written  = 0

    with out_path.open("w") as f:
        for row in explicit:
            d = row_to_dict(row, "explicit_failure")
            if not d["task"]:
                continue
            f.write(json.dumps(d) + "\n")
            written += 1

        for row in backtracks:
            d = row_to_dict(row, "backtrack")
            if not d["task"]:
                continue
            f.write(json.dumps(d) + "\n")
            written += 1

    print(f"\nWrote {written} recovery pairs → {out_path}")

    if written == 0:
        print("No pairs found yet — run more Tasker workflows to build up history.")
        return

    # Print a sample
    with out_path.open() as f:
        first = json.loads(f.readline())
    print("\nSample record:")
    print(f"  type:            {first['type']}")
    print(f"  task:            {first['task']}")
    print(f"  failed_tool:     {first['failed_tool']}({first['failed_params']})")
    print(f"  error:           {first['failed_error']}")
    print(f"  recovery_tool:   {first['recovery_tool']}({first['recovery_params']})")
    print(f"  has_screenshot:  {first['failed_screenshot'] is not None}")

    print(f"""
To load into the training notebook add a cell after the recovery mining cell:

    import json, base64
    from io import BytesIO
    from PIL import Image

    tasker_pairs = []
    with open("{out_path}") as f:
        for line in f:
            d = json.loads(line)
            img = None
            if d["failed_screenshot"]:
                img = Image.open(BytesIO(base64.b64decode(d["failed_screenshot"])))
            tasker_pairs.append({{
                "task":            d["task"],
                "history":         [],
                "wrong_element":   f"{{d['failed_tool']}}({{d['failed_params']}})",
                "correct_element": f"{{d['recovery_tool']}}({{d['recovery_params']}})",
                "operation":       d["recovery_tool"].upper(),
                "value":           str(d["recovery_params"].get("text", "")),
                "screenshot":      img,
                "pos_candidates":  [],
                "neg_candidates":  [],
                "failed_error":    d["failed_error"],
            }})

    print(f"Loaded {{len(tasker_pairs)}} Tasker recovery pairs")
""")


if __name__ == "__main__":
    main()

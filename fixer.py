# fixer.py

import sqlite3
from datetime import datetime, timedelta
import os

class RecorderFixer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_metadata_id(self, entity_id: str):
        cur = self.conn.execute(
            "SELECT metadata_id FROM states_meta WHERE entity_id = ?",
            (entity_id,)
        )
        row = cur.fetchone()
        return row["metadata_id"] if row else None

    def get_statistic_id(self, entity_id: str):
        cur = self.conn.execute(
            "SELECT id FROM statistics_meta WHERE statistic_id = ?",
            (entity_id,)
        )
        row = cur.fetchone()
        return row["id"] if row else None

    def delete_state_everywhere(self, entity_id: str, state_value: str):

        metadata_id = self.get_metadata_id(entity_id)
        if metadata_id is None:
            print(f"Sensor '{entity_id}' not found in states_meta.")
            return 0

        stat_id = self.get_statistic_id(entity_id)
        total_deleted = 0

        try:
            # Remove from states with filter by metadata_id and state
            cur = self.conn.execute(
                "DELETE FROM states WHERE metadata_id = ? AND state = ?",
                (metadata_id, state_value)
            )
            deleted_states = cur.rowcount
            total_deleted += deleted_states

            deleted_stats = 0
            deleted_short = 0

            try:
                float_value = float(state_value)
            except ValueError:
                float_value = None

            if stat_id and float_value is not None:
                # Removing from statistics with filter by metadata_id and values
                cur_stat = self.conn.execute(
                    """
                    DELETE FROM statistics
                    WHERE metadata_id = ? AND (
                        state = ? OR min = ? OR max = ? OR mean = ?
                    )
                    """,
                    (metadata_id, float_value, float_value, float_value, float_value)
                )
                deleted_stats = cur_stat.rowcount
                total_deleted += deleted_stats

                # IMPORTANT: Remove from statistics_short_term by min/max/mean without filtering by metadata_id
                cur_short = self.conn.execute(
                    """
                    DELETE FROM statistics_short_term
                    WHERE min = ? OR max = ? OR mean = ?
                    """,
                    (float_value, float_value, float_value)
                )
                deleted_short = cur_short.rowcount
                total_deleted += deleted_short

            self.conn.commit()

            print(f"Deleted {deleted_states} records from 'states'")
            print(f"Deleted {deleted_stats} records from 'statistics'")
            print(f"Deleted {deleted_short} records from 'statistics_short_term'")
            print(f"Total deleted records: {total_deleted}")

            return total_deleted

        except sqlite3.DatabaseError as e:
            print(f"Database error during deletion: {e}")
            self.conn.rollback()
            return 0

    def list_all_sensors(self):
        cur = self.conn.execute(
            "SELECT entity_id, metadata_id FROM states_meta ORDER BY entity_id"
        )
        return cur.fetchall()

    def get_unique_values(self, entity_id: str):
        metadata_id = self.get_metadata_id(entity_id)
        if metadata_id is None:
            return []
        cur = self.conn.execute(
            "SELECT DISTINCT state FROM states WHERE metadata_id = ? ORDER BY state",
            (metadata_id,)
        )
        return [row["state"] for row in cur.fetchall()]

    def get_raw_states(self, entity_id: str, limit: int = 200):
        metadata_id = self.get_metadata_id(entity_id)
        if metadata_id is None:
            return []
        cur = self.conn.execute(
            "SELECT state_id, state, last_updated FROM states WHERE metadata_id = ? ORDER BY last_updated DESC LIMIT ?",
            (metadata_id, limit)
        )
        return cur.fetchall()

    def list_states_by_id(self, metadata_id: int, limit: int = 200):
        cur = self.conn.execute(
            "SELECT state_id, state, last_updated FROM states WHERE metadata_id = ? ORDER BY last_updated DESC LIMIT ?",
            (metadata_id, limit)
        )
        return cur.fetchall()

    def close(self):
        self.conn.close()

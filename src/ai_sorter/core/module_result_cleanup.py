"""Safe, module-scoped cleanup of analysis results."""

from __future__ import annotations

from pathlib import Path

from .database import Database, DatabaseError


class ModuleResultCleanup:
    """Delete only module-owned analysis results; never touches file identity or locations."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def count_results(
        self,
        module_id: str,
        result_key: str | None = None,
        scope_root: Path | None = None,
    ) -> int:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")

        clauses = ["ar.module_id = ?"]
        params: list[object] = [module_id]
        if result_key is not None:
            clauses.append("ar.result_key = ?")
            params.append(result_key)
        if scope_root is not None:
            root = str(scope_root.resolve()).rstrip("\\/")
            clauses.append(
                "EXISTS (SELECT 1 FROM file_location fl WHERE fl.sha512 = ar.sha512 "
                "AND fl.location_status = 'ACTIVE' AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?))"
            )
            params.extend([root, root + "\\%"]) 

        row = connection.execute(
            f"SELECT COUNT(*) AS count FROM analysis_result ar WHERE {' AND '.join(clauses)}",
            tuple(params),
        ).fetchone()
        return int(row["count"])

    def clear_results(
        self,
        module_id: str,
        result_key: str | None = None,
        scope_root: Path | None = None,
    ) -> int:
        """Delete module results and return number of deleted rows."""
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")

        clauses = ["module_id = ?"]
        params: list[object] = [module_id]
        if result_key is not None:
            clauses.append("result_key = ?")
            params.append(result_key)
        if scope_root is not None:
            root = str(scope_root.resolve()).rstrip("\\/")
            clauses.append(
                "sha512 IN (SELECT fl.sha512 FROM file_location fl "
                "WHERE fl.location_status = 'ACTIVE' AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?))"
            )
            params.extend([root, root + "\\%"]) 

        try:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    f"DELETE FROM analysis_result WHERE {' AND '.join(clauses)}",
                    tuple(params),
                )
                return int(cursor.rowcount if cursor.rowcount is not None else 0)
        except Exception as exc:
            raise DatabaseError("Nie udało się usunąć wyników modułu. Żadne pliki kolekcji nie zostały zmienione.") from exc

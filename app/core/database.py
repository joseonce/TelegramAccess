# -*- coding: utf-8 -*-
"""
Conexión y gestión de la base de datos SQLite para TelegramAccess.
Acceso concurrente seguro con escrituras serializadas y lecturas por hilo (WAL mode).
"""

import sqlite3
import logging
import threading
from contextlib import contextmanager
from typing import List, Tuple, Optional
from .paths import get_data_path

log = logging.getLogger(__name__)

db_lock = threading.Lock()
_tx_local = threading.local()
_read_local = threading.local()
_read_conns_lock = threading.Lock()
_read_conns: list = []


def _describe_params(params) -> str:
    try:
        partes = []
        for p in (params or ()):
            if isinstance(p, (bytes, bytearray)):
                partes.append(f"bytes[{len(p)}]")
            elif isinstance(p, str):
                partes.append(f"str[{len(p)}]")
            elif p is None:
                partes.append("None")
            else:
                partes.append(type(p).__name__)
        return "(" + ", ".join(partes) + ")"
    except Exception:
        return "(?)"


def _resumen_sql(query: str) -> str:
    q = " ".join((query or "").split())
    return (q[:200] + "…") if len(q) > 200 else q


class DatabaseManager:
    def __init__(self, filename: str = "database/telegram.db"):
        self.db_path = get_data_path(filename)
        self._conn: Optional[sqlite3.Connection] = None
        self.connect()

    def connect(self):
        with db_lock:
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=30.0,
                    isolation_level=None
                )
                self._conn.execute("PRAGMA journal_mode=WAL;")
                self._conn.execute("PRAGMA synchronous=NORMAL;")
                self._conn.execute("PRAGMA foreign_keys=ON;")
                self._conn.execute("PRAGMA busy_timeout=30000;")
                log.info(f"Base de datos conectada en modo WAL: {self.db_path}")
            except sqlite3.Error as e:
                log.critical(f"Error fatal al conectar a la base de datos: {e}")
                raise

    def _get_read_conn(self) -> sqlite3.Connection:
        conn = getattr(_read_local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                isolation_level=None
            )
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA busy_timeout=30000;")
            except Exception:
                pass
            _read_local.conn = conn
            with _read_conns_lock:
                _read_conns.append(conn)
        return conn

    @contextmanager
    def transaccion(self):
        tx_conn = getattr(_tx_local, "conn", None)
        if tx_conn is not None:
            _tx_local.depth += 1
            try:
                yield tx_conn
            finally:
                _tx_local.depth -= 1
            return

        with db_lock:
            if not self._conn:
                self.connect()
            self._conn.execute("BEGIN IMMEDIATE;")
            _tx_local.conn = self._conn
            _tx_local.depth = 1
            try:
                yield self._conn
                self._conn.execute("COMMIT;")
            except Exception:
                try:
                    self._conn.execute("ROLLBACK;")
                except Exception:
                    pass
                raise
            finally:
                _tx_local.conn = None
                _tx_local.depth = 0

    def execute(self, query: str, params: Tuple = ()) -> int:
        tx_conn = getattr(_tx_local, "conn", None)
        if tx_conn is not None:
            cur = tx_conn.cursor()
            cur.execute(query, params)
            return cur.rowcount

        with db_lock:
            try:
                if not self._conn:
                    self.connect()
                cur = self._conn.cursor()
                cur.execute(query, params)
                return cur.rowcount
            except sqlite3.Error as e:
                log.error(f"Error en execute: {e} | SQL: {_resumen_sql(query)} | Params: {_describe_params(params)}")
                raise

    def execute_insert(self, query: str, params: Tuple = ()) -> int:
        tx_conn = getattr(_tx_local, "conn", None)
        if tx_conn is not None:
            cur = tx_conn.cursor()
            cur.execute(query, params)
            return cur.lastrowid

        with db_lock:
            try:
                if not self._conn:
                    self.connect()
                cur = self._conn.cursor()
                cur.execute(query, params)
                return cur.lastrowid
            except sqlite3.Error as e:
                log.error(f"Error en execute_insert: {e} | SQL: {_resumen_sql(query)}")
                raise

    def executemany(self, query: str, params_list: List[Tuple]) -> int:
        tx_conn = getattr(_tx_local, "conn", None)
        if tx_conn is not None:
            cur = tx_conn.cursor()
            cur.executemany(query, params_list)
            return cur.rowcount

        with db_lock:
            try:
                if not self._conn:
                    self.connect()
                cur = self._conn.cursor()
                cur.executemany(query, params_list)
                return cur.rowcount
            except sqlite3.Error as e:
                log.error(f"Error en executemany: {e} | SQL: {_resumen_sql(query)}")
                raise

    def query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        tx_conn = getattr(_tx_local, "conn", None)
        conn = tx_conn if tx_conn is not None else self._get_read_conn()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()
        except sqlite3.Error as e:
            log.error(f"Error en query: {e} | SQL: {_resumen_sql(query)} | Params: {_describe_params(params)}")
            return []

    def query_one(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        tx_conn = getattr(_tx_local, "conn", None)
        conn = tx_conn if tx_conn is not None else self._get_read_conn()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()
        except sqlite3.Error as e:
            log.error(f"Error en query_one: {e} | SQL: {_resumen_sql(query)}")
            return None

    def compactar_si_procede(self):
        with db_lock:
            try:
                if self._conn:
                    self._conn.execute("VACUUM;")
                    log.info("Base de datos compactada con éxito.")
            except Exception as e:
                log.debug(f"No se pudo compactar la base de datos: {e}")

    def close(self):
        with db_lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
        with _read_conns_lock:
            for c in _read_conns:
                try:
                    c.close()
                except Exception:
                    pass
            _read_conns.clear()


db = DatabaseManager()

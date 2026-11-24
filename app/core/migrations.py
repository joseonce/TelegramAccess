# -*- coding: utf-8 -*-
"""
Migraciones y esquema de base de datos para TelegramAccess.
Crea y actualiza todas las tablas de Telegram, Telegram Drive y Cuentas.
"""

import logging
from .database import db

log = logging.getLogger(__name__)


def ejecutar_migraciones():
    log.info("Inicializando esquema de base de datos para TelegramAccess...")

    # 1. Tabla de servicios y cuentas
    db.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        active INTEGER DEFAULT 1
    );
    """)
    db.execute("INSERT OR IGNORE INTO services (id, name, active) VALUES ('telegram', 'Telegram', 1);")

    db.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id TEXT NOT NULL,
        name TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        position INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(service_id) REFERENCES services(id)
    );
    """)

    # 2. Chats de Telegram
    db.execute("""
    CREATE TABLE IF NOT EXISTS telegram_chats (
        id TEXT PRIMARY KEY,
        account_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        title TEXT,
        chat_type TEXT,
        username TEXT,
        unread_count INTEGER DEFAULT 0,
        last_message TEXT,
        last_message_date TIMESTAMP,
        muted INTEGER DEFAULT 0,
        pinned INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        protected INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        last_media_type TEXT,
        last_read_message_id INTEGER DEFAULT 0,
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
    );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_telegram_chats_acc ON telegram_chats(account_id);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgchats_acc_date ON telegram_chats(account_id, last_message_date);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgchats_pinned ON telegram_chats(account_id, pinned DESC, last_message_date DESC);")

    # 3. Mensajes de Telegram
    db.execute("""
    CREATE TABLE IF NOT EXISTS telegram_messages (
        id TEXT PRIMARY KEY,
        account_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        sender_name TEXT,
        sender_username TEXT,
        sender_id INTEGER,
        text TEXT,
        media_type TEXT,
        media_path TEXT,
        date TEXT,
        outgoing INTEGER DEFAULT 0,
        reply_to INTEGER,
        edited INTEGER DEFAULT 0,
        duration REAL DEFAULT 0,
        file_name TEXT,
        forward_from TEXT,
        views INTEGER DEFAULT 0,
        media_group_id INTEGER,
        reply_markup TEXT,
        reactions TEXT,
        thread_id INTEGER,
        urls TEXT,
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
    );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_telegram_messages_chat ON telegram_messages(account_id, chat_id);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgmsg_chat_msgid ON telegram_messages(account_id, chat_id, message_id);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgmsg_chat_date ON telegram_messages(account_id, chat_id, date);")

    # 4. Contactos de Telegram
    db.execute("""
    CREATE TABLE IF NOT EXISTS telegram_contacts (
        id TEXT PRIMARY KEY,
        account_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        phone TEXT,
        mutual INTEGER DEFAULT 0,
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
    );
    """)

    # 5. Carpetas de Telegram
    db.execute("""
    CREATE TABLE IF NOT EXISTS telegram_folders (
        id TEXT PRIMARY KEY,
        account_id INTEGER NOT NULL,
        folder_id INTEGER NOT NULL,
        title TEXT,
        emoticon TEXT,
        chat_ids_json TEXT DEFAULT '[]',
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
    );
    """)

    # 6. Chats borrados (tombstones)
    db.execute("""
    CREATE TABLE IF NOT EXISTS telegram_deleted_chats (
        id TEXT PRIMARY KEY,
        account_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
    );
    """)

    # 7. Telegram Drive (nube personal)
    # Comprobar si la tabla tgdrive_items tiene el esquema antiguo incompatible
    cols_drive = {r[1] for r in db.query("PRAGMA table_info(tgdrive_items)")}
    if cols_drive and "name" not in cols_drive:
        log.info("Migrando esquema antiguo de Telegram Drive a la estructura compatible...")
        db.execute("DROP TABLE IF EXISTS tgdrive_parts;")
        db.execute("DROP TABLE IF EXISTS tgdrive_transfers;")
        db.execute("DROP TABLE IF EXISTS tgdrive_pending_deletes;")
        db.execute("DROP TABLE IF EXISTS tgdrive_items;")

    db.execute("""
    CREATE TABLE IF NOT EXISTS tgdrive_items (
        id TEXT PRIMARY KEY,
        account_id INTEGER NOT NULL,
        channel_id INTEGER,
        parent_id TEXT,
        name TEXT NOT NULL,
        tipo TEXT NOT NULL,
        path TEXT NOT NULL DEFAULT '',
        size INTEGER DEFAULT 0,
        mime TEXT,
        sha256 TEXT,
        created_at TEXT NOT NULL,
        modified_at TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'normal',
        trashed_at TEXT,
        original_parent_id TEXT,
        original_path TEXT,
        num_parts INTEGER DEFAULT 1,
        encrypted INTEGER DEFAULT 0,
        meta_version INTEGER DEFAULT 1,
        descripcion TEXT,
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY(parent_id) REFERENCES tgdrive_items(id) ON DELETE CASCADE
    );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgdrive_items_parent ON tgdrive_items(account_id, parent_id, estado);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgdrive_items_sha ON tgdrive_items(account_id, sha256);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgdrive_items_estado ON tgdrive_items(account_id, estado);")

    db.execute("""
    CREATE TABLE IF NOT EXISTS tgdrive_parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT NOT NULL,
        orden INTEGER NOT NULL,
        size INTEGER DEFAULT 0,
        sha256 TEXT,
        message_id INTEGER,
        tg_file_id TEXT,
        tg_unique_id TEXT,
        estado TEXT DEFAULT 'pending',
        UNIQUE(item_id, orden),
        FOREIGN KEY(item_id) REFERENCES tgdrive_items(id) ON DELETE CASCADE
    );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgdrive_parts_item ON tgdrive_parts(item_id);")

    db.execute("""
    CREATE TABLE IF NOT EXISTS tgdrive_transfers (
        id TEXT PRIMARY KEY,
        account_id INTEGER,
        item_id TEXT,
        parent_id TEXT,
        carpeta_destino TEXT,
        operacion TEXT NOT NULL,
        nombre TEXT,
        local_path TEXT,
        size_total INTEGER DEFAULT 0,
        bytes_hechos INTEGER DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        error TEXT,
        prioridad INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        descripcion TEXT,
        FOREIGN KEY(item_id) REFERENCES tgdrive_items(id) ON DELETE SET NULL
    );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_tgdrive_transfers_estado ON tgdrive_transfers(estado);")

    db.execute("""
    CREATE TABLE IF NOT EXISTS tgdrive_pending_deletes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        channel_id INTEGER,
        message_id INTEGER,
        created_at TEXT
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS play_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        media_url TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        service_origin TEXT NOT NULL,
        account_origin_id INTEGER,
        last_position REAL DEFAULT 0.0,
        duration REAL DEFAULT 0.0,
        last_played_at TEXT NOT NULL,
        finished INTEGER DEFAULT 0
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS sound_events (
        event_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        volume REAL DEFAULT 1.0
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS shortcuts (
        shortcut_id TEXT PRIMARY KEY,
        key_combination TEXT NOT NULL
    );
    """)

    # Migraciones incrementales / comprobación de columnas
    try:
        info_chats = [r[1] for r in db.query("PRAGMA table_info(telegram_chats)")]
        if "username" not in info_chats:
            db.execute("ALTER TABLE telegram_chats ADD COLUMN username TEXT;")

        info_msgs = [r[1] for r in db.query("PRAGMA table_info(telegram_messages)")]
        cols_msgs = [
            ("outgoing", "INTEGER DEFAULT 0"),
            ("media_path", "TEXT"),
            ("reply_to", "INTEGER"),
            ("edited", "INTEGER DEFAULT 0"),
            ("forward_from", "TEXT"),
            ("views", "INTEGER DEFAULT 0"),
            ("media_group_id", "INTEGER"),
            ("reply_markup", "TEXT"),
            ("reactions", "TEXT"),
            ("thread_id", "INTEGER"),
            ("urls", "TEXT"),
        ]
        for col, ctype in cols_msgs:
            if col not in info_msgs:
                try:
                    db.execute(f"ALTER TABLE telegram_messages ADD COLUMN {col} {ctype};")
                except Exception:
                    pass
    except Exception as ex:
        log.debug(f"Aviso en migración incremental: {ex}")

    log.info("Migraciones completadas correctamente.")

from contextlib import asynccontextmanager
import aiosqlite
import datetime
from typing import Optional, Dict, List, Any
import config

DB_PATH = config.DB_PATH


@asynccontextmanager
async def get_connection():
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def init_db():
    """Initializes tables and default records."""
    async with get_connection() as conn:
        # Settings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Admins table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                accounts_sold INTEGER DEFAULT 0,
                total_withdrawn REAL DEFAULT 0.0,
                is_banned INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Countries table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dial_code TEXT NOT NULL UNIQUE,
                capacity INTEGER DEFAULT 100,
                used_capacity INTEGER DEFAULT 0,
                main_price REAL DEFAULT 0.80,
                spam_price REAL DEFAULT 0.40,
                new_acc_price REAL DEFAULT 0.60,
                confirm_time INTEGER DEFAULT 600,
                status INTEGER DEFAULT 1,
                premium_only INTEGER DEFAULT 0,
                accept_spam INTEGER DEFAULT 1,
                login_email INTEGER DEFAULT 0
            )
        """)

        # Accounts table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                country_id INTEGER,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                session_path TEXT NOT NULL,
                status TEXT DEFAULT 'confirmed',
                is_downloaded INTEGER DEFAULT 0,
                device_count INTEGER DEFAULT 1,
                term_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure migration columns for accounts table
        try:
            await conn.execute("ALTER TABLE accounts ADD COLUMN device_count INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            await conn.execute("ALTER TABLE accounts ADD COLUMN term_completed INTEGER DEFAULT 0")
        except Exception:
            pass

        # Withdrawals table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wid TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                method TEXT NOT NULL,
                wallet TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)

        # Daily stats table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                accounts_count INTEGER DEFAULT 0,
                total_payout REAL DEFAULT 0.0,
                withdrawals_count INTEGER DEFAULT 0,
                withdrawals_amount REAL DEFAULT 0.0
            )
        """)

        # Seed default settings if empty
        default_settings = {
            "maintenance_mode": "0",
            "withdraw_enabled": "1",
            "receive_enabled": "1",
            "auto_termination": "1",
            "min_wd": "5.0",
            "default_2fa": "",
            "payment_channel": "",
            "stats_channel": "",
            "join_lock_channel": "",
            "error_channel": "",
            "app_id": str(config.DEFAULT_API_ID),
            "app_hash": config.DEFAULT_API_HASH,
            "system_lang_code": config.DEFAULT_SYSTEM_LANG_CODE,
            "app_version": config.DEFAULT_APP_VERSION,
            "active_platform": "TD-direct",
            "proxy_enabled": "0",
            "proxy_type": "socks5",
            "proxy_host": "",
            "proxy_port": "1080",
            "proxy_user": "",
            "proxy_pass": "",
            "proxy_iso": "US",
            "support_url": "https://t.me/telegram",
            "updates_url": "https://t.me/telegram",
        }

        for k, v in default_settings.items():
            await conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )

        # Ensure auto_termination setting is present
        await conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_termination', '1')"
        )

        # Seed initial admins
        for admin_id in list(config.ADMIN_IDS) + [5597944494, 8685436749]:
            if admin_id > 0:
                await conn.execute(
                    "INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,)
                )

        # Seed default starter countries
        starter_countries = [
            ("Bangladesh", "+880", 200, 0.70, 0.35, 0.50, 600),
            ("United States", "+1", 100, 0.90, 0.45, 0.70, 600),
            ("India", "+91", 300, 0.60, 0.30, 0.45, 600),
            ("Indonesia", "+62", 150, 0.65, 0.35, 0.50, 600),
            ("Russia", "+7", 100, 0.85, 0.40, 0.65, 600),
            ("Philippines", "+63", 120, 0.70, 0.35, 0.50, 600),
            ("Pakistan", "+92", 150, 0.60, 0.30, 0.40, 600),
        ]
        for name, dial, cap, mp, sp, np, ct in starter_countries:
            await conn.execute(
                """
                INSERT OR IGNORE INTO countries 
                (name, dial_code, capacity, main_price, spam_price, new_acc_price, confirm_time) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (name, dial, cap, mp, sp, np, ct),
            )

        # Fix any countries with too low confirm_time (e.g. 1s or 10s -> 600s)
        await conn.execute(
            "UPDATE countries SET confirm_time = 600 WHERE confirm_time < 60"
        )

        await conn.commit()


# ================= USER OPERATIONS =================


async def get_user(user_id: int) -> Optional[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_or_update_user(
    user_id: int, username: Optional[str], first_name: Optional[str]
) -> dict:
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """,
            (user_id, username, first_name),
        )
        await conn.commit()
    return await get_user(user_id)


async def update_balance(user_id: int, delta: float) -> float:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE users SET balance = MAX(0.0, balance + ?) WHERE user_id = ?
        """,
            (delta, user_id),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row["balance"] if row else 0.0


async def set_balance(user_id: int, balance: float) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (max(0.0, balance), user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def increment_accounts_sold(user_id: int):
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE users SET accounts_sold = accounts_sold + 1 WHERE user_id = ?
        """,
            (user_id,),
        )
        await conn.commit()


async def set_user_ban_status(user_id: int, is_banned: bool) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?",
            (1 if is_banned else 0, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def set_user_premium_status(user_id: int, is_premium: bool) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "UPDATE users SET is_premium = ? WHERE user_id = ?",
            (1 if is_premium else 0, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def reset_all_balances() -> int:
    async with get_connection() as conn:
        cursor = await conn.execute("UPDATE users SET balance = 0.0")
        await conn.commit()
        return cursor.rowcount


async def get_all_users() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM users ORDER BY joined_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_users_count() -> int:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) as cnt FROM users")
        row = await cursor.fetchone()
        return row["cnt"] if row else 0


async def get_today_users_count() -> int:
    today = datetime.date.today().isoformat()
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE date(joined_at) = ?", (today,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0


# ================= COUNTRY OPERATIONS =================


async def get_all_countries() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM countries ORDER BY name ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_active_countries() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM countries WHERE status = 1 ORDER BY name ASC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_country_by_id(country_id: int) -> Optional[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM countries WHERE id = ?", (country_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_country_by_dial_code(dial_code: str) -> Optional[dict]:
    dial_code = dial_code.strip()
    if not dial_code.startswith("+"):
        dial_code = "+" + dial_code
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM countries WHERE dial_code = ?", (dial_code,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_country(
    name: str,
    dial_code: str,
    capacity: int = 100,
    main_price: float = 0.80,
    spam_price: float = 0.40,
    new_acc_price: float = 0.60,
    confirm_time: int = 600,
    status: int = 1,
    premium_only: int = 0,
    accept_spam: int = 1,
    login_email: int = 0,
) -> int:
    if not dial_code.startswith("+"):
        dial_code = "+" + dial_code
    if confirm_time < 60:
        confirm_time = 600
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO countries 
            (name, dial_code, capacity, main_price, spam_price, new_acc_price, confirm_time, status, premium_only, accept_spam, login_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                dial_code,
                capacity,
                main_price,
                spam_price,
                new_acc_price,
                confirm_time,
                status,
                premium_only,
                accept_spam,
                login_email,
            ),
        )
        await conn.commit()
        return cursor.lastrowid


async def update_country(country_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    set_clause = ", ".join(f"{k} = ?" for k in keys)
    values.append(country_id)

    async with get_connection() as conn:
        cursor = await conn.execute(
            f"UPDATE countries SET {set_clause} WHERE id = ?", values
        )
        await conn.commit()
        return cursor.rowcount > 0


async def delete_country(country_id: int) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM countries WHERE id = ?", (country_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0


async def increment_used_capacity(country_id: int):
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE countries SET used_capacity = used_capacity + 1 WHERE id = ?
        """,
            (country_id,),
        )
        await conn.commit()


# ================= ACCOUNT OPERATIONS =================


async def add_account(
    phone: str,
    user_id: int,
    country_id: Optional[int],
    category: str,
    price: float,
    session_path: str,
) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO accounts (phone, user_id, country_id, category, price, session_path, status)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
        """,
            (phone, user_id, country_id, category, price, session_path),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_account_by_phone(phone: str) -> Optional[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT a.*, u.username, u.first_name, c.name as country_name 
            FROM accounts a
            LEFT JOIN users u ON a.user_id = u.user_id
            LEFT JOIN countries c ON a.country_id = c.id
            WHERE a.phone = ?
        """,
            (phone,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_accounts() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT a.*, u.username, c.name as country_name 
            FROM accounts a
            LEFT JOIN users u ON a.user_id = u.user_id
            LEFT JOIN countries c ON a.country_id = c.id
            ORDER BY a.created_at DESC
        """
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_accounts_by_category(category: Optional[str] = None) -> List[dict]:
    async with get_connection() as conn:
        if category:
            cursor = await conn.execute(
                """
                SELECT a.*, u.username, c.name as country_name 
                FROM accounts a
                LEFT JOIN users u ON a.user_id = u.user_id
                LEFT JOIN countries c ON a.country_id = c.id
                WHERE a.category = ?
                ORDER BY a.created_at DESC
            """,
                (category,),
            )
        else:
            cursor = await conn.execute(
                """
                SELECT a.*, u.username, c.name as country_name 
                FROM accounts a
                LEFT JOIN users u ON a.user_id = u.user_id
                LEFT JOIN countries c ON a.country_id = c.id
                ORDER BY a.created_at DESC
            """
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_accounts_stats() -> dict:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) as total_confirmed FROM accounts WHERE status = 'confirmed'"
        )
        confirmed = (await cursor.fetchone())["total_confirmed"]

        cursor = await conn.execute(
            "SELECT COUNT(*) as downloaded FROM accounts WHERE is_downloaded = 1"
        )
        downloaded = (await cursor.fetchone())["downloaded"]

        cursor = await conn.execute("""
            SELECT category, COUNT(*) as count 
            FROM accounts 
            GROUP BY category
        """)
        cats = {row["category"]: row["count"] for row in await cursor.fetchall()}

        return {
            "total_confirmed": confirmed,
            "total_pending": 0,  # in-memory active sessions
            "downloaded": downloaded,
            "categories": cats,
        }


async def mark_accounts_downloaded(account_ids: List[int]):
    if not account_ids:
        return
    placeholders = ",".join("?" for _ in account_ids)
    async with get_connection() as conn:
        await conn.execute(
            f"UPDATE accounts SET is_downloaded = 1 WHERE id IN ({placeholders})",
            account_ids,
        )
        await conn.commit()


async def delete_bad_numbers() -> int:
    """Removes broken or missing session entries from DB."""
    import os

    deleted_count = 0
    accounts = await get_all_accounts()
    for acc in accounts:
        if not os.path.exists(acc["session_path"]):
            async with get_connection() as conn:
                await conn.execute(
                    "DELETE FROM accounts WHERE id = ?", (acc["id"],)
                )
                await conn.commit()
                deleted_count += 1
    return deleted_count


async def delete_account(account_id: int) -> bool:
    """Deletes an account entry from the database."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM accounts WHERE id = ?", (account_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0


async def update_account_status(account_id: int, status: str) -> bool:
    """Updates account status (e.g. 'confirmed', 'revoked', 'deleted')."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "UPDATE accounts SET status = ? WHERE id = ?", (status, account_id)
        )
        await conn.commit()
        return cursor.rowcount > 0


async def update_account_device_info(
    account_id: int, device_count: int, term_completed: Optional[int] = None
) -> bool:
    """Updates device_count and optionally term_completed status for an account."""
    async with get_connection() as conn:
        if term_completed is not None:
            cursor = await conn.execute(
                "UPDATE accounts SET device_count = ?, term_completed = ? WHERE id = ?",
                (device_count, term_completed, account_id),
            )
        else:
            cursor = await conn.execute(
                "UPDATE accounts SET device_count = ? WHERE id = ?",
                (device_count, account_id),
            )
        await conn.commit()
        return cursor.rowcount > 0


async def get_accounts_by_country_summary() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute("""
            SELECT c.name as country_name, c.dial_code, COUNT(a.id) as accounts_count, COUNT(DISTINCT a.user_id) as users_count
            FROM countries c
            LEFT JOIN accounts a ON c.id = a.country_id
            GROUP BY c.id
            ORDER BY accounts_count DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ================= WITHDRAWAL OPERATIONS =================


async def create_withdrawal(
    wid: str, user_id: int, amount: float, method: str, wallet: str
) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO withdrawals (wid, user_id, amount, method, wallet, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """,
            (wid, user_id, amount, method, wallet),
        )
        # deduct balance
        await conn.execute(
            "UPDATE users SET balance = MAX(0.0, balance - ?) WHERE user_id = ?",
            (amount, user_id),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_withdrawal_by_wid(wid: str) -> Optional[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT w.*, u.username, u.first_name 
            FROM withdrawals w
            LEFT JOIN users u ON w.user_id = u.user_id
            WHERE w.wid = ?
        """,
            (wid,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_withdrawals_by_user(user_id: int, limit: int = 10) -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM withdrawals WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_pending_withdrawals() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute("""
            SELECT w.*, u.username, u.first_name 
            FROM withdrawals w
            LEFT JOIN users u ON w.user_id = u.user_id
            WHERE w.status = 'pending'
            ORDER BY w.created_at ASC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_withdrawal_status(
    wid: str, status: str, admin_note: str = ""
) -> Optional[dict]:
    wd = await get_withdrawal_by_wid(wid)
    if not wd:
        return None

    now = datetime.datetime.now().isoformat()
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE withdrawals 
            SET status = ?, admin_note = ?, processed_at = ?
            WHERE wid = ?
        """,
            (status, admin_note, now, wid),
        )

        if status == "rejected":
            # Refund balance back to user
            await conn.execute(
                """
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            """,
                (wd["amount"], wd["user_id"]),
            )
        elif status == "paid":
            # Track total withdrawn
            await conn.execute(
                """
                UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id = ?
            """,
                (wd["amount"], wd["user_id"]),
            )

        await conn.commit()
    return await get_withdrawal_by_wid(wid)


async def get_all_withdrawals() -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute("""
            SELECT w.*, u.username, u.first_name 
            FROM withdrawals w
            LEFT JOIN users u ON w.user_id = u.user_id
            ORDER BY w.created_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_withdrawals_by_date(date_str: str) -> List[dict]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT w.*, u.username, u.first_name 
            FROM withdrawals w
            LEFT JOIN users u ON w.user_id = u.user_id
            WHERE date(w.created_at) = ?
            ORDER BY w.created_at DESC
        """,
            (date_str,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ================= SETTINGS OPERATIONS =================


async def get_setting(key: str, default: str = "") -> str:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else default


async def set_setting(key: str, value: str):
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
            (key, str(value)),
        )
        await conn.commit()


async def get_all_settings() -> Dict[str, str]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}


# ================= ADMIN OPERATIONS =================

SUPERADMIN_IDS = {5597944494, 8685436749}


async def is_admin(user_id: int) -> bool:
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False

    if uid in SUPERADMIN_IDS or uid in config.ADMIN_IDS:
        return True
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT user_id FROM admins WHERE user_id = ?", (uid,)
        )
        row = await cursor.fetchone()
        return bool(row)


async def add_admin(user_id: int) -> bool:
    async with get_connection() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,)
        )
        await conn.commit()
        return True


async def remove_admin(user_id: int) -> bool:
    if user_id in config.ADMIN_IDS:
        return False  # Cannot remove superadmin from env
    async with get_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM admins WHERE user_id = ?", (user_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0


async def get_all_admins() -> List[int]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT user_id FROM admins")
        rows = await cursor.fetchall()
        ids = set(config.ADMIN_IDS)
        for r in rows:
            ids.add(r["user_id"])
        return sorted([i for i in ids if i > 0])


# ================= DAILY STATS =================


async def record_account_hit(price: float):
    today = datetime.date.today().isoformat()
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO daily_stats (date, accounts_count, total_payout)
            VALUES (?, 1, ?)
            ON CONFLICT(date) DO UPDATE SET
                accounts_count = accounts_count + 1,
                total_payout = total_payout + excluded.total_payout
        """,
            (today, price),
        )
        await conn.commit()


async def record_withdrawal_hit(amount: float):
    today = datetime.date.today().isoformat()
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO daily_stats (date, withdrawals_count, withdrawals_amount)
            VALUES (?, 1, ?)
            ON CONFLICT(date) DO UPDATE SET
                withdrawals_count = withdrawals_count + 1,
                withdrawals_amount = withdrawals_amount + excluded.withdrawals_amount
        """,
            (today, amount),
        )
        await conn.commit()


async def get_daily_summary(date_str: Optional[str] = None) -> dict:
    if not date_str:
        date_str = datetime.date.today().isoformat()

    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM daily_stats WHERE date = ?", (date_str,)
        )
        row = await cursor.fetchone()
        stats = dict(row) if row else {
            "date": date_str,
            "accounts_count": 0,
            "total_payout": 0.0,
            "withdrawals_count": 0,
            "withdrawals_amount": 0.0,
        }

        # Count new users registered on date_str
        cursor = await conn.execute(
            "SELECT COUNT(*) as new_users FROM users WHERE date(joined_at) = ?",
            (date_str,),
        )
        u_row = await cursor.fetchone()
        stats["new_users"] = u_row["new_users"] if u_row else 0

        # Total users
        stats["total_users"] = await get_users_count()

        return stats

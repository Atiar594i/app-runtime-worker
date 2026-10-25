import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, Any, Callable
import socks
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest
from telethon.tl.functions.auth import ResetAuthorizationsRequest
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
    PhoneNumberInvalidError,
    PhoneNumberBannedError,
    PasswordHashInvalidError,
    FreshResetAuthorisationForbiddenError,
    AuthKeyUnregisteredError,
    UserDeactivatedError,
    UserDeactivatedBanError,
)

import config
import database
from utils.platform_presets import get_platform_info


class PendingSession:

    def __init__(
        self,
        user_id: int,
        phone: str,
        country: dict,
        client: TelegramClient,
        phone_code_hash: str,
        confirm_time: int,
        temp_session_path: Path,
    ):
        self.user_id = user_id
        self.phone = phone
        self.country = country
        self.client = client
        self.phone_code_hash = phone_code_hash
        self.confirm_time = confirm_time
        self.temp_session_path = temp_session_path
        self.created_at = time.time()
        self.timeout_task: Optional[asyncio.Task] = None
        self.is_waiting_2fa = False


class SessionManager:

    def __init__(self):
        self.pending_sessions: Dict[int, PendingSession] = {}

    def get_pending(self, user_id: int) -> Optional[PendingSession]:
        return self.pending_sessions.get(user_id)

    async def get_client_config(self) -> Dict[str, Any]:
        """Loads active MTProto API and Platform configurations from database."""
        app_id_str = await database.get_setting(
            "app_id", str(config.DEFAULT_API_ID)
        )
        try:
            api_id = int(app_id_str)
        except ValueError:
            api_id = config.DEFAULT_API_ID

        api_hash = await database.get_setting(
            "app_hash", config.DEFAULT_API_HASH
        )
        active_platform = await database.get_setting(
            "active_platform", "TD-direct"
        )
        system_lang_code = await database.get_setting("system_lang_code", "en")
        app_version = await database.get_setting("app_version", "10.14.5")

        platform_preset = get_platform_info(active_platform)
        custom_model = await database.get_setting("custom_device_model", "")
        custom_os = await database.get_setting("custom_system_version", "")

        device_model = custom_model if custom_model else platform_preset.get("device_model", "Desktop")
        system_version = custom_os if custom_os else platform_preset.get("system_version", "Windows 11 x64")

        # Check proxy settings
        proxy_enabled = await database.get_setting("proxy_enabled", "0")
        proxy_config = None
        if proxy_enabled == "1":
            p_type = await database.get_setting("proxy_type", "socks5")
            p_host = await database.get_setting("proxy_host", "")
            p_port = await database.get_setting("proxy_port", "1080")
            p_user = await database.get_setting("proxy_user", "")
            p_pass = await database.get_setting("proxy_pass", "")

            if p_host and p_port:
                sock_type = (
                    socks.SOCKS5 if "SOCKS5" in p_type.upper() else socks.HTTP
                )
                proxy_config = (
                    sock_type,
                    p_host,
                    int(p_port),
                    True,
                    p_user if p_user else None,
                    p_pass if p_pass else None,
                )

        return {
            "api_id": api_id,
            "api_hash": api_hash,
            "device_model": device_model,
            "system_version": system_version,
            "app_version": app_version
            or platform_preset.get("app_version", "10.14.5"),
            "lang_code": platform_preset.get("lang_code", "en"),
            "system_lang_code": system_lang_code,
            "proxy": proxy_config,
        }

    async def start_login(
        self,
        user_id: int,
        phone: str,
        country: dict,
        timeout_callback: Optional[Callable[[int], Any]] = None,
    ) -> Dict[str, Any]:
        """Initiates Telethon connection and requests login code."""
        # Cancel any previous pending session for this user
        await self.cancel_session(user_id)

        cfg = await self.get_client_config()
        clean_phone = phone.replace("+", "")
        temp_session_file = config.TEMP_SESSIONS_DIR / f"{clean_phone}.session"

        # Remove previous file if exists
        if temp_session_file.exists():
            try:
                os.remove(temp_session_file)
            except Exception:
                pass

        client = TelegramClient(
            str(config.TEMP_SESSIONS_DIR / clean_phone),
            cfg["api_id"],
            cfg["api_hash"],
            device_model=cfg["device_model"],
            system_version=cfg["system_version"],
            app_version=cfg["app_version"],
            lang_code=cfg["lang_code"],
            system_lang_code=cfg["system_lang_code"],
            proxy=cfg["proxy"],
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                send_code_res = await client.send_code_request(phone)
                phone_code_hash = send_code_res.phone_code_hash
            else:
                # Already authorized
                phone_code_hash = ""
        except PhoneNumberInvalidError:
            await client.disconnect()
            return {
                "success": False,
                "error": "The phone number is invalid for Telegram.",
            }
        except PhoneNumberBannedError:
            await client.disconnect()
            return {
                "success": False,
                "error": "This phone number is banned by Telegram.",
            }
        except FloodWaitError as e:
            await client.disconnect()
            return {
                "success": False,
                "error": (
                    f"Too many attempts. Please wait {e.seconds} seconds."
                ),
            }
        except Exception as e:
            await client.disconnect()
            return {"success": False, "error": f"Connection error: {str(e)}"}

        confirm_time = country.get("confirm_time", 600)
        if not confirm_time or confirm_time < 60:
            confirm_time = 600

        pending = PendingSession(
            user_id=user_id,
            phone=phone,
            country=country,
            client=client,
            phone_code_hash=phone_code_hash,
            confirm_time=confirm_time,
            temp_session_path=temp_session_file,
        )

        # Set confirmation countdown timer task
        async def _countdown():
            try:
                await asyncio.sleep(confirm_time)
                if user_id in self.pending_sessions:
                    await self.cancel_session(user_id)
                    if timeout_callback:
                        cb_res = timeout_callback(user_id)
                        if asyncio.iscoroutine(cb_res):
                            await cb_res
            except asyncio.CancelledError:
                pass

        pending.timeout_task = asyncio.create_task(_countdown())
        self.pending_sessions[user_id] = pending

        return {"success": True, "confirm_time": confirm_time}

    async def submit_otp(self, user_id: int, code: str) -> Dict[str, Any]:
        """Submits the received OTP code."""
        session = self.get_pending(user_id)
        if not session:
            return {
                "status": "not_found",
                "message": "No active session in progress.",
            }

        # Strip any formatting spaces
        clean_code = code.replace(" ", "").replace("-", "").strip()

        try:
            await session.client.sign_in(
                phone=session.phone,
                code=clean_code,
                phone_code_hash=session.phone_code_hash,
            )
            # If sign-in succeeds without 2FA
            return await self.finalize_account(user_id)
        except SessionPasswordNeededError:
            session.is_waiting_2fa = True
            return {
                "status": "need_2fa",
                "message": "2FA (Two-Step Verification) password required.",
            }
        except PhoneCodeInvalidError:
            return {
                "status": "invalid_code",
                "message": "Invalid verification code. Please check and try again.",
            }
        except PhoneCodeExpiredError:
            await self.cancel_session(user_id)
            return {
                "status": "expired_code",
                "message": "Verification code expired. Please start again.",
            }
        except FloodWaitError as e:
            await self.cancel_session(user_id)
            return {
                "status": "flood_wait",
                "message": f"Telegram flood limit: please wait {e.seconds} seconds.",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Login failed: {str(e)}",
            }

    async def submit_2fa(self, user_id: int, password: str) -> Dict[str, Any]:
        """Submits 2FA password."""
        session = self.get_pending(user_id)
        if not session:
            return {
                "status": "not_found",
                "message": "No active session in progress.",
            }

        try:
            await session.client.sign_in(password=password)
            return await self.finalize_account(user_id)
        except PasswordHashInvalidError:
            return {
                "status": "invalid_password",
                "message": "Incorrect 2FA password. Please try again.",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"2FA verification failed: {str(e)}",
            }

    async def check_spambot(self, client: TelegramClient) -> str:
        """Sends /start to @SpamBot to check account restrictions."""
        try:
            async with client.conversation("@SpamBot", timeout=6) as conv:
                await conv.send_message("/start")
                resp = await conv.get_response()
                text = resp.text.lower()

                if (
                    "good news" in text
                    or "no limits are currently applied" in text
                ):
                    return "Free"
                elif "permanent" in text or "permanently" in text:
                    return "Permanent Spam"
                else:
                    return "Spam"
        except Exception:
            # If SpamBot takes too long or errors, default to Free
            return "Free"

    async def apply_2fa_and_cleanup(self, client: TelegramClient):
        """Secures the account with default 2FA password if configured."""
        default_2fa = await database.get_setting("default_2fa", "")
        if default_2fa and default_2fa.strip():
            try:
                await client.edit_2fa(new_password=default_2fa.strip())
            except Exception as e:
                print(f"[2FA Update Warning] Could not set 2FA: {e}")

    async def finalize_account(self, user_id: int) -> Dict[str, Any]:
        """Finalizes verified account: checks spam status, saves session, adds balance."""
        session = self.get_pending(user_id)
        if not session:
            return {"status": "error", "message": "Session lost."}

        client = session.client
        phone = session.phone
        country = session.country

        # 1. SpamBot Check
        category = await self.check_spambot(client)

        # 2. Check Country Accept Spam rule (Bypassed for admin)
        is_admin = await database.is_admin(user_id)
        if not is_admin and category in ("Spam", "Permanent Spam") and not country.get(
            "accept_spam", 1
        ):
            await self.cancel_session(user_id)
            return {
                "status": "rejected",
                "message": (
                    "❌ This country does not accept accounts with SpamBot"
                    " restrictions."
                ),
            }

        # 3. Apply default 2FA password to secure the account
        await self.apply_2fa_and_cleanup(client)

        # 4. Disconnect client to flush SQLite session file
        await client.disconnect()

        # 5. Move .session file from temp to target category directory
        clean_phone = phone.replace("+", "")
        temp_file = config.TEMP_SESSIONS_DIR / f"{clean_phone}.session"

        if category in ("Spam", "Permanent Spam"):
            target_dir = config.CONFIRMED_SPAM_DIR
        elif category == "New Register":
            target_dir = config.CONFIRMED_NEW_ACC_DIR
        else:
            target_dir = config.CONFIRMED_FREE_DIR

        target_file = target_dir / f"{clean_phone}.session"
        if temp_file.exists():
            shutil.move(str(temp_file), str(target_file))

        # 6. Calculate Payout based on category
        if category == "Free":
            price = float(country.get("main_price", 0.80))
        elif category in ("Spam", "Permanent Spam"):
            price = float(country.get("spam_price", 0.40))
        elif category == "New Register":
            price = float(country.get("new_acc_price", 0.60))
        else:
            price = float(country.get("main_price", 0.80))

        # 7. Update Database
        await database.add_account(
            phone=phone,
            user_id=user_id,
            country_id=country.get("id"),
            category=category,
            price=price,
            session_path=str(target_file),
        )
        new_balance = await database.update_balance(user_id, price)
        await database.increment_accounts_sold(user_id)
        if country.get("id"):
            await database.increment_used_capacity(country["id"])
        await database.record_account_hit(price)

        # 8. Clean up pending in-memory session
        if session.timeout_task and not session.timeout_task.done():
            session.timeout_task.cancel()
        if user_id in self.pending_sessions:
            del self.pending_sessions[user_id]

        return {
            "status": "success",
            "phone": phone,
            "category": category,
            "price": price,
            "new_balance": new_balance,
            "country_name": country.get("name", "Unknown"),
            "session_path": str(target_file),
        }

    async def cancel_session(self, user_id: int):
        """Cancels and cleans up an ongoing login process."""
        session = self.pending_sessions.pop(user_id, None)
        if session:
            if session.timeout_task and not session.timeout_task.done():
                session.timeout_task.cancel()
            try:
                if session.client.is_connected():
                    await session.client.disconnect()
            except Exception:
                pass
            clean_phone = session.phone.replace("+", "")
            temp_file = config.TEMP_SESSIONS_DIR / f"{clean_phone}.session"
            if temp_file.exists():
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    async def get_session_authorizations(self, session_path: str) -> Dict[str, Any]:
        """Loads a stored session file and queries active devices / authorizations."""
        p = Path(session_path)
        if not p.exists():
            if not str(session_path).endswith(".session"):
                p = Path(f"{session_path}.session")
            if not p.exists():
                return {"success": False, "error": "Session file not found on disk."}

        cfg = await self.get_client_config()
        base_path = str(p.with_suffix(""))

        client = TelegramClient(
            base_path,
            cfg["api_id"],
            cfg["api_hash"],
            device_model=cfg["device_model"],
            system_version=cfg["system_version"],
            app_version=cfg["app_version"],
            lang_code=cfg["lang_code"],
            system_lang_code=cfg["system_lang_code"],
            proxy=cfg["proxy"],
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return {
                    "success": False,
                    "is_revoked": True,
                    "error": "This session is expired or logged out by the user.",
                }

            auths_res = await client(GetAuthorizationsRequest())
            devices = []
            for a in auths_res.authorizations:
                created_str = (
                    a.date_created.strftime("%Y-%m-%d %H:%M")
                    if hasattr(a, "date_created") and a.date_created
                    else "N/A"
                )
                active_str = (
                    a.date_active.strftime("%Y-%m-%d %H:%M")
                    if hasattr(a, "date_active") and a.date_active
                    else "N/A"
                )
                devices.append({
                    "hash": getattr(a, "hash", 0),
                    "device_model": getattr(a, "device_model", "Unknown Device"),
                    "platform": getattr(a, "platform", "Unknown"),
                    "system_version": getattr(a, "system_version", ""),
                    "app_name": getattr(a, "app_name", "Telegram"),
                    "app_version": getattr(a, "app_version", ""),
                    "ip": getattr(a, "ip", "Unknown IP"),
                    "country": getattr(a, "country", ""),
                    "region": getattr(a, "region", ""),
                    "current": bool(getattr(a, "current", False)),
                    "date_created": created_str,
                    "date_active": active_str,
                })

            return {
                "success": True,
                "devices": devices,
                "total": len(devices),
            }
        except (AuthKeyUnregisteredError, UserDeactivatedError, UserDeactivatedBanError) as e:
            return {
                "success": False,
                "is_revoked": True,
                "error": f"Session logged out or revoked: {str(e)}",
            }
        except Exception as e:
            err_str = str(e).lower()
            is_rev = "auth key" in err_str or "unregistered" in err_str or "revoked" in err_str or "deactivated" in err_str
            return {
                "success": False,
                "is_revoked": is_rev,
                "error": f"Failed to retrieve authorizations: {str(e)}",
            }
        finally:
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                pass

    async def logout_session(self, session_path: str) -> Dict[str, Any]:
        """Logs out the session from Telegram and removes local session file."""
        p = Path(session_path)
        if not p.exists() and not str(session_path).endswith(".session"):
            p = Path(f"{session_path}.session")

        cfg = await self.get_client_config()
        base_path = str(p.with_suffix(""))

        client = TelegramClient(
            base_path,
            cfg["api_id"],
            cfg["api_hash"],
            device_model=cfg["device_model"],
            system_version=cfg["system_version"],
            app_version=cfg["app_version"],
            lang_code=cfg["lang_code"],
            system_lang_code=cfg["system_lang_code"],
            proxy=cfg["proxy"],
        )

        try:
            await client.connect()
            if await client.is_user_authorized():
                await client.log_out()
        except Exception as e:
            print(f"[Logout Warning] {e}")
        finally:
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                pass

        if p.exists():
            try:
                os.remove(p)
            except Exception:
                pass

        return {"success": True}

    async def terminate_other_sessions(self, session_path: str) -> Dict[str, Any]:
        """Attempts to terminate all other active authorizations for this session."""
        p = Path(session_path)
        if not p.exists() and not str(session_path).endswith(".session"):
            p = Path(f"{session_path}.session")
        if not p.exists():
            return {"success": False, "error": "Session file not found."}

        cfg = await self.get_client_config()
        base_path = str(p.with_suffix(""))

        client = TelegramClient(
            base_path,
            cfg["api_id"],
            cfg["api_hash"],
            device_model=cfg["device_model"],
            system_version=cfg["system_version"],
            app_version=cfg["app_version"],
            lang_code=cfg["lang_code"],
            system_lang_code=cfg["system_lang_code"],
            proxy=cfg["proxy"],
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return {"success": False, "error": "Session is expired or logged out."}

            await client(ResetAuthorizationsRequest())
            return {"success": True}
        except FreshResetAuthorisationForbiddenError:
            return {
                "success": False,
                "fresh_wait": True,
                "error": "Telegram Security Policy: You cannot terminate other sessions until this login is at least 24 hours old.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                pass


# Global session manager instance
session_manager = SessionManager()

## services/database/email_services.py

import logging
import re
from typing import Optional, List, Dict, Set, Tuple
from datetime import datetime, timezone
from pathlib import Path
import json

from core import db
from models.email_schemas import (
    EmailAccountSchema, 
    EmailAccountProfile, 
    EmailAccountData,
    CompleteAccountInfo
)

log = logging.getLogger(__name__)


class EmailAccountService:
    """Service untuk mengelola email accounts."""
    
    @staticmethod
    async def get_active_accounts() -> List[EmailAccountSchema]:
        """Get all active email accounts."""
        try:
            query = """
                SELECT id, email, app_password, is_active
                FROM email.accounts
                WHERE is_active = true
                ORDER BY id
            """
            results = await db.fetch(query)
            return [EmailAccountSchema(**dict(row)) for row in results]
        except Exception as e:
            log.error(f"[ EMAIL ACCOUNT SERVICE ] Error fetching accounts: {e}")
            raise
    
    @staticmethod
    async def get_account_by_id(account_id: int) -> Optional[EmailAccountSchema]:
        """Get account by ID."""
        try:
            query = """
                SELECT id, email, app_password, is_active
                FROM email.accounts
                WHERE id = $1 AND is_active = true
            """
            result = await db.fetchrow(query, account_id)
            return EmailAccountSchema(**dict(result)) if result else None
        except Exception as e:
            log.error(f"[ EMAIL ACCOUNT SERVICE ] Error fetching account: {e}")
            raise


class ProfileService:
    """Service untuk account profiles."""
    
    @staticmethod
    async def get_profile(account_id: int) -> Optional[EmailAccountProfile]:
        """Get profile for account."""
        try:
            query = """
                SELECT account_id, name, username, gender, phone
                FROM email.account_profiles
                WHERE account_id = $1
            """
            result = await db.fetchrow(query, account_id)
            return EmailAccountProfile(**dict(result)) if result else None
        except Exception as e:
            log.error(f"[ PROFILE SERVICE ] Error fetching profile: {e}")
            raise


class AccountDataService:
    """Service untuk account data (blocked positions only)."""
    
    @staticmethod
    async def get_account_data(account_id: int) -> Optional[EmailAccountData]:
        """Get account data (blocked positions configuration)."""
        try:
            query = """
                SELECT account_id, blocked_job_position
                FROM email.account_data
                WHERE account_id = $1
            """
            result = await db.fetchrow(query, account_id)
            if not result:
                return None

            data = dict(result)

            blocked = data.get("blocked_job_position")
            if isinstance(blocked, str):
                data["blocked_job_position"] = json.loads(blocked)

            return EmailAccountData(**data)

        except Exception as e:
            log.error(f"[ ACCOUNT DATA SERVICE ] Error fetching data: {e}")
            raise
    
    @staticmethod
    def is_position_blocked(
        account_data: EmailAccountData, 
        position: str
    ) -> bool:
        """Check if position is blocked based on keywords or regex."""
        try:
            position_lower = " ".join(position.lower().split())
            blocked = account_data.blocked_job_position
            
            # Check keywords
            keywords = blocked.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in position_lower:
                    return True
            
            # Check regex patterns
            patterns = blocked.get("regex_patterns", [])
            for pattern in patterns:
                try:
                    if re.search(pattern, position_lower):
                        return True
                except re.error:
                    log.warning(f"[ ACCOUNT DATA SERVICE ] Invalid regex: {pattern}")
                    continue
            
            return False
        except Exception as e:
            log.error(f"[ ACCOUNT DATA SERVICE ] Error checking blocked position: {e}")
            return False  # Fail open


class CompleteAccountService:
    """Service untuk mendapatkan complete account info."""
    
    @staticmethod
    async def get_complete_account_info(account_id: int) -> Optional[CompleteAccountInfo]:
        """Get complete account information."""
        try:
            account = await EmailAccountService.get_account_by_id(account_id)
            if not account:
                return None
            
            profile = await ProfileService.get_profile(account_id)
            if not profile:
                log.error(f"[ COMPLETE ACCOUNT SERVICE ] No profile for account {account_id}")
                return None
            
            data = await AccountDataService.get_account_data(account_id)
            if not data:
                log.error(f"[ COMPLETE ACCOUNT SERVICE ] No data for account {account_id}")
                return None
            
            return CompleteAccountInfo(
                account=account,
                profile=profile,
                data=data
            )
        except Exception as e:
            log.error(f"[ COMPLETE ACCOUNT SERVICE ] Error getting complete info: {e}")
            raise
    
    @staticmethod
    async def get_all_active_complete_accounts() -> List[CompleteAccountInfo]:
        """Get all active accounts with complete info."""
        try:
            accounts = await EmailAccountService.get_active_accounts()
            complete_accounts = []
            
            for account in accounts:
                complete = await CompleteAccountService.get_complete_account_info(account.id)
                if complete:
                    complete_accounts.append(complete)
            
            return complete_accounts
        except Exception as e:
            log.error(f"[ COMPLETE ACCOUNT SERVICE ] Error getting all accounts: {e}")
            raise


class SentLogService:
    """Service untuk sent logs."""
    
    @staticmethod
    async def check_already_sent(target_email: str, sender_email: str) -> bool:
        """Check if email already sent."""
        try:
            query = """
                SELECT EXISTS(
                    SELECT 1 
                    FROM email.sent_logs 
                    WHERE target_email = $1 AND sender_email = $2
                )
            """
            result = await db.fetchval(query, target_email, sender_email)
            return bool(result)
        except Exception as e:
            log.error(f"[ SENT LOG SERVICE ] Error checking sent: {e}")
            raise
    
    @staticmethod
    async def record_sent_batch(
        emails: List[Tuple[str, str]],  # [(target, sender), ...]
    ) -> int:
        """Record multiple sent emails."""
        try:
            timestamp = datetime.now(timezone.utc)
            
            query = """
                INSERT INTO email.sent_logs 
                (target_email, sender_email, sent_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (target_email, sender_email) DO NOTHING
                RETURNING id
            """
            
            count = 0
            async with db.transaction():
                for target_email, sender_email in emails:
                    result = await db.fetchval(
                        query, target_email, sender_email, timestamp
                    )
                    if result:
                        count += 1
            
            log.info(f"[ SENT LOG SERVICE ] Recorded {count}/{len(emails)} emails")
            return count
        except Exception as e:
            log.error(f"[ SENT LOG SERVICE ] Error recording batch: {e}")
            raise
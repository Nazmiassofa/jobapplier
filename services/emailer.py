## services/emailer.py

from aiosmtplib import SMTP
from aiosmtplib.errors import SMTPException, SMTPAuthenticationError

import logging
from typing import Optional, Set, List
from pathlib import Path
from helper.email_helper import EmailHelper

from config.const import FEMALE_KEYWORDS, MALE_KEYWORDS
from .email_stats import EmailLogStats

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from .database.email_services import (
    CompleteAccountService,
    AccountDataService,
    SentLogService,
    EmailAccountSchema
)
from models.email_schemas import CompleteAccountInfo

log = logging.getLogger(__name__)

class EmailValidationError(Exception):
    """Raised when email data validation fails."""
    pass


class EmailSender:
    """Simplified email sender with gender-based filtering."""
    
    def __init__(self, stats: EmailLogStats):
        
        self._template_cache: dict[str, str] = {}
        self.stats = stats  

    
    async def send_email_for_account(self, 
                                     account_id: int,
                                     email_data: dict) -> bool:
        """
        Send email using specific account.
        
        Args:
            account_id: ID of sender account
            email_data: Job application data
            
        email_data structure:
            {
                "is_job_vacancy": true,
                "email": ["hr@company.com"],
                "position": "Software Engineer",
                "subject_email": null,
                "gender_required": "female"  # or "male" or null
            }
        
        Returns:
            bool: Success status
        """
        try:
            # 1. Load complete account info
            account_info = await CompleteAccountService.get_complete_account_info(account_id)
            if not account_info:
                log.error(f"[ EMAILER ] Account not found: {account_id}")
                return False
            
            # 2. Validate and extract data
            target_emails, position, job_gender = EmailHelper._validate_and_extract(email_data)
                        
            # 3. Check business rules
            if not await self._should_send_email(
                account_info, target_emails, position, job_gender
            ):
                return False
            
            # 4. Get paths based on username
            username = account_info.profile.username
            cv_path = EmailHelper.get_cv_path(username)
            template_path = EmailHelper.get_template_path(username)
            
            # 5. Prepare email components
            subject = self._prepare_subject(email_data, position, account_info.profile.name)
            body_html = await self._load_and_render_template(
                template_path,
                {
                    "position": position,
                    "name": account_info.profile.name,
                    "phone": account_info.profile.phone
                }
            )
            
            # 6. Build and send message
            msg = self._build_message(
                account_info, list(target_emails), subject, 
                body_html, cv_path
            )
            await self._send_smtp(account_info.account, msg)
            
            # 7. Record sent emails
            await SentLogService.record_sent_batch(
                [(target, account_info.account.email) for target in target_emails]
            )
            
            self.stats.emails_sent += len(target_emails)
            
            log.info(
                f"[ EMAILER ] ✅ Email sent from {account_info.account.email} "
                f"to {len(target_emails)} recipients - Position: {position}"
            )
            return True
            
        except EmailValidationError as e:
            log.warning(f"[ EMAILER ] Validation failed: {e}")
            return False
        
        except (SMTPAuthenticationError, SMTPException) as e:
            log.error(f"[ EMAILER ] SMTP error: {e}")
            return False
        
        except Exception as e:
            self.stats.failed += 1
            log.error(f"[ EMAILER ] Unexpected error: {e}", exc_info=True)
            return False

    
    async def _should_send_email(self,
                                 account_info: CompleteAccountInfo,
                                 target_emails: Set[str],
                                 position: str,
                                 job_gender: Optional[str]
                                 ) -> bool:
        """
        Check business rules:
        1. Gender filtering (auto-block opposite gender)
        2. Blocked positions (from account_data)
        3. Duplicate checking
        """
        
        if job_gender:
            job_gender_lower = job_gender.lower()
            user_gender = account_info.profile.gender.lower()
            
            if user_gender == "male" and job_gender_lower in FEMALE_KEYWORDS:
                log.warning(
                    f"[ EMAILER ] Skipped: Female-only job for male user "
                    f"({account_info.profile.name}) - {position}"
                )
                self.stats.unmatch_gender += 1
                return False
            
            if user_gender == "female" and job_gender_lower in MALE_KEYWORDS:
                log.warning(
                    f"[ EMAILER ] Skipped: Male-only job for female user "
                    f"({account_info.profile.name}) - {position}"
                )
                self.stats.unmatch_gender += 1
                return False
        
        # 2. Check blocked positions (from JSON config)
        if AccountDataService.is_position_blocked(account_info.data, position):
            log.warning(
                f"[ EMAILER ] Skipped: Blocked position for "
                f"{account_info.profile.name} - {position}"
            )
            self.stats.unrelevan_position += 1
            return False
        
        # 3. Check duplicates
        try:
            sender_email = account_info.account.email
            for target_email in target_emails:
                if await SentLogService.check_already_sent(target_email, sender_email):
                    log.warning(
                        f"[ EMAILER ] Skipped: Already sent to {target_email} "
                        f"from {sender_email}"
                    )
                    self.stats.duplicate += 1
                    return False
            return True
        except Exception as e:
            log.error(f"[ EMAILER ] DB check failed: {e}")
            return False
    
    async def _load_and_render_template(
        self, 
        template_path: Path, 
        template_data: dict
    ) -> str:
        """Load and render HTML template with multiple placeholders."""
        template_path_str = str(template_path)
        
        # Check cache
        if template_path_str not in self._template_cache:
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            
            with open(template_path, "r", encoding="utf-8") as f:
                self._template_cache[template_path_str] = f.read()
        
        template = self._template_cache[template_path_str]
        return EmailHelper.render_template(template, template_data)
    
    def _prepare_subject(self, 
                         email_data: dict, 
                         position: str,
                         name: str) -> str:
        
        """Prepare email subject with name replacement."""
        raw_subject = email_data.get("subject_email")
        
        if not raw_subject:
            raw_subject = f"Lamaran Pekerjaan - {name}"
            
            if position:
                raw_subject = f"{position} - {name}"
            
            return raw_subject
        
        return EmailHelper.clean_subject(raw_subject, name)
    
    def _build_message(self,
                       account_info: CompleteAccountInfo,
                       target_emails: List[str],
                       subject: str,
                       body_html: str,
                       cv_path: Path) -> MIMEMultipart:
        
        """Build MIME message with CV attachment."""
        msg = MIMEMultipart('mixed')
        
        # Headers
        display_name = f"{account_info.profile.name} ({account_info.profile.username})"
        msg["From"] = f"{display_name} <{account_info.account.email}>"
        msg["To"] = ", ".join(target_emails)
        msg["Subject"] = subject
        
        # Body (HTML only for simplicity)
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        
        # CV attachment
        if not cv_path.exists():
            raise FileNotFoundError(f"CV not found: {cv_path}")
        
        with open(cv_path, "rb") as f:
            file_data = f.read()
        
        pdf_part = MIMEApplication(file_data, _subtype="pdf")
        pdf_part.add_header(
            'Content-Disposition',
            'attachment',
            filename=cv_path.name
        )
        msg.attach(pdf_part)
        
        return msg
    
    async def _send_smtp(
        self, 
        account: EmailAccountSchema, 
        msg: MIMEMultipart
    ) -> None:
        """Send email via Gmail SMTP."""
        smtp = SMTP(
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            timeout=30,
        )
        
        await smtp.connect()
        await smtp.login(account.email, account.app_password)
        await smtp.send_message(msg)
        await smtp.quit()


class BatchEmailProcessor:
    """Process job applications across multiple accounts."""
    
    def __init__(self, stats: EmailLogStats):
        self.sender = EmailSender(stats)
        self.stats = stats
    
    async def process_job_application(self, email_data: dict) -> dict[str, bool]:
        """
        Send job application from all active accounts.
        
        Returns:
            Dict mapping account email to success status
        """
        self.stats.processed += 1
        results = {}
        
        try:
            complete_accounts = await CompleteAccountService.get_all_active_complete_accounts()
            
            log.info(f"[ BATCH PROCESSOR ] Processing for {len(complete_accounts)} accounts")
            
            for account_info in complete_accounts:
                account_email = account_info.account.email
                
                try:
                    success = await self.sender.send_email_for_account(
                        account_info.account.id,
                        email_data
                    )
                    results[account_email] = success
                except Exception as e:
                    log.error(
                        f"[ BATCH PROCESSOR ] Failed for {account_email}: {e}",
                        exc_info=True
                    )
                    results[account_email] = False
            
            return results
            
        except Exception as e:
            log.error(f"[ BATCH PROCESSOR ] Error processing batch: {e}", exc_info=True)
            return results
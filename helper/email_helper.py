import logging

from typing import List, Set, Optional, Dict, Any, Tuple
from config.const import(CV_BASE_PATH, TEMPLATE_BASE_PATH)
from pathlib import Path

log = logging.getLogger(__name__)

class EmailValidationError(Exception):
    """Raised when email data validation fails."""
    pass


class EmailHelper:
    
    @staticmethod
    def get_cv_path(username: str) -> Path:
        """Get CV path based on username."""
        return CV_BASE_PATH / f"CV_{username}.pdf"
    
    @staticmethod
    def get_template_path(username: str) -> Path:
        """Get template path based on username."""
        return TEMPLATE_BASE_PATH / f"{username}.html"
        
    @staticmethod
    def render_template(template: str, data: dict) -> str:
        """Replace {{placeholder}} in template with dict values."""
        body = template
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            body = body.replace(placeholder, str(value))
        return body
    
    @staticmethod
    def normalize_emails(emails: List[str]) -> Set[str]:
        """Normalize email addresses."""
        normalized = set()
        for email in emails:
            if isinstance(email, str):
                cleaned = email.lower().strip()
                if cleaned:
                    normalized.add(cleaned)
        return normalized
    
    @staticmethod
    def clean_subject(subject: str, name: str) -> str:
        """
        Clean subject khusus untuk auto apply lowongan kerja.
        Hanya ganti kata 'Nama' (berbagai case) dengan nama user.
        """
        if not subject:
            return f"Lamaran Pekerjaan - {name}"

        original_subject = subject
        
        words = []
        i = 0
        n = len(subject)
        
        while i < n:
            if i + 4 <= n and subject[i:i+4].lower() == 'nama':
                is_word_start = (i == 0 or not subject[i-1].isalnum())
                is_word_end = (i + 4 == n or not subject[i+4].isalnum() or 
                            subject[i+4] in ['-', '_'])
                
                if is_word_start and is_word_end:
                    if i + 4 < n and subject[i+4] in ['-', '_']:
                        words.append(f'{name}')
                        i += 4  
                    else:
                        words.append(f'{name}')
                        i += 4 
                    continue
            
            words.append(subject[i])
            i += 1
        
        # Gabungkan semua bagian
        subject = ''.join(words)
        
        # Log perubahan jika ada
        if subject != original_subject:
            log.info(f"[ EMAILER ] Subject cleaned: '{original_subject}' → '{subject}'")
        
        return subject
    
    @staticmethod
    def _validate_and_extract(
            email_data: Dict[str, Any]
        ) -> Tuple[Set[str], str, Optional[str]]:
    
        """Validate email data and extract required fields."""
        
        
        target = email_data.get("email")
        if not target or not isinstance(target, list):
            raise EmailValidationError("Email target must be a non-empty list")
        
        normalized_targets = EmailHelper.normalize_emails(target)
        if not normalized_targets:
            raise EmailValidationError("No valid email addresses found")
        
        position = (email_data.get("position") or "").strip()
        if not position:
            raise EmailValidationError("Position is required")
        
        job_gender = email_data.get("gender_required")
        
        return normalized_targets, position, job_gender
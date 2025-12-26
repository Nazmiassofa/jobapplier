import logging

from typing import List, Set, Optional, Dict, Any, Tuple
from config.const import(CV_BASE_PATH, TEMPLATE_BASE_PATH)
from pathlib import Path
from config.settings import config

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
        
        # Gunakan pendekatan string manipulation tanpa regex kompleks
        words = []
        i = 0
        n = len(subject)
        
        while i < n:
            # Cek apakah substring mulai dari i adalah 'nama' (case insensitive)
            if i + 4 <= n and subject[i:i+4].lower() == 'nama':
                # Periksa apakah ini benar-benar kata 'nama' (bukan bagian dari kata lain)
                is_word_start = (i == 0 or not subject[i-1].isalnum())
                is_word_end = (i + 4 == n or not subject[i+4].isalnum() or 
                            subject[i+4] in ['-', '_'])
                
                if is_word_start and is_word_end:
                    # Ini adalah kata 'nama' yang valid
                    # Periksa apakah diikuti oleh separator
                    if i + 4 < n and subject[i+4] in ['-', '_']:
                        # 'nama' diikuti separator, ganti 'nama' saja
                        words.append(f'{name}')
                        i += 4  # Lewati 'nama'
                        # Separator akan ditambahkan di iterasi berikutnya
                    else:
                        # 'nama' tidak diikuti separator, ganti seluruhnya
                        words.append(f'{name}')
                        i += 4  # Lewati 'nama'
                    continue
            
            # Jika bukan 'nama', tambahkan karakter saat ini
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
        position = email_data.get("position", "").strip()
        job_gender = email_data.get("gender_required")
        
        if not target or not isinstance(target, list):
            raise EmailValidationError("Email target must be a non-empty list")
        
        # if config.ENVIRONMENT != "PROD":
        #     target = [f"{config.DEV_EMAIL}"]
        
        normalized_targets = EmailHelper.normalize_emails(target)
        
        if not normalized_targets:
            raise EmailValidationError("No valid email addresses found")
        
        if not position:
            raise EmailValidationError("Position is required")
        
        return normalized_targets, position, job_gender
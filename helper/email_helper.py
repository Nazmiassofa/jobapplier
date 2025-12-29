## helper/email_helper.py

import logging
import re

from typing import List, Set, Optional, Dict, Any, Tuple
from config.const import(CV_BASE_PATH, TEMPLATE_BASE_PATH)
from pathlib import Path

log = logging.getLogger(__name__)

class EmailValidationError(Exception):
    """Raised when email data validation fails."""
    pass


class EmailHelper:
            
    @staticmethod
    def clean_subject(subject: str, data: Dict[str, Any]) -> str:
        """
        Replace {{placeholder}} in subject with user data.
        Unknown placeholders will be removed entirely.
        
        Args:
            subject: Subject template with {{placeholders}}
            data: Dict containing replacement values
            
        Example:
            subject = "Lowongan_{{name}}_{{position}}_{{domisili}}"
            data = {"name": "John", "position": "Backend Developer"}
            result = "Lowongan_John_Backend Developer"
        """
        original_subject = subject
        
        # Find all {{placeholder}} patterns
        pattern = r'\{\{(\w+)\}\}'
        
        def replace_placeholder(match):
            key = match.group(1)
            value = data.get(key)
            
            if value is None:
                log.warning(
                    f"[ EMAILER ] Placeholder '{{{{{key}}}}}' not found in data, removing it"
                )
                return ""  # Remove placeholder entirely
            
            return str(value)
        
        cleaned_subject = re.sub(pattern, replace_placeholder, subject)
        
        # Clean up extra spaces, underscores, and dashes
        cleaned_subject = re.sub(r'_{2,}', '_', cleaned_subject)  # Multiple underscores → single
        cleaned_subject = re.sub(r'-{2,}', '-', cleaned_subject)  # Multiple dashes → single
        cleaned_subject = re.sub(r'\s{2,}', ' ', cleaned_subject)  # Multiple spaces → single
        cleaned_subject = re.sub(r'[_\-\s]+$', '', cleaned_subject)  # Trailing separators
        cleaned_subject = re.sub(r'^[_\-\s]+', '', cleaned_subject)  # Leading separators
        
        cleaned_subject = cleaned_subject.strip()
                
        if not cleaned_subject:
            name = data.get("name", "Applicant")
            log.warning(
                f"[ EMAILER ] All placeholders removed from '{original_subject}', "
                f"using default subject"
            )
            return f"Lamaran Pekerjaan - {name}"
        
        # Log changes if any
        if cleaned_subject != original_subject:
            log.info(f"[ EMAILER ] Subject cleaned: '{original_subject}' → '{cleaned_subject}'")
        
        return cleaned_subject
    
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
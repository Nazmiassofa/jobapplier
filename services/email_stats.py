# services/email_stats.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass
class EmailLogStats:
    processed: int = 0
    emails_sent: int = 0
    failed: int = 0
    unmatch_gender: int = 0
    unrelevan_position: int = 0
    duplicate: int = 0
    last_reset: datetime = field(default_factory=datetime.now)
    
    def reset(self):
        self.__init__()
    
    def get_summary(self) -> str:
        uptime = datetime.now() - self.last_reset
        return f"""
╔══════════════════════════════════════════════╗
║         EMAIL STATS - Last {uptime.seconds//3600}h {(uptime.seconds//60)%60}m          ║
╠══════════════════════════════════════════════╣
║ Jobs Processed    : {self.processed:>5}      ║
║ Emails Sent       : {self.emails_sent:>5} ✅ ║
║ Failed            : {self.failed:>5} ❌      ║
╠══════════════════════════════════════════════╣
║ Skipped (Gender)  : {self.unmatch_gender:>5} ║
║ Skipped (Blocked) : {self.unrelevan_position:>5}║
║ Skipped (Duplicate): {self.duplicate:>5}     ║
╚══════════════════════════════════════════════╝
        """.strip()
# services/email_stats.py

from dataclasses import dataclass, field
from datetime import datetime

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
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds // 60) % 60
        
        return (
            "\n"
            "╔════════════════════════════════════════════════╗\n"
            f"║         EMAIL STATS - Last {hours}h {minutes}m{' ' * (13 - len(str(hours)) - len(str(minutes)))}║\n"
            "╠════════════════════════════════════════════════╣\n"
            f"║ Jobs Processed     : {self.processed:>5}                 ║\n"
            f"║ Emails Sent        : {self.emails_sent:>5} ✅              ║\n"
            f"║ Failed             : {self.failed:>5} ❌              ║\n"
            "╠════════════════════════════════════════════════╣\n"
            f"║ Skipped (Gender)   : {self.unmatch_gender:>5}                 ║\n"
            f"║ Skipped (Blocked)  : {self.unrelevan_position:>5}                 ║\n"
            f"║ Skipped (Duplicate): {self.duplicate:>5}                 ║\n"
            "╚════════════════════════════════════════════════╝\n"
        )
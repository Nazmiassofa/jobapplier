## test_emailer.py

import asyncio
import logging
from pathlib import Path

from core import db
from config.logger import setup_logging
from services.emailer import BatchEmailProcessor, EmailSender

# Setup logging

setup_logging()
log = logging.getLogger(__name__)


async def init_test_db():
    """Initialize database pool for testing."""
    await db.init_db_pool()

async def close_test_db():
    """Close database pool after testing."""
    await db.close_pool()

async def test_single_account(email_data):
    """Test sending email for single account."""
    
    log.info("\n" + "="*60)
    log.info("TEST 1: Single Account Email Test")
    log.info("="*60)
    
    sender = EmailSender()
    
    # Test with account ID 1
    account_id = 1
    log.info(f"[ TEST ] Testing single account (ID: {account_id})")
    
    try:
        result = await sender.send_email_for_account(account_id, email_data)
        
        if result:
            log.info(f"[ TEST ] ✅ Email sent successfully for account {account_id}")
        else:
            log.warning(f"[ TEST ] ⚠️ Email not sent for account {account_id} (may be filtered)")
        
        return result
    
    except Exception as e:
        log.error(f"[ TEST ] ❌ Error testing single account: {e}", exc_info=True)
        return False


async def test_batch_processing(email_data):
    """Test batch processing for all active accounts."""
    log.info("\n" + "="*60)
    log.info("TEST 2: Batch Processing Test")
    log.info("="*60)
    
    processor = BatchEmailProcessor()
    
    log.info(f"[ TEST ] Testing batch processing for all active accounts")
    
    try:
        results = await processor.process_job_application(email_data)
        
        log.info("\n[ TEST ] Batch Processing Results:")
        log.info("-" * 60)
        
        for account_email, success in results.items():
            status = "SUCCESS" if success else "FAILED/FILTERED"
            log.info(f"  {account_email}: {status}")
        
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        log.info("-" * 60)
        log.info(f"[ TEST ] Summary: {success_count}/{total_count} successful")
        
        return results
    
    except Exception as e:
        log.error(f"[ TEST ] ❌ Error in batch processing: {e}", exc_info=True)
        return {}

async def run_all_tests():
    """Run all tests."""
    try:
    
        email_data = {
            "is_job_vacancy": True,
            "email": ["nizarulul1@gmail.com"],
            "position": "supervisor",
            "subject_email": "Lowongan Pekerjaan_tukang cumi",
            "gender_required": "male"
        }
        
        # Initialize DB
        await init_test_db()
        
        # Uncomment to test actual email sending:
        await test_single_account(email_data)
        # await test_batch_processing(email_data)
        
        log.info("\n" + "="*60)
        log.info("ALL TESTS COMPLETED")
        log.info("="*60)
    
    except Exception as e:
        log.error(f"[ TEST ] ❌ Fatal error in tests: {e}", exc_info=True)
    
    finally:
        # Close DB
        await close_test_db()


async def main():
    """Main test runner."""
    log.info("="*60)
    log.info("AUTO EMAILER - DUMMY TESTER")
    log.info("="*60)
    
    await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
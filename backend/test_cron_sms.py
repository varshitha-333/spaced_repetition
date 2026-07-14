"""
Cron Job SMS Test Script
Tests the daily notification cron job SMS sending functionality
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment_variables():
    """Check if all required environment variables are set."""
    logger.info("=" * 60)
    logger.info("CHECKING ENVIRONMENT VARIABLES")
    logger.info("=" * 60)
    
    vars_to_check = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "TWILIO_FROM_PHONE": os.getenv("TWILIO_FROM_PHONE"),
        "DAILY_NOTIFICATION_SECRET": os.getenv("DAILY_NOTIFICATION_SECRET"),
    }
    
    missing = []
    empty = []
    
    for var_name, var_value in vars_to_check.items():
        if var_value is None:
            missing.append(var_name)
            logger.error(f"❌ {var_name}: NOT SET")
        elif not var_value.strip():
            empty.append(var_name)
            logger.warning(f"⚠️  {var_name}: SET BUT EMPTY")
        else:
            # Show partial value for security
            if var_name in ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "SUPABASE_KEY", "DAILY_NOTIFICATION_SECRET"]:
                masked = var_value[:4] + "..." + var_value[-4:] if len(var_value) > 8 else "***"
                logger.info(f"✅ {var_name}: {masked}")
            else:
                logger.info(f"✅ {var_name}: {var_value}")
    
    if missing:
        logger.error(f"\n❌ MISSING VARIABLES: {', '.join(missing)}")
        logger.error("Please set these environment variables before testing.")
        return False
    
    if empty:
        logger.warning(f"\n⚠️  EMPTY VARIABLES: {', '.join(empty)}")
        logger.warning("These variables are set but have empty values.")
        return False
    
    logger.info("\n✅ All environment variables are set.")
    return True


def test_supabase_connection():
    """Test Supabase connection."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING SUPABASE CONNECTION")
    logger.info("=" * 60)
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        logger.info(f"Supabase URL: {supabase_url}")
        
        client = create_client(supabase_url, supabase_key)
        
        # Test by querying user_state table
        result = client.table('user_state').select('*').limit(1).execute()
        logger.info(f"✅ Connected to Supabase")
        logger.info(f"User state records found: {len(result.data)}")
        
        return True, client
        
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
        return False, None


def test_twilio_connection():
    """Test Twilio connection."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING TWILIO CONNECTION")
    logger.info("=" * 60)
    
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        logger.info(f"Account SID: {account_sid[:8]}...")
        
        client = Client(account_sid, auth_token)
        
        # Test by fetching account info
        account = client.api.accounts(account_sid).fetch()
        logger.info(f"✅ Connected to Twilio account: {account.friendly_name}")
        logger.info(f"Account status: {account.status}")
        
        # Check account balance
        balance = client.api.v2010.account.balance.fetch()
        logger.info(f"Account balance: {balance.balance} {balance.currency}")
        
        return True, client
        
    except Exception as e:
        logger.error(f"❌ Twilio connection failed: {e}")
        return False, None


def get_users_with_sms_enabled(supabase_client):
    """Get users who have SMS notifications enabled."""
    logger.info("\n" + "=" * 60)
    logger.info("GETTING USERS WITH SMS ENABLED")
    logger.info("=" * 60)
    
    try:
        result = supabase_client.table('user_state').select('*').execute()
        
        users_with_sms = []
        for state in result.data:
            if state.get('sms_notifications_enabled') and state.get('notification_phone'):
                users_with_sms.append(state)
        
        logger.info(f"✅ Found {len(users_with_sms)} users with SMS enabled")
        
        for user in users_with_sms:
            logger.info(f"  - User ID: {user['user_id']}")
            logger.info(f"    Phone: {user['notification_phone']}")
            logger.info(f"    Timezone: {user.get('notification_timezone', 'UTC')}")
            logger.info(f"    Notification hour: {user.get('notification_hour', 8)}")
        
        return users_with_sms
        
    except Exception as e:
        logger.error(f"❌ Failed to get users: {e}")
        return []


def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to E.164 format."""
    import re
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(phone).strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not re.fullmatch(r"\+\d{8,15}", cleaned or ""):
        raise ValueError("Phone number must be in international format, for example +14155550100")
    return cleaned


def test_sms_to_user(twilio_client, phone_number):
    """Send a test SMS to a specific user."""
    logger.info("\n" + "=" * 60)
    logger.info("SENDING TEST SMS")
    logger.info("=" * 60)
    
    try:
        from_number = os.getenv("TWILIO_FROM_PHONE")
        
        # Normalize phone number
        normalized_phone = normalize_phone_number(phone_number)
        logger.info(f"Original phone: {phone_number}")
        logger.info(f"Normalized phone: {normalized_phone}")
        
        # Send message
        message_body = f"📚 LearnFlow Cron Test SMS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Your cron job SMS is working!"
        
        logger.info(f"From: {from_number}")
        logger.info(f"To: {normalized_phone}")
        logger.info(f"Body: {message_body}")
        
        message = twilio_client.messages.create(
            body=message_body,
            from_=from_number,
            to=normalized_phone
        )
        
        logger.info(f"✅ SMS sent successfully!")
        logger.info(f"Message SID: {message.sid}")
        logger.info(f"Status: {message.status}")
        logger.info(f"Direction: {message.direction}")
        
        return True, message
        
    except Exception as e:
        logger.error(f"❌ SMS sending failed: {e}")
        return False, None


def test_cron_endpoint():
    """Test the cron job endpoint."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING CRON ENDPOINT")
    logger.info("=" * 60)
    
    try:
        import requests
        
        backend_url = os.getenv("BACKEND_URL", "http://localhost:5000")
        notification_secret = os.getenv("DAILY_NOTIFICATION_SECRET")
        
        if not notification_secret:
            logger.error("❌ DAILY_NOTIFICATION_SECRET not set")
            return False
        
        cron_url = f"{backend_url}/api/notifications/send-daily"
        
        logger.info(f"Cron URL: {cron_url}")
        logger.info(f"Secret: {notification_secret[:4]}...")
        
        headers = {
            "X-Notification-Secret": notification_secret,
            "X-Test-Mode": "true",
            "Content-Type": "application/json"
        }
        
        response = requests.post(cron_url, headers=headers, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text[:500]}")
        
        if response.status_code == 200:
            logger.info("✅ Cron endpoint test successful")
            return True
        else:
            logger.error(f"❌ Cron endpoint test failed with status {response.status_code}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Cron endpoint test failed: {e}")
        return False


def main():
    """Main test function."""
    logger.info("\n" + "=" * 60)
    logger.info("CRON JOB SMS TEST SCRIPT")
    logger.info("=" * 60)
    
    # Check environment variables
    if not check_environment_variables():
        logger.error("\n❌ Environment check failed. Please configure required environment variables.")
        sys.exit(1)
    
    # Test Supabase connection
    supabase_ok, supabase_client = test_supabase_connection()
    if not supabase_ok:
        logger.error("\n❌ Supabase connection failed.")
        sys.exit(1)
    
    # Test Twilio connection
    twilio_ok, twilio_client = test_twilio_connection()
    if not twilio_ok:
        logger.error("\n❌ Twilio connection failed.")
        sys.exit(1)
    
    # Get users with SMS enabled
    users = get_users_with_sms_enabled(supabase_client)
    
    if not users:
        logger.warning("\n⚠️  No users with SMS enabled found.")
        logger.info("You can still test the cron endpoint.")
    else:
        # Ask if user wants to send test SMS
        choice = input("\nDo you want to send a test SMS to the first user? (y/n): ").strip().lower()
        
        if choice in ['y', 'yes']:
            first_user = users[0]
            phone = first_user['notification_phone']
            
            success, message = test_sms_to_user(twilio_client, phone)
            
            if success:
                logger.info("\n✅ Test SMS sent successfully!")
                
                # Wait a moment and check status
                input("\nPress Enter to check message status...")
                
                # Check message status
                try:
                    status = twilio_client.messages(message.sid).fetch()
                    logger.info(f"Message status: {status.status}")
                    logger.info(f"Error code: {status.error_code}")
                    logger.info(f"Error message: {status.error_message}")
                except Exception as e:
                    logger.error(f"Failed to check status: {e}")
            else:
                logger.error("\n❌ Test SMS failed.")
    
    # Test cron endpoint
    choice = input("\nDo you want to test the cron endpoint? (y/n): ").strip().lower()
    
    if choice in ['y', 'yes']:
        test_cron_endpoint()
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST COMPLETED")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

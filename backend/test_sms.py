"""
SMS Test Script
Tests Twilio SMS sending functionality
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
    """Check if all required Twilio environment variables are set."""
    logger.info("=" * 60)
    logger.info("CHECKING ENVIRONMENT VARIABLES")
    logger.info("=" * 60)
    
    vars_to_check = {
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "TWILIO_FROM_PHONE": os.getenv("TWILIO_FROM_PHONE"),
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
            masked = var_value[:4] + "..." + var_value[-4:] if len(var_value) > 8 else "***"
            logger.info(f"✅ {var_name}: {masked}")
    
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


def test_twilio_connection():
    """Test Twilio API connection."""
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


def test_twilio_number(client):
    """Test if the Twilio phone number is valid and has SMS capability."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING TWILIO PHONE NUMBER")
    logger.info("=" * 60)
    
    try:
        from_number = os.getenv("TWILIO_FROM_PHONE")
        logger.info(f"From number: {from_number}")
        
        # Get phone number info
        phone_numbers = client.incoming_phone_numbers.list(phone_number=from_number)
        
        if not phone_numbers:
            logger.error(f"❌ Phone number {from_number} not found in Twilio account")
            return False
        
        phone = phone_numbers[0]
        logger.info(f"✅ Phone number found: {phone.friendly_name}")
        logger.info(f"Capabilities: {phone.capabilities}")
        
        if phone.capabilities.get('sms'):
            logger.info("✅ SMS capability enabled")
        else:
            logger.error("❌ SMS capability NOT enabled on this number")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Phone number validation failed: {e}")
        return False


def normalize_phone_number(phone):
    """Normalize phone number to E.164 format."""
    # Remove all non-numeric characters
    phone = ''.join(c for c in phone if c.isdigit())
    
    # Add + if not present
    if not phone.startswith('+'):
        phone = '+' + phone
    
    return phone


def send_test_sms(client, to_phone):
    """Send a test SMS message."""
    logger.info("\n" + "=" * 60)
    logger.info("SENDING TEST SMS")
    logger.info("=" * 60)
    
    try:
        from_number = os.getenv("TWILIO_FROM_PHONE")
        
        # Normalize phone number
        normalized_phone = normalize_phone_number(to_phone)
        logger.info(f"Original phone: {to_phone}")
        logger.info(f"Normalized phone: {normalized_phone}")
        
        # Send message
        message_body = f"📚 LearnFlow SMS Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Your SMS is working!"
        
        logger.info(f"From: {from_number}")
        logger.info(f"To: {normalized_phone}")
        logger.info(f"Body: {message_body}")
        
        message = client.messages.create(
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


def check_message_status(client, message_sid):
    """Check the status of a sent message."""
    logger.info("\n" + "=" * 60)
    logger.info("CHECKING MESSAGE STATUS")
    logger.info("=" * 60)
    
    try:
        message = client.messages(message_sid).fetch()
        
        logger.info(f"Message SID: {message.sid}")
        logger.info(f"Status: {message.status}")
        logger.info(f"Direction: {message.direction}")
        logger.info(f"From: {message.from_}")
        logger.info(f"To: {message.to}")
        logger.info(f"Body: {message.body}")
        logger.info(f"Date created: {message.date_created}")
        logger.info(f"Date sent: {message.date_sent}")
        logger.info(f"Date updated: {message.date_updated}")
        logger.info(f"Error code: {message.error_code}")
        logger.info(f"Error message: {message.error_message}")
        
        return message
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        return None


def main():
    """Main test function."""
    logger.info("\n" + "=" * 60)
    logger.info("SMS TEST SCRIPT")
    logger.info("=" * 60)
    
    # Check environment variables
    if not check_environment_variables():
        logger.error("\n❌ Environment check failed. Please configure Twilio credentials.")
        sys.exit(1)
    
    # Test Twilio connection
    connected, client = test_twilio_connection()
    if not connected:
        logger.error("\n❌ Twilio connection failed. Please check credentials.")
        sys.exit(1)
    
    # Test Twilio phone number
    if not test_twilio_number(client):
        logger.error("\n❌ Twilio phone number validation failed.")
        sys.exit(1)
    
    # Get phone number from user or use default
    to_phone = input("\nEnter phone number to send test SMS (with country code, e.g., +919110542033): ").strip()
    
    if not to_phone:
        logger.error("❌ Phone number is required.")
        sys.exit(1)
    
    # Send test SMS
    success, message = send_test_sms(client, to_phone)
    
    if success:
        logger.info("\n✅ Test SMS sent successfully!")
        
        # Wait a moment and check status
        input("\nPress Enter to check message status...")
        
        # Check message status
        check_message_status(client, message.sid)
        
        logger.info("\n" + "=" * 60)
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info("Please check your phone for the test message.")
    else:
        logger.error("\n❌ Test SMS failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

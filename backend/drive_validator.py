"""
Google Drive Link Validator
Validates Drive links and checks file accessibility
"""

import requests
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DriveLinkValidator:
    """Validate Google Drive links and check file accessibility."""
    
    def __init__(self, drive_service):
        self.drive_service = drive_service
    
    def validate_link(self, drive_link: str) -> Dict[str, any]:
        """
        Validate a Google Drive link.
        Returns validation result with status and details.
        """
        result = {
            'valid': False,
            'accessible': False,
            'error': None,
            'file_id': None,
            'file_name': None,
            'mime_type': None
        }
        
        try:
            # Extract file ID from link
            file_id = self._extract_file_id(drive_link)
            if not file_id:
                result['error'] = 'Invalid Drive link format'
                return result
            
            result['file_id'] = file_id
            
            # Check if file exists and is accessible
            file_info = self._get_file_info(file_id)
            if not file_info:
                result['error'] = 'File not found or inaccessible'
                return result
            
            result['valid'] = True
            result['accessible'] = True
            result['file_name'] = file_info.get('name')
            result['mime_type'] = file_info.get('mimeType')
            
            logger.info(f"Drive link validated: {file_id} - {file_info.get('name')}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Drive link validation failed: {e}")
        
        return result
    
    def _extract_file_id(self, drive_link: str) -> Optional[str]:
        """Extract file ID from Google Drive link."""
        try:
            # Handle various Drive link formats
            # Format 1: https://drive.google.com/file/d/FILE_ID/view
            # Format 2: https://drive.google.com/open?id=FILE_ID
            # Format 3: https://docs.google.com/document/d/FILE_ID/edit
            
            parsed = urlparse(drive_link)
            
            if 'drive.google.com' in parsed.netloc:
                # Extract from path
                if '/file/d/' in parsed.path:
                    file_id = parsed.path.split('/file/d/')[1].split('/')[0]
                    return file_id
                elif '/open' in parsed.path:
                    # Extract from query parameter
                    from urllib.parse import parse_qs
                    query = parse_qs(parsed.query)
                    return query.get('id', [None])[0]
            
            elif 'docs.google.com' in parsed.netloc:
                # Google Docs/Sheets/Slides
                if '/document/d/' in parsed.path:
                    file_id = parsed.path.split('/document/d/')[1].split('/')[0]
                    return file_id
                elif '/spreadsheets/d/' in parsed.path:
                    file_id = parsed.path.split('/spreadsheets/d/')[1].split('/')[0]
                    return file_id
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract file ID: {e}")
            return None
    
    def _get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file info from Drive API."""
        try:
            if not self.drive_service:
                return None
            
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,trashed'
            ).execute()
            
            # Check if file is trashed
            if file.get('trashed'):
                logger.warning(f"File {file_id} is in trash")
                return None
            
            return file
        except Exception as e:
            logger.error(f"Failed to get file info for {file_id}: {e}")
            return None
    
    def validate_batch(self, drive_links: list) -> Dict[str, any]:
        """
        Validate multiple Drive links.
        Returns summary with individual results.
        """
        results = {
            'total': len(drive_links),
            'valid': 0,
            'invalid': 0,
            'accessible': 0,
            'inaccessible': 0,
            'details': []
        }
        
        for link in drive_links:
            validation = self.validate_link(link)
            results['details'].append({
                'link': link,
                'result': validation
            })
            
            if validation['valid']:
                results['valid'] += 1
            else:
                results['invalid'] += 1
            
            if validation['accessible']:
                results['accessible'] += 1
            else:
                results['inaccessible'] += 1
        
        return results


def validate_drive_link_simple(drive_link: str) -> bool:
    """
    Simple validation without Drive API.
    Checks if link format is correct.
    """
    if not drive_link:
        return False
    
    # Basic format check
    if 'drive.google.com' not in drive_link and 'docs.google.com' not in drive_link:
        return False
    
    # Check for file ID pattern
    if '/d/' not in drive_link and 'id=' not in drive_link:
        return False
    
    return True

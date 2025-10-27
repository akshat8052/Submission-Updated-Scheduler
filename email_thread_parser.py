import re
from datetime import datetime
from typing import List, Dict, Any

class EmailThreadParser:
    """
    A utility class to parse and display email threads in a structured format
    """
    
    def __init__(self):
        self.thread_separators = [
            "From:",
            "-----Original Message-----",
            "________________________________",  # Outlook separator
            "---------- Forwarded message ----------",
            "On .* wrote:",  # Gmail style
            "Begin forwarded message:",
            "=== Original Message ===",
            "> -----Original Message-----",
            ">>> ",  # Multiple quote levels
        ]
        
        self.header_patterns = {
            'from': r'^From:\s*(.+)$',
            'to': r'^To:\s*(.+)$',
            'sent': r'^Sent:\s*(.+)$',
            'date': r'^Date:\s*(.+)$',
            'subject': r'^Subject:\s*(.+)$',
            'cc': r'^CC:\s*(.+)$',
            'bcc': r'^BCC:\s*(.+)$',
        }
    
    def parse_email_thread(self, email_body: str) -> List[Dict[str, Any]]:
        """
        Parse email body to extract individual emails in the thread
        
        Args:
            email_body (str): The complete email body text
            
        Returns:
            List[Dict]: List of parsed emails with metadata
        """
        if not email_body:
            return []
        
        lines = email_body.split('\n')
        emails = []
        current_email = {
            'headers': {},
            'content': [],
            'type': 'current',
            'quote_level': 0
        }
        
        in_headers = False
        header_section_complete = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for thread separator
            is_separator = any(sep in line for sep in self.thread_separators)
            
            # Check for quoted text patterns
            quote_level = self._get_quote_level(line)
            
            # Check if this is the start of a new email in thread
            if is_separator or (i > 0 and self._is_new_email_start(line, lines[max(0, i-1):i+3])):
                # Save current email if it has content
                if current_email['content'] or current_email['headers']:
                    emails.append(self._finalize_email(current_email))
                
                # Start new email
                current_email = {
                    'headers': {},
                    'content': [],
                    'type': 'quoted' if is_separator else 'reply',
                    'quote_level': quote_level
                }
                in_headers = True
                header_section_complete = False
                
                if not is_separator:
                    current_email['content'].append(line)
                    
            elif in_headers and not header_section_complete:
                # Try to extract headers
                header_found = False
                for header_name, pattern in self.header_patterns.items():
                    match = re.match(pattern, line_stripped, re.IGNORECASE)
                    if match:
                        current_email['headers'][header_name] = match.group(1).strip()
                        header_found = True
                        break
                
                if not header_found and line_stripped == '':
                    header_section_complete = True
                elif not header_found:
                    if header_section_complete or not any(':' in line for line in lines[i:i+3]):
                        header_section_complete = True
                        current_email['content'].append(line)
                    
            else:
                # Regular content line
                current_email['content'].append(line)
        
        # Add the last email
        if current_email['content'] or current_email['headers']:
            emails.append(self._finalize_email(current_email))
        
        # If no clear structure found, treat as single email
        if not emails:
            emails = [{
                'headers': {},
                'content': email_body,
                'type': 'current',
                'quote_level': 0,
                'email_id': 1,
                'timestamp': datetime.now().isoformat()
            }]
        else:
            # Add email IDs and timestamps for better tracking
            for idx, email in enumerate(emails):
                email['email_id'] = idx + 1
                if 'timestamp' not in email:
                    email['timestamp'] = datetime.now().isoformat()
        
        return emails[::-1]  # Reverse to show newest first
    
    def _get_quote_level(self, line: str) -> int:
        """Count the quote level based on > characters"""
        count = 0
        for char in line:
            if char == '>':
                count += 1
            elif char != ' ':
                break
        return count
    
    def _is_new_email_start(self, line: str, context_lines: List[str]) -> bool:
        """Determine if this line starts a new email based on context"""
        line_stripped = line.strip()
        
        # Check for common email start patterns
        email_start_patterns = [
            r'^On .+ wrote:$',
            r'^\d{1,2}/\d{1,2}/\d{4}.*wrote:$',
            r'^At \d{1,2}:\d{2}.*wrote:$',
            r'^From:.+@.+$',
            r'^Begin forwarded message:$'
        ]
        
        for pattern in email_start_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                return True
        
        return False
    
    def _finalize_email(self, email_dict: Dict) -> Dict[str, Any]:
        """Finalize email structure and clean content"""
        content = '\n'.join(email_dict['content']).strip()
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return {
            'headers': email_dict['headers'],
            'content': content,
            'type': email_dict['type'],
            'quote_level': email_dict['quote_level']
        }
    
    def extract_thread_summary(self, email_body: str) -> Dict[str, Any]:
        """
        Extract a summary of the email thread
        
        Returns:
            Dict containing thread statistics and summary
        """
        emails = self.parse_email_thread(email_body)
        
        summary = {
            'total_emails': len(emails),
            'participants': set(),
            'subjects': set(),
            'date_range': {'earliest': None, 'latest': None},
            'total_word_count': 0,
            'email_types': {'current': 0, 'reply': 0, 'quoted': 0}
        }
        
        for email in emails:
            # Count email types
            summary['email_types'][email['type']] = summary['email_types'].get(email['type'], 0) + 1
            
            # Extract participants
            if 'from' in email['headers']:
                summary['participants'].add(email['headers']['from'])
            if 'to' in email['headers']:
                for to_addr in email['headers']['to'].split(','):
                    summary['participants'].add(to_addr.strip())
            
            # Extract subjects
            if 'subject' in email['headers']:
                summary['subjects'].add(email['headers']['subject'])
            
            # Count words
            if email['content']:
                summary['total_word_count'] += len(email['content'].split())
        
        # Convert sets to lists for JSON serialization
        summary['participants'] = list(summary['participants'])
        summary['subjects'] = list(summary['subjects'])
        
        return summary
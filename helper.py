"""
Helper functions for the document processing pipeline
"""
import re
import os

def get_message_id(datastr):
    """Extract message_id from the email data string"""
    if not datastr:
        return None
        
    match = re.search(r"<([\w\d]+)@", datastr)
    if match:
        return match.group(1)
    else:
        return None


def get_thread_id(datastr):
    """Extract thread_id from the email data string"""
    if not datastr:
        return None
        
    match = re.search(r"@([A-Z0-9]+)\.", datastr)
    if match:
        return match.group(1)
    else:
        return None
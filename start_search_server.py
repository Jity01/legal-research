#!/usr/bin/env python3
"""
Quick start script for the search server
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import app

if __name__ == '__main__':
    print("=" * 60)
    print("Legal Case Search Server")
    print("=" * 60)
    print("\nStarting server on http://localhost:5001")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)

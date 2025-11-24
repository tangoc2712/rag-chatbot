#!/usr/bin/env python3
"""
Quick setup script for web chat interface
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    print(f"✅ Success: {description}")
    return True

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     E-Commerce RAG Chatbot - Web Chat Setup              ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check if we're in the right directory
    if not Path("src/api/main.py").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    steps = [
        ("Creating chat history table...", 
         "python3 scripts/create_chat_history_table.py"),
        
        ("Starting API server (this will keep running)...", 
         "python3 scripts/run.py api"),
    ]
    
    for description, command in steps:
        if not run_command(command, description):
            print(f"\n⚠️  Setup incomplete. Please fix the error above.")
            sys.exit(1)
        
        # If it's the API server command, it will block, so we break
        if "api" in command:
            break
    
    print("""
    
╔══════════════════════════════════════════════════════════╗
║              Setup Complete! 🎉                          ║
╚══════════════════════════════════════════════════════════╝

📱 Access the web chat interface at:
   👉 http://localhost:8000/static/index.html

📚 API Documentation:
   👉 http://localhost:8000/docs

💡 Tips:
   - Set customer ID with: "set customer <id>"
   - Ask about products, orders, and more!
   - Your chat history is saved automatically

Press Ctrl+C to stop the server
    """)

if __name__ == "__main__":
    main()

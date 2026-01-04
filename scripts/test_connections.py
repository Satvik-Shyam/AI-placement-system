#!/usr/bin/env python3
"""
Connection Test Script

Run this to verify all database connections are working.
Usage: python scripts/test_connections.py
"""
import sys
sys.path.insert(0, '.')

from app.db.postgres import test_postgres_connection
from app.db.mongodb import test_mongo_connection
from app.services.deepseek_client import get_deepseek_client
from app.core.config import get_settings


def main():
    settings = get_settings()
    print("=" * 50)
    print("PLACEMENT PLATFORM - CONNECTION TEST")
    print("=" * 50)
    
    # Test PostgreSQL
    print("\n[1] Testing PostgreSQL...")
    print(f"    URL: postgresql://{settings.postgres_user}:****@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    if test_postgres_connection():
        print("    ✅ PostgreSQL: CONNECTED")
    else:
        print("    ❌ PostgreSQL: FAILED")
    
    # Test MongoDB
    print("\n[2] Testing MongoDB...")
    print(f"    URI: {settings.mongodb_uri}")
    print(f"    Database: {settings.mongodb_db}")
    if test_mongo_connection():
        print("    ✅ MongoDB: CONNECTED")
    else:
        print("    ❌ MongoDB: FAILED")
    
    # Test DeepSeek (only if API key is set)
    print("\n[3] Testing DeepSeek API...")
    if settings.deepseek_api_key and settings.deepseek_api_key != "your_deepseek_api_key_here":
        print(f"    Base URL: {settings.deepseek_base_url}")
        client = get_deepseek_client()
        if client.test_connection():
            print("    ✅ DeepSeek: CONNECTED")
        else:
            print("    ❌ DeepSeek: FAILED")
    else:
        print("    ⚠️  DeepSeek: API key not configured (skip for now)")
    
    print("\n" + "=" * 50)
    print("Connection test complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
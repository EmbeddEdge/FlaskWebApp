#!/bin/bash

# Script to export Supabase schema using pg_dump
# This will create a complete schema dump including all DDL statements

# You'll need your Supabase database connection details
# Get these from: Supabase Dashboard > Project Settings > Database

# Format: postgresql://[user]:[password]@[host]:[port]/[database]

echo "Supabase Schema Export Script"
echo "=============================="
echo ""
echo "Before running, you need your DATABASE_URL from Supabase"
echo "Go to: Project Settings > Database > Connection String > URI"
echo ""
echo "Usage:"
echo "  export DATABASE_URL='your_connection_string'"
echo "  ./export_supabase_schema.sh"
echo ""

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export DATABASE_URL='postgresql://user:pass@host:port/database'"
    exit 1
fi

# Export schema only (no data)
echo "Exporting schema to schema_exported.sql..."
pg_dump "$DATABASE_URL" \
    --schema-only \
    --no-owner \
    --no-acl \
    --schema=public \
    --file=schema_exported.sql

if [ $? -eq 0 ]; then
    echo "✅ Schema exported successfully to schema_exported.sql"
    echo ""
    echo "Next steps:"
    echo "1. Review schema_exported.sql"
    echo "2. Update your schema.sql file with any missing tables"
else
    echo "❌ Export failed. Check your DATABASE_URL"
fi

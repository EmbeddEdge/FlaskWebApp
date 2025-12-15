"""
Export current Supabase schema to a SQL file
This script connects to your Supabase database and generates a schema.sql file
"""
import os
import psycopg2
from datetime import datetime

# Load environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("\nSet it first:")
    print("  export DATABASE_URL='your_supabase_connection_string'")
    exit(1)

def export_schema():
    """Export the current database schema"""
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        output = []
        output.append(f"-- Supabase Schema Export")
        output.append(f"-- Generated: {datetime.now().isoformat()}")
        output.append(f"-- Database: Supabase PostgreSQL\n")
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(tables)} tables: {', '.join(tables)}\n")
        
        for table in tables:
            print(f"Exporting: {table}...")
            
            # Get CREATE TABLE statement
            cursor.execute(f"""
                SELECT 
                    'CREATE TABLE IF NOT EXISTS ' || table_name || ' (' || 
                    string_agg(
                        column_name || ' ' || 
                        data_type ||
                        CASE 
                            WHEN character_maximum_length IS NOT NULL 
                            THEN '(' || character_maximum_length || ')'
                            ELSE ''
                        END ||
                        CASE 
                            WHEN column_default IS NOT NULL 
                            THEN ' DEFAULT ' || column_default
                            ELSE ''
                        END ||
                        CASE 
                            WHEN is_nullable = 'NO' 
                            THEN ' NOT NULL'
                            ELSE ''
                        END,
                        ', '
                        ORDER BY ordinal_position
                    ) || ');'
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = '{table}'
                GROUP BY table_name;
            """)
            
            create_statement = cursor.fetchone()
            if create_statement:
                output.append(f"\n-- Table: {table}")
                output.append(create_statement[0])
            
            # Get constraints
            cursor.execute(f"""
                SELECT
                    'ALTER TABLE ' || tc.table_name || 
                    ' ADD CONSTRAINT ' || tc.constraint_name || 
                    ' ' || tc.constraint_type || 
                    CASE 
                        WHEN tc.constraint_type = 'FOREIGN KEY' 
                        THEN ' (' || kcu.column_name || ') REFERENCES ' || 
                             ccu.table_name || '(' || ccu.column_name || ')'
                        WHEN tc.constraint_type = 'PRIMARY KEY'
                        THEN ' (' || kcu.column_name || ')'
                        ELSE ''
                    END || ';'
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                LEFT JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_schema = 'public' 
                    AND tc.table_name = '{table}'
                    AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE');
            """)
            
            constraints = cursor.fetchall()
            for constraint in constraints:
                if constraint[0]:
                    output.append(constraint[0])
        
        # Get indexes
        output.append("\n-- Indexes")
        cursor.execute("""
            SELECT indexdef || ';'
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        
        indexes = cursor.fetchall()
        for index in indexes:
            if index[0] and 'CREATE INDEX' in index[0]:
                output.append(index[0])
        
        # Write to file
        schema_content = '\n'.join(output)
        
        with open('schema_current.sql', 'w') as f:
            f.write(schema_content)
        
        print(f"\n✅ Schema exported successfully to schema_current.sql")
        print(f"   Total tables: {len(tables)}")
        print(f"   File size: {len(schema_content)} bytes")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error exporting schema: {e}")
        return False

if __name__ == "__main__":
    print("Supabase Schema Exporter")
    print("=" * 50)
    export_schema()

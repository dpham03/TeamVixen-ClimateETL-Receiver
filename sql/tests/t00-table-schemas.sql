-- Test for table schema (data base structure)

SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'prancer';
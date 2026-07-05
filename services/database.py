import pyodbc

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        'SERVER=142.79.224.75,21443;'
        'DATABASE=GreenTransSugamParivahan;'
        'UID=data_analytics;'
        'PWD=User@1234;'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
        'Connection Timeout=60;',
        timeout=60,
        autocommit=True
    )
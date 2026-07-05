import pymssql

def get_connection():
    return pymssql.connect(
        server="142.79.224.75",
        port=21443,
        user="data_analytics",
        password="User@1234",
        database="GreenTransSugamParivahan",
        timeout=60,
        login_timeout=60,
        as_dict=False
    )
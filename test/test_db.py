import json
from decimal import Decimal

from database.connection import PGConnection

c = PGConnection()
conn = c.get_conn()
cursor = conn.cursor()

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

# fetch results and save them as json 
# one row at a time, each row is a dict
# except useembed_description column
cursor.execute("SELECT * FROM goods;")
colnames = [desc[0] for desc in cursor.description]
raw_rows = cursor.fetchall()
rows = [dict(zip(colnames, row)) for row in raw_rows]

with open("./src/data/documents/goods.json", "w") as f:
    json.dump(rows, f, indent=4, default=decimal_serializer)

cursor.execute("SELECT * FROM services;")
colnames = [desc[0] for desc in cursor.description]
raw_rows = cursor.fetchall()
rows = [dict(zip(colnames, row)) for row in raw_rows]

with open("./src/data/documents/services.json", "w") as f:
    json.dump(rows, f, indent=4, default=decimal_serializer)


conn.close()

cursor.close()

from uuid import uuid4

import pandas as pd

from config import settings
from database.connection import PGConnection


def clean_goods_data(file_path) -> pd.DataFrame:
    df = pd.read_csv(file_path, dtype=str)
    df["CGST Rate  (%)"] = pd.to_numeric(
        df["CGST Rate  (%)"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    df["SGST / UTGST  Rate (%)"] = pd.to_numeric(
        df["SGST / UTGST  Rate (%)"].str.replace(r"[^\d.]", "", regex=True),
        errors="coerce",
    )
    df["IGST Rate  (%)"] = pd.to_numeric(
        df["IGST Rate  (%)"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    df["Compensation  Cess"] = pd.to_numeric(
        df["Compensation  Cess"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    return df


def clean_services_data(file_path) -> pd.DataFrame:
    df = pd.read_csv(file_path, dtype=str)
    df["CGST Rate(%)"] = pd.to_numeric(
        df["CGST Rate(%)"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    df["SGST/UTGST Rate(%)"] = pd.to_numeric(
        df["SGST/UTGST Rate(%)"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    df["IGST Rate(%)"] = pd.to_numeric(
        df["IGST Rate(%)"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"
    )
    return df


def insert_data(path: str) -> None:
    c = PGConnection(settings.POSTGRES_DSN.unicode_string())
    conn = c.get_conn()
    cursor = conn.cursor()

    table_name = path.split("/")[-1].split(".")[0]
    if table_name == "goods":
        df = clean_goods_data(path)
    elif table_name == "services":
        df = clean_services_data(path)

    try:
        conn.autocommit = False

        for index, row in df.iterrows():
            row_values = tuple(None if pd.isna(value) else value for value in row)
            row_values = (str(uuid4()),) + row_values
            placeholders = ", ".join(["%s"] * (len(df.columns) + 1))

            sql_query = f"INSERT INTO {table_name} VALUES ({placeholders})"

            cursor.execute(sql_query, row_values)

        conn.commit()
        conn.autocommit = True
    except Exception as e:
        print(e)
    finally:
        conn.close()


# Populate the database with excel data for demo
if __name__ == "__main__":
    paths = ["./data/tax_excels/goods.csv", "./data/tax_excels/services.csv"]

    for path in paths:
        insert_data(path)

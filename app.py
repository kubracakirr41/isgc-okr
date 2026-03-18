from flask import Flask, request, jsonify, send_file, render_template
import hashlib, hmac, secrets, io, os
from datetime import datetime
from functools import wraps
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    def get_db():
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    def dict_row(cursor, row):
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    PH = "%s"
else:
    import sqlite3
    def get_db():
        conn = sqlite3.connect("isgc.db")
        conn.row_factory = sqlite3.Row
        return conn
    def dict_row(cursor, row):
        return dict(row)
    PH = "?"

OKR_STRUKTUR = [
    {"no": 1, "okr": "LIDERLIK, YONETIM, SORUMLULUK", "krs": [
        {"no": 1, "kr": "Yoneticilerin Planli ISGC Aktivitelerine Katilim Orani", "birim": "%"},
        {"no": 2, "kr": "Yoneticilerin ISGC Kurul Toplantilarina Katilim Orani", "birim": "%"},
        {"no": 3, "kr": "ISGC Liderler Saha Turu Katilim Orani", "birim": "%"},
        {"no": 4, "kr": "Yillik Bolum ISGC Hedeflerinin Belirlenmesi Ve Ilgili Yoneticilerin Performans Hedeli Olarak Verilme Orani", "birim":

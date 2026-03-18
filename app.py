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
        {"no": 4, "kr": "Yillik Bolum ISGC Hedeflerinin Belirlenmesi Ve Ilgili Yoneticilerin Performans Hedeli Olarak Verilme Orani", "birim": "%"},
        {"no": 5, "kr": "Ust Yonetim Tarafindan Sirket ISGC Hedeflerinin Aylik Bazda Planli Olarak Gozden Gecirilme Orani", "birim": "%"},
    ]},
    {"no": 2, "okr": "YASALARA ve STANDARTLARA UYUM", "krs": [
        {"no": 1, "kr": "Is Sagligi Mevzuati Uyum Orani", "birim": "%"},
        {"no": 2, "kr": "Is Guvenligi Mevzuati Uyum Orani", "birim": "%"},
        {"no": 3, "kr": "Cevre Mevzuati Uyum Orani", "birim": "%"},
        {"no": 4, "kr": "Is Sagligi Mevzuati Uyumu Geciken Aksiyon Sayisi", "birim": "sayi"},
        {"no": 5, "kr": "Is Guvenligi Mevzuati Uyumu Geciken Aksiyon Sayisi", "birim": "sayi"},
        {"no": 6, "kr": "Cevre Mevzuati Uyumu Geciken Aksiyon Sayisi", "birim": "sayi"},
    ]},
    {"no": 3, "okr": "RISK YONETIMI", "krs": [
        {"no": 1, "kr": "Operasyon Bazli Is Sagligi Risk Degerlendirme Tamamlanma Orani", "birim": "%"},
        {"no": 2, "kr": "Cok Yuksek Is Sagligi Risk Sayisi", "birim": "sayi"},
        {"no": 3, "kr": "Yuksek Is Sagligi Risk Sayisi", "birim": "sayi"},
    ]},
    {"no": 4, "okr": "EGITIM, OGRETIM VE FARKINDALIK", "krs": [
        {"no": 1, "kr": "Calisan Basina Yillik ISGC Egitim Saati", "birim": "saat"},
        {"no": 2, "kr": "ISGC Egitim Plani Tamamlanma Orani", "birim": "%"},
    ]},
    {"no": 5, "okr": "OPERASYONEL ISGC STANDARTLARI", "krs": [
        {"no": 1, "kr": "Kayip Gunlu Kaza Siklik Orani", "birim": "oran"},
        {"no": 2, "kr": "Kaza Agirlik Orani", "birim": "oran"},
        {"no": 3, "kr": "Ramak Kala Sayisi", "birim": "sayi"},
    ]},
    {"no": 6, "okr": "DEGISIM YONETIMI", "krs": [
        {"no": 1, "kr": "Degisim Yonetimi Proseduru Uygulanma Orani", "birim": "%"},
    ]},
    {"no": 7, "okr": "HIZMET VE URUN ALIMI", "krs": [
        {"no": 1, "kr": "Yuklenici ISGC Denetim Tamamlanma Orani", "birim": "%"},
    ]},
    {"no": 8, "okr": "ACIL DURUM YONETIMI", "krs": [
        {"no": 1, "kr": "Acil Durum Tatbikat Plani Tamamlanma Orani", "birim": "%"},
    ]},
    {"no": 9, "okr": "KAZA, OLAY ARASTIRMA", "krs": [
        {"no": 1, "kr": "Kaza/Olay Arastirma Tamamlanma Orani", "birim": "%"},
        {"no": 2, "kr": "Kaza/Olay Aksiyonlarinin Zamaninda Kapanma Orani", "birim": "%"},
    ]},
    {"no": 10, "okr": "YENI PROJELER VE TASFIYELER", "krs": [
        {"no": 1, "kr": "Yeni Proje ISGC Degerlendirme Tamamlanma Orani", "birim": "%"},
    ]},
    {"no": 11, "okr": "GOZLEM, SUREKLI IYILESTIRME, ILETISIM", "krs": [
        {"no": 1, "kr": "ISGC Gozlem Plani Tamamlanma Orani", "birim": "%"},
        {"no": 2, "kr": "Kapatilan Iyilestirme Aksiyonu Orani", "birim": "%"},
    ]},
]

COMPANIES = [
    "ASSAN ALUMINYUM", "ASSAN HANIL", "ASSAN LIMAN",
    "ASSAN LOJISTIK", "ASSAN PANEL", "ISPAK ESNEK AMBALAJ",
]

MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AGU","SEP","OKT","NOV","DEC"]
MONTH_TR = ["Ocak","Subat","Mart","Nisan","Mayis","Haziran","Temmuz","Agustos","Eylul","Ekim","Kasim","Aralik"]

def init_db():
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'company',
            company TEXT, created_at TEXT DEFAULT (NOW()::text))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY, company TEXT NOT NULL, yil INTEGER NOT NULL,
            ay TEXT NOT NULL, okr_no INTEGER NOT NULL, kr_no INTEGER NOT NULL,
            deger REAL, giren_user TEXT, created_at TEXT, updated_at TEXT,
            UNIQUE(company, yil, ay, okr_no, kr_no))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER, expires_at TEXT)""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'company',
            company TEXT, created_at TEXT DEFAULT (datetime('now')))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, yil INTEGER NOT NULL,
            ay TEXT NOT NULL, okr_no INTEGER NOT NULL, kr_no INTEGER NOT NULL,
            deger REAL, giren_user TEXT, created_at TEXT, updated_at TEXT,
            UNIQUE(company, yil, ay, okr_no, kr_no))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER, expires_at TEXT)""")
    conn.commit()
    default_users = [
        ("admin","Admin2026!","admin",None),
        ("assan_al","AlPass26!","company","ASSAN ALUMINYUM"),
        ("assan_hanil","HanPass26!","company","ASSAN HANIL"),
        ("assan_liman","LimPass26!","company","ASSAN LIMAN"),
        ("assan_loj","LojPass26!","company","ASSAN LOJISTIK"),
        ("assan_panel","PanPass26!","company","ASSAN PANEL"),
        ("ispak","IspPass26!","company","ISPAK ESNEK AMBALAJ"),
    ]
    for username, password, role, company in default_users:
        try:
            if DATABASE_URL:
                cur.execute("INSERT INTO users (username,password_hash,role,company) VALUES (%s,%s,%s,%s)", (username, hash_password(password), role, company))
            else:
                cur.execute("INSERT INTO users (username,password_hash,role,company) VALUES (?,?,?,?)", (username, hash_password(password), role, company))
        except:
            pass
    conn.commit()
    conn.close()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_password(pw, hashed):
    return hmac.compare_digest(hash_password(pw), hashed)

def get_token():
    return request.headers.get("Authorization","").replace("Bearer ","") or request.cookies.get("token","")

def get_user_from_token(token):
    conn = get_db()
    cur = conn.cursor()
    try:
        if DATABASE_URL:
            cur.execute("SELECT u.* FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token=%s", (token,))
        else:
            cur.execute("SELECT u.* FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token=?", (token,))
        row = cur.fetchone()
        return dict_row(cur, row) if row else None
    finally:
        conn.close()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token()
        if not token:
            return jsonify({"error": "Yetkisiz erisim"}), 401
        user = get_user_from_token(token)
        if not user:
            return jsonify({"error": "Oturum suresi doldu"}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token()
        user = get_user_from_token(token)
        if not user or user["role"] != "admin":
            return jsonify({"error": "Yonetici yetkisi gerekli"}), 403
        request.user = user
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/giris")
def giris_page():
    return render_template("giris.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username","").strip()
    password = data.get("password","")
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    else:
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    user = dict_row(cur, row) if row else None
    conn.close()
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Kullanici adi veya sifre hatali"}), 401
    token = secrets.token_hex(32)
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        expires = "(NOW() + INTERVAL '8 hours')::text"
        cur.execute(f"INSERT INTO sessions(token,user_id,expires_at) VALUES(%s,%s,{expires})", (token, user["id"]))
    else:
        cur.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,datetime('now','+8 hours'))", (token, user["id"]))
    conn.commit()
    conn.close()
    return jsonify({"token": token, "role": user["role"], "company": user["company"], "username": user["username"]})

@app.route("/api/logout", methods=["POST"])
@require_auth
def logout():
    token = get_token()
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("DELETE FROM sessions WHERE token=%s", (token,))
    else:
        cur.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/me")
@require_auth
def me():
    return jsonify({"username": request.user["username"], "role": request.user["role"], "company": request.user["company"]})

@app.route("/api/okr-struktur")
@require_auth
def okr_struktur():
    return jsonify(OKR_STRUKTUR)

@app.route("/api/entries", methods=["POST"])
@require_auth
def save_entries():
    data = request.json or {}
    company = request.user["company"]
    if request.user["role"] == "admin":
        company = data.get("company", company)
    yil = int(data.get("yil", datetime.now().year))
    ay = data.get("ay", "")
    rows = data.get("rows", [])
    if not ay or ay not in MONTHS:
        return jsonify({"error": "Gecersiz ay"}), 400
    if not company:
        return jsonify({"error": "Sirket belirtilmedi"}), 400
    conn = get_db()
    cur = conn.cursor()
    saved = 0
    for row in rows:
        try:
            if DATABASE_URL:
                cur.execute("""INSERT INTO entries (company,yil,ay,okr_no,kr_no,deger,giren_user,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW()::text)
                    ON CONFLICT(company,yil,ay,okr_no,kr_no)
                    DO UPDATE SET deger=EXCLUDED.deger, updated_at=NOW()::text, giren_user=EXCLUDED.giren_user""",
                    (company, yil, ay, row["okr_no"], row["kr_no"], row.get("deger"), request.user["username"]))
            else:
                cur.execute("""INSERT INTO entries (company,yil,ay,okr_no,kr_no,deger,giren_user,updated_at)
                    VALUES (?,?,?,?,?,?,?,datetime('now'))
                    ON CONFLICT(company,yil,ay,okr_no,kr_no)
                    DO UPDATE SET deger=excluded.deger, updated_at=excluded.updated_at, giren_user=excluded.giren_user""",
                    (company, yil, ay, row["okr_no"], row["kr_no"], row.get("deger"), request.user["username"]))
            saved += 1
        except Exception as e:
            print(e)
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "saved": saved})

@app.route("/api/entries")
@require_auth
def get_entries():
    company = request.args.get("company")
    yil = request.args.get("yil", datetime.now().year)
    ay = request.args.get("ay")
    if request.user["role"] == "company":
        company = request.user["company"]
    conn = get_db()
    cur = conn.cursor()
    q = f"SELECT * FROM entries WHERE yil={PH}"
    params = [yil]
    if company:
        q += f" AND company={PH}"; params.append(company)
    if ay:
        q += f" AND ay={PH}"; params.append(ay)
    cur.execute(q, params)
    rows = [dict_row(cur, r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/dashboard/summary")
@require_auth
def dashboard_summary():
    yil = request.args.get("yil", datetime.now().year)
    conn = get_db()
    cur = conn.cursor()
    result = []
    for company in COMPANIES:
        if DATABASE_URL:
            cur.execute("SELECT ay, AVG(deger) as avg_deger FROM entries WHERE company=%s AND yil=%s AND deger IS NOT NULL GROUP BY ay", (company, yil))
        else:
            cur.execute("SELECT ay, AVG(deger) as avg_deger FROM entries WHERE company=? AND yil=? AND deger IS NOT NULL GROUP BY ay", (company, yil))
        rows = cur.fetchall()
        monthly = {}
        for r in rows:
            if DATABASE_URL:
                monthly[r[0]] = round(float(r[1]), 2)
            else:
                monthly[r["ay"]] = round(r["avg_deger"], 2)
        ytd_vals = list(monthly.values())
        ytd = round(sum(ytd_vals)/len(ytd_vals), 2) if ytd_vals else None
        result.append({"company": company, "monthly": monthly, "ytd": ytd, "ay_sayisi": len(monthly)})
    conn.close()
    return jsonify(result)

@app.route("/api/export/excel")
@require_auth
def export_excel():
    yil = int(request.args.get("yil", datetime.now().year))
    company_filter = request.args.get("company")
    if request.user["role"] == "company":
        company_filter = request.user["company"]
    conn = get_db()
    cur = conn.cursor()
    q = f"SELECT * FROM entries WHERE yil={PH}"
    params = [yil]
    if company_filter:
        q += f" AND company={PH}"; params.append(company_filter)
    cur.execute(q, params)
    rows = [dict_row(cur, r) for r in cur.fetchall()]
    conn.close()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ozet"
    header_font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    center = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws.merge_cells("A1:O1")
    ws["A1"] = f"KIBAR HOLDING - ISGC OKR TAKIP SISTEMI - {yil}"
    ws["A1"].font = Font(bold=True, color="FFFFFF", size=14, name="Calibri")
    ws["A1"].fill = PatternFill("solid", fgColor="0A0C10")
    ws["A1"].alignment = center
    headers = ["Sirket"] + MONTH_TR + ["YTD Ort."]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = header_font
        cell.fill = PatternFill("solid", fgColor="1A1E28")
        cell.alignment = center
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = 13 if col > 1 else 22
    entry_map = {}
    for r in rows:
        k = (r["company"], r["ay"])
        if k not in entry_map:
            entry_map[k] = []
        if r["deger"] is not None:
            entry_map[k].append(r["deger"])
    for i, company in enumerate(COMPANIES):
        row_idx = i + 3
        ws.cell(row=row_idx, column=1, value=company).font = Font(bold=True, name="Calibri")
        ws.cell(row=row_idx, column=1).border = border
        monthly_vals = []
        for j, ay in enumerate(MONTHS):
            vals = entry_map.get((company, ay), [])
            avg = round(sum(vals)/len(vals), 2) if vals else None
            if avg is not None:
                monthly_vals.append(avg)
            cell = ws.cell(row=row_idx, column=j+2, value=avg)
            cell.alignment = center
            cell.border = border
            if avg is not None:
                color = "00C87A" if avg >= 70 else ("FFC107" if avg >= 50 else "FF6B6B")
                cell.font = Font(color=color, bold=True, name="Calibri")
        ytd = round(sum(monthly_vals)/len(monthly_vals), 2) if monthly_vals else None
        ws.cell(row=row_idx, column=14, value=ytd).border = border
    ws.freeze_panes = "B3"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"ISGC_OKR_{yil}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/api/admin/users", methods=["GET"])
@require_admin
def list_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id,username,role,company,created_at FROM users ORDER BY id")
    rows = [dict_row(cur, r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/admin/users", methods=["POST"])
@require_admin
def create_user():
    data = request.json or {}
    username = data.get("username","").strip()
    password = data.get("password","")
    role = data.get("role","company")
    company = data.get("company")
    if not username or not password:
        return jsonify({"error": "Kullanici adi ve sifre zorunlu"}), 400
    conn = get_db()
    cur = conn.cursor()
    try:
        if DATABASE_URL:
            cur.execute("INSERT INTO users(username,password_hash,role,company) VALUES(%s,%s,%s,%s)", (username, hash_password(password), role, company))
        else:
            cur.execute("INSERT INTO users(username,password_hash,role,company) VALUES(?,?,?,?)", (username, hash_password(password), role, company))
        conn.commit()
    except:
        conn.close()
        return jsonify({"error": "Bu kullanici adi zaten var"}), 409
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@require_admin
def delete_user(uid):
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    else:
        cur.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/users/<int:uid>/password", methods=["PUT"])
@require_admin
def reset_password(uid):
    data = request.json or {}
    new_pw = data.get("password","")
    if len(new_pw) < 6:
        return jsonify({"error": "Sifre en az 6 karakter olmali"}), 400
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hash_password(new_pw), uid))
    else:
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_pw), uid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

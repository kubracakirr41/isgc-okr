# Kibar Holding – İSGÇ OKR Takip Sistemi

Şirket bazında aylık İSGÇ OKR verisi toplayan, dashboard'da gösteren ve Excel'e export eden web uygulaması.

---

## Sistem Mimarisi

```
isgc_app/
├── app.py              ← Flask backend (API + sayfa yönlendirme)
├── isgc.db             ← SQLite veritabanı (otomatik oluşur)
├── requirements.txt    ← Python bağımlılıkları
├── templates/
│   ├── index.html      ← Giriş sayfası
│   ├── giris.html      ← Şirket veri giriş ekranı
│   └── dashboard.html  ← Admin dashboard
└── README.md
```

---

## Kurulum

### 1. Python kurulumu (3.9+)
```bash
python --version   # 3.9 veya üzeri olmalı
```

### 2. Bağımlılıkları yükleyin
```bash
pip install flask openpyxl
```

### 3. Uygulamayı başlatın
```bash
cd isgc_app
python app.py
```

Uygulama http://localhost:5000 adresinde çalışmaya başlar.

---

## Varsayılan Kullanıcılar

| Kullanıcı Adı | Şifre         | Rol      | Şirket               |
|---------------|---------------|----------|----------------------|
| admin         | Admin2026!    | Yönetici | (tüm şirketler)      |
| assan_al      | AlPass26!     | Şirket   | ASSAN ALÜMİNYUM      |
| assan_hanil   | HanPass26!    | Şirket   | ASSAN HANİL          |
| assan_liman   | LimPass26!    | Şirket   | ASSAN LİMAN          |
| assan_loj     | LojPass26!    | Şirket   | ASSAN LOJİSTİK       |
| assan_panel   | PanPass26!    | Şirket   | ASSAN PANEL          |
| ispak         | IspPass26!    | Şirket   | İSPAK ESNEK AMBALAJ  |

> ⚠️ İlk kurulumdan sonra admin şifrelerini değiştirin!

---

## Kullanım

### Şirket kullanıcısı (aylık veri girişi)
1. http://localhost:5000 adresine gidin
2. Şirket kullanıcı adı ve şifresini girin
3. **Veri Girişi** sayfasında yıl ve ay seçin
4. 11 OKR kategorisindeki KR değerlerini girin
5. **Kaydet** butonuna tıklayın

### Admin (dashboard)
1. admin kullanıcısı ile giriş yapın
2. **Dashboard** sayfasında tüm şirketlerin verisini görün
3. **Excel İndir** butonu ile rapor alın

---

## API Endpointleri

| Method | URL                        | Açıklama                       |
|--------|----------------------------|--------------------------------|
| POST   | /api/login                 | Giriş (token döner)            |
| POST   | /api/logout                | Çıkış                          |
| GET    | /api/me                    | Aktif kullanıcı bilgisi        |
| GET    | /api/okr-struktur          | OKR/KR yapısı                  |
| POST   | /api/entries               | Toplu veri kaydetme            |
| GET    | /api/entries               | Veri sorgulama                 |
| GET    | /api/dashboard/summary     | Dashboard özet verisi          |
| GET    | /api/dashboard/okr-detail  | OKR bazında detay              |
| GET    | /api/export/excel          | Excel raporu indir             |
| GET    | /api/admin/users           | Kullanıcı listesi (admin)      |
| POST   | /api/admin/users           | Kullanıcı oluştur (admin)      |
| DELETE | /api/admin/users/<id>      | Kullanıcı sil (admin)          |
| PUT    | /api/admin/users/<id>/password | Şifre sıfırla (admin)      |

---

## Sunucuya Taşıma (Production)

### Linux sunucu için (Ubuntu/Debian)

```bash
# Gerekli paketler
sudo apt install python3-pip python3-venv nginx

# Sanal ortam
python3 -m venv venv
source venv/bin/activate
pip install flask openpyxl gunicorn

# Gunicorn ile çalıştır
gunicorn -w 4 -b 127.0.0.1:5000 app:app --daemon
```

### Nginx konfigürasyonu (/etc/nginx/sites-available/isgc)
```nginx
server {
    listen 80;
    server_name isgc.sirketiniz.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL için Let's Encrypt
```bash
sudo certbot --nginx -d isgc.sirketiniz.com
```

---

## Güvenlik Notları

- `app.secret_key` her başlatmada yeni oluşur – production'da sabit bir değer atayın
- Şifreler SHA-256 ile hash'lenerek saklanır
- Oturum tokenları 8 saat geçerlidir
- Şirket kullanıcıları yalnızca kendi şirketlerinin verisini görebilir/düzenleyebilir

---

## Destek

Teknik sorunlar için sistem yöneticinize başvurun.

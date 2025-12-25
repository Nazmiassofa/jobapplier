# Micro Service Job Auto Applier

Service untuk mengirim email lamaran kerja secara otomatis berdasarkan gender dan preferensi posisi.  
Sumber data lowongan bisa berasal darimanapun, contoh:
- Bot Telegram fetch data lowongan kerja > publish ke Redis
- Service scraper website lowongan > publish ke redis
- dll

Service ini akan melakukan subscribe ke Redis dan memproses pengiriman email **(support multiple email)**.


## Payload Sample

Contoh payload yang dikirim ke Redis:

```json
{
  "is_job_vacancy": true,
  "email": ["hr@company.com"],
  "position": "Software Engineer",
  "subject_email": null,
  "gender_required": "female"
}
```

---

## Tech Stack
- Redis
- PostgreSQL

---

## Database Tables

### email.accounts

Menyimpan akun email yang digunakan sebagai pengirim.

| Column        | Type          | Nullable | Default |
|---------------|---------------|----------|---------|
| id            | integer       | ❌       | auto    |
| email         | varchar(255)  | ❌       | —       |
| app_password  | varchar(500)  | ❌       | —       |
| is_active     | boolean       | ❌       | true    |
| created_at    | timestamptz   | ❌       | now()   |  

Gunakan App pasword, bukan password akun gmail.

---

### email.account_data

Menyimpan konfigurasi tambahan per akun email, seperti filter posisi pekerjaan yang tidak ingin dilamar.

| Column                | Type          | Nullable | Default |
|-----------------------|---------------|----------|---------|
| id                    | integer       | ❌       | auto    |
| account_id            | integer       | ❌       | —       |
| blocked_job_position  | jsonb         | ❌       | `{ "keywords": [], "regex_patterns": [] }` |
| created_at            | timestamptz   | ✅       | now()   |
| updated_at            | timestamptz   | ✅       | now()   |

**blocked_job_position**
- `keywords`: daftar kata kunci posisi yang diblokir
- `regex_patterns`: daftar regex untuk filtering lanjutan

---

### email.account_profiles

Menyimpan profil pengirim untuk personalisasi email (nama, kontak, dsb).

| Column      | Type          | Nullable | Default |
|-------------|---------------|----------|---------|
| id          | integer       | ❌       | auto    |
| account_id  | integer       | ❌       | —       |
| name        | varchar(255)  | ❌       | —       |
| username    | varchar(255)  | ❌       | —       |
| gender      | varchar(10)   | ❌       | —       |
| phone       | varchar(30)   | ✅       | —       |
| created_at  | timestamptz   | ❌       | now()   |

---

### email.sent_logs

Mencatat email yang berhasil dikirim untuk keperluan audit dan pencegahan duplikasi.

| Column        | Type          | Nullable | Default |
|---------------|---------------|----------|---------|
| id            | integer       | ❌       | auto    |
| target_email  | varchar(255)  | ❌       | —       |
| sender_email  | varchar(500)  | ❌       | —       |
| sent_at       | timestamptz   | ❌       | now()   |

---

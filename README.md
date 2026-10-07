# Otomasi NEW LOS — generate data & testing

Dua kegunaan, satu set Page Object (`pages/`):

| | Generate data (`generate/`) | Testing (`tests/`) |
| --- | --- | --- |
| Tujuan | Menyiapkan data sampai status tertentu (Origination Completed) | Memastikan fitur berperilaku benar |
| Hasil | Data di server + ID-nya (jejak di `runs/`) | Laporan pass/fail pytest |
| Gagal berarti | Hambatan: perbaiki, lalu teruskan dengan `--lanjut` | Temuan: kemungkinan bug |
| Sifat | Berurutan, menyimpan state antar fase | Tiap test berdiri sendiri |

## Generate data: Origination sampai Completed

Membuat satu Origination dari nol sampai berstatus **Completed**, dalam 12 fase lewat 7 akun:

| Fase | Akun | Langkah |
| --- | --- | --- |
| 1 | Staff Bisnis | Customer baru (search "aku" → Create New Customer & Pipeline), data pipeline, fasilitas (Konven, Syariah, atau keduanya) |
| 2 | Staff Bisnis | Submit pipeline, komentar "Bismillaah" (timeout server dicoba ulang; dilewati bila sudah ter-Submit) |
| 3 | TL Bisnis | Approval List → Go to task → Approve |
| 4 | Staff Bisnis | Go to task → Go To Origination (staff DEPI & DH, comment) |
| 5 | Staff Bisnis | Origination List → Detail → Pembahasan Origination: Tanggal Entry, dokumen wajib (nomor acak 6 digit, tanggal hari ini, PDF), Other Document (Add New → Create New) → Submit |
| 6 | TL Bisnis | Submit → Send |
| 7 | Kadiv Bisnis | Approve → Approve & Kirim ke LPS |
| 8 | TL DEPI | Isi dokumen wajib DEPI → Submit → Send |
| 9 | Kadiv DEPI | Approve |
| 10 | TL DH | Isi dokumen wajib DH → Submit → Send |
| 11 | Kadiv DH | Approve |
| 12 | Staff Bisnis | Cek status Completed di Origination List |

> **Membuat data sungguhan** di `base_url`. Pastikan URL di `config.json` adalah lingkungan uji.

## Sekali di awal

```powershell
cd otomasi-origination
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Butuh Google Chrome. Chromedriver diunduh otomatis oleh Selenium.

`config.json` **tidak ada di repo** (berisi base_url, username akun, dan nama staf). Minta
berkasnya ke pemilik repo, atau salin `config.example.json` menjadi `config.json` lalu isi.

## Menjalankan

```powershell
.venv\Scripts\python -m generate.jalankan                             # skenario Konven, browser terlihat
.venv\Scripts\python -m generate.jalankan --skenario syariah
.venv\Scripts\python -m generate.jalankan --skenario konven-syariah   # dua fasilitas dalam satu pipeline
.venv\Scripts\python -m generate.jalankan --headless                  # tanpa jendela
.venv\Scripts\python -m generate.jalankan --sampai 4                  # berhenti setelah fase 4 (Go To Origination)
.venv\Scripts\python -m generate.jalankan --lanjut                    # teruskan run yang gagal di tengah
```

Opsi lain: `--nama "<Nama Customer>"` (bawaan: acak) dan `--jejak <berkas>` (berkas jejak di `runs/`).

Bila gagal, screenshot dan HTML halaman disimpan di `runs/artefak/`. Dalam mode berjendela, browser
dibiarkan terbuka sampai Anda menekan Enter. Setelah penyebabnya beres, `--lanjut` meneruskan
dari fase yang gagal, memakai customer/pipeline yang sama (tersimpan di berkas jejak skenario itu).

## Skenario Konven vs Syariah

| `--skenario` | Fasilitas yang ditambahkan di fase 1 | Jejak run |
| --- | --- | --- |
| `konven` (bawaan) | Konven | `runs/jejak.json` |
| `syariah` | Syariah | `runs/jejak_syariah.json` |
| `konven-syariah` | Konven, lalu Syariah (Add New dua kali) | `runs/jejak_konven_syariah.json` |

Bedanya hanya di form **Add New Fasilitas Pembiayaan** (fase 1); fase lain sama persis, karena
alur Origination tidak bercabang menurut segmen. Akun yang dipakai pun sama: Segmen Pembiayaan
di form itu bisa diganti bebas, walau terisi bawaan dari divisi user.

| | Konven | Syariah |
| --- | --- | --- |
| Segmen Pembiayaan | dibiarkan (bawaan divisi) | diganti ke Syariah |
| Produk | `produk` (Dana Talangan) | **Skema pembiayaan**: `syariah.skema` |
| Nominal | Nominal Pengajuan acak | sub-form skema, lihat di bawah |
| Lainnya | – | Tujuan Pembiayaan: `syariah.tujuan_pembiayaan` |

Sub-form syariah berbeda per skema (Musyarakah: Syirkah SMI + Syirkah Nasabah; Murabahah: Objek +
Harga Beli; Qardh: Jumlah pinjaman; dst.) dan labelnya bisa diganti dari DB. Karena itu diisi
generik: setiap field bertanda `*` yang masih kosong diisi nominal acak bila punya pilihan mata
uang, selain itu `syariah.teks_objek`. Bila skema yang dipilih belum dimapping di lingkungan itu,
run berhenti dengan pesan yang jelas.

Pada `konven-syariah`, Konven diisi lebih dulu karena form fasilitas baru terisi segmen bawaan
divisi user. Go To Origination tetap menghasilkan **satu** origination (`FAS-xxxxx`) per pipeline,
jadi fase 2–12 tidak berubah.

Skenario Syariah dan Konven + Syariah **belum pernah dijalankan** terhadap server; skenario Konven sudah.

## Banyak Origination sekaligus

`generate.batch` menjalankan beberapa skenario berturut-turut (bawaan 2 Konven, 2 Syariah,
6 Konven + Syariah; ubah di `KOMPOSISI`). Tiap run mendapat nama perusahaan dasar yang berbeda
ditambah kode unik, dan jejaknya sendiri (`runs/jejak_batch_NN.json`). Rencananya ada di
`runs/jejak_batch.json`.

```powershell
.venv\Scripts\python -m generate.batch --rencana   # lihat rencana (nama per run) tanpa menjalankan
.venv\Scripts\python -m generate.batch             # jalankan; ulangi perintah ini untuk meneruskan setelah gagal
.venv\Scripts\python -m generate.batch --baru      # buang rencana lama, buat nama-nama baru
```

Batch berhenti pada run pertama yang gagal. Menjalankan ulang melewati run yang sudah selesai dan
meneruskan run yang gagal dengan `--lanjut`.

## Mengubah data isian

Semua nilai ada di `config.json` → `data`. Nilai `*_opsi` dan `tipe_proses` adalah regex, karena
label opsi berasal dari tabel parameter DB dan bisa berbeda antar lingkungan (contoh:
Tipe Proses di sebagian lingkungan masih berlabel "Fast Track", bukan "Origination").

Other Document diatur lewat `other_document_*`:

| Kunci | Arti |
| --- | --- |
| `other_document_jumlah` | Berapa dokumen yang ditambahkan (0 = lewati) |
| `other_document_kategori` | `Document Pembiayaan` atau `Supporting Document` |
| `other_document_group`, `other_document_jenis` | Regex label opsi; kosong = opsi pertama |
| `other_document_keterangan` | Isi Keterangan; kosong = dibiarkan kosong |

`config.json` berisi username akun. Di dev, login cukup username, jadi perlakukan berkas ini
seperti kredensial dan jangan dibagikan.

## Testing (pytest)

```powershell
.venv\Scripts\python -m pytest                       # semua test, browser terlihat
.venv\Scripts\python -m pytest --headless
.venv\Scripts\python -m pytest tests/test_login.py -k staff_bisnis
```

Memakai `config.json` yang sama (base_url, akun). Test yang ada sekarang (`test_login.py`,
`test_dashboard.py`) hanya membaca dan **tidak membuat data**. Bila test gagal, screenshot + HTML
halaman tempat gagal disimpan di `runs/artefak/tests/` dan path-nya tampil di laporan.

Fixture di `tests/conftest.py`:

| Fixture | Isi |
| --- | --- |
| `konfig` | isi `config.json` |
| `los` | satu browser untuk seluruh sesi; buat Page Object lewat `los.halaman(...)` |
| `masuk_sebagai` | `los = masuk_sebagai('tl_bisnis')` — login sebagai peran, logout otomatis setelah test |

Aturan menulis test:
- **Assert hanya di test, tidak di Page Object.** Page Object melakukan aksi dan mengembalikan nilai,
  supaya tetap bisa dipakai generate.
- Langkah yang belum ada di Page Object ditambahkan ke Page Object halaman itu, bukan ditulis
  langsung di test.
- Test yang butuh data di status tertentu (mis. origination yang sudah di-Submit Staff) bisa
  memakai data dari generate: `python -m generate.jalankan --sampai 5`, lalu ambil ID-nya dari
  berkas jejak di `runs/`. Test yang membuat atau mengubah data sebaiknya ditandai jelas di namanya
  atau docstring-nya.

## Struktur kode

```text
core/                  fondasi bersama
  driver.py            Los: helper Selenium (menunggu, klik, popup, select MUI) + factory halaman()/modal()
  lokator.py           Lokator: deklarasi elemen di class halaman (page factory)
  config.py, util.py, data_uji.py
pages/                 Page Object, dipakai generate/ dan tests/
  login.py             LoginPage
  dashboard.py         DashboardPage (To Do List → Go to task)
  pipeline.py          PipelineListPage, CreatePipelinePage, PipelineDetailPage, NotificationModal
  fasilitas.py         FormFasilitasModal (isi_konven, isi_syariah)
  origination.py       OriginationListPage, PembahasanPage, OtherDocumentModal
generate/              automation generate data
  jalankan.py          CLI satu run (pilih skenario)
  batch.py             CLI banyak run berturut-turut
  skenario.py          SKENARIO: Konven / Syariah / Konven + Syariah
  alur.py              12 fase (rangkaian Page Object) + runner
  jejak.py             berkas jejak run (untuk --lanjut)
tests/                 automation testing (pytest)
  conftest.py          fixture: konfig, los, masuk_sebagai + bukti saat gagal
  test_*.py
assets/dokumen.pdf     PDF yang diunggah ke semua dokumen
runs/                  jejak run + artefak/ (bukti kegagalan) — tidak di-commit
pytest.ini, requirements.txt, config.example.json
```

**Page Object & page factory.** Elemen dideklarasikan sebagai atribut class, mirip `@FindBy`:

```python
class PipelineDetailPage(Halaman):
    tombol_submit = Lokator("(//button[normalize-space()='Submit'])[last()]")

    def submit(self, komentar):
        self.tombol_submit.klik(60)
        ...

detail = los.halaman(PipelineDetailPage)     # halaman biasa
form = los.modal(FormFasilitasModal, 30)     # popup: ditunggu lewat teksnya (POLA), jadi akar lokator './/'
```

Bedanya dengan PageFactory Selenium Java: elemen **dicari ulang setiap kali dipakai**, tidak disimpan
saat halaman dibuat. Popup MUI dipasang di portal dan daftar opsi dirender ulang, jadi elemen yang
disimpan cepat basi. Lokator berparameter memakai `{}`: `self.baris_berisi(customer).satu(20)`.

Menambah langkah baru: tambahkan lokator + method di Page Object halaman itu, lalu panggil dari
fase di `generate/alur.py` atau dari test. Menambah skenario: tambahkan entri di `SKENARIO` (dan pengisi di
`PENGISI_FASILITAS` bila jenis fasilitasnya baru).

## Catatan teknis

- **Buffering** ditunggu berbasis kondisi, bukan jeda tetap: sampai spinner yang berputar hilang
  dan tidak ada teks "Auto Saving…", "Sedang Submit Dokumen", atau "Mengunggah". Loader global
  aplikasi berbentuk dialog, jadi popup selalu dicari lewat teksnya.
- **Go to task** memakai Filter "Nama Customer" di To Do List/Approval List, karena daftarnya
  ratusan baris dan tidak terurut terbaru-dulu. Bila tugas belum muncul dalam 2,5 menit, skrip
  membuka halaman tujuan langsung lewat URL.
- **Customer baru**: halaman Create Pipeline hanya menerima Institution Type, Nama Customer, dan
  GAM. Jenis Customer, Tipe Proses, PIC2, dan Analis diisi di halaman detail setelah Save pertama.
- **Completed** di-set backend setelah approval Kadiv terakhir, bila semua dokumen wajib Bisnis,
  DEPI, dan DH sudah *Sent to LPS*.

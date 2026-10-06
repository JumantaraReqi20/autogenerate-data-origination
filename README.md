# Otomasi Origination sampai Completed

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

## Google Colab / Jupyter

`origination_syariah_colab.ipynb` menjalankan skenario Syariah di Colab (Chrome headless).
Buka di Colab, Runtime → Run all, lalu unggah `config.json` saat diminta. Bila server LOS hanya
bisa diakses dari jaringan internal/VPN, pakai *Connect to a local runtime*.

## Menjalankan

```powershell
.venv\Scripts\python buat_origination.py              # run baru, browser terlihat
.venv\Scripts\python buat_origination.py --headless   # tanpa jendela
.venv\Scripts\python buat_origination.py --sampai 3   # berhenti setelah fase 3 (mis. hanya sampai Go To Origination)
.venv\Scripts\python buat_origination.py --lanjut     # teruskan run yang gagal di tengah
```

## Skenario Konven vs Syariah

Satu skenario = satu file. Opsi `--lanjut`, `--headless`, `--sampai` berlaku di keduanya.

| File | Skenario | Jejak run |
| --- | --- | --- |
| `buat_origination.py` | Konven | `jejak.json` |
| `buat_origination_syariah.py` | Syariah | `jejak_syariah.json` |
| `buat_origination_konven_syariah.py` | Dua fasilitas dalam satu pipeline: Konven + Syariah | `jejak_konven_syariah.json` |

```powershell
.venv\Scripts\python buat_origination_syariah.py
.venv\Scripts\python buat_origination_konven_syariah.py
```

Bedanya hanya di form **Add New Fasilitas Pembiayaan** (fase 1); fase lain sama persis, karena
alur Origination tidak bercabang menurut segmen. Karena itu file syariah tidak menyalin alurnya:
ia memanggil `main()` dari `buat_origination.py` dengan pengisi fasilitasnya sendiri, sehingga
perbaikan alur otomatis berlaku untuk kedua skenario. Akun yang dipakai pun sama: Segmen
Pembiayaan di form itu bisa diganti bebas, walau terisi bawaan dari divisi user.

| | Konven (bawaan) | Syariah |
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

Skenario **Konven + Syariah** menambah dua fasilitas berturut-turut di fase 1 (Add New dua kali),
memakai pengisi yang sama dengan kedua skenario di atas, jadi tidak ada kunci `config.json` baru.
Konven diisi lebih dulu karena form fasilitas baru terisi segmen bawaan divisi user. Go To
Origination tetap menghasilkan **satu** origination (`FAS-xxxxx`) per pipeline, jadi fase 2–12
tidak berubah. `main(isi_fasilitas=...)` menerima satu fungsi atau list fungsi.

Skenario syariah dan Konven + Syariah **belum pernah dijalankan** terhadap server; skenario konven sudah.

## Banyak Origination sekaligus

`buat_batch.py` menjalankan beberapa skenario berturut-turut (bawaan 2 Konven, 2 Syariah,
6 Konven + Syariah; ubah di `KOMPOSISI`). Tiap run mendapat nama perusahaan dasar yang berbeda
ditambah kode unik, dan jejaknya sendiri (`jejak_batch_NN.json`). Rencananya ada di `jejak_batch.json`.

```powershell
.venv\Scripts\python buat_batch.py --rencana   # lihat rencana (nama per run) tanpa menjalankan
.venv\Scripts\python buat_batch.py             # jalankan; ulangi perintah ini untuk meneruskan setelah gagal
.venv\Scripts\python buat_batch.py --baru      # buang rencana lama, buat nama-nama baru
```

Batch berhenti pada run pertama yang gagal. Menjalankan ulang melewati run yang sudah selesai dan
meneruskan run yang gagal dengan `--lanjut`. Skrip tunggal juga menerima `--nama` dan `--jejak`.

Bila gagal, screenshot dan HTML halaman disimpan di `artefak/`. Dalam mode berjendela, browser
dibiarkan terbuka sampai Anda menekan Enter. Setelah penyebabnya beres, `--lanjut` meneruskan
dari fase yang gagal, memakai customer/pipeline yang sama (tersimpan di `jejak.json`).

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

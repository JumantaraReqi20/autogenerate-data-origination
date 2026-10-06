"""
Otomasi pembuatan data: satu Origination dari nol sampai berstatus "Completed" —
skenario pembiayaan KONVEN (fasilitas: Produk + Nominal Pengajuan).

    .venv\\Scripts\\python buat_origination.py              # run baru, browser terlihat
    .venv\\Scripts\\python buat_origination.py --lanjut     # teruskan run yang gagal di tengah
    .venv\\Scripts\\python buat_origination.py --headless   # tanpa jendela browser

Skenario Syariah (buat_origination_syariah.py) dan Konven + Syariah dalam satu pipeline
(buat_origination_konven_syariah.py) memakai alur di file ini dan hanya mengganti pengisi form
fasilitas (main(isi_fasilitas=...)).

MEMBUAT DATA SUNGGUHAN di base_url (config.json): customer baru, pipeline, origination
(FAS-xxxxx), dan dokumen.

Satu fase = satu akun. Fase yang selesai dicatat di jejak.json; --lanjut melewatinya,
jadi kegagalan di fase Kadiv DH tidak memaksa membuat customer baru dari awal.
"""
import argparse
import json
import random
import re
import sys
import time

from selenium.webdriver.common.by import By

from los import FOLDER, GagalLangkah, Los, hari_ini, log, xp_literal

KONFIG = json.loads((FOLDER / 'config.json').read_text(encoding='utf-8'))
AKUN = KONFIG['akun']
DATA = KONFIG['data']
BERKAS_JEJAK = FOLDER / 'jejak.json'
BERKAS_PDF = str(FOLDER / 'dokumen.pdf')

RUTE_PIPELINE = '/loan-processing/submission-proposal/pipeline'
RUTE_ORIGINATION = '/origination-submission/origination'

PERUSAHAAN = [
    'Garuda Nusantara', 'Telkom Sinergi', 'Pertamina Energi', 'Astra Mandiri', 'Indofood Prima',
    'Unilever Nusa', 'Semen Gresik Raya', 'Wijaya Karya Infra', 'Jasa Marga Tol', 'Bukit Asam Daya',
    'Angkasa Pura Logistik', 'Pelindo Samudra', 'Waskita Beton', 'Adhi Karya Persada', 'Hutama Karya Jaya',
]


def detail_pipeline(pid: str) -> str:
    return f'{RUTE_PIPELINE}/{pid}/detail'


def pembahasan(fas: str) -> str:
    return f'{RUTE_ORIGINATION}/{fas}/origination-creation'


def eksak(teks: str) -> str:
    """Regex cocok-persis (case-insensitive) untuk label opsi."""
    return rf'^\s*{re.escape(teks)}\s*$'


# ============================================================================ jejak

def baca_jejak() -> dict:
    return json.loads(BERKAS_JEJAK.read_text(encoding='utf-8')) if BERKAS_JEJAK.exists() else {}


def simpan_jejak(**isi):
    j = baca_jejak()
    j.update(isi)
    BERKAS_JEJAK.write_text(json.dumps(j, indent=1, ensure_ascii=False), encoding='utf-8')


# ============================================================================ data uji

def nama_customer_baru() -> str:
    """
    Huruf pertama kapital, TIDAK diawali PT/TBK/dll. dan tidak diakhiri Persero/TBK
    (CreateNewPipelineCustom.constant.ts). Akhiran unik supaya barisnya bisa dicari di
    To Do List / Origination List tanpa tertukar dengan data lain.
    """
    kode = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=4))
    return f'{random.choice(PERUSAHAAN)} Oto {kode}'


# Diisi dari --nama; kosong = nama_customer_baru().
NAMA_CUSTOMER = None


def nominal_acak() -> str:
    """1–99 milyar dengan sisa jutaan supaya tidak selalu bulat."""
    return str(random.randint(1, 99) * 1_000_000_000 + random.randint(0, 899) * 1_000_000)


def nomor_dokumen_acak() -> str:
    return str(random.randint(100_000, 999_999))


# ============================================================================ fase 1–11

def fase_buat_pipeline(los: Los):
    customer = NAMA_CUSTOMER or nama_customer_baru()
    log(f'  customer: {customer}')

    # 2. Loan Processing → Proposal Pengajuan → Pipeline
    los.buka(RUTE_PIPELINE)

    # 3. Add New Pipeline
    los.klik_xpath("//button[contains(normalize-space(), 'Add New Pipeline')]")

    # 4. Pencarian "aku"
    cari = los.satu("//div[contains(@class,'MuiDialog-root')]//input[@placeholder='Pencarian...']", 30)
    los.ketik(cari, DATA['kata_pencarian'])

    # 5. Tunggu 3 detik → Create New Customer & Pipeline → Ya
    time.sleep(3)
    los.buffering()
    los.klik_xpath("//button[normalize-space()='Create New Customer & Pipeline']", 60)
    # Popup "Customer sudah ada dalam pengajuan" hanya muncul bila pencarian ada hasilnya, dan
    # bisa terlambat saat server lambat — jadi tunggu mana yang lebih dulu: pindah halaman atau popup.
    def lanjut_ke_create():
        if 'create-new-debtor' in los.d.current_url:
            return True
        p = los.popup(r'Customer sudah ada dalam pengajuan')
        ya = los.cari(los.tombol('Ya', p), p) if p else []
        if ya:
            los.klik(ya[0])
            time.sleep(1.5)
        return False

    los.tunggu(lanjut_ke_create, 90, 'halaman Create Pipeline tidak terbuka', jeda=1)
    los.buffering()

    # 6. Institution Type, Nama Customer, General Account Manager
    los.pilih_select('Institution Type', eksak(DATA['institution_type']))
    los.ketik(los.satu("//input[@placeholder='Nama Customer']"), customer)
    los.pilih_autocomplete(los.satu("//input[@placeholder='Input General Account Manager']"),
                           DATA['gam_cari'], DATA['gam_opsi'])

    # 7. Save → (peringatan DK / rekomendasi nama) → Success → Close → halaman detail pipeline
    los.klik_xpath("//*[@id='button-save']", 30, pesan='tombol Save belum aktif — ada field wajib yang kosong?')
    los.buffering()
    los.konfirmasi_bila_ada(r'Terdapat kemiripan', 'Save', 3)
    if los.konfirmasi_bila_ada(r'Rekomendasi Nama Customer', 'Create New Customer & Pipeline', 3):
        los.konfirmasi_bila_ada(r'serupa pada rekomendasi', 'Ya', 8)
    los.sukses_lalu_tutup()
    los.tunggu(lambda: re.search(r'/pipeline/[^/]+/detail', los.d.current_url), 60, 'tidak pindah ke detail pipeline')
    pipeline_id = re.search(r'/pipeline/([^/]+)/detail', los.d.current_url).group(1)
    simpan_jejak(customer=customer, pipeline_id=pipeline_id)
    log(f'  pipeline: {pipeline_id}')
    los.buffering()

    # 8. Data pipeline (untuk customer baru, field ini baru bisa diisi di halaman detail)
    los.pilih_select('Jenis Customer', eksak(DATA['jenis_customer']))
    los.pilih_radio('isGroup', 'false')          # Customer Memiliki Group: Tidak
    los.pilih_radio('isRelatedToSmi', 'false')   # Terkait Dengan SMI: Tidak
    # Label "Fast Track" diganti "Origination" di source terbaru; lingkungan lama masih "Fast Track".
    los.pilih_select('Tipe Proses', DATA['tipe_proses'])
    los.pilih_select('Tipe Pembiayaan', eksak(DATA['tipe_pembiayaan']))
    los.pilih_autocomplete(los.satu("//input[@placeholder='Pilih PIC2']"), DATA['pic2_cari'], DATA['pic2_opsi'])
    los.pilih_autocomplete(los.satu("//input[@placeholder='Nama Analis']"), DATA['analis_cari'], DATA['analis_opsi'])

    # 9. Save → Success → Close
    los.klik_xpath("(//button[normalize-space()='Save'])[last()]", 60)
    los.konfirmasi_bila_ada(r'DATA MANDATORY', 'Ya', 3)
    los.sukses_lalu_tutup()

    # 10. Satu fasilitas per pengisi di ISI_FASILITAS
    for isi in ISI_FASILITAS:
        tambah_fasilitas(los, isi)


def tambah_fasilitas(los: Los, isi):
    """Fasilitas Pembiayaan → Add New → Create New → Confirm → isi → Save."""
    los.klik_xpath("//button[normalize-space()='Add New']")
    pemilih = los.tunggu_popup('Tambah Fasilitas Pembiayaan')
    los.d.execute_script('arguments[0].click()',
                         pemilih.find_element(By.CSS_SELECTOR, 'input[type="radio"][value="new"]'))
    los.klik_xpath(los.tombol('Confirm', pemilih), 15, induk=pemilih)
    form = los.tunggu_popup('Add New Fasilitas Pembiayaan', 30)
    los.buffering()
    isi(los, form)
    los.klik_xpath(los.tombol('Save', form), 15, induk=form)
    los.sukses_lalu_tutup()


def rupiah(angka: str) -> str:
    return 'Rp' + f'{int(angka):,}'.replace(',', '.')


def isi_fasilitas_konven(los: Los, form):
    """Segmen tetap bawaan divisi (Konven) → Produk → Nominal Pengajuan."""
    los.pilih_select('Choose Produk', DATA['produk'], induk=form)
    nominal = nominal_acak()
    los.ketik(los.satu(".//input[@placeholder='Input Nominal Pengajuan']", 15, form), nominal)
    log(f'  fasilitas konven: {DATA["produk"]}, nominal {rupiah(nominal)}')


# Pengisi form "Add New Fasilitas Pembiayaan", satu per fasilitas. Diganti skenario lain lewat main().
ISI_FASILITAS = [isi_fasilitas_konven]


def fase_submit_pipeline(los: Los):
    """
    11. Submit → Comment "Bismillaah" → Save → Success → Close.

    Fase tersendiri supaya --lanjut tidak membuat customer baru bila yang gagal hanya Submit.
    Server dev kadang menjawab "timeout of 60000ms exceeded" padahal Submit-nya tetap diproses;
    karena itu sebelum tiap percobaan dicek dulu apakah tombol Submit masih ada.
    """
    pid = baca_jejak()['pipeline_id']
    for percobaan in range(1, 4):
        los.buka(detail_pipeline(pid))
        los.satu("//*[normalize-space(text())='Fasilitas Pembiayaan']", 120, pesan='detail pipeline tidak termuat')
        los.buffering()
        if not los.cari("//button[normalize-space()='Submit']"):
            log('  tombol Submit sudah tidak ada — pipeline sudah ter-Submit')
            return
        try:
            los.klik_xpath("(//button[normalize-space()='Submit'])[last()]", 60,
                           pesan='Submit belum aktif — ada field mandatory pipeline yang kosong?')
            los.konfirmasi_bila_ada(r'yakin ingin Submit', 'Ya', 3)
            isi_komentar_lalu_simpan(los, DATA['komentar_submit'])
            los.sukses_lalu_tutup()
            return
        except GagalLangkah as e:
            if 'timeout' not in str(e).lower() or percobaan == 3:
                raise
            log(f'  server timeout saat Submit (percobaan {percobaan}), cek ulang 20 detik lagi')
            time.sleep(20)


def isi_komentar_lalu_simpan(los: Los, komentar: str):
    p = los.tunggu_popup(r'Comment', 30)
    los.ketik(los.satu(".//textarea[@placeholder='Comment']", 15, p), komentar)
    los.klik_xpath(los.tombol('Save', p), 15, induk=p)


# ============================================================================ fase 13–17

def fase_tl_approve_pipeline(los: Los):
    j = baca_jejak()
    los.buka_tugas(j['customer'], detail_pipeline(j['pipeline_id']))
    los.klik_xpath("(//button[normalize-space()='Approve'])[last()]", 60)
    los.konfirmasi_bila_ada(r'yakin ingin Submit', 'Ya', 3)
    isi_komentar_lalu_simpan(los, DATA['komentar'])
    los.sukses_lalu_tutup()


def fase_go_to_origination(los: Los):
    j = baca_jejak()
    customer = j['customer']
    los.buka_tugas(customer, detail_pipeline(j['pipeline_id']))
    if '/pipeline/' not in los.d.current_url:
        los.buka(detail_pipeline(j['pipeline_id']))

    los.klik_xpath("//button[contains(normalize-space(), 'Go To Origination')]", 60)
    notif = los.tunggu_popup('Notification to DEPI', 30)
    los.buffering()

    # Dua field "Nama Staff" (multi-select): urutan 1 = DEPI, urutan 2 = DH.
    for urutan, cari, opsi in ((0, DATA['staff_depi_cari'], DATA['staff_depi_opsi']),
                               (1, DATA['staff_dh_cari'], DATA['staff_dh_opsi'])):
        kotak = los.cari(".//div[contains(@class,'MuiAutocomplete-root')]//input", notif)[urutan]
        los.pilih_autocomplete(kotak, cari, opsi)
        los.klik(los.satu(".//*[normalize-space(text())='Selected Pipeline']", 10, notif))

    los.ketik(los.satu(".//textarea[@placeholder='Comment']", 15, notif), DATA['komentar'])
    los.klik_xpath(los.tombol('Save', notif), 15, induk=notif,
                   pesan='Save belum aktif — staff DEPI/DH/komentar belum lengkap?')
    los.sukses_lalu_tutup()
    los.tunggu(lambda: RUTE_ORIGINATION in los.d.current_url, 60, 'tidak pindah ke Origination List')

    # Bucket baru muncul 14–67 detik setelah Go To Origination (diproses asinkron).
    log('  menunggu origination muncul di Origination List...')
    baris = tunggu_baris_origination(los, customer, 300)
    fas_id = baris.find_element(By.XPATH, './td[6]').text.strip()
    simpan_jejak(fas_id=fas_id)
    log(f'  origination: {fas_id}')


def tunggu_baris_origination(los: Los, customer: str, batas: float):
    xp = f"//tbody/tr[contains(normalize-space(), {xp_literal(customer)})]"
    akhir = time.time() + batas
    while True:
        los.buka(RUTE_ORIGINATION)
        try:
            return los.satu(xp, 20)
        except GagalLangkah:
            if time.time() > akhir:
                raise GagalLangkah(f'{customer} tidak muncul di Origination List setelah {int(batas)} detik')
            time.sleep(10)


# ============================================================================ Pembahasan Origination

JUDUL_HALAMAN = "//*[normalize-space(text())='Pembahasan Origination']"


def buka_stepper_pembahasan(los: Los):
    if 'origination-creation' not in los.d.current_url:
        los.klik_xpath(f'({JUDUL_HALAMAN})[1]', 60)
        los.tunggu(lambda: 'origination-creation' in los.d.current_url, 60, 'stepper Pembahasan Origination tidak terbuka')
    los.satu("//button[contains(normalize-space(), 'Filter Dokumen')]", 120,
             pesan='halaman Pembahasan Origination tidak selesai dimuat')
    los.buffering()


def isi_tanggal_entry(los: Los):
    kotak = los.cari("//input[@placeholder='Pilih tanggal']")
    if kotak and kotak[0].is_enabled() and not kotak[0].get_attribute('value'):
        log('  isi Tanggal Entry Pengajuan')
        los.ketik_tanggal(kotak[0], hari_ini(), f'({JUDUL_HALAMAN})[last()]')


def isi_dokumen_wajib(los: Los):
    """
    Isi dokumen bertanda * yang terlihat oleh peran ini: Nomor (acak 6 digit), Tanggal
    (hari ini), dan satu PDF. Bila tidak ada satu pun yang bertanda wajib, dokumen pertama
    yang diisi — Submit baru aktif kalau ada minimal satu berkas Draft.
    """
    xp_blok = ("//input[@placeholder='Input Nomor Dokumen']"
               "/ancestor::div[.//button[normalize-space()='Tambah file'] or .//input[@type='file']][1]")

    def judul(blok):
        return re.sub(r'\s+', ' ', blok.text.split('Nomor Dokumen')[0]).strip()

    semua = los.cari(xp_blok)
    if not semua:
        raise GagalLangkah('Tidak ada dokumen yang bisa diisi oleh peran ini di Pembahasan Origination')
    target = [i for i, b in enumerate(semua) if '*' in judul(b)] or [0]

    for i in target:
        blok = los.cari(xp_blok)[i]
        nama = judul(blok)
        log(f'  isi dokumen: {nama}')
        los.ketik(blok.find_element(By.XPATH, ".//input[@placeholder='Input Nomor Dokumen']"), nomor_dokumen_acak())
        los.ketik_tanggal(blok.find_element(By.XPATH, ".//input[@placeholder='DD/MM/YYYY']"), hari_ini(),
                          f'({JUDUL_HALAMAN})[last()]')

        tambah = los.cari(".//button[normalize-space()='Tambah file']", blok)
        if tambah:
            los.klik(tambah[0])
            time.sleep(0.8)
        unggah = los.tunggu(lambda: blok.find_elements(By.XPATH, ".//input[@type='file']"), 15,
                            f'kotak unggah "{nama}" tidak muncul')[0]
        unggah.send_keys(BERKAS_PDF)

        # Unggah tidak memunculkan popup: tunggu kartu berkas berstatus Draft.
        los.tunggu(lambda: los.cari(".//*[normalize-space(text())='Draft']", blok), 120,
                   f'unggah ke "{nama}" tidak menjadi Draft')
        los.buffering()


def tambah_other_document(los: Los):
    """
    Section Other Document → Add New → Create New → Confirm → modal "Add Dokumen":
    Kategori → Group → Jenis (berantai; Group/Jenis dimuat dari API), unggah PDF,
    Nomor (acak 6 digit), Tanggal (hari ini), Keterangan → Save.
    """
    xp_section = ("//*[normalize-space(text())='Other Document']"
                  "/ancestor::div[.//button[normalize-space()='Add New']][1]")
    los.klik_xpath(f"{xp_section}//button[normalize-space()='Add New']", 30,
                   pesan='tombol Add New di Other Document tidak ada')

    pemilih = los.tunggu_popup(r'Create New', 15)
    los.d.execute_script('arguments[0].click()',
                         pemilih.find_element(By.CSS_SELECTOR, 'input[type="radio"][value="new"]'))
    los.klik_xpath(los.tombol('Confirm', pemilih), 15, induk=pemilih)

    form = los.tunggu_popup(r'Kategori Dokumen', 30)
    los.buffering()
    pilihan = [
        los.pilih_dari_daftar(los.satu(f".//input[@placeholder='{nama}']", 15, form), DATA[kunci])
        for nama, kunci in (('Kategori Dokumen', 'other_document_kategori'),
                            ('Group Dokumen', 'other_document_group'),
                            ('Jenis Dokumen', 'other_document_jenis'))
    ]
    log(f'  other document: {" / ".join(pilihan)}')

    form.find_element(By.XPATH, ".//input[@type='file']").send_keys(BERKAS_PDF)
    los.buffering()
    # Sebagian versi memunculkan popup "berhasil" sendiri setelah berkas dipilih.
    los.konfirmasi_bila_ada(r'berhasil', 'Close', 3)

    nomor = nomor_dokumen_acak()
    los.ketik(los.satu(".//input[@placeholder='Input Nomor Dokumen']", 15, form), nomor)
    los.ketik_tanggal(los.satu(".//input[@placeholder='Input Tanggal Dokumen']", 15, form), hari_ini(),
                      "//*[normalize-space(text())='Upload By']")
    if DATA.get('other_document_keterangan'):
        los.ketik(los.satu(".//textarea[@placeholder='Input Keterangan']", 15, form), DATA['other_document_keterangan'])

    los.klik_xpath(los.tombol('Save', form), 30, induk=form,
                   pesan='Save Add Dokumen belum aktif — ada field wajib yang kosong?')
    los.sukses_lalu_tutup()
    los.satu(f"{xp_section}//tbody/tr[contains(normalize-space(), '{nomor}')]", 60,
             pesan=f'dokumen bernomor {nomor} tidak muncul di tabel Other Document')


def kirim_pembahasan(los: Los, tombol_bawah: str, tombol_konfirmasi: str):
    """
    Tombol bawah (Submit/Approve) → dialog konfirmasi → tombol konfirmasi
    (Submit untuk Staff, Send untuk TL, "Approve & Kirim ke LPS" untuk Kadiv) → "Aksi berhasil".
    """
    los.klik_xpath(f"(//button[normalize-space()={xp_literal(tombol_bawah)}])[last()]", 60,
                   pesan=f'tombol {tombol_bawah} tidak aktif — belum ada dokumen Draft/menunggu?')
    dialog = los.tunggu(
        lambda: next((p for p in los.d.find_elements(By.CSS_SELECTOR, '.MuiDialog-root')
                      if p.is_displayed() and los.cari(los.tombol(tombol_konfirmasi, p), p)), None),
        60, f'dialog dengan tombol "{tombol_konfirmasi}" tidak muncul')
    los.klik_xpath(los.tombol(tombol_konfirmasi, dialog), 15, induk=dialog)
    log(f'  {los.sukses_lalu_tutup(r"Aksi berhasil|berhasil", 300)}')


def fase_staff_pembahasan(los: Los):
    customer = baca_jejak()['customer']
    # 18. Origination List → Detail (kolom Action) → stepper Pembahasan Origination
    baris = tunggu_baris_origination(los, customer, 120)
    los.klik(baris.find_element(By.XPATH, './td[2]//button'))
    los.tunggu(lambda: '/debtor-information' in los.d.current_url or 'origination-creation' in los.d.current_url,
               60, 'detail origination tidak terbuka')
    los.buffering()
    buka_stepper_pembahasan(los)
    isi_tanggal_entry(los)
    isi_dokumen_wajib(los)
    for _ in range(int(DATA.get('other_document_jumlah', 0))):
        tambah_other_document(los)
    kirim_pembahasan(los, 'Submit', 'Submit')


def fase_pembahasan(isi_dokumen: bool, tombol_bawah: str, tombol_konfirmasi: str):
    def kerja(los: Los):
        j = baca_jejak()
        los.buka_tugas(j['customer'], pembahasan(j['fas_id']))
        buka_stepper_pembahasan(los)
        if isi_dokumen:
            isi_dokumen_wajib(los)
        kirim_pembahasan(los, tombol_bawah, tombol_konfirmasi)
    return kerja


def fase_cek_completed(los: Los):
    j = baca_jejak()
    xp = f"//tbody/tr[contains(normalize-space(), {xp_literal(j['fas_id'])})]/td[3]"
    akhir = time.time() + 180
    while True:
        los.buka(RUTE_ORIGINATION)
        status = (los.cari(xp) or [None])[0]
        teks = status.text.strip() if status else '(baris tidak ditemukan)'
        if 'completed' in teks.lower():
            log(f'SELESAI: {j["customer"]} / {j["pipeline_id"]} / {j["fas_id"]} berstatus {teks}')
            return
        if time.time() > akhir:
            raise GagalLangkah(f'{j["fas_id"]} belum Completed, status sekarang: {teks}')
        time.sleep(15)


# ============================================================================ urutan

FASE = [
    ('1-10  Staff Bisnis: customer, pipeline, fasilitas', 'staff_bisnis', fase_buat_pipeline),
    ('11    Staff Bisnis: Submit pipeline', 'staff_bisnis', fase_submit_pipeline),
    ('13-14 TL Bisnis: approve pipeline', 'tl_bisnis', fase_tl_approve_pipeline),
    ('16-17 Staff Bisnis: Go To Origination', 'staff_bisnis', fase_go_to_origination),
    ('18    Staff Bisnis: isi Pembahasan Origination + Other Document, Submit', 'staff_bisnis', fase_staff_pembahasan),
    ('20    TL Bisnis: Submit, Send', 'tl_bisnis', fase_pembahasan(False, 'Submit', 'Send')),
    ('21    Kadiv Bisnis: Approve', 'kadiv_bisnis', fase_pembahasan(False, 'Approve', 'Approve & Kirim ke LPS')),
    ('23    TL DEPI: isi dokumen, Submit', 'tl_depi', fase_pembahasan(True, 'Submit', 'Send')),
    ('25    Kadiv DEPI: Approve', 'kadiv_depi', fase_pembahasan(False, 'Approve', 'Approve & Kirim ke LPS')),
    ('27    TL DH: isi dokumen, Submit', 'tl_dh', fase_pembahasan(True, 'Submit', 'Send')),
    ('29    Kadiv DH: Approve', 'kadiv_dh', fase_pembahasan(False, 'Approve', 'Approve & Kirim ke LPS')),
    ('30    Cek status Completed', 'staff_bisnis', fase_cek_completed),
]


def main(isi_fasilitas=isi_fasilitas_konven, skenario: str = 'Konven', berkas_jejak: str = 'jejak.json'):
    """
    Jalankan seluruh fase. Skenario lain cukup memberi `isi_fasilitas` sendiri dan berkas jejak
    terpisah, supaya --lanjut sebuah skenario tidak meneruskan run skenario lain.
    `isi_fasilitas` boleh satu fungsi atau list fungsi (satu fasilitas per fungsi, berurutan).
    """
    global ISI_FASILITAS, BERKAS_JEJAK, NAMA_CUSTOMER
    ISI_FASILITAS = list(isi_fasilitas) if isinstance(isi_fasilitas, (list, tuple)) else [isi_fasilitas]
    BERKAS_JEJAK = FOLDER / berkas_jejak

    ap = argparse.ArgumentParser(description=f'Buat satu Origination ({skenario}) sampai Completed.')
    ap.add_argument('--lanjut', action='store_true', help='teruskan run sebelumnya (lewati fase yang sudah selesai)')
    ap.add_argument('--headless', action='store_true', help='jalankan tanpa jendela browser')
    ap.add_argument('--sampai', type=int, default=len(FASE), help='berhenti setelah fase ke-N (1-based)')
    ap.add_argument('--nama', help='nama customer baru (bawaan: acak); dipakai buat_batch.py supaya unik')
    ap.add_argument('--jejak', help=f'berkas jejak run (bawaan: {berkas_jejak})')
    arg = ap.parse_args()
    NAMA_CUSTOMER = arg.nama
    if arg.jejak:
        BERKAS_JEJAK = FOLDER / arg.jejak

    if not arg.lanjut and BERKAS_JEJAK.exists():
        BERKAS_JEJAK.unlink()
    log(f'Skenario pembiayaan: {skenario} (jejak: {BERKAS_JEJAK.name})')

    los = Los(KONFIG['base_url'], headless=arg.headless)
    mulai = time.time()
    try:
        for no, (nama, peran, kerja) in enumerate(FASE[:arg.sampai], start=1):
            if nama in baca_jejak().get('fase_selesai', []):
                log(f'--- lewati (sudah selesai): {nama}')
                continue
            log(f'=== [{no}/{len(FASE)}] {nama} ===')
            los.login(AKUN[peran])
            kerja(los)
            los.logout()
            simpan_jejak(fase_selesai=baca_jejak().get('fase_selesai', []) + [nama])
        log(f'Total waktu: {int(time.time() - mulai) // 60} menit {int(time.time() - mulai) % 60} detik')
        log(f'Jejak: {json.dumps({k: v for k, v in baca_jejak().items() if k != "fase_selesai"}, ensure_ascii=False)}')
    except Exception as e:  # noqa: BLE001 — semua kegagalan dilaporkan dengan bukti yang sama
        bukti = los.simpan_bukti('gagal')
        log(f'GAGAL: {e}')
        log(f'Bukti: {bukti}')
        log('Perbaiki penyebabnya lalu jalankan ulang dengan --lanjut untuk meneruskan dari fase ini.')
        if not arg.headless and sys.stdin.isatty():
            input('Browser dibiarkan terbuka untuk diperiksa. Tekan Enter untuk menutup...')
        los.tutup()
        sys.exit(1)
    los.tutup()


if __name__ == '__main__':
    main()

"""Origination Submission: Origination List, stepper Pembahasan Origination, popup Add Dokumen (Other Document)."""
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from core.data_uji import nomor_dokumen_acak
from core.lokator import Lokator
from core.util import GagalLangkah, hari_ini, log, xp_literal
from .base import Halaman, Modal, PemilihCreateNewModal

RUTE_ORIGINATION = '/origination-submission/origination'


class OriginationListPage(Halaman):
    baris_berisi = Lokator("//tbody/tr[contains(normalize-space(), {})]", 'baris Origination List')
    status_berisi = Lokator("//tbody/tr[contains(normalize-space(), {})]/td[3]", 'kolom Status')

    def buka(self):
        self.los.buka(RUTE_ORIGINATION)

    def tunggu_baris(self, kata: str, batas: float) -> WebElement:
        """Baris yang memuat `kata` (nama customer). Bucket baru muncul asinkron, jadi daftar dimuat ulang."""
        akhir = time.time() + batas
        while True:
            self.buka()
            try:
                return self.baris_berisi(kata).satu(20)
            except GagalLangkah:
                if time.time() > akhir:
                    raise GagalLangkah(f'{kata} tidak muncul di Origination List setelah {int(batas)} detik')
                time.sleep(10)

    @staticmethod
    def fas_id(baris: WebElement) -> str:
        return baris.find_element(By.XPATH, './td[6]').text.strip()

    def buka_detail(self, customer: str):
        """Origination List → Detail (kolom Action) → halaman detail origination."""
        los = self.los
        baris = self.tunggu_baris(customer, 120)
        los.klik(baris.find_element(By.XPATH, './td[2]//button'))
        los.tunggu(lambda: los.url_berisi('/debtor-information', 'origination-creation'),
                   60, 'detail origination tidak terbuka')
        los.buffering()

    def tunggu_completed(self, fas_id: str, batas: float = 180) -> str:
        """Status di-set backend setelah approval Kadiv terakhir; dimuat ulang sampai Completed."""
        akhir = time.time() + batas
        while True:
            self.buka()
            status = (self.status_berisi(fas_id).semua() or [None])[0]
            isi = status.text.strip() if status else '(baris tidak ditemukan)'
            if 'completed' in isi.lower():
                return isi
            if time.time() > akhir:
                raise GagalLangkah(f'{fas_id} belum Completed, status sekarang: {isi}')
            time.sleep(15)


class PembahasanPage(Halaman):
    """Stepper "Pembahasan Origination" (origination-creation): dokumen wajib, Other Document, Submit/Approve."""

    _JUDUL = "//*[normalize-space(text())='Pembahasan Origination']"
    # Elemen netral untuk menutup kalender date picker.
    _NETRAL = f'({_JUDUL})[last()]'
    _BLOK_DOKUMEN = ("//input[@placeholder='Input Nomor Dokumen']"
                     "/ancestor::div[.//button[normalize-space()='Tambah file'] or .//input[@type='file']][1]")
    _SECTION_OTHER = ("//*[normalize-space(text())='Other Document']"
                      "/ancestor::div[.//button[normalize-space()='Add New']][1]")

    menu_stepper = Lokator(f'({_JUDUL})[1]', 'stepper Pembahasan Origination')
    tombol_filter_dokumen = Lokator("//button[contains(normalize-space(), 'Filter Dokumen')]")
    input_tanggal_entry = Lokator("//input[@placeholder='Pilih tanggal']", 'Tanggal Entry Pengajuan')
    blok_dokumen = Lokator(_BLOK_DOKUMEN, 'blok dokumen')
    tombol_add_new_other = Lokator(f"{_SECTION_OTHER}//button[normalize-space()='Add New']",
                                   'tombol Add New di Other Document')
    baris_other = Lokator(_SECTION_OTHER + "//tbody/tr[contains(normalize-space(), {})]", 'baris Other Document')

    @staticmethod
    def rute(fas_id: str) -> str:
        return f'{RUTE_ORIGINATION}/{fas_id}/origination-creation'

    def buka_stepper(self):
        los = self.los
        if 'origination-creation' not in los.d.current_url:
            self.menu_stepper.klik(60)
            los.tunggu(lambda: 'origination-creation' in los.d.current_url, 60, 'stepper Pembahasan Origination tidak terbuka')
        self.tombol_filter_dokumen.satu(120, 'halaman Pembahasan Origination tidak selesai dimuat')
        los.buffering()

    def isi_tanggal_entry(self):
        kotak = self.input_tanggal_entry.semua()
        if kotak and kotak[0].is_enabled() and not kotak[0].get_attribute('value'):
            log('  isi Tanggal Entry Pengajuan')
            self.los.ketik_tanggal(kotak[0], hari_ini(), self._NETRAL)

    def isi_dokumen_wajib(self, berkas_pdf: str):
        """
        Isi dokumen bertanda * yang terlihat oleh peran ini: Nomor (acak 6 digit), Tanggal
        (hari ini), dan satu PDF. Bila tidak ada satu pun yang bertanda wajib, dokumen pertama
        yang diisi — Submit baru aktif kalau ada minimal satu berkas Draft.
        """
        los = self.los

        def judul(blok):
            return re.sub(r'\s+', ' ', blok.text.split('Nomor Dokumen')[0]).strip()

        semua = self.blok_dokumen.semua()
        if not semua:
            raise GagalLangkah('Tidak ada dokumen yang bisa diisi oleh peran ini di Pembahasan Origination')
        target = [i for i, b in enumerate(semua) if '*' in judul(b)] or [0]

        for i in target:
            # Dicari ulang tiap putaran: unggahan sebelumnya merender ulang blok-blok dokumen.
            blok = self.blok_dokumen.semua()[i]
            nama = judul(blok)
            log(f'  isi dokumen: {nama}')
            los.ketik(blok.find_element(By.XPATH, ".//input[@placeholder='Input Nomor Dokumen']"), nomor_dokumen_acak())
            los.ketik_tanggal(blok.find_element(By.XPATH, ".//input[@placeholder='DD/MM/YYYY']"), hari_ini(), self._NETRAL)

            tambah = los.cari(".//button[normalize-space()='Tambah file']", blok)
            if tambah:
                los.klik(tambah[0])
                time.sleep(0.8)
            unggah = los.tunggu(lambda: blok.find_elements(By.XPATH, ".//input[@type='file']"), 15,
                                f'kotak unggah "{nama}" tidak muncul')[0]
            unggah.send_keys(berkas_pdf)

            # Unggah tidak memunculkan popup: tunggu kartu berkas berstatus Draft.
            los.tunggu(lambda: los.cari(".//*[normalize-space(text())='Draft']", blok), 120,
                       f'unggah ke "{nama}" tidak menjadi Draft')
            los.buffering()

    def tambah_other_document(self, data: dict, berkas_pdf: str):
        """Section Other Document → Add New → Create New → Confirm → popup Add Dokumen → Save."""
        los = self.los
        self.tombol_add_new_other.klik(30)
        los.modal(PemilihCreateNewModal, 15, pola=r'Create New').pilih_create_new()

        form = los.modal(OtherDocumentModal, 30)
        los.buffering()
        nomor = form.isi(data, berkas_pdf)
        form.save()
        self.baris_other(nomor).satu(60, f'dokumen bernomor {nomor} tidak muncul di tabel Other Document')

    def kirim(self, tombol_bawah: str, tombol_konfirmasi: str):
        """
        Tombol bawah (Submit/Approve) → dialog konfirmasi → tombol konfirmasi
        (Submit untuk Staff, Send untuk TL, "Approve & Kirim ke LPS" untuk Kadiv) → "Aksi berhasil".
        """
        los = self.los
        los.klik_xpath(f"(//button[normalize-space()={xp_literal(tombol_bawah)}])[last()]", 60,
                       pesan=f'tombol {tombol_bawah} tidak aktif — belum ada dokumen Draft/menunggu?')
        dialog = los.tunggu(
            lambda: next((p for p in los.d.find_elements(By.CSS_SELECTOR, '.MuiDialog-root')
                          if p.is_displayed() and los.cari(los.tombol(tombol_konfirmasi, p), p)), None),
            60, f'dialog dengan tombol "{tombol_konfirmasi}" tidak muncul')
        los.klik_xpath(los.tombol(tombol_konfirmasi, dialog), 15, induk=dialog)
        log(f'  {los.sukses_lalu_tutup(r"Aksi berhasil|berhasil", 300)}')


class OtherDocumentModal(Modal):
    """
    Popup "Add Dokumen": Kategori → Group → Jenis (berantai; Group/Jenis dimuat dari API),
    unggah PDF, Nomor (acak 6 digit), Tanggal (hari ini), Keterangan.
    """

    POLA = r'Kategori Dokumen'
    input_kategori = Lokator(".//input[@placeholder='Kategori Dokumen']")
    input_group = Lokator(".//input[@placeholder='Group Dokumen']")
    input_jenis = Lokator(".//input[@placeholder='Jenis Dokumen']")
    input_nomor = Lokator(".//input[@placeholder='Input Nomor Dokumen']", 'kotak Nomor Dokumen')
    input_tanggal = Lokator(".//input[@placeholder='Input Tanggal Dokumen']", 'kotak Tanggal Dokumen')
    input_keterangan = Lokator(".//textarea[@placeholder='Input Keterangan']", 'kotak Keterangan')

    def isi(self, data: dict, berkas_pdf: str) -> str:
        """Isi seluruh form; mengembalikan nomor dokumen (untuk mencari barisnya di tabel)."""
        los = self.los
        pilihan = [
            los.pilih_dari_daftar(kotak.satu(15), data[kunci])
            for kotak, kunci in ((self.input_kategori, 'other_document_kategori'),
                                 (self.input_group, 'other_document_group'),
                                 (self.input_jenis, 'other_document_jenis'))
        ]
        log(f'  other document: {" / ".join(pilihan)}')

        self.akar.find_element(By.XPATH, ".//input[@type='file']").send_keys(berkas_pdf)
        los.buffering()
        # Sebagian versi memunculkan popup "berhasil" sendiri setelah berkas dipilih.
        los.konfirmasi_bila_ada(r'berhasil', 'Close', 3)

        nomor = nomor_dokumen_acak()
        self.input_nomor.ketik(nomor, 15)
        los.ketik_tanggal(self.input_tanggal.satu(15), hari_ini(), "//*[normalize-space(text())='Upload By']")
        if data.get('other_document_keterangan'):
            self.input_keterangan.ketik(data['other_document_keterangan'], 15)
        return nomor

    def save(self):
        self.klik_tombol('Save', 30, 'Save Add Dokumen belum aktif — ada field wajib yang kosong?')
        self.los.sukses_lalu_tutup()

"""Loan Processing → Proposal Pengajuan → Pipeline: daftar, Create Pipeline, detail, Go To Origination."""
import re
import time
from collections.abc import Callable

from core.lokator import Lokator
from core.util import eksak
from .base import CommentModal, Halaman, Modal, PemilihCreateNewModal
from .fasilitas import FormFasilitasModal

RUTE_PIPELINE = '/loan-processing/submission-proposal/pipeline'


class PipelineListPage(Halaman):
    tombol_add_new_pipeline = Lokator("//button[contains(normalize-space(), 'Add New Pipeline')]")
    input_pencarian = Lokator("//div[contains(@class,'MuiDialog-root')]//input[@placeholder='Pencarian...']",
                              'kotak Pencarian customer')
    tombol_create_new = Lokator("//button[normalize-space()='Create New Customer & Pipeline']")

    def buka(self):
        self.los.buka(RUTE_PIPELINE)

    def create_new_customer(self, kata_pencarian: str):
        """Add New Pipeline → cari kata kunci → Create New Customer & Pipeline → (Ya) → halaman Create Pipeline."""
        los = self.los
        self.tombol_add_new_pipeline.klik()
        self.input_pencarian.ketik(kata_pencarian, 30)

        time.sleep(3)
        los.buffering()
        self.tombol_create_new.klik(60)

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


class CreatePipelinePage(Halaman):
    """Customer baru: halaman ini hanya menerima Institution Type, Nama Customer, dan GAM."""

    input_nama_customer = Lokator("//input[@placeholder='Nama Customer']")
    input_gam = Lokator("//input[@placeholder='Input General Account Manager']", 'kotak General Account Manager')
    tombol_save = Lokator("//*[@id='button-save']", 'tombol Save')

    def isi(self, institution_type: str, nama_customer: str, gam_cari: str, gam_opsi: str):
        los = self.los
        los.pilih_select('Institution Type', eksak(institution_type))
        self.input_nama_customer.ketik(nama_customer)
        los.pilih_autocomplete(self.input_gam.satu(), gam_cari, gam_opsi)

    def save(self) -> str:
        """Save → (peringatan DK / rekomendasi nama) → Success → Close → detail pipeline. Mengembalikan ID pipeline."""
        los = self.los
        self.tombol_save.klik(30, 'tombol Save belum aktif — ada field wajib yang kosong?')
        los.buffering()
        los.konfirmasi_bila_ada(r'Terdapat kemiripan', 'Save', 3)
        if los.konfirmasi_bila_ada(r'Rekomendasi Nama Customer', 'Create New Customer & Pipeline', 3):
            los.konfirmasi_bila_ada(r'serupa pada rekomendasi', 'Ya', 8)
        los.sukses_lalu_tutup()
        los.tunggu(lambda: re.search(r'/pipeline/[^/]+/detail', los.d.current_url), 60, 'tidak pindah ke detail pipeline')
        pipeline_id = re.search(r'/pipeline/([^/]+)/detail', los.d.current_url).group(1)
        los.buffering()
        return pipeline_id


class PipelineDetailPage(Halaman):
    judul_fasilitas = Lokator("//*[normalize-space(text())='Fasilitas Pembiayaan']", 'section Fasilitas Pembiayaan')
    input_pic2 = Lokator("//input[@placeholder='Pilih PIC2']", 'kotak PIC2')
    input_analis = Lokator("//input[@placeholder='Nama Analis']", 'kotak Nama Analis')
    tombol_save = Lokator("(//button[normalize-space()='Save'])[last()]", 'tombol Save')
    tombol_add_new_fasilitas = Lokator("//button[normalize-space()='Add New']", 'tombol Add New fasilitas')
    tombol_submit_apa_pun = Lokator("//button[normalize-space()='Submit']", 'tombol Submit')
    tombol_submit = Lokator("(//button[normalize-space()='Submit'])[last()]", 'tombol Submit')
    tombol_approve = Lokator("(//button[normalize-space()='Approve'])[last()]", 'tombol Approve')
    tombol_go_to_origination = Lokator("//button[contains(normalize-space(), 'Go To Origination')]")

    @staticmethod
    def rute(pipeline_id: str) -> str:
        return f'{RUTE_PIPELINE}/{pipeline_id}/detail'

    def buka(self, pipeline_id: str):
        self.los.buka(self.rute(pipeline_id))

    def tunggu_termuat(self):
        self.judul_fasilitas.satu(120, 'detail pipeline tidak termuat')
        self.los.buffering()

    def isi_data_pipeline(self, data: dict):
        """Untuk customer baru, field ini baru bisa diisi di halaman detail setelah Save pertama."""
        los = self.los
        los.pilih_select('Jenis Customer', eksak(data['jenis_customer']))
        los.pilih_radio('isGroup', 'false')          # Customer Memiliki Group: Tidak
        los.pilih_radio('isRelatedToSmi', 'false')   # Terkait Dengan SMI: Tidak
        # Label "Fast Track" diganti "Origination" di source terbaru; lingkungan lama masih "Fast Track".
        los.pilih_select('Tipe Proses', data['tipe_proses'])
        los.pilih_select('Tipe Pembiayaan', eksak(data['tipe_pembiayaan']))
        los.pilih_autocomplete(self.input_pic2.satu(), data['pic2_cari'], data['pic2_opsi'])
        los.pilih_autocomplete(self.input_analis.satu(), data['analis_cari'], data['analis_opsi'])

    def simpan_data_pipeline(self):
        self.tombol_save.klik(60)
        self.los.konfirmasi_bila_ada(r'DATA MANDATORY', 'Ya', 3)
        self.los.sukses_lalu_tutup()

    def tambah_fasilitas(self, isi: Callable[[FormFasilitasModal], None]):
        """Fasilitas Pembiayaan → Add New → Create New → Confirm → `isi(form)` → Save."""
        los = self.los
        self.tombol_add_new_fasilitas.klik()
        los.modal(PemilihCreateNewModal, pola='Tambah Fasilitas Pembiayaan').pilih_create_new()
        form = los.modal(FormFasilitasModal, 30)
        los.buffering()
        isi(form)
        form.save()

    def sudah_submit(self) -> bool:
        return not self.tombol_submit_apa_pun.ada()

    def submit(self, komentar: str):
        """Submit → (konfirmasi) → Comment → Save → Success → Close."""
        self.tombol_submit.klik(60, 'Submit belum aktif — ada field mandatory pipeline yang kosong?')
        self._komentar_lalu_sukses(komentar)

    def approve(self, komentar: str):
        self.tombol_approve.klik(60)
        self._komentar_lalu_sukses(komentar)

    def _komentar_lalu_sukses(self, komentar: str):
        los = self.los
        los.konfirmasi_bila_ada(r'yakin ingin Submit', 'Ya', 3)
        los.modal(CommentModal, 30).isi_lalu_simpan(komentar)
        los.sukses_lalu_tutup()

    def go_to_origination(self) -> 'NotificationModal':
        self.tombol_go_to_origination.klik(60)
        notif = self.los.modal(NotificationModal, 30)
        self.los.buffering()
        return notif


class NotificationModal(Modal):
    """Popup Go To Origination: dua field "Nama Staff" (multi-select) — urutan 0 = DEPI, 1 = DH."""

    POLA = 'Notification to DEPI'
    input_nama_staff = Lokator(".//div[contains(@class,'MuiAutocomplete-root')]//input", 'kotak Nama Staff')
    label_selected_pipeline = Lokator(".//*[normalize-space(text())='Selected Pipeline']", 'label Selected Pipeline')
    input_komentar = Lokator(".//textarea[@placeholder='Comment']", 'kotak komentar')

    def pilih_staff(self, urutan: int, kata: str, pola_opsi: str):
        kotak = self.input_nama_staff.semua()[urutan]
        self.los.pilih_autocomplete(kotak, kata, pola_opsi)
        # Klik area netral supaya daftar opsi multi-select tertutup.
        self.los.klik(self.label_selected_pipeline.satu(10))

    def save(self, komentar: str):
        self.input_komentar.ketik(komentar, 15)
        self.klik_tombol('Save', pesan='Save belum aktif — staff DEPI/DH/komentar belum lengkap?')
        self.los.sukses_lalu_tutup()

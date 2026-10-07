"""
Popup "Add New Fasilitas Pembiayaan" di detail pipeline.

Begitu Segmen Pembiayaan = Syariah, "Produk" berganti label menjadi "Skema pembiayaan" (opsi dari
parameter productSyariah) dan "Nominal Pengajuan" hilang, diganti sub-form per skema
(ModalFormFacility.tsx, SyariahForm.tsx): Musyarakah = Syirkah SMI + Syirkah Nasabah;
Murabahah = Objek + Harga Beli; Qardh = Jumlah pinjaman; dst. Label sub-form bisa diganti dari
konfigurasi skema di DB, jadi sub-form diisi GENERIK lewat `_isi_field_wajib_kosong`.
"""
import re

from selenium.webdriver.common.by import By

from core.data_uji import nominal_acak, rupiah
from core.lokator import Lokator
from core.util import GagalLangkah, log
from .base import Modal


class FormFasilitasModal(Modal):
    POLA = 'Add New Fasilitas Pembiayaan'
    input_nominal = Lokator(".//input[@placeholder='Input Nominal Pengajuan']", 'kotak Nominal Pengajuan')
    input_tujuan = Lokator(".//input[@placeholder='Tujuan Pembiayaan']", 'kotak Tujuan Pembiayaan')
    pesan_skema_belum_dimapping = Lokator(".//*[contains(normalize-space(), 'Skema belum dimapping')]")
    label_wajib = Lokator(".//*[normalize-space(text())='*']", 'tanda wajib *')

    _XP_ISIAN_KETIK = (".//input[(not(@type) or @type='text' or @type='number')"
                       " and not(@disabled) and not(@readonly) and not(@aria-hidden='true')"
                       " and not(@role='combobox') and not(contains(@placeholder, 'DD/MM'))"
                       " and not(contains(@class, 'MuiSelect-nativeInput'))] | .//textarea[not(@disabled)]")

    def isi_konven(self, produk: str):
        """Segmen tetap bawaan divisi (Konven) → Produk → Nominal Pengajuan."""
        self.los.pilih_select('Choose Produk', produk, induk=self.akar)
        nominal = nominal_acak()
        self.input_nominal.ketik(nominal, 15)
        log(f'  fasilitas konven: {produk}, nominal {rupiah(nominal)}')

    def isi_syariah(self, segmen: str, skema: str, tujuan_pembiayaan: str, teks_objek: str):
        """Segmen Pembiayaan → Syariah, lalu Skema pembiayaan, Tujuan Pembiayaan, dan sub-form skema."""
        los = self.los
        # Segmen sudah terisi bawaan divisi, jadi placeholder-nya tak terlihat: dicari lewat label.
        los.pilih_select_berlabel('Segmen Pembiayaan', segmen, induk=self.akar)
        los.buffering()
        los.pilih_select('Choose Skema pembiayaan', skema, induk=self.akar)
        los.buffering()
        if self.pesan_skema_belum_dimapping.ada():
            raise GagalLangkah(f'Skema "{skema}" belum dimapping di lingkungan ini (pesan aplikasi: '
                               '"Skema belum dimapping, mohon kontak Admin"). Pilih skema lain di config.json.')
        self.input_tujuan.ketik(tujuan_pembiayaan, 15)
        log(f'  fasilitas syariah: skema {skema}')
        self._isi_field_wajib_kosong(teks_objek)

    def _isi_field_wajib_kosong(self, isi_teks: str):
        """
        Isi setiap field bertanda * yang masih kosong dan bisa diketik: nominal acak bila
        wadahnya memuat pilihan mata uang (IDR/USD), selain itu `isi_teks`. Dropdown, autocomplete,
        tanggal, dan field nonaktif (mis. "Mitra Syarik SMI", "Total Syirkah") dilewati.
        """
        los = self.los
        for bintang in self.label_wajib.semua():
            label = bintang.find_element(By.XPATH, '..')
            nama = re.sub(r'\s*\*\s*$', '', re.sub(r'\s+', ' ', label.text)).strip()
            wadah = label.find_element(By.XPATH, './ancestor::div[.//input or .//textarea][1]')
            isian = [i for i in los.cari(self._XP_ISIAN_KETIK, wadah) if not i.get_attribute('value')]
            if not isian:
                continue
            mata_uang = any(re.search(r'^(IDR|USD)$', c.text.strip())
                            for c in wadah.find_elements(By.XPATH, ".//*[@role='combobox']"))
            nilai = nominal_acak() if mata_uang else isi_teks
            los.ketik(isian[0], nilai)
            log(f'    {nama}: {rupiah(nilai) if mata_uang else nilai}')
            los.buffering(10)

    def save(self):
        self.klik_tombol('Save')
        self.los.sukses_lalu_tutup()

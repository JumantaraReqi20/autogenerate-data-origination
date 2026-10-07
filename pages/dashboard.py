import time

from selenium.webdriver.common.by import By

from core.lokator import Lokator
from core.util import log
from .base import Halaman


class DashboardPage(Halaman):
    judul_daftar_tugas = Lokator("//*[normalize-space(text())='To Do List' or normalize-space(text())='Approval List']",
                                 'To Do List / Approval List')
    # Tombol Filter pertama milik To Do List (yang kedua milik Inquiry Data).
    tombol_filter = Lokator("(//button[normalize-space()='Filter'])[1]", 'tombol Filter To Do List')
    popover_filter = Lokator("//*[contains(@class,'MuiPopover-root')]", 'popover Filter')
    baris_tugas = Lokator("//button[normalize-space()='Go to task']/parent::*[*[normalize-space()={}]]",
                          'baris tugas')

    def buka_tugas(self, customer: str, url_cadangan: str, batas: float = 150) -> bool:
        """
        Dashboard → To Do List / Approval List → Filter "Nama Customer" → Apply → "Go to task".

        Daftarnya berisi ratusan tugas dan tidak diurutkan terbaru-dulu, jadi barisnya dicari
        lewat filter. Tugas dibuat backend secara asinkron; bila belum muncul, dicoba ulang.
        Setelah habis batas, jatuh ke URL cadangan supaya run tidak berhenti hanya karena
        dashboard terlambat.
        """
        los = self.los
        akhir = time.time() + batas
        while time.time() < akhir:
            los.buka('/')
            self.judul_daftar_tugas.satu(60)
            self.tombol_filter.klik(30)
            self._filter_nama_customer(customer)
            los.buffering()
            time.sleep(1.5)
            baris = self.baris_tugas(customer).semua()
            if baris:
                los.klik(baris[0].find_element(By.XPATH, ".//button[normalize-space()='Go to task']"))
                los.tunggu(lambda: los.d.current_url.rstrip('/') != los.base_url, 60, 'Go to task tidak berpindah halaman')
                los.buffering()
                log(f'  Go to task → {los.d.current_url.replace(los.base_url, "")}')
                return True
            log('  tugas belum muncul di dashboard, coba lagi 15 detik lagi')
            time.sleep(15)
        log(f'  tugas tidak ditemukan di dashboard, buka langsung {url_cadangan}')
        los.buka(url_cadangan)
        return False

    def _filter_nama_customer(self, customer: str):
        pop = self.los.halaman(FilterTugasPopover, self.popover_filter.satu(15))
        pop.input_nama_customer.ketik(customer, 15)
        pop.tombol_apply.klik(15)


class FilterTugasPopover(Halaman):
    input_nama_customer = Lokator(".//input[@placeholder='example: proses..']", 'kotak Nama Customer di Filter')
    tombol_apply = Lokator(".//button[normalize-space()='Apply']", 'tombol Apply')

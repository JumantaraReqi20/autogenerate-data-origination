from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from core.driver import Los
from core.lokator import Lokator


class Halaman:
    """Page Object. Dibuat lewat `los.halaman(Kelas)`; locator-nya dideklarasikan dengan `Lokator`."""

    def __init__(self, los: Los, akar: WebElement | None = None):
        self.los = los
        self.akar = akar


class Modal(Halaman):
    """
    Popup MUI (.MuiDialog-root). Dibuat lewat `los.modal(Kelas)`, yang menunggu popup dengan teks
    cocok `POLA`; popup itu menjadi `akar`, jadi lokator './/' dicari di dalamnya.
    """

    POLA: str = ''

    def klik_tombol(self, label: str, batas: float = 15, pesan: str | None = None) -> WebElement:
        return self.los.klik_xpath(self.los.tombol(label, self.akar), batas, induk=self.akar, pesan=pesan)


class PemilihCreateNewModal(Modal):
    """Popup berisi radio Existing/Create New → Confirm. Dipakai Fasilitas dan Other Document."""

    def pilih_create_new(self):
        radio = self.akar.find_element(By.CSS_SELECTOR, 'input[type="radio"][value="new"]')
        self.los.d.execute_script('arguments[0].click()', radio)
        self.klik_tombol('Confirm')


class CommentModal(Modal):
    """Popup "Comment" setelah Submit/Approve: isi komentar → Save."""

    POLA = r'Comment'
    input_komentar = Lokator(".//textarea[@placeholder='Comment']", 'kotak komentar')

    def isi_lalu_simpan(self, komentar: str):
        self.input_komentar.ketik(komentar, 15)
        self.klik_tombol('Save')

"""
Page factory versi aplikasi ini.

Seperti `@FindBy` di PageFactory Java, elemen dideklarasikan sebagai atribut class halaman:

    class PipelineDetailPage(Halaman):
        tombol_submit = Lokator("(//button[normalize-space()='Submit'])[last()]")

    detail = los.halaman(PipelineDetailPage)
    detail.tombol_submit.klik(60)

Bedanya: elemen TIDAK disimpan saat halaman dibuat, melainkan dicari ulang setiap kali dipakai.
Di aplikasi ini popup MUI dipasang di portal, loader global berupa dialog, dan daftar opsi
dirender ulang — elemen yang disimpan cepat basi (StaleElementReferenceException).

Lokator yang diawali './/' dicari di dalam `akar` halaman (mis. popup untuk Modal); yang
diawali '//' dicari di seluruh dokumen. Lokator boleh berparameter `{}`; nilainya diisi lewat
pemanggilan dan otomatis dibungkus xp_literal: `self.baris_customer('Agoda Oto ABCD').satu()`.
"""
from selenium.webdriver.remote.webelement import WebElement

from .util import xp_literal


class Lokator:
    def __init__(self, xpath: str, deskripsi: str | None = None):
        self.xpath = xpath
        self.deskripsi = deskripsi

    def __set_name__(self, pemilik, nama: str):
        self.deskripsi = self.deskripsi or nama.replace('_', ' ')

    def __get__(self, halaman, pemilik):
        if halaman is None:
            return self
        return Elemen(halaman.los, self.xpath, halaman.akar, self.deskripsi)


class Elemen:
    """Lokator yang sudah terikat ke browser (dan akar) sebuah halaman."""

    def __init__(self, los, xpath: str, induk: WebElement | None, deskripsi: str):
        self.los = los
        self.xpath = xpath
        self.induk = induk
        self.deskripsi = deskripsi

    def __call__(self, *nilai: str) -> 'Elemen':
        return Elemen(self.los, self.xpath.format(*map(xp_literal, nilai)), self.induk, self.deskripsi)

    def semua(self) -> list[WebElement]:
        """Semua elemen yang tampil saat ini (tanpa menunggu)."""
        return self.los.cari(self.xpath, self.induk)

    def ada(self) -> bool:
        return bool(self.semua())

    def satu(self, batas: float = 60, pesan: str | None = None) -> WebElement:
        """Tunggu elemen pertama yang tampil."""
        return self.los.satu(self.xpath, batas, self.induk, pesan or f'{self.deskripsi} tidak muncul ({self.xpath})')

    def klik(self, batas: float = 60, pesan: str | None = None) -> WebElement:
        """Tunggu elemen tampil DAN aktif, lalu klik."""
        return self.los.klik_xpath(self.xpath, batas, self.induk,
                                   pesan or f'{self.deskripsi} tidak muncul/aktif ({self.xpath})')

    def ketik(self, isi: str, batas: float = 60):
        self.los.ketik(self.satu(batas), isi)

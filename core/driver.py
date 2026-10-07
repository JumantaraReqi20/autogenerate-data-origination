"""
Helper Selenium generik untuk aplikasi NEW LOS (Next.js + MUI). Tidak tahu apa pun tentang
halaman tertentu — itu tugas pages/.

Hal yang perlu diingat tentang DOM aplikasi ini:
- Loader global adalah sebuah MuiDialog berisi spinner saja (src/components/shared/Loader).
  Jadi "dialog pertama" belum tentu popup; popup selalu dicari lewat TEKS-nya.
- Popup Success/Error/Warning: src/components/shared/SmiModal/{Success,Error,Confirm}Modal.
  Success = "Success" + "...berhasil..." + tombol Close.
  Error   = "Error!" + tombol Close.
- Select MUI dirender sebagai [role=combobox]; opsinya [role=option] di dalam listbox
  yang dipasang di luar form (portal), jadi dicari dari seluruh dokumen.
"""
import re
import time
from pathlib import Path
from typing import TypeVar

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from .util import GagalLangkah, log, tampil, teks, xp_literal

H = TypeVar('H')


class Los:
    def __init__(self, base_url: str, folder_bukti: Path, headless: bool = False):
        self.base_url = base_url.rstrip('/')
        self.folder_bukti = folder_bukti
        opsi = webdriver.ChromeOptions()
        if headless:
            opsi.add_argument('--headless=new')
        opsi.add_argument('--window-size=1440,900')
        opsi.add_argument('--ignore-certificate-errors')
        opsi.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.d = webdriver.Chrome(options=opsi)
        self.d.implicitly_wait(0)

    # ------------------------------------------------------------------ page factory

    def halaman(self, kelas: type[H], akar: WebElement | None = None) -> H:
        """Buat Page Object `kelas` yang terikat ke browser ini (opsional: ke elemen `akar`)."""
        return kelas(self, akar)

    def modal(self, kelas: type[H], batas: float = 60, pola: str | None = None) -> H:
        """Tunggu popup yang teksnya cocok dengan `pola` (bawaan: `kelas.POLA`), lalu bungkus jadi Page Object."""
        return kelas(self, self.tunggu_popup(pola or kelas.POLA, batas))

    # ------------------------------------------------------------------ dasar

    def tutup(self):
        try:
            self.d.quit()
        except WebDriverException:
            pass

    def simpan_bukti(self, nama: str):
        """Screenshot + HTML saat gagal, untuk dilihat sesudahnya."""
        self.folder_bukti.mkdir(parents=True, exist_ok=True)
        cap = time.strftime('%Y%m%d-%H%M%S')
        png = self.folder_bukti / f'{cap}-{nama}.png'
        try:
            self.d.save_screenshot(str(png))
            (self.folder_bukti / f'{cap}-{nama}.html').write_text(self.d.page_source, encoding='utf-8')
        except WebDriverException:
            pass
        return png

    def tunggu(self, fungsi, batas: float = 60, pesan: str = 'kondisi tidak terpenuhi', jeda: float = 0.5):
        """Ulangi `fungsi` sampai mengembalikan nilai truthy, atau gagal setelah `batas` detik."""
        akhir = time.time() + batas
        while True:
            try:
                hasil = fungsi()
                if hasil:
                    return hasil
            except (StaleElementReferenceException, ElementClickInterceptedException):
                pass
            if time.time() > akhir:
                raise GagalLangkah(f'{pesan} (setelah {int(batas)} detik)')
            time.sleep(jeda)

    def cari(self, xpath: str, induk=None) -> list[WebElement]:
        return [e for e in (induk or self.d).find_elements(By.XPATH, xpath) if tampil(e)]

    def satu(self, xpath: str, batas: float = 60, induk=None, pesan: str = None) -> WebElement:
        return self.tunggu(lambda: (self.cari(xpath, induk) or [None])[0],
                           batas, pesan or f'elemen tidak muncul: {xpath}')

    def klik(self, el: WebElement):
        self.d.execute_script('arguments[0].scrollIntoView({block:"center"})', el)
        try:
            el.click()
        except (ElementClickInterceptedException, WebDriverException):
            self.d.execute_script('arguments[0].click()', el)

    def klik_xpath(self, xpath: str, batas: float = 60, induk=None, pesan: str = None):
        el = self.tunggu(lambda: next((e for e in self.cari(xpath, induk) if e.is_enabled()), None),
                         batas, pesan or f'tombol tidak muncul/aktif: {xpath}')
        self.klik(el)
        return el

    def ketik(self, el: WebElement, isi: str):
        self.klik(el)
        el.send_keys(Keys.CONTROL, 'a')
        el.send_keys(Keys.DELETE)
        el.send_keys(isi)

    def tombol(self, label: str, induk=None) -> str:
        """XPath tombol dengan teks persis."""
        return f".//button[normalize-space()={xp_literal(label)}]" if induk else f"//button[normalize-space()={xp_literal(label)}]"

    def buka(self, path: str):
        self.d.get(self.base_url + path)
        time.sleep(1)
        if '/login' in self.d.current_url and not path.startswith('/login'):
            raise GagalLangkah('Terlempar ke halaman login — sesi habis?')
        self.buffering()

    def url_berisi(self, *bagian: str) -> bool:
        return any(b in self.d.current_url for b in bagian)

    # ------------------------------------------------------------------ menunggu

    # Hanya spinner yang BERPUTAR (indeterminate). Progress bar determinate dipakai sebagai
    # indikator kelengkapan stepper ("Validasi 0%") dan tampil terus — bukan tanda loading.
    _JS_SIBUK = """
      const tampil = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
      const spinner = [...document.querySelectorAll(
        '.MuiCircularProgress-indeterminate, .MuiLinearProgress-indeterminate, .MuiLinearProgress-query')].some(tampil);
      const teks = /Auto Saving\\.\\.\\.|Sedang Submit Dokumen|Mengunggah/.test(document.body ? document.body.innerText : '');
      return spinner || teks;
    """

    def buffering(self, batas: float = 120):
        """Tunggu sampai spinner/loader hilang. Lunak: lewat batas hanya dicatat, tidak gagal."""
        time.sleep(0.6)
        akhir = time.time() + batas
        while time.time() < akhir:
            try:
                if not self.d.execute_script(self._JS_SIBUK):
                    time.sleep(0.4)
                    if not self.d.execute_script(self._JS_SIBUK):
                        return
            except WebDriverException:
                pass
            time.sleep(0.5)
        log(f'  (masih ada indikator loading setelah {int(batas)} detik, lanjut)')

    # ------------------------------------------------------------------ popup

    def popup(self, pola: str) -> WebElement | None:
        """Popup MUI yang tampil dan teksnya cocok dengan regex `pola` (paling atas bila bertumpuk)."""
        cocok = [p for p in self.d.find_elements(By.CSS_SELECTOR, '.MuiDialog-root')
                 if tampil(p) and re.search(pola, teks(p), re.I)]
        return cocok[-1] if cocok else None

    def tunggu_popup(self, pola: str, batas: float = 60) -> WebElement:
        return self.tunggu(lambda: self.popup(pola), batas, f'popup "{pola}" tidak muncul')

    def sukses_lalu_tutup(self, pola: str = r'berhasil', batas: float = 180) -> str:
        """
        Tunggu popup sukses lalu klik Close. Popup Error langsung menggagalkan run dengan
        isi pesannya — tanpa ini kegagalan backend hanya terlihat sebagai timeout.
        """
        def cek():
            ok = self.popup(pola)
            if ok:
                return ok
            err = self.popup(r'Error!|Terjadi kesalahan')
            if err:
                raise GagalLangkah(f'Aplikasi menampilkan error: {teks(err)}')
            return None

        p = self.tunggu(cek, batas, f'popup sukses "{pola}" tidak muncul')
        isi = teks(p)
        self.klik_xpath(self.tombol('Close', p), 15, induk=p)
        self.tunggu(lambda: not tampil(p), 20, 'popup sukses tidak tertutup')
        self.buffering()
        return isi

    def konfirmasi_bila_ada(self, pola: str, label_tombol: str, batas: float = 5) -> bool:
        """Klik tombol di popup konfirmasi bila popup itu muncul dalam `batas` detik."""
        try:
            p = self.tunggu_popup(pola, batas)
        except GagalLangkah:
            return False
        self.klik_xpath(self.tombol(label_tombol, p), 15, induk=p)
        self.buffering()
        return True

    # ------------------------------------------------------------------ input

    def opsi(self, pola: str) -> list[WebElement]:
        return [o for o in self.cari("//*[@role='option']") if re.search(pola, teks(o), re.I)]

    def klik_opsi(self, pola: str, pesan: str) -> str:
        """
        Cari opsi yang cocok lalu klik, dalam SATU percobaan `tunggu`. Daftar opsi autocomplete
        berbasis API bisa dirender ulang di antara "ditemukan" dan "diklik" (hasil pencarian tiba
        dua kali), sehingga elemennya basi; percobaan berikutnya mencari ulang dari awal.
        Mengembalikan label opsi yang diklik.
        """
        def cari_lalu_klik():
            o = next((x for x in self.opsi(pola) if teks(x)), None)
            if o is None:
                return None
            label = teks(o)
            self.klik(o)
            return label

        return self.tunggu(cari_lalu_klik, 30, pesan)

    def pilih_select(self, teks_sekarang: str, pola_opsi: str, induk=None):
        """MUI Select: dikenali dari teks yang sedang tampil (biasanya placeholder)."""
        kotak = self.satu(f".//*[@role='combobox'][contains(normalize-space(), {xp_literal(teks_sekarang)})]",
                          30, induk or self.d, f'dropdown "{teks_sekarang}" tidak ditemukan')
        self.klik(kotak)
        self.klik_opsi(pola_opsi, f'opsi "{pola_opsi}" tidak ada di dropdown "{teks_sekarang}"')
        self.tunggu(lambda: not self.cari("//*[@role='listbox']"), 10, 'dropdown tidak tertutup')
        time.sleep(0.3)

    def pilih_select_berlabel(self, label: str, pola_opsi: str, induk=None):
        """MUI Select yang sudah berisi nilai (placeholder tak terlihat): dicari lewat teks labelnya."""
        kotak = self.satu(f".//*[normalize-space(text())={xp_literal(label)}]"
                          f"/ancestor::div[.//*[@role='combobox']][1]//*[@role='combobox']",
                          30, induk or self.d, f'dropdown berlabel "{label}" tidak ditemukan')
        self.klik(kotak)
        self.klik_opsi(pola_opsi, f'opsi "{pola_opsi}" tidak ada di dropdown "{label}"')
        self.tunggu(lambda: not self.cari("//*[@role='listbox']"), 10, 'dropdown tidak tertutup')
        time.sleep(0.5)

    def pilih_autocomplete(self, kotak: WebElement, kata: str, pola_opsi: str):
        """MUI Autocomplete berbasis API: ketik kata kunci, tunggu opsi yang cocok, pilih."""
        self.ketik(kotak, kata)
        self.klik_opsi(pola_opsi, f'opsi "{pola_opsi}" tidak muncul setelah mengetik "{kata}"')
        time.sleep(0.5)

    def pilih_dari_daftar(self, kotak: WebElement, pola_opsi: str = '') -> str:
        """
        MUI Autocomplete yang daftarnya muncul saat diklik (tanpa mengetik). Pilih opsi yang
        cocok dengan `pola_opsi`, atau opsi pertama bila pola kosong. Mengembalikan labelnya.
        """
        self.tunggu(lambda: kotak.is_enabled(), 30, 'dropdown masih nonaktif')
        self.klik(kotak)
        label = self.klik_opsi(pola_opsi or '.', f'opsi "{pola_opsi or "(pertama)"}" tidak muncul')
        time.sleep(0.5)
        return label

    def pilih_radio(self, nama: str, nilai: str):
        r = self.d.find_element(By.CSS_SELECTOR, f'input[type="radio"][name="{nama}"][value="{nilai}"]')
        self.d.execute_script('arguments[0].click()', r)
        self.tunggu(lambda: r.is_selected(), 5, f'radio {nama}={nilai} tidak terpilih')

    def ketik_tanggal(self, kotak: WebElement, tanggal: str, xpath_netral: str):
        """
        Date picker MUI (DD/MM/YYYY): diketik digit per digit, lalu kalendernya ditutup dengan
        mengklik elemen netral (judul halaman). Sengaja bukan Escape: Escape ikut menutup popup lain.
        """
        self.klik(kotak)
        kotak.send_keys(Keys.CONTROL, 'a')
        kotak.send_keys(tanggal.replace('/', ''))
        time.sleep(0.3)
        netral = self.cari(xpath_netral)
        if netral:
            self.klik(netral[0])
        time.sleep(0.3)

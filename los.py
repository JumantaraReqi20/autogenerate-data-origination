"""
Helper Selenium untuk aplikasi NEW LOS (Next.js + MUI).

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
from datetime import date
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

FOLDER = Path(__file__).parent
ARTEFAK = FOLDER / 'artefak'


def log(pesan: str):
    print(f'[{time.strftime("%H:%M:%S")}] {pesan}', flush=True)


def hari_ini() -> str:
    return date.today().strftime('%d/%m/%Y')


class GagalLangkah(Exception):
    """Kegagalan yang pesannya sudah cukup jelas untuk dibaca manusia."""


def _teks(el: WebElement) -> str:
    try:
        return re.sub(r'\s+', ' ', el.text or '').strip()
    except StaleElementReferenceException:
        return ''


def _tampil(el: WebElement) -> bool:
    try:
        return el.is_displayed()
    except StaleElementReferenceException:
        return False


def xp_literal(s: str) -> str:
    """String aman untuk XPath (menangani tanda kutip)."""
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    return "concat('" + s.replace("'", "',\"'\",'") + "')"


class Los:
    def __init__(self, base_url: str, headless: bool = False):
        self.base_url = base_url.rstrip('/')
        opsi = webdriver.ChromeOptions()
        if headless:
            opsi.add_argument('--headless=new')
        opsi.add_argument('--window-size=1440,900')
        opsi.add_argument('--ignore-certificate-errors')
        opsi.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.d = webdriver.Chrome(options=opsi)
        self.d.implicitly_wait(0)

    # ------------------------------------------------------------------ dasar

    def tutup(self):
        try:
            self.d.quit()
        except WebDriverException:
            pass

    def simpan_bukti(self, nama: str):
        """Screenshot + HTML saat gagal, untuk dilihat sesudahnya."""
        ARTEFAK.mkdir(exist_ok=True)
        cap = time.strftime('%Y%m%d-%H%M%S')
        png = ARTEFAK / f'{cap}-{nama}.png'
        try:
            self.d.save_screenshot(str(png))
            (ARTEFAK / f'{cap}-{nama}.html').write_text(self.d.page_source, encoding='utf-8')
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
        return [e for e in (induk or self.d).find_elements(By.XPATH, xpath) if _tampil(e)]

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

    def ketik(self, el: WebElement, teks: str):
        self.klik(el)
        el.send_keys(Keys.CONTROL, 'a')
        el.send_keys(Keys.DELETE)
        el.send_keys(teks)

    def tombol(self, teks: str, induk=None) -> str:
        """XPath tombol dengan teks persis."""
        return f".//button[normalize-space()={xp_literal(teks)}]" if induk else f"//button[normalize-space()={xp_literal(teks)}]"

    def buka(self, path: str):
        self.d.get(self.base_url + path)
        time.sleep(1)
        if '/login' in self.d.current_url and not path.startswith('/login'):
            raise GagalLangkah('Terlempar ke halaman login — sesi habis?')
        self.buffering()

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
                 if _tampil(p) and re.search(pola, _teks(p), re.I)]
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
                raise GagalLangkah(f'Aplikasi menampilkan error: {_teks(err)}')
            return None

        p = self.tunggu(cek, batas, f'popup sukses "{pola}" tidak muncul')
        teks = _teks(p)
        self.klik_xpath(self.tombol('Close', p), 15, induk=p)
        self.tunggu(lambda: not _tampil(p), 20, 'popup sukses tidak tertutup')
        self.buffering()
        return teks

    def konfirmasi_bila_ada(self, pola: str, teks_tombol: str, batas: float = 5) -> bool:
        """Klik tombol di popup konfirmasi bila popup itu muncul dalam `batas` detik."""
        try:
            p = self.tunggu_popup(pola, batas)
        except GagalLangkah:
            return False
        self.klik_xpath(self.tombol(teks_tombol, p), 15, induk=p)
        self.buffering()
        return True

    # ------------------------------------------------------------------ input

    def opsi(self, pola: str) -> list[WebElement]:
        return [o for o in self.cari("//*[@role='option']") if re.search(pola, _teks(o), re.I)]

    def pilih_select(self, teks_sekarang: str, pola_opsi: str, induk=None):
        """MUI Select: dikenali dari teks yang sedang tampil (biasanya placeholder)."""
        kotak = self.satu(f".//*[@role='combobox'][contains(normalize-space(), {xp_literal(teks_sekarang)})]",
                          30, induk or self.d, f'dropdown "{teks_sekarang}" tidak ditemukan')
        self.klik(kotak)
        o = self.tunggu(lambda: (self.opsi(pola_opsi) or [None])[0], 30,
                        f'opsi "{pola_opsi}" tidak ada di dropdown "{teks_sekarang}"')
        self.klik(o)
        self.tunggu(lambda: not self.cari("//*[@role='listbox']"), 10, 'dropdown tidak tertutup')
        time.sleep(0.3)

    def pilih_select_berlabel(self, label: str, pola_opsi: str, induk=None):
        """MUI Select yang sudah berisi nilai (placeholder tak terlihat): dicari lewat teks labelnya."""
        kotak = self.satu(f".//*[normalize-space(text())={xp_literal(label)}]"
                          f"/ancestor::div[.//*[@role='combobox']][1]//*[@role='combobox']",
                          30, induk or self.d, f'dropdown berlabel "{label}" tidak ditemukan')
        self.klik(kotak)
        o = self.tunggu(lambda: (self.opsi(pola_opsi) or [None])[0], 30,
                        f'opsi "{pola_opsi}" tidak ada di dropdown "{label}"')
        self.klik(o)
        self.tunggu(lambda: not self.cari("//*[@role='listbox']"), 10, 'dropdown tidak tertutup')
        time.sleep(0.5)

    def pilih_autocomplete(self, kotak: WebElement, kata: str, pola_opsi: str):
        """MUI Autocomplete berbasis API: ketik kata kunci, tunggu opsi yang cocok, pilih."""
        self.ketik(kotak, kata)
        o = self.tunggu(lambda: (self.opsi(pola_opsi) or [None])[0], 30,
                        f'opsi "{pola_opsi}" tidak muncul setelah mengetik "{kata}"')
        self.klik(o)
        time.sleep(0.5)

    def pilih_dari_daftar(self, kotak: WebElement, pola_opsi: str = '') -> str:
        """
        MUI Autocomplete yang daftarnya muncul saat diklik (tanpa mengetik). Pilih opsi yang
        cocok dengan `pola_opsi`, atau opsi pertama bila pola kosong. Mengembalikan labelnya.
        """
        self.tunggu(lambda: kotak.is_enabled(), 30, 'dropdown masih nonaktif')
        self.klik(kotak)
        o = self.tunggu(lambda: ([x for x in self.opsi(pola_opsi or '.') if _teks(x)] or [None])[0], 30,
                        f'opsi "{pola_opsi or "(pertama)"}" tidak muncul')
        label = _teks(o)
        self.klik(o)
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

    # ------------------------------------------------------------------ sesi

    def login(self, username: str):
        log(f'Login sebagai {username}')
        self.d.delete_all_cookies()
        self.d.get(self.base_url + '/login')
        kotak = self.satu("//input[@id='input-username']", 60)
        self.ketik(kotak, username)
        self.klik_xpath("//*[@id='login-button']")
        try:
            self.tunggu(lambda: '/login' not in self.d.current_url, 60, 'masih di halaman login')
        except GagalLangkah:
            pesan = ''
            try:
                alert = self.d.switch_to.alert
                pesan = alert.text
                alert.dismiss()
            except WebDriverException:
                pass
            raise GagalLangkah(f'Login {username} gagal. {pesan or "Mungkin butuh sandi/OTP."}')
        self.buffering()

    def logout(self):
        """Tombol header "Logout" → popup "Apakah anda yakin ingin keluar?" → Ya."""
        try:
            tombol = self.cari(self.tombol('Logout'))
            if tombol:
                self.klik(tombol[0])
                self.konfirmasi_bila_ada(r'yakin ingin keluar', 'Ya', 10)
                self.tunggu(lambda: '/login' in self.d.current_url, 30, 'tidak kembali ke halaman login')
        except GagalLangkah:
            pass
        # Jaring pengaman: sesi berikutnya harus mulai bersih apa pun yang terjadi di atas.
        self.d.delete_all_cookies()
        log('Logout')

    # ------------------------------------------------------------------ To Do List

    def buka_tugas(self, customer: str, url_cadangan: str, batas: float = 150) -> bool:
        """
        Dashboard → To Do List / Approval List → Filter "Nama Customer" → Apply → "Go to task".

        Daftarnya berisi ratusan tugas dan tidak diurutkan terbaru-dulu, jadi barisnya dicari
        lewat filter. Tugas dibuat backend secara asinkron; bila belum muncul, dicoba ulang.
        Setelah habis batas, jatuh ke URL cadangan supaya run tidak berhenti hanya karena
        dashboard terlambat.
        """
        baris_xp = (f"//button[normalize-space()='Go to task']"
                    f"/parent::*[*[normalize-space()={xp_literal(customer)}]]")
        akhir = time.time() + batas
        while time.time() < akhir:
            self.buka('/')
            self.satu("//*[normalize-space(text())='To Do List' or normalize-space(text())='Approval List']", 60)
            # Tombol Filter pertama milik To Do List (yang kedua milik Inquiry Data).
            self.klik_xpath("(//button[normalize-space()='Filter'])[1]", 30)
            pop = self.satu("//*[contains(@class,'MuiPopover-root')]", 15)
            self.ketik(self.satu(".//input[@placeholder='example: proses..']", 15, pop), customer)
            self.klik_xpath(self.tombol('Apply', pop), 15, induk=pop)
            self.buffering()
            time.sleep(1.5)
            baris = self.cari(baris_xp)
            if baris:
                self.klik(baris[0].find_element(By.XPATH, ".//button[normalize-space()='Go to task']"))
                self.tunggu(lambda: self.d.current_url.rstrip('/') != self.base_url, 60, 'Go to task tidak berpindah halaman')
                self.buffering()
                log(f'  Go to task → {self.d.current_url.replace(self.base_url, "")}')
                return True
            log('  tugas belum muncul di dashboard, coba lagi 15 detik lagi')
            time.sleep(15)
        log(f'  tugas tidak ditemukan di dashboard, buka langsung {url_cadangan}')
        self.buka(url_cadangan)
        return False

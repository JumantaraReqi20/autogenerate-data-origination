from selenium.common.exceptions import WebDriverException

from core.lokator import Lokator
from core.util import GagalLangkah, log
from .base import Halaman


class LoginPage(Halaman):
    input_username = Lokator("//input[@id='input-username']", 'kotak username')
    tombol_login = Lokator("//*[@id='login-button']", 'tombol login')
    tombol_logout = Lokator("//button[normalize-space()='Logout']", 'tombol Logout')

    def login(self, username: str):
        los = self.los
        log(f'Login sebagai {username}')
        los.d.delete_all_cookies()
        los.d.get(los.base_url + '/login')
        self.input_username.ketik(username)
        self.tombol_login.klik()
        try:
            los.tunggu(lambda: '/login' not in los.d.current_url, 60, 'masih di halaman login')
        except GagalLangkah:
            pesan = ''
            try:
                alert = los.d.switch_to.alert
                pesan = alert.text
                alert.dismiss()
            except WebDriverException:
                pass
            raise GagalLangkah(f'Login {username} gagal. {pesan or "Mungkin butuh sandi/OTP."}')
        los.buffering()

    def logout(self):
        """Tombol header "Logout" → popup "Apakah anda yakin ingin keluar?" → Ya."""
        los = self.los
        try:
            tombol = self.tombol_logout.semua()
            if tombol:
                los.klik(tombol[0])
                los.konfirmasi_bila_ada(r'yakin ingin keluar', 'Ya', 10)
                los.tunggu(lambda: '/login' in los.d.current_url, 30, 'tidak kembali ke halaman login')
        except GagalLangkah:
            pass
        # Jaring pengaman: sesi berikutnya harus mulai bersih apa pun yang terjadi di atas.
        los.d.delete_all_cookies()
        log('Logout')

"""Login & logout untuk setiap peran yang dipakai alur Origination. Hanya membaca; tidak membuat data."""
import pytest

from pages import LoginPage

PERAN = ['staff_bisnis', 'tl_bisnis', 'kadiv_bisnis', 'tl_depi', 'kadiv_depi', 'tl_dh', 'kadiv_dh']


@pytest.mark.parametrize('peran', PERAN)
def test_login_lalu_logout(los, konfig, peran):
    login = los.halaman(LoginPage)

    login.login(konfig['akun'][peran])
    assert '/login' not in los.d.current_url
    assert login.tombol_logout.satu(30), 'tombol Logout tidak tampil setelah login'

    login.logout()
    assert '/login' in los.d.current_url, f'tidak kembali ke halaman login, sekarang di {los.d.current_url}'

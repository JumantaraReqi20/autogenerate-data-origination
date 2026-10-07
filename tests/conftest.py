"""
Fixture bersama untuk automation testing.

- `konfig`         isi config.json (base_url, akun, data).
- `los`            satu browser untuk seluruh sesi pytest; tiap login menghapus cookie lebih dulu.
- `masuk_sebagai`  login sebagai peran di config.json → akun, logout otomatis setelah test.

Saat sebuah test gagal, screenshot + HTML halaman disimpan di runs/artefak/tests/ SEBELUM
fixture dibereskan (sebelum logout), jadi yang terekam adalah halaman tempat test gagal.
"""
import re

import pytest

from core.config import ARTEFAK, baca_konfig
from core.driver import Los
from pages import LoginPage


def pytest_addoption(parser):
    parser.addoption('--headless', action='store_true', help='jalankan browser tanpa jendela')


@pytest.fixture(scope='session')
def konfig() -> dict:
    return baca_konfig()


@pytest.fixture(scope='session')
def los(konfig, pytestconfig):
    browser = Los(konfig['base_url'], ARTEFAK / 'tests', headless=pytestconfig.getoption('headless'))
    yield browser
    browser.tutup()


@pytest.fixture
def masuk_sebagai(los, konfig):
    login = los.halaman(LoginPage)

    def masuk(peran: str) -> Los:
        login.login(konfig['akun'][peran])
        return los

    yield masuk
    login.logout()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    laporan = yield
    if laporan.when == 'call' and laporan.failed and 'los' in item.funcargs:
        bukti = item.funcargs['los'].simpan_bukti(re.sub(r'[^\w.-]+', '_', item.name))
        laporan.sections.append(('bukti', str(bukti)))
    return laporan

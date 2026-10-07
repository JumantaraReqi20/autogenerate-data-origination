"""Dashboard: daftar tugas per peran. Hanya membaca; tidak membuat data."""
import pytest

from pages import DashboardPage


@pytest.mark.parametrize('peran', ['staff_bisnis', 'tl_bisnis'])
def test_dashboard_menampilkan_daftar_tugas(masuk_sebagai, peran):
    los = masuk_sebagai(peran)
    dashboard = los.halaman(DashboardPage)

    los.buka('/')
    assert dashboard.judul_daftar_tugas.satu(60)
    assert dashboard.tombol_filter.ada(), 'tombol Filter To Do List tidak tampil'

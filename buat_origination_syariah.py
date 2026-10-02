"""
Otomasi pembuatan data: satu Origination dari nol sampai berstatus "Completed" —
skenario pembiayaan SYARIAH.

    .venv\\Scripts\\python buat_origination_syariah.py              # run baru, browser terlihat
    .venv\\Scripts\\python buat_origination_syariah.py --lanjut     # teruskan run yang gagal di tengah
    .venv\\Scripts\\python buat_origination_syariah.py --headless   # tanpa jendela browser

Alurnya (12 fase, 7 akun) SAMA dengan skenario konven di buat_origination.py; di kode, alur
Origination tidak bercabang menurut segmen. Yang berbeda hanya form "Add New Fasilitas
Pembiayaan", yang diisi oleh `isi_fasilitas_syariah` di bawah. Akun pun sama: Segmen Pembiayaan
di form itu bisa diganti bebas walau terisi bawaan dari divisi user.

Nilai isian ada di config.json → data.syariah. Jejak run disimpan terpisah (jejak_syariah.json).
"""
import re

from selenium.webdriver.common.by import By

import buat_origination as alur
from los import GagalLangkah, Los, log

SYARIAH = alur.DATA['syariah']


def isi_fasilitas_syariah(los: Los, form):
    """
    Segmen Pembiayaan → Syariah, lalu Skema pembiayaan, Tujuan Pembiayaan, dan sub-form skema.

    Begitu segmen Syariah, "Produk" berganti label menjadi "Skema pembiayaan" (opsi dari parameter
    productSyariah) dan "Nominal Pengajuan" hilang, diganti sub-form per skema (ModalFormFacility.tsx,
    SyariahForm.tsx): Musyarakah = Syirkah SMI + Syirkah Nasabah; Murabahah = Objek + Harga Beli;
    Qardh = Jumlah pinjaman; dst. Label sub-form bisa diganti dari konfigurasi skema di DB, jadi
    sub-form diisi GENERIK lewat `isi_field_wajib_kosong`.
    """
    # Segmen sudah terisi bawaan divisi, jadi placeholder-nya tak terlihat: dicari lewat label.
    los.pilih_select_berlabel('Segmen Pembiayaan', SYARIAH['segmen'], induk=form)
    los.buffering()
    los.pilih_select('Choose Skema pembiayaan', SYARIAH['skema'], induk=form)
    los.buffering()
    if los.cari(".//*[contains(normalize-space(), 'Skema belum dimapping')]", form):
        raise GagalLangkah(f'Skema "{SYARIAH["skema"]}" belum dimapping di lingkungan ini (pesan aplikasi: '
                           '"Skema belum dimapping, mohon kontak Admin"). Pilih skema lain di config.json.')
    los.ketik(los.satu(".//input[@placeholder='Tujuan Pembiayaan']", 15, form), SYARIAH['tujuan_pembiayaan'])
    log(f'  fasilitas syariah: skema {SYARIAH["skema"]}')
    isi_field_wajib_kosong(los, form, SYARIAH['teks_objek'])


def isi_field_wajib_kosong(los: Los, form, teks: str):
    """
    Isi setiap field bertanda * di `form` yang masih kosong dan bisa diketik: nominal acak bila
    wadahnya memuat pilihan mata uang (IDR/USD), selain itu `teks`. Dropdown, autocomplete,
    tanggal, dan field nonaktif (mis. "Mitra Syarik SMI", "Total Syirkah") dilewati.
    """
    xp_isian = (".//input[(not(@type) or @type='text' or @type='number')"
                " and not(@disabled) and not(@readonly) and not(@aria-hidden='true')"
                " and not(@role='combobox') and not(contains(@placeholder, 'DD/MM'))"
                " and not(contains(@class, 'MuiSelect-nativeInput'))] | .//textarea[not(@disabled)]")
    for bintang in los.cari(".//*[normalize-space(text())='*']", form):
        label = bintang.find_element(By.XPATH, '..')
        nama = re.sub(r'\s*\*\s*$', '', re.sub(r'\s+', ' ', label.text)).strip()
        wadah = label.find_element(By.XPATH, './ancestor::div[.//input or .//textarea][1]')
        isian = [i for i in los.cari(xp_isian, wadah) if not i.get_attribute('value')]
        if not isian:
            continue
        mata_uang = any(re.search(r'^(IDR|USD)$', c.text.strip())
                        for c in wadah.find_elements(By.XPATH, ".//*[@role='combobox']"))
        nilai = alur.nominal_acak() if mata_uang else teks
        los.ketik(isian[0], nilai)
        log(f'    {nama}: {alur.rupiah(nilai) if mata_uang else nilai}')
        los.buffering(10)


if __name__ == '__main__':
    alur.main(isi_fasilitas=isi_fasilitas_syariah, skenario='Syariah', berkas_jejak='jejak_syariah.json')

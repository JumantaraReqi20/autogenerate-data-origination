"""
Skenario pembiayaan. Alur 12 fase sama untuk semua skenario (alur Origination tidak bercabang
menurut segmen); yang berbeda hanya fasilitas yang ditambahkan di fase 1.
"""
from collections.abc import Callable
from dataclasses import dataclass

from pages import FormFasilitasModal

# Cara mengisi form "Add New Fasilitas Pembiayaan" per jenis fasilitas, dari config.json → data.
PENGISI_FASILITAS: dict[str, Callable[[FormFasilitasModal, dict], None]] = {
    'konven': lambda form, data: form.isi_konven(data['produk']),
    'syariah': lambda form, data: form.isi_syariah(
        data['syariah']['segmen'], data['syariah']['skema'],
        data['syariah']['tujuan_pembiayaan'], data['syariah']['teks_objek']),
}


@dataclass(frozen=True)
class Skenario:
    label: str
    fasilitas: tuple[str, ...]   # kunci PENGISI_FASILITAS, berurutan (satu fasilitas per item)
    berkas_jejak: str            # bawaan, relatif ke runs/


SKENARIO = {
    'konven': Skenario('Konven', ('konven',), 'jejak.json'),
    'syariah': Skenario('Syariah', ('syariah',), 'jejak_syariah.json'),
    # Konven sengaja diisi lebih dulu: form fasilitas baru terisi Segmen bawaan divisi user, dan
    # pengisi konven mengandalkan dropdown "Choose Produk" yang hanya ada bila segmennya bukan Syariah.
    'konven-syariah': Skenario('Konven + Syariah', ('konven', 'syariah'), 'jejak_konven_syariah.json'),
}

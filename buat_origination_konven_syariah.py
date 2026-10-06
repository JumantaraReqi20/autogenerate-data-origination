"""
Otomasi pembuatan data: satu Origination dari nol sampai berstatus "Completed" —
skenario DUA fasilitas pembiayaan dalam satu pipeline: satu KONVEN dan satu SYARIAH.

    .venv\\Scripts\\python buat_origination_konven_syariah.py              # run baru, browser terlihat
    .venv\\Scripts\\python buat_origination_konven_syariah.py --lanjut     # teruskan run yang gagal di tengah
    .venv\\Scripts\\python buat_origination_konven_syariah.py --headless   # tanpa jendela browser

Alurnya (12 fase, 7 akun) SAMA dengan buat_origination.py; yang berbeda hanya fase 1, yang
menambah dua fasilitas berturut-turut lewat Add New. Pengisinya dipakai ulang dari skenario
Konven dan Syariah, jadi nilai isian sama: data.produk untuk konven, data.syariah untuk syariah.

Konven sengaja diisi lebih dulu: form fasilitas baru terisi Segmen bawaan divisi user, dan
pengisi konven mengandalkan dropdown "Choose Produk" yang hanya ada bila segmennya bukan Syariah.

Go To Origination tetap menghasilkan SATU origination (FAS-xxxxx) per pipeline, berapa pun
fasilitasnya. Jejak run disimpan terpisah (jejak_konven_syariah.json).
"""
import buat_origination as alur
from buat_origination_syariah import isi_fasilitas_syariah

if __name__ == '__main__':
    alur.main(isi_fasilitas=[alur.isi_fasilitas_konven, isi_fasilitas_syariah],
              skenario='Konven + Syariah', berkas_jejak='jejak_konven_syariah.json')

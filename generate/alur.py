"""
Urutan 12 fase pembuatan satu Origination sampai "Completed". Satu fase = satu akun.

Fase yang selesai dicatat di berkas jejak; --lanjut melewatinya, jadi kegagalan di fase Kadiv DH
tidak memaksa membuat customer baru dari awal.
"""
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.config import ARTEFAK, BERKAS_PDF
from core.data_uji import nama_customer_baru
from core.driver import Los
from core.util import GagalLangkah, log
from pages import (
    CreatePipelinePage,
    DashboardPage,
    LoginPage,
    OriginationListPage,
    PembahasanPage,
    PipelineDetailPage,
    PipelineListPage,
)
from pages.origination import RUTE_ORIGINATION

from .jejak import Jejak
from .skenario import PENGISI_FASILITAS, Skenario


@dataclass
class Run:
    los: Los
    data: dict
    jejak: Jejak
    skenario: Skenario
    nama_customer: str | None = None
    berkas_pdf: str = str(BERKAS_PDF)


# ============================================================================ pipeline

def fase_buat_pipeline(run: Run):
    los, data = run.los, run.data
    customer = run.nama_customer or nama_customer_baru()
    log(f'  customer: {customer}')

    daftar = los.halaman(PipelineListPage)
    daftar.buka()
    daftar.create_new_customer(data['kata_pencarian'])

    create = los.halaman(CreatePipelinePage)
    create.isi(data['institution_type'], customer, data['gam_cari'], data['gam_opsi'])
    pipeline_id = create.save()
    run.jejak.simpan(customer=customer, pipeline_id=pipeline_id)
    log(f'  pipeline: {pipeline_id}')

    detail = los.halaman(PipelineDetailPage)
    detail.isi_data_pipeline(data)
    detail.simpan_data_pipeline()
    for jenis in run.skenario.fasilitas:
        detail.tambah_fasilitas(lambda form, jenis=jenis: PENGISI_FASILITAS[jenis](form, data))


def fase_submit_pipeline(run: Run):
    """
    Submit → Comment → Save → Success → Close.

    Fase tersendiri supaya --lanjut tidak membuat customer baru bila yang gagal hanya Submit.
    Server dev kadang menjawab "timeout of 60000ms exceeded" padahal Submit-nya tetap diproses;
    karena itu sebelum tiap percobaan dicek dulu apakah tombol Submit masih ada.
    """
    detail = run.los.halaman(PipelineDetailPage)
    for percobaan in range(1, 4):
        detail.buka(run.jejak['pipeline_id'])
        detail.tunggu_termuat()
        if detail.sudah_submit():
            log('  tombol Submit sudah tidak ada — pipeline sudah ter-Submit')
            return
        try:
            detail.submit(run.data['komentar_submit'])
            return
        except GagalLangkah as e:
            if 'timeout' not in str(e).lower() or percobaan == 3:
                raise
            log(f'  server timeout saat Submit (percobaan {percobaan}), cek ulang 20 detik lagi')
            time.sleep(20)


def fase_tl_approve_pipeline(run: Run):
    j = run.jejak.baca()
    run.los.halaman(DashboardPage).buka_tugas(j['customer'], PipelineDetailPage.rute(j['pipeline_id']))
    run.los.halaman(PipelineDetailPage).approve(run.data['komentar'])


def fase_go_to_origination(run: Run):
    los, data = run.los, run.data
    j = run.jejak.baca()
    customer = j['customer']
    detail = los.halaman(PipelineDetailPage)
    los.halaman(DashboardPage).buka_tugas(customer, detail.rute(j['pipeline_id']))
    if '/pipeline/' not in los.d.current_url:
        detail.buka(j['pipeline_id'])

    notif = detail.go_to_origination()
    notif.pilih_staff(0, data['staff_depi_cari'], data['staff_depi_opsi'])
    notif.pilih_staff(1, data['staff_dh_cari'], data['staff_dh_opsi'])
    notif.save(data['komentar'])
    los.tunggu(lambda: RUTE_ORIGINATION in los.d.current_url, 60, 'tidak pindah ke Origination List')

    # Bucket baru muncul 14–67 detik setelah Go To Origination (diproses asinkron).
    log('  menunggu origination muncul di Origination List...')
    daftar = los.halaman(OriginationListPage)
    fas_id = daftar.fas_id(daftar.tunggu_baris(customer, 300))
    run.jejak.simpan(fas_id=fas_id)
    log(f'  origination: {fas_id}')


# ============================================================================ Pembahasan Origination

def fase_staff_pembahasan(run: Run):
    los = run.los
    los.halaman(OriginationListPage).buka_detail(run.jejak['customer'])
    pembahasan = los.halaman(PembahasanPage)
    pembahasan.buka_stepper()
    pembahasan.isi_tanggal_entry()
    pembahasan.isi_dokumen_wajib(run.berkas_pdf)
    for _ in range(int(run.data.get('other_document_jumlah', 0))):
        pembahasan.tambah_other_document(run.data, run.berkas_pdf)
    pembahasan.kirim('Submit', 'Submit')


def fase_pembahasan(isi_dokumen: bool, tombol_bawah: str, tombol_konfirmasi: str) -> Callable[[Run], None]:
    """Fase TL/Kadiv: Go to task → (isi dokumen wajib) → Submit/Approve → konfirmasi."""
    def kerja(run: Run):
        j = run.jejak.baca()
        run.los.halaman(DashboardPage).buka_tugas(j['customer'], PembahasanPage.rute(j['fas_id']))
        pembahasan = run.los.halaman(PembahasanPage)
        pembahasan.buka_stepper()
        if isi_dokumen:
            pembahasan.isi_dokumen_wajib(run.berkas_pdf)
        pembahasan.kirim(tombol_bawah, tombol_konfirmasi)
    return kerja


def fase_cek_completed(run: Run):
    j = run.jejak.baca()
    status = run.los.halaman(OriginationListPage).tunggu_completed(j['fas_id'])
    log(f'SELESAI: {j["customer"]} / {j["pipeline_id"]} / {j["fas_id"]} berstatus {status}')


# ============================================================================ urutan

FASE: list[tuple[str, str, Callable[[Run], None]]] = [
    ('1-10  Staff Bisnis: customer, pipeline, fasilitas', 'staff_bisnis', fase_buat_pipeline),
    ('11    Staff Bisnis: Submit pipeline', 'staff_bisnis', fase_submit_pipeline),
    ('13-14 TL Bisnis: approve pipeline', 'tl_bisnis', fase_tl_approve_pipeline),
    ('16-17 Staff Bisnis: Go To Origination', 'staff_bisnis', fase_go_to_origination),
    ('18    Staff Bisnis: isi Pembahasan Origination + Other Document, Submit', 'staff_bisnis', fase_staff_pembahasan),
    ('20    TL Bisnis: Submit, Send', 'tl_bisnis', fase_pembahasan(False, 'Submit', 'Send')),
    ('21    Kadiv Bisnis: Approve', 'kadiv_bisnis', fase_pembahasan(False, 'Approve', 'Approve & Kirim ke LPS')),
    ('23    TL DEPI: isi dokumen, Submit', 'tl_depi', fase_pembahasan(True, 'Submit', 'Send')),
    ('25    Kadiv DEPI: Approve', 'kadiv_depi', fase_pembahasan(False, 'Approve', 'Approve & Kirim ke LPS')),
    ('27    TL DH: isi dokumen, Submit', 'tl_dh', fase_pembahasan(True, 'Submit', 'Send')),
    ('29    Kadiv DH: Approve', 'kadiv_dh', fase_pembahasan(False, 'Approve', 'Approve & Kirim ke LPS')),
    ('30    Cek status Completed', 'staff_bisnis', fase_cek_completed),
]


def jalankan(konfig: dict, skenario: Skenario, berkas_jejak: Path, *, lanjut: bool = False,
             headless: bool = False, sampai: int = len(FASE), nama_customer: str | None = None) -> bool:
    """Jalankan fase 1..`sampai`. Mengembalikan False bila gagal (bukti tersimpan di runs/artefak)."""
    jejak = Jejak(berkas_jejak)
    if not lanjut:
        jejak.hapus()
    log(f'Skenario pembiayaan: {skenario.label} (jejak: {berkas_jejak.name})')

    los = Los(konfig['base_url'], ARTEFAK, headless=headless)
    run = Run(los, konfig['data'], jejak, skenario, nama_customer)
    login = los.halaman(LoginPage)
    mulai = time.time()
    try:
        for no, (nama, peran, kerja) in enumerate(FASE[:sampai], start=1):
            if nama in jejak.fase_selesai():
                log(f'--- lewati (sudah selesai): {nama}')
                continue
            log(f'=== [{no}/{len(FASE)}] {nama} ===')
            login.login(konfig['akun'][peran])
            kerja(run)
            login.logout()
            jejak.tandai_selesai(nama)
        durasi = int(time.time() - mulai)
        log(f'Total waktu: {durasi // 60} menit {durasi % 60} detik')
        log(f'Jejak: {json.dumps({k: v for k, v in jejak.baca().items() if k != "fase_selesai"}, ensure_ascii=False)}')
        los.tutup()
        return True
    except Exception as e:  # noqa: BLE001 — semua kegagalan dilaporkan dengan bukti yang sama
        bukti = los.simpan_bukti('gagal')
        log(f'GAGAL: {e}')
        log(f'Bukti: {bukti}')
        log('Perbaiki penyebabnya lalu jalankan ulang dengan --lanjut untuk meneruskan dari fase ini.')
        if not headless and sys.stdin.isatty():
            input('Browser dibiarkan terbuka untuk diperiksa. Tekan Enter untuk menutup...')
        los.tutup()
        return False

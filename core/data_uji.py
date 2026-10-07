import random

PERUSAHAAN = [
    'Garuda Nusantara', 'Telkom Sinergi', 'Pertamina Energi', 'Astra Mandiri', 'Indofood Prima',
    'Unilever Nusa', 'Semen Gresik Raya', 'Wijaya Karya Infra', 'Jasa Marga Tol', 'Bukit Asam Daya',
    'Angkasa Pura Logistik', 'Pelindo Samudra', 'Waskita Beton', 'Adhi Karya Persada', 'Hutama Karya Jaya',
]


def kode_acak() -> str:
    return ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=4))


def nama_customer(dasar: str, kode: str) -> str:
    return f'{dasar} Oto {kode}'


def nama_customer_baru() -> str:
    """
    Huruf pertama kapital, TIDAK diawali PT/TBK/dll. dan tidak diakhiri Persero/TBK
    (CreateNewPipelineCustom.constant.ts). Akhiran unik supaya barisnya bisa dicari di
    To Do List / Origination List tanpa tertukar dengan data lain.
    """
    return nama_customer(random.choice(PERUSAHAAN), kode_acak())


def nominal_acak() -> str:
    """1–99 milyar dengan sisa jutaan supaya tidak selalu bulat."""
    return str(random.randint(1, 99) * 1_000_000_000 + random.randint(0, 899) * 1_000_000)


def nomor_dokumen_acak() -> str:
    return str(random.randint(100_000, 999_999))


def rupiah(angka: str) -> str:
    return 'Rp' + f'{int(angka):,}'.replace(',', '.')

import re
import time
from datetime import date

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement


def log(pesan: str):
    print(f'[{time.strftime("%H:%M:%S")}] {pesan}', flush=True)


def hari_ini() -> str:
    return date.today().strftime('%d/%m/%Y')


class GagalLangkah(Exception):
    """Kegagalan yang pesannya sudah cukup jelas untuk dibaca manusia."""


def teks(el: WebElement) -> str:
    try:
        return re.sub(r'\s+', ' ', el.text or '').strip()
    except StaleElementReferenceException:
        return ''


def tampil(el: WebElement) -> bool:
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


def eksak(s: str) -> str:
    """Regex cocok-persis (case-insensitive) untuk label opsi."""
    return rf'^\s*{re.escape(s)}\s*$'

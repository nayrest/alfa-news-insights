"""RAG по аналитике Альфа-Банка: чанки + поиск BM25 на чистом Python.

Без эмбеддингов, чтобы не зависеть от моделей вне разрешённого списка.
Материалы кладутся в ALFA_ANALYTICS_DIR как .pdf, .txt или .md.
"""

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-zа-я0-9]+", re.IGNORECASE)
_STOP = set(
    "и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от меня "
    "еще нет о из ему теперь когда даже ну вдруг ли если уже или ни быть был него до вас нибудь опять уж вам ведь "
    "там потом себя ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без будто чего раз "
    "тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь этом один почти мой тем чтобы "
    "нее сейчас были куда зачем всех никогда можно при наконец два об другой хоть после над больше тот через эти "
    "нас про всего них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть том нельзя "
    "такой им более всегда конечно всю между также это г гг т р млрд млн".split()
)


def tokenize(text: str) -> list[str]:
    """Слова в нижнем регистре, обрезанные до 6 букв — грубая замена стеммингу для русского."""
    words = _WORD_RE.findall(text.lower().replace("ё", "е"))
    return [w[:6] for w in words if w not in _STOP and len(w) > 1]


@dataclass
class Chunk:
    chunk_id: str  # например A3
    doc: str  # название материала
    text: str


MIN_TEXT_CHARS = 200  # меньше — считаем, что извлечь текст не удалось


def _pdf_pypdf(path: Path) -> str:
    from pypdf import PdfReader

    return "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def _pdf_pdftotext(path: Path) -> str:
    """poppler-utils: лучше справляется с вёрсткой аналитических отчётов, чем pypdf."""
    import shutil
    import subprocess

    if not shutil.which("pdftotext"):
        return ""
    res = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        timeout=60,
        check=False,
    )
    return res.stdout.decode("utf-8", errors="ignore")


def _pdf_ocr(path: Path, dpi: int = 200) -> str:
    """OCR для PDF из картинок: pdftoppm рендерит страницы, Tesseract (rus+eng) распознаёт.

    Это не LLM, лимит токенов не тратится. Страницы распознаются параллельно.
    """
    import os
    import shutil
    import subprocess
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["pdftoppm", "-r", str(dpi), "-png", str(path), os.path.join(tmp, "p")],
            capture_output=True,
            timeout=300,
            check=False,
        )
        pages = sorted(Path(tmp).glob("p*.png"))
        env = {**os.environ, "OMP_THREAD_LIMIT": "1"}  # один поток на процесс — параллелим сами

        def ocr(img: Path) -> str:
            res = subprocess.run(
                ["tesseract", str(img), "stdout", "-l", "rus+eng", "--psm", "3"],
                capture_output=True,
                timeout=180,
                check=False,
                env=env,
            )
            return res.stdout.decode("utf-8", errors="ignore")

        with ThreadPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as pool:
            texts = list(pool.map(ocr, pages))
    return "\n\n".join(texts)


def read_document(path: Path) -> tuple[str, str]:
    """Возвращает (текст, способ извлечения)."""
    if path.suffix.lower() != ".pdf":
        return path.read_text(encoding="utf-8", errors="ignore"), "text"
    best, method = "", "none"
    for name, extractor in (("pdftotext", _pdf_pdftotext), ("pypdf", _pdf_pypdf), ("ocr", _pdf_ocr)):
        try:
            text = extractor(path)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s не смог прочитать %s: %s", name, path.name, exc)
            continue
        if len(text.strip()) > len(best.strip()):
            best, method = text, name
        if len(best.strip()) >= MIN_TEXT_CHARS:
            break
    return best, method


def split_chunks(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        p = re.sub(r"\s+", " ", p)
        if len(buf) + len(p) + 1 > max_chars and buf:
            chunks.append(buf)
            buf = ""
        while len(p) > max_chars:  # очень длинный абзац режем по предложениям
            cut = p.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > max_chars // 3 else max_chars
            chunks.append(p[:cut].strip())
            p = p[cut:].strip()
        buf = f"{buf} {p}".strip()
    if buf:
        chunks.append(buf)
    return chunks


class AnalyticsIndex:
    def __init__(self, chunks: list[Chunk], files: list[dict] | None = None):
        self.chunks = chunks
        self.files = files or []  # диагностика: сколько текста и фрагментов дал каждый файл
        self.by_id = {c.chunk_id: c for c in chunks}
        self._tokens = [tokenize(f"{c.doc} {c.text}") for c in chunks]
        self._tf = [Counter(t) for t in self._tokens]
        n = len(chunks) or 1
        df = Counter(term for toks in self._tokens for term in set(toks))
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self._avgdl = sum(len(t) for t in self._tokens) / n if chunks else 1.0

    @classmethod
    def from_dir(cls, directory: str) -> "AnalyticsIndex":
        chunks: list[Chunk] = []
        report: list[dict] = []
        base = Path(directory)
        files = sorted(p for p in base.glob("*") if p.suffix.lower() in (".pdf", ".txt", ".md")) if base.is_dir() else []
        # Если для PDF рядом лежит .txt с тем же именем (ручная конвертация) — берём его
        stems_with_txt = {p.stem for p in files if p.suffix.lower() in (".txt", ".md")}
        for path in files:
            if path.suffix.lower() == ".pdf" and path.stem in stems_with_txt:
                continue
            try:
                text, method = read_document(path)
            except Exception as exc:  # noqa: BLE001
                log.warning("Не удалось прочитать %s: %s", path.name, exc)
                report.append({"file": path.name, "chars": 0, "chunks": 0, "method": "error", "error": str(exc)[:200]})
                continue
            if method == "ocr" and len(text.strip()) >= MIN_TEXT_CHARS:
                # Кэшируем распознанный текст рядом с PDF: OCR медленный, повторять при каждом старте незачем.
                # При следующем запуске возьмётся .txt (см. stems_with_txt выше).
                try:
                    path.with_suffix(".txt").write_text(text, encoding="utf-8")
                    log.info("OCR %s: %s симв., сохранено в %s", path.name, len(text), path.with_suffix(".txt").name)
                except OSError as exc:
                    log.warning("Не удалось сохранить OCR-текст для %s: %s", path.name, exc)
            parts = split_chunks(text)
            for part in parts:
                chunks.append(Chunk(chunk_id=f"A{len(chunks) + 1}", doc=path.stem, text=part))
            n_chars = len(text.strip())
            report.append({"file": path.name, "chars": n_chars, "chunks": len(parts), "method": method})
            if n_chars < MIN_TEXT_CHARS:
                log.warning(
                    "Из %s почти не извлёкся текст (%s симв.) — вероятно, PDF из картинок; "
                    "положите рядом %s.txt с текстом",
                    path.name,
                    n_chars,
                    path.stem,
                )
        log.info("Аналитика Альфа-Банка: %s файлов, %s фрагментов", len(files), len(chunks))
        return cls(chunks, report)

    @property
    def documents(self) -> list[str]:
        return sorted({c.doc for c in self.chunks})

    def search(self, query: str, k: int = 3, k1: float = 1.5, b: float = 0.75) -> list[dict]:
        q = tokenize(query)
        if not q or not self.chunks:
            return []
        scores = []
        for i, tf in enumerate(self._tf):
            dl = len(self._tokens[i]) or 1
            s = 0.0
            for term in q:
                f = tf.get(term)
                if f:
                    s += self._idf.get(term, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self._avgdl))
            if s > 0:
                scores.append((s, i))
        scores.sort(reverse=True)
        return [
            {"id": self.chunks[i].chunk_id, "doc": self.chunks[i].doc, "text": self.chunks[i].text, "score": round(s, 3)}
            for s, i in scores[:k]
        ]


_index: AnalyticsIndex | None = None


def get_index() -> AnalyticsIndex:
    global _index
    if _index is None:
        from app.config import get_settings

        _index = AnalyticsIndex.from_dir(get_settings().alfa_analytics_dir)
    return _index


def reload_index() -> AnalyticsIndex:
    global _index
    _index = None
    return get_index()

# utils/pdf_tools.py
import io
import subprocess
from typing import Tuple

# Intento con pikepdf si está disponible (pip install pikepdf)
try:
    import pikepdf
    HAS_PIKEPDF = True
except Exception:
    HAS_PIKEPDF = False

TARGET_BYTES = 1 * 1024 * 1024   # 1 MB (solo informativo)
MAX_BYTES    = 5 * 1024 * 1024   # 5 MB (límite duro)

def _compress_with_pikepdf(pdf_bytes: bytes) -> Tuple[bytes, bool]:
    """Optimiza streams con pikepdf. Devuelve (bytes, hubo_mejora)."""
    if not HAS_PIKEPDF:
        return pdf_bytes, False
    try:
        inbuf = io.BytesIO(pdf_bytes)
        outbuf = io.BytesIO()
        with pikepdf.open(inbuf) as pdf:
            # optimize/linearize suele reducir tamaño sin romper estructura
            pdf.save(outbuf, linearize=True, optimize_version=True, fix_metadata=True)
        out = outbuf.getvalue()
        return (out, len(out) < len(pdf_bytes))
    except Exception:
        return pdf_bytes, False

def _compress_with_qpdf(pdf_bytes: bytes) -> Tuple[bytes, bool]:
    """Fallback con qpdf (requiere qpdf instalado en el OS)."""
    try:
        with open('/tmp/_in.pdf', 'wb') as f:
            f.write(pdf_bytes)
        cmd = [
            "qpdf",
            "--linearize",
            "--object-streams=generate",
            "--stream-data=compress",
            "/tmp/_in.pdf",
            "/tmp/_out.pdf"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open('/tmp/_out.pdf', 'rb') as f:
            out = f.read()
        return (out, len(out) < len(pdf_bytes))
    except Exception:
        return pdf_bytes, False

def compress_best_effort(pdf_bytes: bytes) -> Tuple[bytes, int, int]:
    """
    Intenta comprimir lo máximo posible. Orden:
    1) pikepdf → 2) qpdf → si nada mejora, deja original.
    Retorna: (bytes_finales, size_inicial, size_final)
    """
    original = len(pdf_bytes)
    best = pdf_bytes

    cand, improved = _compress_with_pikepdf(best)
    if improved:
        best = cand

    cand, improved = _compress_with_qpdf(best)
    if improved:
        best = cand

    return best, original, len(best)
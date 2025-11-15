import hashlib
from typing import Dict, List


def _normalize_list(values: List[str]) -> List[str]:
    return sorted([v.strip() for v in values if isinstance(v, str) and v.strip()])


def compute_meli_item_hash(normalized: Dict, raw: Dict | None = None) -> str:
    titulo = str(normalized.get("titulo", ""))
    descricao = str(normalized.get("descricao", ""))
    preco = str(normalized.get("preco", ""))
    imagens = _normalize_list(normalized.get("imagens", []) or [])

    status_meli = ""
    categoria = ""
    condicao = ""
    if isinstance(raw, dict):
        status_meli = str(raw.get("status", ""))
        categoria = str(raw.get("category_id", ""))
        condicao = str(raw.get("condition", ""))

    base = "|".join([
        titulo,
        descricao,
        preco,
        status_meli,
        ";".join(imagens),
        categoria,
        condicao,
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
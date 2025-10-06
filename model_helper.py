from datetime import datetime, date
from typing import Dict, Any, Callable, Optional
from app import db

def _to_float(s: str) -> Optional[float]:
    if s is None: return None
    s = str(s).strip()
    if s == '': return None
    if s.count(',') and s.count('.') == 0:
        s = s.replace(',', '.')
    else:
        s = s.replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None

def _to_int(s: str) -> Optional[int]:
    if s is None: return None
    s = str(s).strip()
    if s == '': return None
    try:
        return int(s)
    except ValueError:
        return None

def _to_bool(s: str) -> Optional[bool]:
    if s is None: return None
    s = str(s).strip().lower()
    if s == '': return None
    return s in ('1', 'true', 'yes', 'on')

def _to_str(s: str) -> Optional[str]:
    if s is None: return None
    s = str(s).strip()
    return s if s != '' else None

def _to_date(s: str) -> Optional[date]:
    if not s: return None
    return datetime.strptime(s, '%Y-%m-%d').date()

COERCERS: Dict[str, Callable[[str], Any]] = {
    'float': _to_float,
    'int': _to_int,
    'bool': _to_bool,
    'str': _to_str,
    'date': _to_date,
}

def coerce_opt(val: Any, type_name: str):
    """Trả None nếu rỗng/không hợp lệ, ngược lại trả về giá trị đã chuyển kiểu."""
    fn = COERCERS[type_name]
    return fn(val)

def exists_by_keys(Model, filters: Dict[str, Any]) -> bool:
    """Kiểm tra tồn tại theo dict filters (filter_by)."""
    return db.session.query(Model).filter_by(**filters).first() is not None

def partial_update_fields(instance, data: Dict[str, Any], field_types: Dict[str, str]):
    """
    Chỉ set những field có giá trị hợp lệ trong data (rỗng -> bỏ qua).
    field_types: {'electricity': 'float', 'name': 'str', ...}
    """
    for field, t in field_types.items():
        if field not in data:
            continue
        val = coerce_opt(data.get(field), t)
        if val is None:
            continue
        setattr(instance, field, val)

def build_insert_payload(data: Dict[str, Any], field_types: Dict[str, str]) -> Dict[str, Any]:
    """
    Chuẩn bị payload cho insert mới.
    - numeric rỗng -> 0/0.0
    - str rỗng -> None
    - bool rỗng -> False
    """
    out = {}
    for field, t in field_types.items():
        val = coerce_opt(data.get(field), t)
        if val is None:
            if t == 'float': val = 0.0
            elif t == 'int': val = 0
            elif t == 'bool': val = False
            else: val = None
        out[field] = val
    return out
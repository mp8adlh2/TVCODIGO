import time
import threading
from datetime import datetime
from typing import List, Dict, Tuple

# Buffer circular em memória com os últimos eventos do Kernel Cyber Deck
_LOG_LOCK = threading.Lock()
_LOG_BUFFER: List[Dict] = []
_LOG_ID_SEQ = 0

def push_kernel_log(msg: str, level: str = "info"):
    """Registra uma mensagem no buffer do Kernel para exibição ao vivo no frontend."""
    global _LOG_ID_SEQ
    with _LOG_LOCK:
        _LOG_ID_SEQ += 1
        now_str = datetime.now().strftime("%H:%M:%S")
        entry = {
            "id": _LOG_ID_SEQ,
            "time": now_str,
            "msg": msg,
            "level": level
        }
        _LOG_BUFFER.append(entry)
        if len(_LOG_BUFFER) > 150:
            _LOG_BUFFER.pop(0)
    # Também imprime no console do servidor / Render para rastreamento
    print(f"[{now_str}] {msg}", flush=True)

def get_kernel_logs(since_id: int = 0) -> Tuple[List[Dict], int]:
    """Retorna logs mais recentes que since_id para streaming no frontend."""
    with _LOG_LOCK:
        if since_id <= 0:
            # Se é a primeira consulta, retorna os últimos 35 logs
            return list(_LOG_BUFFER[-35:]), _LOG_ID_SEQ
        return [l for l in _LOG_BUFFER if l["id"] > since_id], _LOG_ID_SEQ

def clear_kernel_logs():
    """Limpa o buffer de logs se necessário."""
    global _LOG_BUFFER, _LOG_ID_SEQ
    with _LOG_LOCK:
        _LOG_BUFFER.clear()
        _LOG_ID_SEQ = 0

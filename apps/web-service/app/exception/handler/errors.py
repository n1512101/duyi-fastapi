"""エラーコード設定

ハードコードされた辞書：例外型 → (業務エラーコード, HTTPステータスコード, デフォルトメッセージ)
"""

from fastapi.exceptions import RequestValidationError

from app.exception.database import DatabaseException
from app.exception.not_found import NotFoundException

ERROR_MAP: dict[type, tuple[str, int, str]] = {
    RequestValidationError: ("422001", 422, "データ検証エラー"),
    DatabaseException: ("422002", 422, "データ検証エラー"),
    NotFoundException: ("404001", 404, "リソースが存在しません"),
    Exception: ("500001", 500, "サーバー内部エラー"),
}


PROTOCOL_ERROR_MAP: dict[int, str] = {
    404: "パスが存在しません",
    405: "許可されていないリクエストメソッド",
    415: "サポートされていないメディアタイプ",
}

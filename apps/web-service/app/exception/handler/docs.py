"""ERROR_MAP と PROTOCOL_ERROR_MAP から API ドキュメントに表示するエラーコードの説明を生成する"""


def generate_error_docs() -> str:
    from app.exception.handler.errors import ERROR_MAP, PROTOCOL_ERROR_MAP

    lines: list[str] = ["## エラーコードの説明\n"]

    # 業務例外テーブル
    lines.append("### 業務エラー\n")
    lines.append("| 業務エラーコード | HTTPステータスコード | メッセージ |")
    lines.append("|-----------|-----------|------|")
    seen: set[str] = set()
    for exc_type, (code, http_status, message) in ERROR_MAP.items():
        if exc_type is Exception:
            continue
        if code not in seen:
            seen.add(code)
            lines.append(f"| {code} | {http_status} | {message} |")

    # プロトコル例外テーブル
    lines.append("\n### プロトコルエラー\n")
    lines.append("| エラーコード | HTTPステータスコード | メッセージ |")
    lines.append("|--------|-----------|------|")
    for http_status, message in PROTOCOL_ERROR_MAP.items():
        code = str(http_status)
        lines.append(f"| {code} | {http_status} | {message} |")

    return "\n".join(lines)

def allowed(chunk, user_permissions: set[str] | None = None) -> bool:
    user_permissions = user_permissions or {"public"}
    required = set(chunk.permissions or ["public"])
    return bool(required & user_permissions)


def filter_chunks(chunks, user_permissions=None):
    return [c for c in chunks if allowed(c, user_permissions)]

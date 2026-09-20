"""MediStock application package."""

# Python 3.14 (PEP 649) compatibility patch for SQLModel 0.0.22:
# In Python 3.14, class annotations are lazily compiled into `__annotate_func__`
# rather than stored directly in `__annotations__` at class creation time.
# We ensure SQLModel's compatibility helper retrieves them cleanly so table
# models (like User) work smoothly.
try:
    import sqlmodel._compat
    import sqlmodel.main

    _orig_get_annotations = sqlmodel._compat.get_annotations

    def _patched_get_annotations(class_dict):
        ann = _orig_get_annotations(class_dict)
        if not ann and "__annotate_func__" in class_dict:
            try:
                return class_dict["__annotate_func__"](1)
            except Exception:
                pass
        return ann

    sqlmodel._compat.get_annotations = _patched_get_annotations
    sqlmodel.main.get_annotations = _patched_get_annotations
except (ImportError, AttributeError):
    pass

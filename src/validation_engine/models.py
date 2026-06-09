from typing import Dict

class ValidationErrorDetail:
    """
    Representa uma violação individual de restrição SHACL.
    """
    def __init__(self, focus_node: str, path: str, message: str, severity: str, constraint: str):
        self.focus_node = focus_node
        self.path = path
        self.message = message
        self.severity = severity
        self.constraint = constraint

    def to_dict(self) -> Dict[str, str]:
        """
        Converte os detalhes do erro para um dicionário serializável.
        """
        return {
            "focus_node": self.focus_node,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
            "constraint": self.constraint
        }

    def __repr__(self) -> str:
        return (f"ValidationErrorDetail(focus_node={self.focus_node}, path={self.path}, "
                f"severity={self.severity}, message={self.message})")

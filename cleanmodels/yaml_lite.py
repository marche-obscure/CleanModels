"""Lecteur YAML minimal, suffisant pour extra_model_paths.yaml de ComfyUI.

Sous-ensemble géré : mappings imbriqués par indentation (espaces), scalaires simples
ou entre guillemets, blocs littéraux « | », commentaires « # ».
Les guillemets sont simplement retirés, sans interprétation des séquences « \ »,
pour que les chemins Windows restent intacts.
"""


class YamlError(Exception):
    def __init__(self, line: int, message: str):
        super().__init__(f"ligne {line} : {message}")
        self.line = line


def _strip_comment(text: str) -> str:
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
    return text.rstrip()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _indent_of(line: str, number: int) -> int:
    leading = line[: len(line) - len(line.lstrip(" \t"))]
    if "\t" in leading:
        raise YamlError(number, "indentation par tabulation non autorisée")
    return len(leading)


def parse(text: str) -> dict:
    lines = text.splitlines()
    root: dict = {}
    # Entrées : [indentation de la clé, mapping, indentation des enfants ou None]
    stack: list = [[-1, root, None]]
    i = 0
    while i < len(lines):
        number = i + 1
        line = lines[i]
        i += 1
        content = _strip_comment(line.strip())
        if not content:
            continue
        indent = _indent_of(line, number)
        if content.startswith("-"):
            raise YamlError(number, "les listes « - » ne sont pas gérées")
        key, sep, value = content.partition(":")
        key = _unquote(key.strip())
        if not sep or not key:
            raise YamlError(number, "« clé: valeur » attendu")

        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1]
        if parent[2] is None:
            parent[2] = indent
        elif parent[2] != indent:
            raise YamlError(number, "indentation incohérente")
        mapping = parent[1]

        value = value.strip()
        if value.startswith("|"):
            block = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and _indent_of(nxt, i + 1) <= indent:
                    break
                block.append(nxt)
                i += 1
            body = [b for b in block if b.strip()]
            cut = min((len(b) - len(b.lstrip(" ")) for b in body), default=0)
            mapping[key] = "\n".join(b[cut:].rstrip() for b in block).strip("\n")
        elif value == "":
            child: dict = {}
            mapping[key] = child
            stack.append([indent, child, None])
        else:
            mapping[key] = _unquote(value)
    return root

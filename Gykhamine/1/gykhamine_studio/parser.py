"""Module généré automatiquement depuis gy.py"""
import re
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Pango, GtkSource

#  SYNTAX HIGHLIGHTING ENGINE & PARSER
# ═══════════════════════════════════════════════════════════════════════
def apply_syntax_highlighting(textview, lang):
    buf = textview.get_buffer()
    text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
    tag_table = buf.get_tag_table()
    colors = {
        "keyword": ("#c678dd", Pango.Weight.BOLD),
        "type": ("#e5c07b", Pango.Weight.NORMAL),
        "function": ("#61afef", Pango.Weight.NORMAL),
        "variable": ("#e06c75", Pango.Weight.NORMAL),
        "string": ("#98c379", Pango.Weight.NORMAL),
        "comment": ("#5c6370", Pango.Weight.NORMAL, True),
        "number": ("#d19a66", Pango.Weight.NORMAL),
        "tag": ("#e06c75", Pango.Weight.NORMAL),
        "attr": ("#d19a66", Pango.Weight.NORMAL),
        "jinja": ("#c678dd", Pango.Weight.BOLD),
        "preproc": ("#56b6c2", Pango.Weight.NORMAL),
    }
    for name, props in colors.items():
        tag = Gtk.TextTag(name=name)
        tag.set_property("foreground", props[0])
        if len(props) > 1 and props[1] != Pango.Weight.NORMAL: tag.set_property("weight", props[1])
        if len(props) > 2 and props[2]: tag.set_property("style", Pango.Style.ITALIC)
        if not tag_table.lookup(name): tag_table.add(tag)
    for tag_name in colors.keys():
        buf.remove_tag_by_name(tag_name, buf.get_start_iter(), buf.get_end_iter())
    
    patterns = []
    if lang in ("html", "jinja"):
        patterns = [(r'(<!--[\s\S]*?-->)', "comment"), (r'(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})', "jinja"), (r'(</?[a-zA-Z0-9:_-]+)', "tag"), (r'\b([a-zA-Z0-9:_-]+)(?=\s*=)', "attr"), (r'("[^"]*"|\'[^\']*\')', "string")]
    elif lang in ("python", "py"):
        patterns = [(r'(#.*)', "comment"), (r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\')', "string"), (r'\b(True|False|None|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b', "keyword"), (r'\b\d+\b', "number"), (r'\bclass\s+([A-Z]\w*)', "type"), (r'(@\w+)', "function"), (r'\b[a-zA-Z_]\w*(?=\s*\()', "function"), (r'\b[a-zA-Z_]\w*(?=\s*=)', "variable")]
    elif lang in ("c", "cpp", "h"):
        patterns = [(r'(//.*|/\*[\s\S]*?\*/)', "comment"), (r'("[^"]*"|\'[^\']*\'|`[^`]*`)', "string"), (r'^\s*#\s*\w+', "preproc"), (r'\b(auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|inline|int|long|register|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while|class|public|private|protected|virtual|template|namespace|bool|true|false|wchar_t)\b', "keyword"), (r'\b\d+\b', "number"), (r'\b[A-Z]\w*\b', "type"), (r'\b[a-zA-Z_]\w*(?=\s*\()', "function")]
    elif lang in ("css",):
        patterns = [(r'(/\*[\s\S]*?\*/)', "comment"), (r'("[^"]*"|\'[^\']*\')', "string"), (r'(@[a-zA-Z-]+)', "keyword"), (r'(\.[a-zA-Z0-9_-]+|#[a-zA-Z0-9_-]+)', "type"), (r'\b[a-zA-Z-]+(?=\s*:)', "attr"), (r'#[0-9a-fA-F]{3,6}\b|\b\d+(?:px|em|rem|%|vh|vw|deg|s|ms)?\b', "number")]
    elif lang in ("javascript", "js"):
        patterns = [(r'(//.*|/\*[\s\S]*?\*/)', "comment"), (r'("[^"]*"|\'[^\']*\'|`[^`]*`)', "string"), (r'\b(break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|finally|for|function|if|import|in|instanceof|new|return|super|switch|this|throw|try|typeof|var|void|while|with|yield|let|async|await|of)\b', "keyword"), (r'\b\d+\b', "number"), (r'\b[A-Z]\w*\b', "type"), (r'\b[a-zA-Z_]\w*(?=\s*\()', "function"), (r'\b[a-zA-Z_]\w*(?=\s*=)', "variable")]
    elif lang in ("bash", "sh", "pl"):
        patterns = [(r'(#.*)', "comment"), (r'("[^"]*"|\'[^\']*\')', "string"), (r'\b(if|then|else|elif|fi|case|esac|for|while|until|do|done|in|function|return|exit|break|continue|export|source|local)\b', "keyword"), (r'(\$[a-zA-Z_]\w*|\$\{[^}]+\})', "variable"), (r'\b(echo|cd|ls|pwd|grep|awk|sed|chmod|chown|sudo|apt|mkdir|rm|cp|mv|cat|find|curl|wget|python3|pip)\b', "function")]
    
    for pattern, tag_name in patterns:
        for match in re.finditer(pattern, text):
            buf.apply_tag_by_name(tag_name, buf.get_iter_at_offset(match.start()), buf.get_iter_at_offset(match.end()))

SEPARATOR_RE = re.compile(r'^#{4,}.*$|^/{4,}.*$|^-{4,}.*$', re.MULTILINE)

def _find_matching_brace(lines, start_idx):
    """Trouve l'index de la ligne contenant l'accolade fermante correspondante."""
    depth = 0
    for i in range(start_idx, len(lines)):
        # On compte les accolades. (Une version parfaite ignorerait les chaînes, 
        # mais ce compteur suffit pour 99% du code bien formaté).
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0:
            return i
    return len(lines) - 1










def _get_indent(line: str) -> int:
    """Calcule l'indentation réelle (espaces + tabulations)"""
    return len(line) - len(line.lstrip(' \t'))

def _get_decorator_start(lines: list, idx: int) -> int:
    """Remonte les lignes pour trouver le début de la chaîne de décorateurs"""
    start = idx
    for k in range(idx - 1, -1, -1):
        stripped = lines[k].strip()
        if stripped.startswith('@'):
            start = k
        elif stripped == '' or stripped.startswith('#'):
            continue # Ignore les lignes vides ou commentaires entre le décorateur et la def
        else:
            break # On a touché un autre code, on s'arrête
    return start

def _find_function_end(lines: list, start_idx: int, base_indent: int) -> int:
    """Trouve la fin d'une fonction ou classe, en partant de la ligne de définition (pas du décorateur)."""
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        current_indent = _get_indent(line)
        # Dès qu'on retombe au niveau d'indentation de la fonction/classe, le bloc est fini
        if current_indent <= base_indent:
            return i - 1
        i += 1
    return len(lines) - 1

def _find_control_flow_end(lines: list, start_idx: int, base_indent: int, allow_continuations: bool = False) -> int:
    """Trouve la fin d'un bloc en se basant strictement sur l'indentation."""
    continuations = {'elif', 'else', 'except', 'finally'}
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        current_indent = _get_indent(line)
        if current_indent < base_indent:
            return i - 1
        elif current_indent == base_indent:
            is_continuation = any(stripped.startswith(kw) for kw in continuations)
            if not allow_continuations or not is_continuation:
                return i - 1
        i += 1
    return len(lines) - 1




def _find_if_else_chain_end(lines: list, start_idx: int) -> int:
    """Trouve la fin d'une chaîne if/else if/else ou try/catch/finally en JS/C."""
    base_indent = _get_indent(lines[start_idx])
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        
        current_indent = _get_indent(line)
        
        # Si on revient à l'indentation de base ou moins, c'est fini
        if current_indent <= base_indent:
            # Vérifier si c'est une continuation valide (else, catch, finally)
            is_continuation = any(stripped.startswith(kw) for kw in ['else', 'catch', 'finally'])
            if not is_continuation:
                return i - 1
            # Si c'est une continuation, on continue la boucle pour trouver la fin de ce nouveau bloc
            base_indent = current_indent
            
        i += 1
    return len(lines) - 1

def _find_brace_or_stmt_end(lines: list, start_idx: int) -> int:
    """
    Trouve la fin d'un bloc délimité par des accolades {} en ignorant 
    les accolades présentes dans les chaînes de caractères et les commentaires.
    """
    depth = 0
    found_open = False
    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    
    for i in range(start_idx, len(lines)):
        line = lines[i]
        j = 0
        while j < len(line):
            char = line[j]
            next_char = line[j+1] if j + 1 < len(line) else ''
            
            # Gestion des commentaires
            if not in_single_quote and not in_double_quote and not in_backtick:
                if not in_block_comment and char == '/' and next_char == '/':
                    in_line_comment = True
                if not in_line_comment and char == '/' and next_char == '*':
                    in_block_comment = True
                    j += 1 # Sauter le *
                if in_block_comment and char == '*' and next_char == '/':
                    in_block_comment = False
                    j += 1 # Sauter le /
            
            # Gestion des chaînes de caractères
            if not in_line_comment and not in_block_comment:
                if char == '\\' and (in_single_quote or in_double_quote or in_backtick):
                    j += 1 # Sauter le caractère échappé
                    continue
                
                if char == "'" and not in_double_quote and not in_backtick:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote and not in_backtick:
                    in_double_quote = not in_double_quote
                elif char == '`' and not in_single_quote and not in_double_quote:
                    in_backtick = not in_backtick
                
                # Comptage des accolades uniquement si on n'est ni dans une chaîne ni dans un commentaire
                if not in_single_quote and not in_double_quote and not in_backtick:
                    if char == '{':
                        depth += 1
                        found_open = True
                    elif char == '}':
                        depth -= 1
                        if found_open and depth == 0:
                            return i
            
            j += 1
        
        # Fin de ligne : reset du commentaire ligne
        in_line_comment = False
        
    # Si on arrive ici, c'est qu'on n'a pas trouvé la fermeture correspondante
    return len(lines) - 1    






def _parse_python_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur Python optimisé : Décorateurs groupés, if/else fusionnés, indentation préservée, SANS boucle infinie."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
            
        current_indent = _get_indent(line)
        
        # Détection des structures
        is_class = re.match(r'^class\s+(\w+)', stripped)
        is_func = re.match(r'^(async\s+)?def\s+(\w+)', stripped)
        is_import = re.match(r'^(import|from)\s+', stripped)
        is_main = re.match(r'^if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', stripped)
        is_if = re.match(r'^if\s+', stripped)
        is_try = re.match(r'^try\s*:', stripped)
        is_docstring = stripped.startswith('"""') or stripped.startswith("'''")
        is_decorator = stripped.startswith('@')
        
        # CORRECTION CRITIQUE : On ignore les décorateurs ici pour qu'ils soient capturés 
        # par le bloc is_func/is_class qui suit, évitant ainsi la boucle infinie.
        if is_decorator:
            i += 1
            continue
            
        if is_class or is_func:
            # 1. Capturer les décorateurs associés
            start_idx = _get_decorator_start(lines, i)
            # 2. L'indentation de référence est celle de la fonction/classe
            base_indent = current_indent
            # 3. Trouver la fin en partant de la ligne de la fonction (i), pas du décorateur
            end_idx = _find_function_end(lines, i, base_indent)
            
            raw_code = "".join(lines[start_idx:end_idx + 1])
            name = is_class.group(1) if is_class else is_func.group(2)
            btype = "class" if is_class else "function"
            
            blocks.append({
                "type": btype,
                "name": f"{name} (Indent: {base_indent})",
                "code": raw_code,
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        elif is_if or is_try:
            # Fusionne if/elif/else ou try/except/finally
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=True)
            raw_code = "".join(lines[i:end_idx + 1])
            name = "Condition (if/else)" if is_if else "Gestion d'erreur (try/except)"
            
            blocks.append({
                "type": "logic_block",
                "name": f"{name} (Indent: {current_indent})",
                "code": raw_code,
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        elif is_import:
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=False)
            blocks.append({
                "type": "import",
                "name": "Imports",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        elif stripped.startswith('#') or is_docstring:
            end_idx = i
            for k in range(i + 1, len(lines)):
                k_stripped = lines[k].strip()
                if k_stripped.startswith('#') or k_stripped.startswith('"""') or k_stripped.startswith("'''") or not k_stripped:
                    end_idx = k
                else:
                    break
            blocks.append({
                "type": "comment",
                "name": "Commentaire / Docstring",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
        else:
            # Fallback pour tout autre code racine
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=False)
            blocks.append({
                "type": "other",
                "name": f"Bloc de code (Indent: {current_indent})",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
    return blocks











def _parse_template_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur HTML/Jinja RADICAL :
    - Ignore TOUTES les balises HTML structurelles (div, section, etc.).
    - Ne découpe QUE sur les blocs logiques (Django/Jinja) et les scripts/styles.
    - Retourne le fichier complet si aucun bloc logique n'est trouvé.
    - Sans récursion.
    """
    lines = code.splitlines(keepends=True)
    blocks = []
    
    # Indices des lignes déjà attribuées à un bloc spécial
    used_lines = set()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped:
            i += 1
            continue
            
        start_idx = i
        end_idx = i
        block_type = None
        block_name = "Bloc"
        
        # 1. Détection Bloc Django/Jinja Root ({% block ... %})
        m_block = re.match(r"\{%-?\s*block\s+(\w+).*?%\}", stripped, re.IGNORECASE)
        if m_block:
            block_type = "django_block"
            block_name = f"block: {m_block.group(1)}"
            # Chercher {% endblock %}
            for k in range(i + 1, len(lines)):
                if re.match(r"\{%-?\s*endblock\b", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1 # Fermeture implicite à la fin
        
        # 2. Détection Style
        elif re.match(r"<style(\s[^>]*)?>", stripped, re.IGNORECASE):
            block_type = "style"
            block_name = "<style>"
            for k in range(i + 1, len(lines)):
                if re.match(r"</style\s*>", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1

        # 3. Détection Script
        elif re.match(r"<script(\s[^>]*)?>", stripped, re.IGNORECASE):
            block_type = "script"
            block_name = "<script>"
            for k in range(i + 1, len(lines)):
                if re.match(r"</script\s*>", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1
        
        # Si un bloc spécial a été détecté
        if block_type:
            raw_code = "".join(lines[start_idx:end_idx + 1])
            blocks.append({
                "type": block_type,
                "name": block_name,
                "code": raw_code,
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            # Marquer les lignes comme utilisées
            for x in range(start_idx, end_idx + 1):
                used_lines.add(x)
            i = end_idx + 1
            continue
            
        i += 1

    # SI AUCUN BLOC LOGIQUE N'A ÉTÉ TROUVÉ : Retourner le fichier entier
    if not blocks:
        return [{
            "type": "html_file",
            "name": Path(file_path).name if file_path else "template.html",
            "code": code,
            "start": 0,
            "end": len(lines) - 1,
            "children": []
        }]

    # Optionnel : Si vous voulez aussi récupérer le HTML "orphelin" entre les blocs django
    # comme un bloc "Autre", décommentez ci-dessous. Sinon, seul le fichier complet ou les blocs logiques sont retournés.
    """
    orphan_start = None
    for idx in range(len(lines)):
        if idx not in used_lines:
            if orphan_start is None: orphan_start = idx
        else:
            if orphan_start is not None:
                blocks.append({
                    "type": "html_fragment",
                    "name": "HTML Orphelin",
                    "code": "".join(lines[orphan_start:idx]),
                    "start": orphan_start,
                    "end": idx - 1,
                    "children": []
                })
                orphan_start = None
    if orphan_start is not None:
        blocks.append({
            "type": "html_fragment",
            "name": "HTML Orphelin",
            "code": "".join(lines[orphan_start:]),
            "start": orphan_start,
            "end": len(lines) - 1,
            "children": []
        })
    blocks.sort(key=lambda b: b['start'])
    """
    
    return blocks
    
    
def _parse_css_blocks(code: str, file_path: str) -> list[dict]:
    lines = code.splitlines(keepends=True)
    
    def _extract_css_children(start_idx, end_idx):
        """Extrait récursivement les sélecteurs, variables, propriétés et règles @"""
        children = []
        i = start_idx
        while i <= end_idx:
            line = lines[i]
            stripped = line.strip()
            
            # Ignorer les lignes vides et les commentaires simples
            if not stripped or stripped.startswith('/*') or stripped.startswith('*'):
                i += 1
                continue

            # 1. Détection des règles @ (@media, @keyframes, @font-face, @import, etc.)
            is_at_rule = re.match(r'^@([\w-]+)', stripped)
            if is_at_rule:
                rule_type = is_at_rule.group(1)
                block_name = stripped[:60]
                
                # Trouver le début de l'accolade (parfois sur la ligne suivante)
                brace_start = i
                for k in range(i, min(i + 10, len(lines))):
                    if '{' in lines[k]:
                        brace_start = k
                        break
                
                brace_end = _find_matching_brace(lines, brace_start)
                raw_code = "".join(lines[i:brace_end + 1])
                
                # APPEL RÉCURSIF : Analyser l'intérieur du @media ou @keyframes
                sub_children = _extract_css_children(brace_start + 1, brace_end - 1)
                
                children.append({
                    "type": f"css_at_{rule_type}",
                    "name": block_name,
                    "code": raw_code,
                    "start": i,
                    "end": brace_end,
                    "children": sub_children
                })
                i = brace_end + 1
                continue

            # 2. Détection des Sélecteurs standards (.class, #id, element) contenant { }
            if '{' in stripped and not stripped.startswith('--'):
                # Nettoyer le nom du sélecteur (enlever le { et les espaces)
                block_name = stripped.split('{')[0].strip()[:50]
                
                brace_start = i
                for k in range(i, min(i + 5, len(lines))):
                    if '{' in lines[k]:
                        brace_start = k
                        break
                
                brace_end = _find_matching_brace(lines, brace_start)
                raw_code = "".join(lines[i:brace_end + 1])
                
                # APPEL RÉCURSIF : Analyser les propriétés à l'intérieur du sélecteur
                sub_children = _extract_css_children(brace_start + 1, brace_end - 1)
                
                children.append({
                    "type": "css_selector",
                    "name": block_name,
                    "code": raw_code,
                    "start": i,
                    "end": brace_end,
                    "children": sub_children
                })
                i = brace_end + 1
                continue

            # 3. Détection des Variables CSS (--nom-variable: valeur;)
            is_variable = re.match(r'^--[\w-]+\s*:', stripped)
            # 4. Détection des Propriétés simples (se terminant par ;)
            is_property = stripped.endswith(';') and not is_variable

            if is_variable or is_property:
                block_type = "css_variable" if is_variable else "css_property"
                # Extraire le nom de la variable ou de la propriété (avant les deux-points)
                block_name = stripped.split(':')[0].strip()[:40] if ':' in stripped else stripped[:40]
                
                # Une propriété peut s'étaler sur plusieurs lignes, on cherche le ;
                prop_end = i
                for k in range(i, min(i + 15, len(lines))):
                    if ';' in lines[k]:
                        prop_end = k
                        break
                
                raw_code = "".join(lines[i:prop_end + 1])
                
                children.append({
                    "type": block_type,
                    "name": block_name,
                    "code": raw_code,
                    "start": i,
                    "end": prop_end,
                    "children": [] # Les propriétés sont des feuilles (pas d'enfants)
                })
                i = prop_end + 1
                continue

            # Fallback : si c'est une ligne bizarre, on avance
            i += 1
            
        return children

    # --- Parsing du niveau racine ---
    # On traite tout le fichier comme un conteneur dont on extrait les enfants de premier niveau
    root_children = _extract_css_children(0, len(lines) - 1)
    
    if root_children:
        return [{
            "type": "css_file",
            "name": Path(file_path).name if file_path else "Stylesheet.css",
            "code": code,
            "start": 0,
            "end": len(lines) - 1,
            "children": root_children
        }]
    
    # Fallback si le fichier est vide ou incompréhensible
    return [{"type": "css_file", "name": "Stylesheet", "code": code, "start": 0, "end": len(lines)-1, "children": []}]


def _parse_js_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur JS robuste : Se concentre uniquement sur les fonctions, classes et exports majeurs via les accolades."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped or stripped.startswith('//'):
            i += 1
            continue
            
        # Détection des structures principales
        is_class = re.match(r'^(export\s+)?(default\s+)?class\s+(\w+)', stripped)
        # Match function declaration or arrow function assignment
        is_func = re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+(\w+)|^(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?(?:function|\([^)]*\)\s*=>|\w+\s*=>)', stripped)
        is_export_default = re.match(r'^export\s+default\s+', stripped)
        
        start_idx = -1
        name = "Anonymous"
        btype = "other"
        
        if is_class:
            start_idx = i
            name = is_class.group(3)
            btype = "class"
        elif is_func:
            start_idx = i
            if is_func.group(4): name = is_func.group(4) # Named function
            elif is_func.group(6): name = is_func.group(6) # Variable assignment
            btype = "function"
        elif is_export_default and ('{' in stripped or 'function' in stripped or 'class' in stripped):
             # Cas export default { ... } ou export default function...
             start_idx = i
             name = "Default Export"
             btype = "other"

        if start_idx != -1:
            # Chercher l'accolade ouvrante
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
                raw_code = "".join(lines[start_idx:end_idx + 1])
                
                blocks.append({
                    "type": btype,
                    "name": name,
                    "code": raw_code,
                    "start": start_idx,
                    "end": end_idx,
                    "children": []
                })
                i = end_idx + 1
                continue
        
        i += 1
        
    return blocks

def _parse_c_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur C/C++ robuste : Se concentre uniquement sur les fonctions, structs et classes via les accolades."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            i += 1
            continue
            
        # Détection des structures principales
        is_struct_class = re.match(r'^(typedef\s+)?(struct|class|enum|union|namespace)\s+(\w*)', stripped)
        # Fonction C classique : type nom(...)
        is_func = re.match(r'^(void|int|char|float|double|bool|auto|unsigned|signed|long|short|size_t|ssize_t|uint\d+_t|int\d+_t|struct\s+\w+)\s+\**\s*(\w+)\s*\(', stripped)
        
        start_idx = -1
        name = "Unknown"
        btype = "other"
        
        if is_struct_class:
            start_idx = i
            name = is_struct_class.group(3) if is_struct_class.group(3) else "Anonymous"
            btype = "class" # On groupe struct/class/enum sous "class" pour l'icône
        elif is_func:
            start_idx = i
            name = is_func.group(2)
            btype = "function"
            
        if start_idx != -1:
            # Chercher l'accolade ouvrante
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
                raw_code = "".join(lines[start_idx:end_idx + 1])
                
                blocks.append({
                    "type": btype,
                    "name": name,
                    "code": raw_code,
                    "start": start_idx,
                    "end": end_idx,
                    "children": []
                })
                i = end_idx + 1
                continue
        
        i += 1
        
    return blocks    
def parse_blocks(code: str, file_path: str = "") -> list[dict]:
    ext = Path(file_path).suffix.lower()
    if ext in ('.html', '.jinja', '.jinja2', '.htm'): return _parse_template_blocks(code, file_path)
    elif ext == '.css': return _parse_css_blocks(code, file_path)
    elif ext == '.js': return _parse_js_blocks(code, file_path)
    elif ext in ('.c', '.cpp', '.h'): return _parse_c_blocks(code, file_path)
    else: return _parse_python_blocks(code, file_path)

# ═══════════════════════════════════════════════════════════════════════

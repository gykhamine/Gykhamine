"""Module généré automatiquement depuis gy.py"""
import re
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Pango, GtkSource

#  SYNTAX HIGHLIGHTING ENGINE & PARSER
# ═══════════════════════════════════════════════════════════════════════

def _get_indent(line: str) -> int:
    """Calcule l'indentation réelle (espaces + tabulations)"""
    return len(line) - len(line.lstrip(' 	'))


def _is_blank(line: str) -> bool:
    return not line.strip()


def _get_decorator_start(lines: list, idx: int) -> int:
    """Remonte les lignes pour trouver le début de la chaîne de décorateurs"""
    start = idx
    for k in range(idx - 1, -1, -1):
        stripped = lines[k].strip()
        if stripped.startswith('@'):
            start = k
        elif _is_blank(lines[k]) or stripped.startswith('#'):
            continue
        else:
            break
    return start


def _skip_blank_lines(lines: list, start: int) -> int:
    """Skip blank lines and return the index of the next non-blank line."""
    i = start
    while i < len(lines) and _is_blank(lines[i]):
        i += 1
    return i


def _find_triple_quote_end(lines: list, start_idx: int, quote_char: str) -> int:
    """
    Trouve la fin d'une chaîne triple-quotes ( ou ''') 
    en gérant correctement les multi-lignes.
    """
    first_line = lines[start_idx].strip()
    # Check if the triple quote opens AND closes on the same line
    # e.g. x = """hello"""  or  """hello"""
    # We need at least 6 chars (open + close) after stripping
    if len(first_line) >= 6:
        # Find the opening triple quote position
        for qc in [quote_char * 3]:
            pos = first_line.find(qc)
            if pos != -1:
                # Check if there's a closing triple quote after it
                close_pos = first_line.find(qc, pos + 3)
                if close_pos != -1:
                    return start_idx
    
    # Multi-line: search for the closing triple quote on subsequent lines
    for i in range(start_idx + 1, len(lines)):
        if quote_char * 3 in lines[i]:
            return i
    return len(lines) - 1


def _find_block_comment_end(lines: list, start_idx: int) -> int:
    """Trouve la fin d'un commentaire bloc C-style /* ... */"""
    in_comment = False
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if '/*' in line:
            in_comment = True
        if '*/' in line and in_comment:
            return i
    return len(lines) - 1


def _find_function_end_indent(lines: list, start_idx: int, base_indent: int) -> int:
    """Trouve la fin d'une fonction/classe Python en se basant strictement sur l'indentation."""
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        if _is_blank(line):
            i += 1
            continue
        current_indent = _get_indent(line)
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
        if _is_blank(line):
            i += 1
            continue
        current_indent = _get_indent(line)
        if current_indent < base_indent:
            return i - 1
        elif current_indent == base_indent:
            is_continuation = any(lines[i].strip().startswith(kw) for kw in continuations)
            if not allow_continuations or not is_continuation:
                return i - 1
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
            
            if not in_single_quote and not in_double_quote and not in_backtick:
                if not in_block_comment and char == '/' and next_char == '/':
                    in_line_comment = True
                if not in_line_comment and char == '/' and next_char == '*':
                    in_block_comment = True
                    j += 1
                if in_block_comment and char == '*' and next_char == '/':
                    in_block_comment = False
                    j += 1
            
            if not in_line_comment and not in_block_comment:
                if char == '\\' and (in_single_quote or in_double_quote or in_backtick):
                    j += 1
                    continue
                if char == "'" and not in_double_quote and not in_backtick:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote and not in_backtick:
                    in_double_quote = not in_double_quote
                elif char == '`' and not in_single_quote and not in_double_quote:
                    in_backtick = not in_backtick
                
                if not in_single_quote and not in_double_quote and not in_backtick:
                    if char == '{':
                        depth += 1
                        found_open = True
                    elif char == '}':
                        depth -= 1
                        if found_open and depth == 0:
                            return i
            j += 1
        in_line_comment = False
    return len(lines) - 1


def _find_matching_brace(lines, start_idx):
    """Trouve l'index de la ligne contenant l'accolade fermante correspondante."""
    depth = 0
    for i in range(start_idx, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0:
            return i
    return len(lines) - 1


# ═══════════════════════════════════════════════════════════════════════
#  PYTHON PARSER - Robuste et complet
# ═══════════════════════════════════════════════════════════════════════

def _parse_python_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur Python robuste :
    - Imports groupés en un seul bloc
    - Triple-quotes ( et ''') gérés correctement
    - Décorateurs associés à leurs fonctions/classes
    - if/elif/else et try/except/finally fusionnés
    - Indentation cohérente préservée
    - Variables globales au niveau module
    """
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    # ---- PHASE 1 : Collecter tous les imports consécutifs en haut ----
    import_start = None
    import_end = None
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r'^(import|from)\s+', stripped):
            if import_start is None:
                import_start = i
            import_end = i
            i += 1
        elif _is_blank(lines[i]) or stripped.startswith('#'):
            # Allow blank lines and comments between imports
            if import_start is not None:
                import_end = i
            i += 1
        else:
            break
    
    if import_start is not None and import_end is not None:
        # Trim trailing blank/comment lines from import block
        while import_end > import_start and (_is_blank(lines[import_end]) or lines[import_end].strip().startswith('#')):
            import_end -= 1
        
        blocks.append({
            "type": "import",
            "name": "Imports",
            "code": "".join(lines[import_start:import_end + 1]),
            "start": import_start,
            "end": import_end,
            "children": []
        })
        i = import_end + 1
    
    # ---- PHASE 2 : Parser le reste du fichier ----
    # Also catch late imports (after code) and group them individually
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if _is_blank(line):
            i += 1
            continue
            
        current_indent = _get_indent(line)
        
        # ---- Triple-quoted strings (docstrings or standalone) ----
        is_triple_double = stripped.startswith('"""')
        is_triple_single = stripped.startswith("'''")
        
        if is_triple_double or is_triple_single:
            quote_char = '"' if is_triple_double else "'"
            start_idx = i
            
            # Include decorators above the docstring (class/function docstrings)
            # Check if this is part of a class/function definition coming next
            # Look ahead to see if next non-blank line is class/def
            end_idx = _find_triple_quote_end(lines, i, quote_char)
            
            # Check if this docstring belongs to a class/def right after it
            next_non_blank = _skip_blank_lines(lines, end_idx + 1)
            is_docstring_of_struct = False
            if next_non_blank < len(lines):
                next_stripped = lines[next_non_blank].strip()
                if re.match(r'^(class\s|def\s|async\s+def\s)', next_stripped):
                    is_docstring_of_struct = True
            
            if not is_docstring_of_struct:
                blocks.append({
                    "type": "comment",
                    "name": "Docstring / Commentaire multiligne",
                    "code": "".join(lines[start_idx:end_idx + 1]),
                    "start": start_idx,
                    "end": end_idx,
                    "children": []
                })
                i = end_idx + 1
                continue
            # If it IS a docstring of a struct, let the struct parser handle it
            # Skip it here, the struct parser will include it
        
        # ---- Decorateurs seuls (seront capturés par la classe/fonction suivante) ----
        if stripped.startswith('@') and not re.match(r'^(class|def|async)\s', stripped):
            i += 1
            continue
        
        # ---- Classes et Fonctions ----
        is_class = re.match(r'^class\s+(\w+)', stripped)
        is_func = re.match(r'^(async\s+)?def\s+(\w+)', stripped)
        
        if is_class or is_func:
            # Capturer les décorateurs associés (remonte en arrière)
            start_idx = _get_decorator_start(lines, i)
            base_indent = current_indent
            end_idx = _find_function_end_indent(lines, i, base_indent)
            
            raw_code = "".join(lines[start_idx:end_idx + 1])
            name = is_class.group(1) if is_class else is_func.group(2)
            btype = "class" if is_class else "function"
            
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
        
        # ---- Imports tardifs (après du code) ----
        if re.match(r'^(import|from)\s+', stripped):
            # Group consecutive late imports
            imp_start = i
            while i < len(lines):
                s = lines[i].strip()
                if re.match(r'^(import|from)\s+', s):
                    i += 1
                elif _is_blank(lines[i]):
                    i += 1
                else:
                    break
            imp_end = i - 1
            while imp_end > imp_start and _is_blank(lines[imp_end]):
                imp_end -= 1
            blocks.append({
                "type": "import",
                "name": "Imports",
                "code": "".join(lines[imp_start:imp_end + 1]),
                "start": imp_start,
                "end": imp_end,
                "children": []
            })
            continue
        
        # ---- if/elif/else et try/except/finally ----
        is_if = re.match(r'^if\s+', stripped)
        is_try = re.match(r'^try\s*:', stripped)
        is_for = re.match(r'^for\s+', stripped)
        is_while = re.match(r'^while\s+', stripped)
        is_with = re.match(r'^with\s+', stripped)
        
        if is_if or is_try or is_for or is_while or is_with:
            end_idx = _find_control_flow_end(lines, i, current_indent, allow_continuations=True)
            raw_code = "".join(lines[i:end_idx + 1])
            if is_if:
                name = "Condition (if/else)"
            elif is_try:
                name = "Gestion d'erreur (try/except)"
            elif is_for:
                name = "Boucle (for)"
            elif is_while:
                name = "Boucle (while)"
            else:
                name = "Contexte (with)"
            
            blocks.append({
                "type": "logic_block",
                "name": name,
                "code": raw_code,
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Commentaires # ----
        if stripped.startswith('#'):
            end_idx = i
            for k in range(i + 1, len(lines)):
                k_stripped = lines[k].strip()
                if k_stripped.startswith('#') or _is_blank(lines[k]):
                    end_idx = k
                else:
                    break
            # Trim trailing blank lines
            while end_idx > i and _is_blank(lines[end_idx]):
                end_idx -= 1
            blocks.append({
                "type": "comment",
                "name": "Commentaire",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Séparateurs (####, ----, ====) ----
        if re.match(r'^#{4,}', stripped) or re.match(r'^-{4,}', stripped) or re.match(r'^={4,}', stripped):
            blocks.append({
                "type": "separator",
                "name": "Séparateur",
                "code": line,
                "start": i,
                "end": i,
                "children": []
            })
            i += 1
            continue
            
        # ---- Variables globales et autre code au niveau module ----
        else:
            # Group consecutive non-structural lines at the same indent level
            end_idx = i
            while end_idx < len(lines):
                next_line = lines[end_idx]
                next_stripped = next_line.strip()
                if _is_blank(next_line):
                    end_idx += 1
                    continue
                # Stop if we hit a structural element
                if (re.match(r'^(class\s|def\s|async\s+def\s|if\s|for\s|while\s|with\s|try\s*:)', next_stripped)
                    or re.match(r'^(import|from)\s+', next_stripped)
                    or next_stripped.startswith('#')
                    or next_stripped.startswith('@')
                    or next_stripped.startswith('"""') or next_stripped.startswith("'''")):
                    break
                # Stop if indentation goes back to base or less
                if _get_indent(next_line) < current_indent and current_indent > 0:
                    break
                end_idx += 1
            end_idx -= 1
            # Trim trailing blank lines
            while end_idx > i and _is_blank(lines[end_idx]):
                end_idx -= 1
                
            blocks.append({
                "type": "other",
                "name": "Code module",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
            
    return blocks


# ═══════════════════════════════════════════════════════════════════════
#  JAVASCRIPT / TYPESCRIPT PARSER
# ═══════════════════════════════════════════════════════════════════════

def _parse_js_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur JS/TS robuste :
    - Imports groupés en un seul bloc
    - Commentaires (//, /* */) en blocs séparés
    - Fonctions, classes, exports
    - Variables globales
    """
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    # ---- PHASE 1 : Collecter les imports/exports en haut ----
    import_start = None
    import_end = None
    import_kw = re.compile(r'^(import\s|export\s+(?:default\s+)?.*\s+from\s|["\']use\s+strict["\']\s*;?)')
    
    while i < len(lines):
        stripped = lines[i].strip()
        if import_kw.match(stripped):
            if import_start is None:
                import_start = i
            import_end = i
            i += 1
        elif _is_blank(lines[i]) or stripped.startswith('//'):
            if import_start is not None:
                import_end = i
            i += 1
        else:
            break
    
    if import_start is not None and import_end is not None:
        while import_end > import_start and (_is_blank(lines[import_end]) or lines[import_end].strip().startswith('//')):
            import_end -= 1
        blocks.append({
            "type": "import",
            "name": "Imports",
            "code": "".join(lines[import_start:import_end + 1]),
            "start": import_start,
            "end": import_end,
            "children": []
        })
        i = import_end + 1
    
    # ---- PHASE 2 : Parser le reste ----
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if _is_blank(line):
            i += 1
            continue
        
        # ---- Block comments /* ... */ ----
        if '/*' in stripped and '*/' not in stripped:
            start_idx = i
            end_idx = _find_block_comment_end(lines, i)
            blocks.append({
                "type": "comment",
                "name": "Commentaire bloc",
                "code": "".join(lines[start_idx:end_idx + 1]),
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Single line comments groupés ----
        if stripped.startswith('//'):
            end_idx = i
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('//') or _is_blank(lines[i]):
                    end_idx = i
                    i += 1
                else:
                    break
            while end_idx > 0 and _is_blank(lines[end_idx]):
                end_idx -= 1
            blocks.append({
                "type": "comment",
                "name": "Commentaire",
                "code": "".join(lines[end_idx - (i - end_idx - 1):i]) if end_idx >= (i - 1) else "".join(lines[end_idx:i + 1]),
                "start": max(0, i - (i - end_idx)),
                "end": end_idx,
                "children": []
            })
            continue
        
        # ---- Classes ----
        is_class = re.match(r'^(export\s+)?(default\s+)?class\s+(\w+)', stripped)
        if is_class:
            start_idx = i
            name = is_class.group(3)
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
            else:
                end_idx = i
            blocks.append({
                "type": "class",
                "name": name,
                "code": "".join(lines[start_idx:end_idx + 1]),
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Functions ----
        is_func = re.match(
            r'^(export\s+)?(default\s+)?(async\s+)?function\s+(\w+)'
            r'|^(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?(?:function|\([^)]*\)\s*=>|\w+\s*=>)',
            stripped
        )
        if is_func:
            start_idx = i
            name = is_func.group(4) or is_func.group(7) or "Anonymous"
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
            else:
                end_idx = i
            blocks.append({
                "type": "function",
                "name": name,
                "code": "".join(lines[start_idx:end_idx + 1]),
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Late imports ----
        if import_kw.match(stripped):
            imp_start = i
            while i < len(lines):
                s = lines[i].strip()
                if import_kw.match(s) or _is_blank(lines[i]):
                    i += 1
                else:
                    break
            imp_end = i - 1
            while imp_end > imp_start and _is_blank(lines[imp_end]):
                imp_end -= 1
            blocks.append({
                "type": "import",
                "name": "Imports",
                "code": "".join(lines[imp_start:imp_end + 1]),
                "start": imp_start,
                "end": imp_end,
                "children": []
            })
            continue
        
        # ---- Other code (variables, expressions) ----
        end_idx = i
        while end_idx < len(lines):
            s = lines[end_idx].strip()
            if _is_blank(lines[end_idx]):
                end_idx += 1
                continue
            if (s.startswith('//') or s.startswith('/*')
                or re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s', s)
                or re.match(r'^(export\s+)?(default\s+)?class\s', s)
                or import_kw.match(s)):
                break
            end_idx += 1
        end_idx -= 1
        while end_idx > i and _is_blank(lines[end_idx]):
            end_idx -= 1
        if end_idx >= i:
            blocks.append({
                "type": "other",
                "name": "Code",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
        else:
            i += 1
        
    return blocks


# ═══════════════════════════════════════════════════════════════════════
#  C / C++ PARSER
# ═══════════════════════════════════════════════════════════════════════

def _parse_c_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur C/C++ robuste :
    - #include groupés en un seul bloc
    - #define groupés
    - Commentaires (//, /* */) en blocs séparés
    - Fonctions, structs, classes, enums, namespaces
    """
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    # ---- PHASE 1 : Group preprocessor directives ----
    preproc_start = None
    preproc_end = None
    preproc_re = re.compile(r'^\s*#\s*(include|define|undef|if|ifdef|ifndef|elif|else|endif|pragma|error|warning)\b')
    
    while i < len(lines):
        stripped = lines[i].strip()
        if preproc_re.match(lines[i]):
            if preproc_start is None:
                preproc_start = i
            preproc_end = i
            i += 1
        elif _is_blank(lines[i]) or stripped.startswith('//'):
            if preproc_start is not None:
                preproc_end = i
            i += 1
        elif stripped.startswith('/*'):
            if preproc_start is not None:
                preproc_end = i
            # Skip block comment
            end_c = _find_block_comment_end(lines, i)
            i = end_c + 1
        else:
            break
    
    if preproc_start is not None and preproc_end is not None:
        while preproc_end > preproc_start and (_is_blank(lines[preproc_end]) or lines[preproc_end].strip().startswith('//')):
            preproc_end -= 1
        blocks.append({
            "type": "import",
            "name": "Preprocessor / Includes",
            "code": "".join(lines[preproc_start:preproc_end + 1]),
            "start": preproc_start,
            "end": preproc_end,
            "children": []
        })
        i = preproc_end + 1
    
    # ---- PHASE 2 : Parse rest ----
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if _is_blank(line):
            i += 1
            continue
        
        # ---- Block comments ----
        if '/*' in stripped and '*/' not in stripped:
            start_idx = i
            end_idx = _find_block_comment_end(lines, i)
            blocks.append({
                "type": "comment",
                "name": "Commentaire bloc",
                "code": "".join(lines[start_idx:end_idx + 1]),
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Single line comments ----
        if stripped.startswith('//'):
            end_idx = i
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('//') or _is_blank(lines[i]):
                    end_idx = i
                    i += 1
                else:
                    break
            while end_idx > 0 and _is_blank(lines[end_idx]):
                end_idx -= 1
            blocks.append({
                "type": "comment",
                "name": "Commentaire",
                "code": "".join(lines[i - (i - end_idx):i]),
                "start": i - (i - end_idx),
                "end": end_idx,
                "children": []
            })
            continue
        
        # ---- Skip preprocessor (already grouped or standalone) ----
        if preproc_re.match(line):
            i += 1
            continue
        
        # ---- Structs, Classes, Enums, Namespaces, Unions ----
        is_struct = re.match(r'^(typedef\s+)?(struct|class|enum|union|namespace)\s+(\w*)', stripped)
        if is_struct:
            start_idx = i
            name = is_struct.group(3) if is_struct.group(3) else "Anonymous"
            btype = "class"
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
            else:
                end_idx = i
            blocks.append({
                "type": btype,
                "name": name,
                "code": "".join(lines[start_idx:end_idx + 1]),
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Functions ----
        is_func = re.match(
            r'^(void|int|char|float|double|bool|auto|unsigned|signed|long|short|size_t|ssize_t|uint\d+_t|int\d+_t|struct\s+\w+|static\s+\w+|extern\s+\w+)\s+\**\s*(\w+)\s*\(',
            stripped
        )
        if is_func:
            start_idx = i
            name = is_func.group(2)
            brace_idx = -1
            for k in range(i, min(i + 20, len(lines))):
                if '{' in lines[k]:
                    brace_idx = k
                    break
            if brace_idx != -1:
                end_idx = _find_brace_or_stmt_end(lines, brace_idx)
            else:
                end_idx = i
            blocks.append({
                "type": "function",
                "name": name,
                "code": "".join(lines[start_idx:end_idx + 1]),
                "start": start_idx,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # ---- Other code (global variables, etc.) ----
        end_idx = i
        while end_idx < len(lines):
            s = lines[end_idx].strip()
            if _is_blank(lines[end_idx]):
                end_idx += 1
                continue
            if (s.startswith('//') or s.startswith('/*')
                or re.match(r'^(typedef\s+)?(struct|class|enum|union|namespace)\s', s)
                or preproc_re.match(lines[end_idx])):
                break
            end_idx += 1
        end_idx -= 1
        while end_idx > i and _is_blank(lines[end_idx]):
            end_idx -= 1
        if end_idx >= i:
            blocks.append({
                "type": "other",
                "name": "Code",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
        else:
            i += 1
    
    return blocks


# ═══════════════════════════════════════════════════════════════════════
#  HTML / JINJA TEMPLATE PARSER
# ═══════════════════════════════════════════════════════════════════════

def _parse_template_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur HTML/Jinja :
    - Ne découpe QUE sur les blocs logiques (Django/Jinja) et les scripts/styles.
    - Retourne le fichier complet si aucun bloc logique n'est trouvé.
    """
    lines = code.splitlines(keepends=True)
    blocks = []
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
        
        # 1. Bloc Django/Jinja ({% block ... %})
        m_block = re.match(r"\{%-?\s*block\s+(\w+).*?%}", stripped, re.IGNORECASE)
        if m_block:
            block_type = "django_block"
            block_name = f"block: {m_block.group(1)}"
            for k in range(i + 1, len(lines)):
                if re.match(r"\{%-?\s*endblock\b", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1
        
        # 2. Style
        elif re.match(r"<style(\s[^>]*)?>", stripped, re.IGNORECASE):
            block_type = "style"
            block_name = "<style>"
            for k in range(i + 1, len(lines)):
                if re.match(r"</style\s*>", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1

        # 3. Script
        elif re.match(r"<script(\s[^>]*)?>", stripped, re.IGNORECASE):
            block_type = "script"
            block_name = "<script>"
            for k in range(i + 1, len(lines)):
                if re.match(r"</script\s*>", lines[k].strip(), re.IGNORECASE):
                    end_idx = k
                    break
            else:
                end_idx = len(lines) - 1
        
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
            for x in range(start_idx, end_idx + 1):
                used_lines.add(x)
            i = end_idx + 1
            continue
            
        i += 1

    if not blocks:
        return [{
            "type": "html_file",
            "name": Path(file_path).name if file_path else "template.html",
            "code": code,
            "start": 0,
            "end": len(lines) - 1,
            "children": []
        }]
    
    return blocks


# ═══════════════════════════════════════════════════════════════════════
#  CSS PARSER
# ═══════════════════════════════════════════════════════════════════════

def _parse_css_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur CSS à plat : un bloc par élément de premier niveau (règle @, sélecteur,
    propriété/variable isolée), exactement comme les autres parseurs (Python, JS, C...).
    Pas de bloc parent 'css_file' qui engloberait tout, pas de sous-blocs enfants :
    la séparation se fait uniquement au niveau de chaque élément rencontré. Le contenu
    interne d'un sélecteur ou d'une règle @ (ex: propriétés dans un @media) reste tel
    quel dans le code de ce bloc, il n'est pas redécoupé récursivement."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        stripped = lines[i].strip()

        if not stripped or stripped.startswith('/*') or stripped.startswith('*'):
            i += 1
            continue

        is_at_rule = re.match(r'^@([\w-]+)', stripped)
        if is_at_rule:
            rule_type = is_at_rule.group(1)
            block_name = stripped[:60]
            brace_start = i
            for k in range(i, min(i + 10, n)):
                if '{' in lines[k]:
                    brace_start = k
                    break
            brace_end = _find_matching_brace(lines, brace_start)
            blocks.append({
                "type": f"css_at_{rule_type}",
                "name": block_name,
                "code": "".join(lines[i:brace_end + 1]),
                "start": i,
                "end": brace_end,
                "children": []
            })
            i = brace_end + 1
            continue

        if '{' in stripped and not stripped.startswith('--'):
            block_name = stripped.split('{')[0].strip()[:50]
            brace_start = i
            for k in range(i, min(i + 5, n)):
                if '{' in lines[k]:
                    brace_start = k
                    break
            brace_end = _find_matching_brace(lines, brace_start)
            blocks.append({
                "type": "css_selector",
                "name": block_name,
                "code": "".join(lines[i:brace_end + 1]),
                "start": i,
                "end": brace_end,
                "children": []
            })
            i = brace_end + 1
            continue

        is_variable = re.match(r'^--[\w-]+\s*:', stripped)
        is_property = stripped.endswith(';') and not is_variable

        if is_variable or is_property:
            block_type = "css_variable" if is_variable else "css_property"
            block_name = stripped.split(':')[0].strip()[:40] if ':' in stripped else stripped[:40]
            prop_end = i
            for k in range(i, min(i + 15, n)):
                if ';' in lines[k]:
                    prop_end = k
                    break
            blocks.append({
                "type": block_type,
                "name": block_name,
                "code": "".join(lines[i:prop_end + 1]),
                "start": i,
                "end": prop_end,
                "children": []
            })
            i = prop_end + 1
            continue

        i += 1

    if blocks:
        return blocks

    return [{"type": "css_file", "name": Path(file_path).name if file_path else "Stylesheet.css", "code": code, "start": 0, "end": max(n - 1, 0), "children": []}]


# ═══════════════════════════════════════════════════════════════════════
#  SHELL / BASH PARSER
# ═══════════════════════════════════════════════════════════════════════

def _parse_shell_blocks(code: str, file_path: str) -> list[dict]:
    """Parseur Shell : fonctions, if/then/fi, boucles, shebang, variables."""
    lines = code.splitlines(keepends=True)
    blocks = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if _is_blank(line):
            i += 1
            continue
        
        # Shebang
        if stripped.startswith('#!'):
            blocks.append({
                "type": "comment",
                "name": "Shebang",
                "code": line,
                "start": i,
                "end": i,
                "children": []
            })
            i += 1
            continue
        
        # Comments
        if stripped.startswith('#') and not stripped.startswith('#!'):
            end_idx = i
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('#') or _is_blank(lines[i]):
                    end_idx = i
                    i += 1
                else:
                    break
            while end_idx > 0 and _is_blank(lines[end_idx]):
                end_idx -= 1
            blocks.append({
                "type": "comment",
                "name": "Commentaire",
                "code": "".join(lines[i - (i - end_idx):i]),
                "start": i - (i - end_idx),
                "end": end_idx,
                "children": []
            })
            continue
        
        # Functions
        is_func = re.match(r'^(\w[\w_-]*)\s*\(\)', stripped)
        if is_func:
            name = is_func.group(1)
            # Find matching closing keyword
            end_idx = _find_shell_block_end(lines, i)
            blocks.append({
                "type": "function",
                "name": name,
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # if/for/while/case blocks
        is_control = re.match(r'^(if|for|while|until|case)\b', stripped)
        if is_control:
            end_idx = _find_shell_block_end(lines, i)
            blocks.append({
                "type": "logic_block",
                "name": f"{is_control.group(1)} block",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
            continue
        
        # Other code
        end_idx = i
        while end_idx < len(lines):
            s = lines[end_idx].strip()
            if _is_blank(lines[end_idx]):
                end_idx += 1
                continue
            if (re.match(r'^(\w[\w_-]*)\s*\(\)', s)
                or re.match(r'^(if|for|while|until|case)\b', s)
                or s.startswith('#')):
                break
            end_idx += 1
        end_idx -= 1
        while end_idx > i and _is_blank(lines[end_idx]):
            end_idx -= 1
        if end_idx >= i:
            blocks.append({
                "type": "other",
                "name": "Code",
                "code": "".join(lines[i:end_idx + 1]),
                "start": i,
                "end": end_idx,
                "children": []
            })
            i = end_idx + 1
        else:
            i += 1
    
    return blocks


def _find_shell_block_end(lines: list, start_idx: int) -> int:
    """Find end of shell block by tracking do/done, if/fi, case/esac."""
    open_close = {'do': 'done', 'then': 'fi', 'if': 'fi', 'for': 'done', 'while': 'done', 'until': 'done', 'case': 'esac'}
    stack = []
    for i in range(start_idx, len(lines)):
        stripped = lines[i].strip()
        # Skip comments
        if stripped.startswith('#'):
            continue
        words = stripped.split()
        for w in words:
            w = w.rstrip(';{')
            if w in open_close and w not in ('done', 'fi', 'esac'):
                stack.append(open_close[w])
            elif stack and w == stack[-1]:
                stack.pop()
                if not stack:
                    return i
    return len(lines) - 1


# ═══════════════════════════════════════════════════════════════════════
#  GENERIC FALLBACK PARSER (for unknown languages)
# ═══════════════════════════════════════════════════════════════════════

def _parse_generic_blocks(code: str, file_path: str) -> list[dict]:
    """
    Parseur générique : sépare le code en blocs logiques
    basé sur les lignes vides, les commentaires et l'indentation.
    """
    lines = code.splitlines(keepends=True)
    if not lines:
        return [{"type": "other", "name": "Empty", "code": code, "start": 0, "end": 0, "children": []}]
    
    blocks = []
    block_start = 0
    i = 0
    
    while i < len(lines):
        stripped = lines[i].strip()
        
        # Detect blank line separators (2+ consecutive blank lines = block boundary)
        if _is_blank(lines[i]) and i + 1 < len(lines) and _is_blank(lines[i + 1]):
            end_idx = i - 1
            # Trim trailing blanks
            while end_idx > block_start and _is_blank(lines[end_idx]):
                end_idx -= 1
            if end_idx >= block_start:
                blocks.append({
                    "type": "other",
                    "name": f"Bloc {len(blocks) + 1}",
                    "code": "".join(lines[block_start:end_idx + 1]),
                    "start": block_start,
                    "end": end_idx,
                    "children": []
                })
            # Skip blank lines
            while i < len(lines) and _is_blank(lines[i]):
                i += 1
            block_start = i
        else:
            i += 1
    
    # Last block
    if block_start < len(lines):
        end_idx = len(lines) - 1
        while end_idx > block_start and _is_blank(lines[end_idx]):
            end_idx -= 1
        blocks.append({
            "type": "other",
            "name": f"Bloc {len(blocks) + 1}",
            "code": "".join(lines[block_start:end_idx + 1]),
            "start": block_start,
            "end": end_idx,
            "children": []
        })
    
    return blocks if blocks else [{"type": "other", "name": "Code", "code": code, "start": 0, "end": len(lines) - 1, "children": []}]


# ═══════════════════════════════════════════════════════════════════════
#  MAIN DISPATCHER - Routing par extension
# ═══════════════════════════════════════════════════════════════════════

def parse_blocks(code: str, file_path: str = "") -> list[dict]:
    ext = Path(file_path).suffix.lower() if file_path else ""
    
    # HTML / Templates
    if ext in ('.html', '.htm', '.jinja', '.jinja2', '.xhtml'):
        return _parse_template_blocks(code, file_path)
    # CSS / SCSS
    elif ext in ('.css', '.scss', '.sass', '.less'):
        return _parse_css_blocks(code, file_path)
    # JavaScript / TypeScript
    elif ext in ('.js', '.jsx', '.mjs', '.cjs'):
        return _parse_js_blocks(code, file_path)
    elif ext in ('.ts', '.tsx'):
        return _parse_js_blocks(code, file_path)
    # C / C++ / Obj-C
    elif ext in ('.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx', '.m', '.mm'):
        return _parse_c_blocks(code, file_path)
    # Shell / Bash
    elif ext in ('.sh', '.bash', '.zsh', '.fish'):
        return _parse_shell_blocks(code, file_path)
    # Python (default pour .py, .pyw, .pyi, et fichiers sans extension connue)
    elif ext in ('.py', '.pyw', '.pyi'):
        return _parse_python_blocks(code, file_path)
    # Java
    elif ext in ('.java', '.kt', '.kts'):
        return _parse_c_blocks(code, file_path)
    # Go
    elif ext == '.go':
        return _parse_c_blocks(code, file_path)
    # Rust
    elif ext == '.rs':
        return _parse_c_blocks(code, file_path)
    # PHP
    elif ext == '.php':
        return _parse_c_blocks(code, file_path)
    # Ruby
    elif ext in ('.rb', '.erb'):
        return _parse_python_blocks(code, file_path)
    # Lua
    elif ext == '.lua':
        return _parse_python_blocks(code, file_path)
    # SQL
    elif ext in ('.sql', '.mysql', '.pgsql'):
        return _parse_shell_blocks(code, file_path)
    # YAML / TOML / JSON / Config
    elif ext in ('.yaml', '.yml', '.toml', '.json', '.xml', '.ini', '.cfg', '.conf'):
        return _parse_generic_blocks(code, file_path)
    # Dockerfile, Makefile, etc.
    elif ext in ('.dockerfile',) or Path(file_path).name in ('Dockerfile', 'Makefile', 'Rakefile', 'Gemfile', 'CMakeLists.txt'):
        return _parse_shell_blocks(code, file_path)
    # Default: generic parser
    else:
        return _parse_generic_blocks(code, file_path)


# ═══════════════════════════════════════════════════════════════════════
#  SYNTAX HIGHLIGHTING (GtkSource Language Map)
# ═══════════════════════════════════════════════════════════════════════

# Mapping extension -> GtkSource language ID for proper syntax highlighting
GTKSOURCE_LANG_MAP = {
    # Python
    'py': 'python', 'pyw': 'python', 'pyi': 'python', 'pyx': 'python',
    # JavaScript / TypeScript (JS reste prioritaire pour la coloration)
    'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript', 'tsx': 'typescript',
    # Web
    'css': 'css', 'scss': 'scss', 'sass': 'sass', 'less': 'less',
    'html': 'html', 'htm': 'html', 'xhtml': 'html',
    'jinja': 'html', 'jinja2': 'html', 'django': 'html', 'twig': 'html',
    # C-family
    'c': 'c', 'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'c++': 'cpp',
    'h': 'c', 'hpp': 'cpp', 'hxx': 'cpp', 'hh': 'cpp',
    'm': 'objc', 'mm': 'objc',
    'cs': 'cs',                          # C#
    # JVM
    'java': 'java', 'kt': 'kotlin', 'kts': 'kotlin', 'scala': 'scala',
    'groovy': 'groovy',
    # Systèmes
    'go': 'go', 'rs': 'rust', 'swift': 'swift', 'm': 'objc',
    # Scripting
    'rb': 'ruby', 'erb': 'html',
    'sh': 'sh', 'bash': 'sh', 'zsh': 'sh', 'fish': 'fish', 'ksh': 'sh',
    'pl': 'perl', 'pm': 'perl',
    'lua': 'lua', 'tcl': 'tcl',
    'php': 'php', 'phtml': 'php',
    # Données / Config
    'sql': 'sql', 'mysql': 'sql', 'pgsql': 'sql', 'sqlite': 'sql',
    'json': 'json', 'jsonc': 'json', 'json5': 'json',
    'xml': 'xml', 'xsl': 'xml', 'xslt': 'xml', 'svg': 'xml',
    'yaml': 'yaml', 'yml': 'yaml',
    'toml': 'toml',
    'ini': 'ini', 'cfg': 'ini', 'conf': 'ini', 'properties': 'ini',
    # Divers
    'md': 'markdown', 'markdown': 'markdown',
    'rst': 'rst', 'tex': 'tex', 'bib': 'tex',
    'dockerfile': 'dockerfile',
    'diff': 'diff', 'patch': 'diff',
    'vim': 'vim', 'vimrc': 'vim',
    'asm': 'asm', 's': 'asm',
    'vhdl': 'vhdl', 'verilog': 'verilog',
    'proto': 'proto', 'protobuf': 'proto',
    'graphql': 'graphql', 'gql': 'graphql',
    # Texte brut
    'txt': 'text', 'log': 'text',
}


def get_gtksource_lang_id(file_ext: str) -> str:
    """
    Retourne l'ID de langage GtkSource pour une extension donnée.
    Garantit un ID non-vide : retombe sur 'text' si inconnu.
    """
    if not file_ext:
        return 'text'
    ext = file_ext.lstrip('.').lower()
    return GTKSOURCE_LANG_MAP.get(ext, 'text')


def get_gtksource_lang_id_for_filename(filename: str) -> str:
    """
    Résout l'ID de langage GtkSource à partir d'un nom de fichier complet.
    Gère les fichiers sans extension comme Dockerfile, Makefile, .bashrc, etc.
    """
    if not filename:
        return 'text'
    p = Path(filename)
    name_lower = p.name.lower()
    # Fichiers spéciaux (sans extension)
    special = {
        'dockerfile': 'dockerfile',
        'containerfile': 'dockerfile',
        'makefile': 'sh',
        'gnumakefile': 'sh',
        'rakefile': 'ruby',
        'gemfile': 'ruby',
        'cmakelists.txt': 'cmake',
        'vagrantfile': 'ruby',
        '.bashrc': 'sh', '.bash_profile': 'sh', '.profile': 'sh',
        '.zshrc': 'sh', '.zshenv': 'sh',
        '.vimrc': 'vim', '.gvimrc': 'vim',
    }
    if name_lower in special:
        return special[name_lower]
    if name_lower.startswith('.'):
        special_hidden = {'.bashrc': 'sh', '.zshrc': 'sh', '.vimrc': 'vim',
                          '.profile': 'sh', '.bash_profile': 'sh'}
        if name_lower in special_hidden:
            return special_hidden[name_lower]
    return get_gtksource_lang_id(p.suffix)


# ═══════════════════════════════════════════════════════════════════════

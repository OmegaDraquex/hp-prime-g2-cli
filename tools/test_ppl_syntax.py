"""
Strict HP Prime G2 PPL Linter, Parser & AST Interpreter
Enforces all compilation and runtime rules measured on HP Prime G2 (firmware 2.4.15515)
and the HP Prime Virtual Calculator, adapted from JordiRigau/hp-prime-kit.
"""

import sys
import re
import math
import random

BANNED_KEYWORDS = {
    "ELSEIF", "ELIF", "ENDIF", "ENDFOR", "ENDWHILE",
    "ENDCASE", "ENDFUNC", "ENDPROC"
}

KNOWN_PPL_BUILTINS = {
    "RGB", "RECT_P", "RECT", "LINE_P", "LINE", "ARC_P", "ARC",
    "PIXON_P", "PIXON", "TEXTOUT_P", "TEXTOUT", "BLIT_P", "BLIT",
    "DIMGROB_P", "DIMGROB", "RANDINT", "SIZE", "TYPE", "STRING",
    "CONCAT", "IFTE", "MIN", "MAX", "WAIT", "GETKEY", "MOUSE",
    "MSGBOX", "INPUT", "CHOOSE", "PRINT", "EXPR", "MID", "LEFT",
    "RIGHT", "POS", "MEMBER", "FILLPOLY_P", "INVERT_P", "DRAWMENU"
}

KEYWORDS = {
    "IF", "THEN", "ELSE", "END", "FOR", "FROM", "TO", "DOWNTO",
    "STEP", "DO", "WHILE", "REPEAT", "UNTIL", "CASE", "DEFAULT",
    "BREAK", "CONTINUE", "RETURN", "LOCAL", "EXPORT", "BEGIN",
    "AND", "OR", "NOT", "IFTE", "MOD", "XOR"
}


# ============================================================================
# PART 1: STATIC LINTER (HP Prime G2 Hardware Compilation Rules)
# ============================================================================
def validate_ppl(source_code):
    lines = source_code.splitlines()
    errors = []
    warnings = []

    block_stack = []
    defined_funcs = set()
    declared_forwards = {}
    defined_globals = set()

    # Check non-ASCII characters in source
    for line_num, raw_line in enumerate(lines, 1):
        for ch in raw_line:
            if ord(ch) > 127:
                errors.append(
                    f"Line {line_num}: [non-ascii] Non-ASCII character {ch!r} (U+{ord(ch):04X}) found"
                )

    # Strip comments and replace string literals with placeholders
    clean_lines = []
    for line in lines:
        c_idx = line.find("//")
        if c_idx != -1:
            line = line[:c_idx]
        line = re.sub(r'"[^"]*"', '""', line)
        clean_lines.append(line)

    in_func = False
    seen_code_in_func = False
    current_locals = set()

    for line_num, line in enumerate(clean_lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # 1. Check banned keywords (ELSEIF, ENDIF, etc.)
        words = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', stripped)
        for w in words:
            wu = w.upper()
            if wu in BANNED_KEYWORDS:
                errors.append(
                    f"Line {line_num}: [invalid-keyword] '{w}' does not exist in HP PPL! Use IF..THEN..ELSE..END; or CASE."
                )

        # 2. Forbid square-bracket indexing var[...] (HP PPL only uses [ ] for matrix literals, not postfix indexing!)
        for m_sq in re.finditer(r'([A-Za-z0-9_)\]])\s*\[', stripped):
            errors.append(
                f"Line {line_num}: [square-bracket-index] Invalid '[' after '{m_sq.group(1)}': HP PPL uses parentheses L(i) for list/matrix indexing, NOT square brackets L[i]!"
            )

        # 3. Check function definitions and forward declarations at top level
        if not block_stack:
            m_exp_var = re.match(r'^EXPORT\s+([A-Za-z_]\w*)\s*(?::=.*)?;', stripped, re.I)
            if m_exp_var and "(" not in stripped.split(":=")[0]:
                defined_globals.add(m_exp_var.group(1))
                if stripped.count(":=") > 1:
                    warnings.append(f"Line {line_num}: [export-initialised] Prefer 1 initialised EXPORT per line")
                continue

            m_fwd = re.match(r'^([A-Za-z_]\w*)\s*\(([^)]*)\)\s*;$', stripped)
            if m_fwd:
                fname = m_fwd.group(1)
                if fname.upper() not in KEYWORDS and fname.upper() not in KNOWN_PPL_BUILTINS:
                    declared_forwards[fname] = line_num
                continue

            m_fn = re.match(r'^(?:EXPORT\s+)?([A-Za-z_]\w*)\s*\(([^)]*)\)\s*$', stripped, re.I)
            if m_fn:
                fname = m_fn.group(1)
                defined_funcs.add(fname)
                params = [p.strip() for p in m_fn.group(2).split(",") if p.strip()]
                current_locals = set(params)
                continue

        # 4. Check LOCAL rules (ppl.locals-at-top & ppl.local-limit)
        if re.match(r'^LOCAL\b', stripped, re.I):
            if not in_func:
                errors.append(f"Line {line_num}: [local-outside-func] LOCAL outside BEGIN..END")
            elif seen_code_in_func:
                errors.append(
                    f"Line {line_num}: [local-first] LOCAL declared after executable statements [ppl.locals-at-top, G2]"
                )
            local_body = re.sub(r'^LOCAL\s+', '', stripped, flags=re.I).rstrip(';')
            local_body_no_lists = re.sub(r'\{[^}]*\}', '{}', local_body)
            local_vars = [v.strip() for v in local_body_no_lists.split(',') if v.strip()]
            if len(local_vars) >= 9:
                errors.append(
                    f"Line {line_num}: [local-limit] {len(local_vars)} variables in one LOCAL (max 8, safe <=6) [ppl.local-limit, G2]"
                )
            elif len(local_vars) >= 7:
                warnings.append(
                    f"Line {line_num}: [local-limit] {len(local_vars)} variables in one LOCAL (prefer <=6) [ppl.local-limit, G2]"
                )
            for lv in local_vars:
                vname = lv.split(":=")[0].strip()
                current_locals.add(vname)
            continue

        # 5. Check index-call: e.g. FUNC(...)(...)
        if re.search(r'\)\s*\(', stripped):
            errors.append(
                f"Line {line_num}: [index-call] Cannot index the result of a call directly [ppl.index-call, G2]"
            )

        # 6. Check equality-statement: single '=' used for assignment at start of statement
        if re.match(r'^[A-Za-z_]\w*(?:\([^)]+\))?\s*=\s*[^=]', stripped):
            errors.append(
                f"Line {line_num}: [equality-statement] Single '=' assigns nothing; use ':=' [ppl.equality-operators, G2]"
            )

        # 7. Check TEXTOUT_P arguments (font != 0 and width provided)
        if "TEXTOUT_P" in stripped.upper():
            m_to = re.search(r'TEXTOUT_P\s*\((.*)\)\s*;', stripped, re.I)
            if m_to:
                args_str = m_to.group(1)
                depth = 0
                args = []
                cur = []
                for c in args_str:
                    if c in '([{':
                        depth += 1
                    elif c in ')]}':
                        depth -= 1
                    if c == ',' and depth == 0:
                        args.append(''.join(cur).strip())
                        cur = []
                    else:
                        cur.append(c)
                args.append(''.join(cur).strip())
                if len(args) < 6:
                    warnings.append(
                        f"Line {line_num}: [textout-width] TEXTOUT_P has {len(args)} args; pass explicit width [interface.textout-width, G2]"
                    )
                font_arg = args[4] if len(args) >= 7 else (args[3] if len(args) >= 4 else "")
                if font_arg == "0":
                    errors.append(
                        f"Line {line_num}: [textout-font] TEXTOUT_P font is 0; HP PPL fonts are 1 (small), 2 (normal), 3 (large)"
                    )

        # 8. Check unknown function/list calls
        for m_call in re.finditer(r'\b([A-Za-z_]\w*)\s*\(', stripped):
            cname = m_call.group(1)
            cu = cname.upper()
            if (cu not in KNOWN_PPL_BUILTINS
                    and cu not in KEYWORDS
                    and cname not in defined_funcs
                    and cname not in declared_forwards
                    and cname not in current_locals
                    and cname not in defined_globals):
                errors.append(
                    f"Line {line_num}: [unknown-name] Call/index on unknown identifier '{cname}'"
                )

        # 9. Block tracking
        tokens = re.findall(r'\b[A-Za-z_]\w*\b|;', stripped)
        i = 0
        while i < len(tokens):
            tu = tokens[i].upper()
            if tu == "BEGIN":
                block_stack.append(("BEGIN", line_num))
                in_func = True
                seen_code_in_func = False
            elif tu in ("IF", "FOR", "WHILE", "CASE"):
                block_stack.append((tu, line_num))
                if in_func:
                    seen_code_in_func = True
            elif tu == "REPEAT":
                block_stack.append(("REPEAT", line_num))
                if in_func:
                    seen_code_in_func = True
            elif tu == "UNTIL":
                if not block_stack or block_stack[-1][0] != "REPEAT":
                    errors.append(f"Line {line_num}: [unbalanced] UNTIL without matching REPEAT")
                else:
                    block_stack.pop()
            elif tu == "END":
                if i + 1 >= len(tokens) or tokens[i + 1] != ";":
                    errors.append(f"Line {line_num}: [end-semicolon] END without ';' [ppl.end-semicolon, G2]")
                if not block_stack:
                    errors.append(f"Line {line_num}: [unbalanced] END without matching block")
                else:
                    top_type, _ = block_stack.pop()
                    if top_type == "BEGIN" and not block_stack:
                        in_func = False
                        seen_code_in_func = False
            else:
                if in_func and tu not in ("LOCAL", ";"):
                    seen_code_in_func = True
            i += 1

        # 10. Balanced delimiters per line
        if stripped.count('(') != stripped.count(')'):
            errors.append(f"Line {line_num}: Unbalanced parentheses")
        if stripped.count('[') != stripped.count(']'):
            errors.append(f"Line {line_num}: Unbalanced brackets")
        if stripped.count('{') != stripped.count('}'):
            errors.append(f"Line {line_num}: Unbalanced braces")

    for fwd_name, fwd_line in declared_forwards.items():
        if fwd_name not in defined_funcs:
            errors.append(
                f"Line {fwd_line}: [undefined-forward] Forward-declared function '{fwd_name}()' is never defined!"
            )

    if block_stack:
        errors.append(f"[unbalanced] Unclosed blocks at end of file: {block_stack}")

    return errors, warnings


# ============================================================================
# PART 2: HP PPL LEXER, PARSER & INTERPRETER (hp-prime-kit)
# ============================================================================
class PPLError(Exception):
    pass


TOKEN_SPEC = re.compile(r"""
    (?P<SPACE>   [ \t\r]+ )
  | (?P<NL>      \n )
  | (?P<COMMENT> //[^\n]* )
  | (?P<STR>     "(?:""|\\.|[^"\n])*" )
  | (?P<HEX>     \#[0-9A-Fa-f]+h\b )
  | (?P<NUM>     \d+(?:\.\d+)?(?:[eE][+-]?\d+)? )
  | (?P<OP2>     :=|==|<>|!=|<=|>=|\.\. )
  | (?P<OP1>     [+\-*/^=<>,;:()\[\]{}] )
  | (?P<WORD>    [A-Za-z_]\w* )
""", re.VERBOSE)


class Tok(object):
    __slots__ = ('kind', 'val', 'line')
    def __init__(self, kind, val, line):
        self.kind = kind
        self.val = val
        self.line = line


def lex(text):
    line = 1
    pos = 0
    n = len(text)
    out = []
    while pos < n:
        m = TOKEN_SPEC.match(text, pos)
        if not m:
            raise PPLError(f'line {line}: unexpected character {text[pos]!r}')
        kind = m.lastgroup
        val = m.group()
        pos = m.end()
        if kind == 'NL':
            line += 1
        elif kind in ('SPACE', 'COMMENT'):
            continue
        elif kind == 'WORD':
            u = val.upper()
            out.append(Tok(u if u in KEYWORDS else 'ID', val, line))
        elif kind == 'NUM':
            out.append(Tok('NUM', float(val), line))
        elif kind == 'HEX':
            out.append(Tok('NUM', float(int(val[1:-1], 16)), line))
        elif kind == 'STR':
            body = val[1:-1].replace('""', '"').replace(r'\"', '"')
            out.append(Tok('STR', body, line))
        else:
            out.append(Tok(val, val, line))
    out.append(Tok('EOF', '', line))
    return out


class Parser(object):
    def __init__(self, tokens, filename='<ppl>'):
        self.toks = tokens
        self.i = 0
        self.filename = filename

    def peek(self, k=0):
        idx = min(self.i + k, len(self.toks) - 1)
        return self.toks[idx]

    def at(self, *kinds):
        return self.peek().kind in kinds

    def take(self, *kinds):
        t = self.peek()
        if kinds and t.kind not in kinds:
            want = ' or '.join(kinds)
            raise PPLError(f'{self.filename}:{t.line}: expected {want}, got {t.val!r}')
        self.i += 1
        return t

    def match(self, *kinds):
        if self.at(*kinds):
            return self.take()
        return None

    def program(self):
        funcs, globs = {}, []
        while not self.at('EOF'):
            self.match('EXPORT')
            if self.at('ID') and self.peek(1).kind == '(':
                name = self.take('ID').val
                self.take('(')
                params = []
                if not self.at(')'):
                    params.append(self.take('ID').val)
                    while self.match(','):
                        params.append(self.take('ID').val)
                self.take(')')
                if self.match(';'):
                    continue
                body = self.block()
                self.match(';')
                funcs[name] = (params, body)
            elif self.at('ID'):
                globs.extend(self._decl_list())
                self.take(';')
            else:
                t = self.peek()
                raise PPLError(f'{self.filename}:{t.line}: unexpected {t.val!r} at top level')
        return funcs, globs

    def _decl_list(self):
        items = []
        while True:
            name = self.take('ID').val
            init = self.expr() if self.match(':=', '=') else None
            items.append((name, init))
            if not self.match(','):
                return items

    def block(self):
        self.take('BEGIN')
        stmts = self.stmt_list('END')
        self.take('END')
        return stmts

    def stmt_list(self, *enders):
        stmts = []
        while not self.at(*enders) and not self.at('EOF'):
            if self.match(';'):
                continue
            stmts.append(self.stmt())
            self.match(';')
        return stmts

    def stmt(self):
        if self.match('LOCAL'):
            return ('local', self._decl_list())
        if self.match('IF'):
            return self._if()
        if self.match('CASE'):
            return self._case()
        if self.match('FOR'):
            return self._for()
        if self.match('WHILE'):
            cond = self.expr()
            self.take('DO')
            body = self.stmt_list('END')
            self.take('END')
            return ('while', cond, body)
        if self.match('REPEAT'):
            body = self.stmt_list('UNTIL')
            self.take('UNTIL')
            cond = self.expr()
            return ('repeat', body, cond)
        if self.match('RETURN'):
            if self.at(';', 'END', 'ELSE'):
                return ('return', None)
            return ('return', self.expr())
        if self.match('BREAK'):
            n = self.expr() if self.at('NUM') else None
            return ('break', n)
        if self.match('CONTINUE'):
            return ('continue',)
        if self.at('BEGIN'):
            return ('block', self.block())
        e = self.expr()
        if self.match(':='):
            return ('assign', e, self.expr())
        return ('expr', e)

    def _if(self):
        cond = self.expr()
        self.take('THEN')
        then = self.stmt_list('ELSE', 'END')
        els = []
        if self.match('ELSE'):
            els = self.stmt_list('END')
        self.take('END')
        return ('if', cond, then, els)

    def _case(self):
        arms, default = [], []
        while not self.at('END', 'EOF'):
            if self.match(';'):
                continue
            if self.match('IF'):
                c = self.expr()
                self.take('THEN')
                b = self.stmt_list('END')
                self.take('END')
                self.match(';')
                arms.append((c, b))
            elif self.match('DEFAULT'):
                default = self.stmt_list('END')
            else:
                t = self.peek()
                raise PPLError(f'{self.filename}:{t.line}: inside CASE expected IF or DEFAULT, got {t.val!r}')
        self.take('END')
        return ('case', arms, default)

    def _for(self):
        var = self.take('ID').val
        self.take('FROM')
        init = self.expr()
        direction = -1 if self.match('DOWNTO') else (self.take('TO') and 1)
        limit = self.expr()
        step = self.expr() if self.match('STEP') else None
        self.take('DO')
        body = self.stmt_list('END')
        self.take('END')
        return ('for', var, init, limit, step, direction, body)

    def expr(self):
        return self._or()

    def _or(self):
        e = self._and()
        while self.match('OR', 'XOR'):
            e = ('bin', 'OR', e, self._and())
        return e

    def _and(self):
        e = self._not()
        while self.match('AND'):
            e = ('bin', 'AND', e, self._not())
        return e

    def _not(self):
        if self.match('NOT'):
            return ('un', 'NOT', self._not())
        return self._cmp()

    def _cmp(self):
        e = self._add()
        while self.at('==', '=', '<>', '!=', '<', '<=', '>', '>='):
            op = self.take().kind
            e = ('bin', op, e, self._add())
        return e

    def _add(self):
        e = self._mul()
        while self.at('+', '-'):
            op = self.take().kind
            e = ('bin', op, e, self._mul())
        return e

    def _mul(self):
        e = self._pow()
        while self.at('*', '/', 'MOD'):
            op = self.take().kind
            e = ('bin', op, e, self._pow())
        return e

    def _pow(self):
        e = self._unary()
        if self.match('^'):
            e = ('bin', '^', e, self._pow())
        return e

    def _unary(self):
        if self.match('-'):
            return ('un', '-', self._unary())
        if self.match('+'):
            return self._unary()
        return self._postfix()

    def _postfix(self):
        e = self._atom()
        while self.match('('):
            args = []
            if not self.at(')'):
                args.append(self.expr())
                while self.match(','):
                    args.append(self.expr())
            self.take(')')
            e = ('call', e, args)
        return e

    def _atom(self):
        t = self.peek()
        if self.match('NUM'):
            return ('num', t.val)
        if self.match('STR'):
            return ('str', t.val)
        if self.match('ID') or self.match('IFTE'):
            return ('var', t.val)
        if self.match('('):
            e = self.expr()
            self.take(')')
            return e
        if self.match('{'):
            items = []
            if not self.at('}'):
                items.append(self.expr())
                while self.match(','):
                    items.append(self.expr())
            self.take('}')
            return ('seq', items)
        raise PPLError(f'{self.filename}:{t.line}: unexpected token {t.val!r} in expression')


class _Return(Exception):
    def __init__(self, value):
        self.value = value


def _truth(v):
    if isinstance(v, (int, float)):
        return v != 0.0
    if isinstance(v, (list, str)):
        return len(v) > 0
    return bool(v)


def _as_text(v):
    if isinstance(v, str):
        return v
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    if isinstance(v, list):
        return '{%s}' % ','.join(_as_text(x) for x in v)
    return str(v)


class Machine(object):
    def __init__(self, touch_events=None):
        self.funcs = {}
        self.globals_ = {f'G{i}': float(i) for i in range(10)}
        self.io = []
        self.touch_events = list(touch_events) if touch_events else []

    def load(self, text, filename='<ppl>'):
        funcs, globs = Parser(lex(text), filename).program()
        self.funcs.update(funcs)
        for name, init in globs:
            self.globals_[name] = self.evaluate(init, {}) if init is not None else 0.0

    def call(self, name, *args):
        if name not in self.funcs:
            raise PPLError(f'no such function: {name}')
        params, body = self.funcs[name]
        if len(args) != len(params):
            raise PPLError(f'{name} takes {len(params)} arguments, got {len(args)}')
        frame = {p: (list(a) if isinstance(a, list) else a) for p, a in zip(params, args)}
        prev_fn = getattr(self, '_cur_fn', None)
        self._cur_fn = name
        try:
            last = self.run(body, frame)
        except _Return as d:
            self._cur_fn = prev_fn
            return d.value
        self._cur_fn = prev_fn
        return last if last is not None else 0.0

    def run(self, statements, frame):
        last = None
        for s in statements:
            v = self._stmt(s, frame)
            if v is not None:
                last = v
        return last

    def _stmt(self, s, frame):
        kind = s[0]
        if kind == 'local':
            for name, init in s[1]:
                frame[name] = self.evaluate(init, frame) if init is not None else 0.0
        elif kind == 'assign':
            value = self.evaluate(s[2], frame)
            self._assign(s[1], value, frame)
            return value
        elif kind == 'expr':
            return self.evaluate(s[1], frame)
        elif kind == 'if':
            if _truth(self.evaluate(s[1], frame)):
                return self.run(s[2], frame)
            return self.run(s[3], frame)
        elif kind == 'for':
            _, var, init, enders, step, direction, body = s
            i = self.evaluate(init, frame)
            limit = self.evaluate(enders, frame)
            inc = abs(self.evaluate(step, frame) if step is not None else 1.0) * direction
            last = None
            while (inc > 0 and i <= limit) or (inc < 0 and i >= limit):
                frame[var] = i
                v = self.run(body, frame)
                if v is not None:
                    last = v
                i = frame[var] + inc
            return last
        elif kind == 'while':
            last = None
            while _truth(self.evaluate(s[1], frame)):
                v = self.run(s[2], frame)
                if v is not None:
                    last = v
            return last
        elif kind == 'repeat':
            last = None
            while True:
                v = self.run(s[1], frame)
                if v is not None:
                    last = v
                if _truth(self.evaluate(s[2], frame)):
                    break
            return last
        elif kind == 'return':
            raise _Return(self.evaluate(s[1], frame) if s[1] is not None else 0.0)
        elif kind == 'block':
            return self.run(s[1], frame)
        else:
            raise PPLError(f'Unsupported statement {kind}')

    def _assign(self, target, value, frame):
        if target[0] == 'var':
            name = target[1]
            if name in frame:
                frame[name] = value
            else:
                self.globals_[name] = value
            return
        if target[0] == 'call':
            base, args = target[1], target[2]
            if base[0] != 'var':
                raise PPLError('assignment target too complex')
            name = base[1]
            container = frame[name] if name in frame else self.globals_.get(name)
            idx = [int(self.evaluate(a, frame)) for a in args]
            if isinstance(container, list):
                i = idx[0]
                if i == len(container) + 1 or i == 0:
                    container.append(value)
                    return
                if not (1 <= i <= len(container)):
                    raise PPLError(f'index {i} out of range in {name} (1..{len(container)})')
                container[i - 1] = value
                return
            raise PPLError(f'{name} is not a list')
        raise PPLError(f'invalid assignment target {target[0]}')

    def evaluate(self, e, frame):
        kind = e[0]
        if kind in ('num', 'str'):
            return e[1]
        if kind == 'var':
            name = e[1]
            if name in frame:
                return frame[name]
            if name in self.globals_:
                return self.globals_[name]
            if name in self.funcs:
                return self.call(name)
            if name.upper() == 'GETKEY':
                if getattr(self, '_cur_fn', None) == 'GetTouchInput' and self.touch_events and self.touch_events[0][0] == 'key':
                    _, k = self.touch_events.pop(0)
                    return float(k)
                return -1.0
            if name.upper() == 'MOUSE':
                if getattr(self, '_cur_fn', None) == 'GetTouchInput' and self.touch_events and self.touch_events[0][0] == 'touch':
                    _, tx, ty = self.touch_events.pop(0)
                    return [[float(tx), float(ty), float(tx), float(ty), 0.0], []]
                return [[], []]
            raise PPLError(f'undefined variable: {name}')
        if kind == 'seq':
            return [self.evaluate(x, frame) for x in e[1]]
        if kind == 'un':
            v = self.evaluate(e[2], frame)
            if e[1] == '-':
                return -v
            return 0.0 if _truth(v) else 1.0
        if kind == 'bin':
            op, ia, ib = e[1], e[2], e[3]
            if op == 'AND':
                return 1.0 if (_truth(self.evaluate(ia, frame)) and _truth(self.evaluate(ib, frame))) else 0.0
            if op == 'OR':
                return 1.0 if (_truth(self.evaluate(ia, frame)) or _truth(self.evaluate(ib, frame))) else 0.0
            a, b = self.evaluate(ia, frame), self.evaluate(ib, frame)
            if op == '+':
                if isinstance(a, str) or isinstance(b, str):
                    return _as_text(a) + _as_text(b)
                return a + b
            if op == '-': return a - b
            if op == '*': return a * b
            if op == '/': return a / b
            if op in ('==', '='): return 1.0 if a == b else 0.0
            if op in ('<>', '!='): return 1.0 if a != b else 0.0
            if op == '<': return 1.0 if a < b else 0.0
            if op == '<=': return 1.0 if a <= b else 0.0
            if op == '>': return 1.0 if a > b else 0.0
            if op == '>=': return 1.0 if a >= b else 0.0
            raise PPLError(f'unknown operator {op}')
        if kind == 'call':
            base, arg_nodes = e[1], e[2]
            if base[0] == 'var' and base[1].upper() == 'IFTE' and len(arg_nodes) == 3:
                cond = self.evaluate(arg_nodes[0], frame)
                return self.evaluate(arg_nodes[1] if _truth(cond) else arg_nodes[2], frame)
            if base[0] == 'var':
                name = base[1]
                container = frame.get(name, self.globals_.get(name))
                if isinstance(container, list):
                    idx = int(round(self.evaluate(arg_nodes[0], frame)))
                    if not (1 <= idx <= len(container)):
                        raise PPLError(f'index {idx} out of range in {name} (1..{len(container)})')
                    return container[idx - 1]
                if name in self.funcs:
                    return self.call(name, *[self.evaluate(a, frame) for a in arg_nodes])
                cu = name.upper()
                args = [self.evaluate(a, frame) for a in arg_nodes]
                if cu == 'SIZE':
                    return float(len(args[0]))
                if cu == 'STRING':
                    return f'"{args[0]}"' if isinstance(args[0], str) else _as_text(args[0])
                if cu == 'CONCAT':
                    return list(args[0]) + list(args[1])
                if cu == 'RGB':
                    return float(int(args[0]) * 65536 + int(args[1]) * 256 + int(args[2]))
                if cu == 'RANDINT':
                    return float(random.randint(int(args[0]), int(args[1])))
                if cu == 'MIN':
                    return min(args)
                if cu == 'MAX':
                    return max(args)
                if cu in ('RECT_P', 'LINE_P', 'PIXON_P', 'TEXTOUT_P', 'BLIT_P', 'DIMGROB_P', 'WAIT'):
                    self.io.append((cu, args))
                    return 0.0
            raise PPLError(f'unsupported call {e}')


def verify_ast_and_runtime(source_code, filename):
    # Scripted touchscreen & key sequence for a full game cycle inside LOOGYPOKER():
    # 1. Tap [+] bet (130, 220)
    # 2. Tap [-] bet (25, 220)
    # 3. Tap [DEAL] (200, 220)
    # 4. Tap card 1..5 to toggle discards
    # 5. Tap [DRAW / HOLD] (160, 220)
    # 6. Tap to continue on Result screen (160, 220)
    # 7. Tap [RESET] (285, 220)
    # 8. Press ESC (key 4) to exit cleanly
    events = [
        ('touch', 130, 220),
        ('touch', 25, 220),
        ('touch', 200, 220),
        ('touch', 30, 160),
        ('touch', 95, 160),
        ('touch', 155, 160),
        ('touch', 220, 160),
        ('touch', 280, 160),
        ('touch', 160, 220),
        ('touch', 160, 220),
        ('touch', 285, 220),
        ('key', 4),
    ]
    m = Machine(touch_events=events)
    m.load(source_code, filename)

    # 1. Execute ShuffleDeck on 30-card deck
    deck = [float(r) for r in range(1, 7) for _ in range(5)]
    shuffled = m.call('ShuffleDeck', deck)
    assert len(shuffled) == 30 and sorted(shuffled) == sorted(deck)

    # 2. Execute EvalHand and CompHands on sample hands
    h_5kind = m.call('EvalHand', [6.0, 6.0, 6.0, 6.0, 6.0])
    assert h_5kind == [6.0, 6.0, 0.0, 0.0, 0.0, 0.0], f"Unexpected 5-of-a-kind eval: {h_5kind}"

    h_fh = m.call('EvalHand', [5.0, 5.0, 5.0, 2.0, 2.0])
    assert h_fh == [4.0, 5.0, 2.0, 0.0, 0.0, 0.0], f"Unexpected Full House eval: {h_fh}"

    h_2pair = m.call('EvalHand', [6.0, 6.0, 3.0, 3.0, 1.0])
    assert h_2pair == [2.0, 6.0, 3.0, 1.0, 0.0, 0.0], f"Unexpected Two Pair eval: {h_2pair}"

    h_junk1 = m.call('EvalHand', [6.0, 5.0, 4.0, 3.0, 2.0])
    h_junk2 = m.call('EvalHand', [5.0, 4.0, 3.0, 2.0, 1.0])
    assert m.call('CompHands', h_5kind, h_fh) == 1.0
    assert m.call('CompHands', h_2pair, h_fh) == -1.0
    assert m.call('CompHands', h_junk1, h_junk2) == 0.0

    # 3. Execute full end-to-end game cycle of EXPORT LOOGYPOKER()
    ret = m.call('LOOGYPOKER')
    assert ret == 0.0

    return len(m.funcs), len(m.globals_), len(m.io)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_ppl_syntax.py <file.txt>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        src = f.read()

    errs, warns = validate_ppl(src)
    if errs:
        print(f"LINT FAILED with {len(errs)} error(s):")
        for e in errs:
            print("  ERROR:", e)
        for w in warns:
            print("  WARN:", w)
        sys.exit(1)

    try:
        n_funcs, n_globs, n_io = verify_ast_and_runtime(src, sys.argv[1])
    except PPLError as e:
        print(f"AST / RUNTIME VERIFICATION FAILED: {e}")
        sys.exit(1)

    print(f"LINT & AST INTERPRETER PASS (0 errors, {len(warns)} warnings): {sys.argv[1]}")
    print(f"  Parsed & executed {n_funcs} PPL functions, {n_globs} globals, and {n_io} G1/G0 graphics calls with 0 errors!")

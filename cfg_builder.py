#!/usr/bin/env python3
"""
CS5860 — reduced control-flow graph of a Java method.

A vertex is a basic block (longest run of statements that always execute
together), not one statement. Comments are dropped by the lexer.

python3 cfg_builder.py tests -o output
"""

from __future__ import annotations

import argparse
import html
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. Lexer — comments disappear here
# ---------------------------------------------------------------------------

KEYWORDS = {
    "if", "else", "while", "for", "do", "switch", "case", "default",
    "break", "continue", "return", "class", "public", "private",
    "protected", "static", "void", "int", "boolean", "true", "false",
}
TYPES = {"void", "int", "boolean"}
OPS = ["++", "--", "&&", "||", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/="]


@dataclass
class Tok:
    kind: str
    text: str


class Lexer:
    def __init__(self, src: str) -> None:
        self.s, self.n, self.i = src, len(src), 0

    def tokenize(self) -> List[Tok]:
        out: List[Tok] = []
        while True:
            t = self._next()
            out.append(t)
            if t.kind == "EOF":
                return out

    def _next(self) -> Tok:
        s, n = self.s, self.n
        while self.i < n:
            c = s[self.i]
            if c.isspace():
                self.i += 1
                continue
            if c == "/" and self.i + 1 < n and s[self.i + 1] == "/":
                while self.i < n and s[self.i] != "\n":
                    self.i += 1
                continue
            if c == "/" and self.i + 1 < n and s[self.i + 1] == "*":
                self.i += 2
                while self.i + 1 < n and not (s[self.i] == "*" and s[self.i + 1] == "/"):
                    self.i += 1
                self.i = min(self.i + 2, n)
                continue
            break
        if self.i >= n:
            return Tok("EOF", "")
        p, c = self.i, s[self.i]
        if c.isalpha() or c == "_":
            while self.i < n and (s[self.i].isalnum() or s[self.i] == "_"):
                self.i += 1
            t = s[p:self.i]
            return Tok("KW" if t in KEYWORDS else "ID", t)
        if c.isdigit():
            while self.i < n and (s[self.i].isdigit() or s[self.i] == "."):
                self.i += 1
            return Tok("NUM", s[p:self.i])
        if c in "\"'":
            q = c
            self.i += 1
            while self.i < n and s[self.i] != q:
                self.i += 1 + (s[self.i] == "\\")
            self.i += 1
            return Tok("STR", s[p:self.i])
        for op in OPS:
            if s.startswith(op, self.i):
                self.i += len(op)
                return Tok("OP", op)
        self.i += 1
        return Tok("OP", c)


# ---------------------------------------------------------------------------
# 2. Parser — Java subset to a statement tree
# ---------------------------------------------------------------------------

@dataclass
class AST:
    kind: str
    src: str = ""
    kids: List["AST"] = field(default_factory=list)
    cond: Optional["AST"] = None
    then: Optional["AST"] = None
    els: Optional["AST"] = None
    init: Optional["AST"] = None
    update: Optional["AST"] = None
    body: Optional["AST"] = None
    expr: Optional["AST"] = None
    lhs: Optional["AST"] = None
    rhs: Optional["AST"] = None
    cases: List[Tuple[List[str], List["AST"]]] = field(default_factory=list)


class Parser:
    def __init__(self, toks: List[Tok]) -> None:
        self.toks, self.i = toks, 0

    def t(self) -> Tok:
        return self.toks[self.i]

    def at(self, *xs: str) -> bool:
        return self.t().text in xs

    def eat(self, want: Optional[str] = None) -> Tok:
        tok = self.t()
        if want is not None and tok.text != want:
            raise SyntaxError(f"expected {want}, got {tok.text}")
        self.i += 1
        return tok

    def join(self, a: int, b: int) -> str:
        parts: List[str] = []
        for k in range(a, b):
            t = self.toks[k].text
            if not t:
                continue
            if parts and parts[-1][-1] not in ".([{" and t not in ".,;)]}":
                if not (t == "(" and parts[-1][-1].isalnum()):
                    parts.append(" ")
            parts.append(t)
        return "".join(parts)

    def parse_file(self) -> List[AST]:
        methods: List[AST] = []
        while self.t().kind != "EOF":
            if self.at("class"):
                methods.extend(self._class())
            elif self.at("public", "private", "protected", "static") or self._is_type():
                m = self._method()
                if m:
                    methods.append(m)
            else:
                self.i += 1
        if not methods:
            raise SyntaxError("no method found")
        return methods

    def _is_type(self) -> bool:
        return self.t().kind == "ID" or self.t().text in TYPES

    def _skip_type(self) -> None:
        self.eat()
        while self.at("["):
            self.eat("[")
            self.eat("]")

    def _class(self) -> List[AST]:
        self.eat("class")
        self.eat()
        self.eat("{")
        ms = []
        while not self.at("}") and self.t().kind != "EOF":
            m = self._method()
            if m:
                ms.append(m)
        self.eat("}")
        return ms

    def _method(self) -> Optional[AST]:
        while self.at("public", "private", "protected", "static"):
            self.eat()
        if not self._is_type():
            self.i += 1
            return None
        self._skip_type()
        if self.t().kind != "ID":
            return None
        name = self.eat().text
        if not self.at("("):
            while not self.at(";") and self.t().kind != "EOF":
                self.i += 1
            if self.at(";"):
                self.eat(";")
            return None
        self.eat("(")
        while not self.at(")") and self.t().kind != "EOF":
            self.i += 1
        self.eat(")")
        return AST("method", name, body=self._block())

    def _block(self) -> AST:
        self.eat("{")
        kids = []
        while not self.at("}") and self.t().kind != "EOF":
            kids.append(self._stmt())
        self.eat("}")
        return AST("block", kids=kids)

    def _stmt(self) -> AST:
        if self.at("{"):
            return self._block()
        if self.at("if"):
            return self._if()
        if self.at("while"):
            return self._while()
        if self.at("for"):
            return self._for()
        if self.at("do"):
            return self._do()
        if self.at("switch"):
            return self._switch()
        if self.at("return"):
            a = self.i
            self.eat("return")
            e = None if self.at(";") else self._expr()
            self.eat(";")
            return AST("return", self.join(a, self.i), expr=e)
        if self.at("break"):
            self.eat("break")
            self.eat(";")
            return AST("break", "break;")
        if self.at("continue"):
            self.eat("continue")
            self.eat(";")
            return AST("continue", "continue;")
        if self.at(";"):
            self.eat(";")
            return AST("empty")
        if self._is_decl():
            a = self.i
            self._skip_type()
            while True:
                self.eat()
                if self.at("="):
                    self.eat("=")
                    self._expr()
                if not self.at(","):
                    break
                self.eat(",")
            self.eat(";")
            return AST("decl", self.join(a, self.i))
        a = self.i
        e = self._expr()
        self.eat(";")
        return AST("expr", self.join(a, self.i), expr=e)

    def _is_decl(self) -> bool:
        j = self.i
        if not (self.toks[j].kind == "ID" or self.toks[j].text in TYPES):
            return False
        j += 1
        while self.toks[j].text == "[":
            j += 2
        return self.toks[j].kind == "ID"

    def _if(self) -> AST:
        self.eat("if")
        self.eat("(")
        c = self._expr()
        self.eat(")")
        then = self._stmt()
        els = None
        if self.at("else"):
            self.eat("else")
            els = self._stmt()
        return AST("if", c.src, cond=c, then=then, els=els)

    def _while(self) -> AST:
        self.eat("while")
        self.eat("(")
        c = self._expr()
        self.eat(")")
        return AST("while", c.src, cond=c, body=self._stmt())

    def _do(self) -> AST:
        self.eat("do")
        body = self._stmt()
        self.eat("while")
        self.eat("(")
        c = self._expr()
        self.eat(")")
        self.eat(";")
        return AST("do", c.src, cond=c, body=body)

    def _for(self) -> AST:
        self.eat("for")
        self.eat("(")
        if self._is_foreach():
            a = self.i
            self._skip_type()
            self.eat()
            self.eat(":")
            it = self._expr()
            header = self.join(a, self.i)
            self.eat(")")
            return AST("foreach", f"for ({header})", body=self._stmt())
        init = None
        if not self.at(";"):
            if self._is_decl():
                a = self.i
                self._skip_type()
                while True:
                    self.eat()
                    if self.at("="):
                        self.eat("=")
                        self._expr()
                    if not self.at(","):
                        break
                    self.eat(",")
                init = AST("decl", self.join(a, self.i) + ";")
            else:
                e = self._expr()
                init = AST("expr", e.src + ";", expr=e)
        self.eat(";")
        cond = None if self.at(";") else self._expr()
        self.eat(";")
        upd = None if self.at(")") else self._expr()
        self.eat(")")
        return AST(
            "for",
            cond.src if cond else "true",
            init=init,
            cond=cond,
            update=AST("expr", upd.src + ";", expr=upd) if upd else None,
            body=self._stmt(),
        )

    def _is_foreach(self) -> bool:
        j = self.i
        if not (self.toks[j].kind == "ID" or self.toks[j].text in TYPES):
            return False
        j += 1
        while self.toks[j].text == "[":
            j += 2
        return self.toks[j].kind == "ID" and self.toks[j + 1].text == ":"

    def _switch(self) -> AST:
        self.eat("switch")
        self.eat("(")
        e = self._expr()
        self.eat(")")
        self.eat("{")
        cases: List[Tuple[List[str], List[AST]]] = []
        while not self.at("}") and self.t().kind != "EOF":
            labs: List[str] = []
            while self.at("case", "default"):
                if self.at("default"):
                    self.eat("default")
                    self.eat(":")
                    labs.append("default")
                else:
                    self.eat("case")
                    v = self._expr()
                    self.eat(":")
                    labs.append(v.src)
            stmts: List[AST] = []
            while not self.at("}", "case", "default") and self.t().kind != "EOF":
                stmts.append(self._stmt())
            cases.append((labs, stmts))
        self.eat("}")
        return AST("switch", e.src, expr=e, cases=cases)

    def _expr(self) -> AST:
        return self._assign()

    def _assign(self) -> AST:
        left = self._ternary()
        if self.at("=", "+=", "-=", "*=", "/="):
            op = self.eat().text
            right = self._assign()
            return AST("assign", f"{left.src} {op} {right.src}", lhs=left, rhs=right)
        return left

    def _ternary(self) -> AST:
        c = self._or()
        if not self.at("?"):
            return c
        self.eat("?")
        then = self._expr()
        self.eat(":")
        els = self._ternary()
        return AST("ternary", f"{c.src} ? {then.src} : {els.src}", cond=c, then=then, els=els)

    def _bin(self, nxt, ops: Tuple[str, ...]) -> AST:
        left = nxt()
        while self.at(*ops):
            op = self.eat().text
            right = nxt()
            left = AST("bin", f"{left.src} {op} {right.src}")
        return left

    def _or(self) -> AST:
        return self._bin(self._and, ("||",))

    def _and(self) -> AST:
        return self._bin(self._eq, ("&&",))

    def _eq(self) -> AST:
        return self._bin(self._rel, ("==", "!="))

    def _rel(self) -> AST:
        return self._bin(self._add, ("<", ">", "<=", ">="))

    def _add(self) -> AST:
        return self._bin(self._mul, ("+", "-"))

    def _mul(self) -> AST:
        return self._bin(self._unary, ("*", "/", "%"))

    def _unary(self) -> AST:
        if self.at("!", "-", "+", "++", "--"):
            op = self.eat().text
            e = self._unary()
            return AST("unary", op + e.src)
        return self._post()

    def _post(self) -> AST:
        e = self._prim()
        while True:
            if self.at("++", "--"):
                e = AST("post", e.src + self.eat().text)
            elif self.at("."):
                self.eat(".")
                name = self.eat().text
                if self.at("("):
                    args, src = self._args()
                    e = AST("call", f"{e.src}.{name}{src}")
                else:
                    e = AST("id", f"{e.src}.{name}")
            elif self.at("(") and e.kind in ("id",):
                args, src = self._args()
                e = AST("call", e.src + src)
            elif self.at("["):
                self.eat("[")
                ix = self._expr()
                self.eat("]")
                e = AST("id", f"{e.src}[{ix.src}]")
            else:
                break
        return e

    def _args(self) -> Tuple[List[AST], str]:
        self.eat("(")
        args: List[AST] = []
        if not self.at(")"):
            args.append(self._expr())
            while self.at(","):
                self.eat(",")
                args.append(self._expr())
        self.eat(")")
        return args, "(" + ", ".join(a.src for a in args) + ")"

    def _prim(self) -> AST:
        t = self.t()
        if t.kind in ("NUM", "STR") or t.text in ("true", "false"):
            self.i += 1
            return AST("lit", t.text)
        if t.kind == "ID":
            self.i += 1
            return AST("id", t.text)
        if t.text == "(":
            self.eat("(")
            e = self._expr()
            self.eat(")")
            e.src = f"({e.src})"
            return e
        raise SyntaxError(f"bad expression at '{t.text}'")


# ---------------------------------------------------------------------------
# 3. Lowerer — each construct becomes a fixed jump pattern
# ---------------------------------------------------------------------------

@dataclass
class Ins:
    op: str
    text: str = ""
    target: str = ""
    true: str = ""
    false: str = ""
    cases: List[Tuple[str, str]] = field(default_factory=list)
    default: str = ""


class Lowerer:
    def __init__(self) -> None:
        self.ir: List[Ins] = []
        self.n = 0
        self.loop: List[Tuple[str, str]] = []  # (break, continue)
        self.switch_end: List[str] = []

    def fresh(self, p: str) -> str:
        self.n += 1
        return f"{p}{self.n}"

    def emit(self, **kw) -> None:
        self.ir.append(Ins(**kw))

    def lower(self, s: AST) -> None:
        k = s.kind
        if k == "block":
            for c in s.kids:
                self.lower(c)
        elif k in ("expr", "decl"):
            if k == "expr" and s.expr and s.expr.kind == "ternary":
                self._ternary(None, s.expr)
            elif k == "expr" and s.expr and s.expr.kind == "assign" and s.expr.rhs and s.expr.rhs.kind == "ternary":
                self._ternary(s.expr.lhs, s.expr.rhs)
            elif k == "expr" and s.expr and s.expr.kind == "call" and (
                s.expr.src.startswith("exit(") or "System.exit" in s.expr.src
            ):
                self.emit(op="ret", text=s.src)
            elif s.src:
                self.emit(op="code", text=s.src)
        elif k == "if":
            self._if(s)
        elif k == "while":
            self._while(s)
        elif k == "for":
            self._for(s)
        elif k == "foreach":
            self._foreach(s)
        elif k == "do":
            self._do(s)
        elif k == "switch":
            self._switch(s)
        elif k == "return":
            self.emit(op="ret", text=s.src)
        elif k == "break":
            tgt = self.switch_end[-1] if self.switch_end else self.loop[-1][0]
            self.emit(op="jmp", target=tgt)
        elif k == "continue":
            self.emit(op="jmp", target=self.loop[-1][1])

    def _if(self, s: AST) -> None:
        then, els, end = self.fresh("Then"), self.fresh("Else"), self.fresh("End")
        self.emit(op="br", text=s.cond.src, true=then, false=els if s.els else end)
        self.emit(op="label", text=then)
        self.lower(s.then)
        self.emit(op="jmp", target=end)
        if s.els:
            self.emit(op="label", text=els)
            self.lower(s.els)
            self.emit(op="jmp", target=end)
        self.emit(op="label", text=end)

    def _while(self, s: AST) -> None:
        head, body, end = self.fresh("W"), self.fresh("WB"), self.fresh("WE")
        self.loop.append((end, head))
        self.emit(op="label", text=head)
        self.emit(op="br", text=s.cond.src, true=body, false=end)
        self.emit(op="label", text=body)
        self.lower(s.body)
        self.emit(op="jmp", target=head)
        self.emit(op="label", text=end)
        self.loop.pop()

    def _do(self, s: AST) -> None:
        body, cond, end = self.fresh("Do"), self.fresh("DC"), self.fresh("DE")
        self.loop.append((end, cond))
        self.emit(op="label", text=body)
        self.lower(s.body)
        self.emit(op="jmp", target=cond)
        self.emit(op="label", text=cond)
        self.emit(op="br", text=s.cond.src, true=body, false=end)
        self.emit(op="label", text=end)
        self.loop.pop()

    def _for(self, s: AST) -> None:
        head, body, upd, end = self.fresh("F"), self.fresh("FB"), self.fresh("FU"), self.fresh("FE")
        if s.init:
            self.lower(s.init)
        self.loop.append((end, upd))
        self.emit(op="label", text=head)
        if s.cond:
            self.emit(op="br", text=s.cond.src, true=body, false=end)
        else:
            self.emit(op="jmp", target=body)
        self.emit(op="label", text=body)
        self.lower(s.body)
        self.emit(op="label", text=upd)
        if s.update:
            self.lower(s.update)
        self.emit(op="jmp", target=head)
        self.emit(op="label", text=end)
        self.loop.pop()

    def _foreach(self, s: AST) -> None:
        head, body, end = self.fresh("E"), self.fresh("EB"), self.fresh("EE")
        self.loop.append((end, head))
        self.emit(op="label", text=head)
        self.emit(op="br", text=s.src, true=body, false=end)
        self.emit(op="label", text=body)
        self.lower(s.body)
        self.emit(op="jmp", target=head)
        self.emit(op="label", text=end)
        self.loop.pop()

    def _switch(self, s: AST) -> None:
        end = self.fresh("SW")
        labs = [self.fresh("C") for _ in s.cases]
        default, meta = end, []
        for lab, (labels, _) in zip(labs, s.cases):
            for v in labels:
                if v == "default":
                    default = lab
                else:
                    meta.append((lab, v))
        self.emit(op="switch", text=s.src, cases=meta, default=default)
        self.switch_end.append(end)
        for lab, (_, stmts) in zip(labs, s.cases):
            self.emit(op="label", text=lab)
            for st in stmts:
                self.lower(st)
        self.switch_end.pop()
        self.emit(op="label", text=end)

    def _ternary(self, lhs: Optional[AST], t: AST) -> None:
        then, els, end = self.fresh("Q"), self.fresh("QE"), self.fresh("QX")
        self.emit(op="br", text=t.cond.src, true=then, false=els)
        self.emit(op="label", text=then)
        if t.then.kind == "ternary":
            self._ternary(lhs, t.then)
        else:
            text = f"{lhs.src} = {t.then.src};" if lhs else t.then.src + ";"
            self.emit(op="code", text=text)
        self.emit(op="jmp", target=end)
        self.emit(op="label", text=els)
        if t.els.kind == "ternary":
            self._ternary(lhs, t.els)
        else:
            text = f"{lhs.src} = {t.els.src};" if lhs else t.els.src + ";"
            self.emit(op="code", text=text)
        self.emit(op="jmp", target=end)
        self.emit(op="label", text=end)


# ---------------------------------------------------------------------------
# 4. Leader algorithm — reduced basic blocks
# ---------------------------------------------------------------------------

@dataclass
class Block:
    name: str
    stmts: List[str] = field(default_factory=list)
    kind: str = "process"


@dataclass
class CFG:
    name: str
    blocks: Dict[str, Block] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)
    order: List[str] = field(default_factory=list)

    def add(self, b: Block) -> None:
        self.blocks[b.name] = b
        self.order.append(b.name)


def build_cfg(method: AST) -> CFG:
    lo = Lowerer()
    lo.lower(method.body)
    return blocks_from_ir(method.src, lo.ir)


def blocks_from_ir(name: str, ir: List[Ins]) -> CFG:
    cfg = CFG(name)
    cfg.add(Block("START", kind="start"))
    if not ir:
        cfg.add(Block("STOP", kind="stop"))
        cfg.edges.append(("START", "STOP", ""))
        return cfg

    lab_at = {ins.text: i for i, ins in enumerate(ir) if ins.op == "label"}
    n = len(ir)
    leaders = {0}

    def tgt(L: str) -> Optional[int]:
        return lab_at.get(L)

    for i, ins in enumerate(ir):
        jumps: List[str] = []
        if ins.op == "br":
            jumps = [ins.true, ins.false]
        elif ins.op == "jmp":
            jumps = [ins.target]
        elif ins.op == "switch":
            jumps = [L for L, _ in ins.cases] + [ins.default]
        for L in jumps:
            j = tgt(L)
            if j is not None:
                leaders.add(j)
        if ins.op in ("br", "jmp", "ret", "switch") and i + 1 < n:
            leaders.add(i + 1)

    starts = sorted(leaders)
    ranges: List[Tuple[int, int]] = []
    index_b: Dict[int, int] = {}
    for bi, a in enumerate(starts):
        b = starts[bi + 1] if bi + 1 < len(starts) else n
        ranges.append((a, b))
        for k in range(a, b):
            index_b[k] = bi

    names = []
    for bi, (a, b) in enumerate(ranges):
        nm = str(bi + 1)
        names.append(nm)
        stmts, kind = [], "process"
        for k in range(a, b):
            ins = ir[k]
            if ins.op == "code" and ins.text:
                stmts.append(ins.text)
            elif ins.op == "br":
                stmts.append(ins.text)
                kind = "predicate"
            elif ins.op == "ret":
                stmts.append(ins.text)
            elif ins.op == "switch":
                stmts.append(f"switch ({ins.text})")
                kind = "multi"
        cfg.add(Block(nm, stmts, kind))
    cfg.add(Block("STOP", kind="stop"))

    def bloc(L: str) -> str:
        j = tgt(L)
        return "STOP" if j is None else names[index_b[j]]

    def fall(end: int) -> str:
        return "STOP" if end >= n else names[index_b[end]]

    cfg.edges.append(("START", names[0], ""))
    for bi, (a, b) in enumerate(ranges):
        src = names[bi]
        term = None
        for k in range(b - 1, a - 1, -1):
            if ir[k].op != "label":
                term = ir[k]
                break
        if term is None:
            cfg.edges.append((src, fall(b), ""))
        elif term.op == "br":
            cfg.edges.append((src, bloc(term.true), "true"))
            cfg.edges.append((src, bloc(term.false), "false"))
        elif term.op == "jmp":
            cfg.edges.append((src, bloc(term.target), ""))
        elif term.op == "ret":
            cfg.edges.append((src, "STOP", ""))
        elif term.op == "switch":
            seen = set()
            for L, val in term.cases:
                d = bloc(L)
                if (d, val) not in seen:
                    cfg.edges.append((src, d, f"case {val}"))
                    seen.add((d, val))
            cfg.edges.append((src, bloc(term.default), "default"))
        else:
            cfg.edges.append((src, fall(b), ""))

    changed = True
    while changed:
        changed = False
        for nm in list(cfg.order):
            b = cfg.blocks[nm]
            if b.kind in ("start", "stop") or b.stmts:
                continue
            succs = [d for s, d, _ in cfg.edges if s == nm]
            if len(succs) != 1 or succs[0] == nm:
                continue
            dest = succs[0]
            cfg.edges = [(s, dest if d == nm else d, lab) for s, d, lab in cfg.edges if s != nm]
            del cfg.blocks[nm]
            cfg.order = [x for x in cfg.order if x != nm]
            changed = True

    mapping, k, new_order = {}, 1, []
    for nm in cfg.order:
        if nm in ("START", "STOP"):
            mapping[nm] = nm
        else:
            mapping[nm] = str(k)
            k += 1
        new_order.append(mapping[nm])
    new_blocks = {}
    for old, new in mapping.items():
        blk = cfg.blocks[old]
        blk.name = new
        new_blocks[new] = blk
    cfg.blocks = new_blocks
    cfg.order = new_order
    cfg.edges = list(dict.fromkeys((mapping[s], mapping[d], lab) for s, d, lab in cfg.edges))
    return cfg


# ---------------------------------------------------------------------------
# 5. Output — vertex/edge lists + HTML drawing
# ---------------------------------------------------------------------------

def vg(cfg: CFG) -> int:
    return len(cfg.edges) - len(cfg.blocks) + 2


def format_text(cfg: CFG) -> str:
    lines = [
        f"Function: {cfg.name}",
        f"Cyclomatic complexity V(G) = E - N + 2 = "
        f"{len(cfg.edges)} - {len(cfg.blocks)} + 2 = {vg(cfg)}",
        "",
        "Vertices:",
    ]
    for nm in cfg.order:
        b = cfg.blocks[nm]
        if b.kind in ("start", "stop"):
            lines.append(f"  {nm}")
        elif len(b.stmts) == 1:
            lines.append(f"  {nm}: {b.stmts[0]}")
        else:
            lines.append(f"  {nm}:")
            for st in b.stmts:
                lines.append(f"      {st}")
    lines += ["", "Edges:"]
    for s, d, lab in cfg.edges:
        lines.append(f"  {s} -> {d}" + (f"  [{lab}]" if lab else ""))
    lines.append("")
    return "\n".join(lines)


def format_html(cfg: CFG, text: str) -> str:
    rank = {"START": 0}
    for _ in range(len(cfg.order) + 2):
        for s, d, _ in cfg.edges:
            if s not in rank:
                continue
            if d in rank and rank[d] < rank[s]:
                continue
            cand = rank[s] + 1
            if d not in rank or rank[d] < cand:
                rank[d] = cand
    for nm in cfg.order:
        rank.setdefault(nm, 0)
    layers: Dict[int, List[str]] = {}
    for nm in cfg.order:
        layers.setdefault(rank[nm], []).append(nm)
    pos = {}
    for r, nms in layers.items():
        for i, nm in enumerate(nms):
            pos[nm] = ((i - (len(nms) - 1) / 2) * 220, r * 140)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    pad = 90
    minx, miny = min(xs) - pad, min(ys) - pad
    w, h = max(xs) - minx + pad, max(ys) - miny + pad
    nw = 200

    def box(nm: str) -> Tuple[float, float, float, float]:
        x, y = pos[nm]
        nh = max(64, 18 + (1 + min(len(cfg.blocks[nm].stmts), 5)) * 16)
        return x - minx - nw / 2, y - miny - nh / 2, nw, nh

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(w)}" height="{int(h)}" viewBox="0 0 {w:.0f} {h:.0f}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto">',
        '<path d="M0,0 L10,4 L0,8 z" fill="#333"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#fafafa"/>',
    ]
    for s, d, lab in cfg.edges:
        x1, y1, w1, h1 = box(s)
        x2, y2, w2, h2 = box(d)
        sx, sy, dx, dy = x1 + w1 / 2, y1 + h1, x2 + w2 / 2, y2
        back = pos[d][1] <= pos[s][1]
        if back:
            cx = max(sx, dx) + 90
            path = f"M {sx:.0f} {sy:.0f} C {cx:.0f} {sy:.0f}, {cx:.0f} {dy:.0f}, {dx:.0f} {dy:.0f}"
            mx, my = cx, (sy + dy) / 2
        else:
            path = f"M {sx:.0f} {sy:.0f} L {dx:.0f} {dy:.0f}"
            mx, my = (sx + dx) / 2 + 8, (sy + dy) / 2
        color = "#2e7d32" if lab == "true" else "#c62828" if lab == "false" else "#333"
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.6" marker-end="url(#arrow)"/>')
        if lab:
            parts.append(f'<text x="{mx:.0f}" y="{my:.0f}" font-size="11" fill="{color}">{html.escape(lab)}</text>')
    for nm in cfg.order:
        x, y, bw, bh = box(nm)
        b = cfg.blocks[nm]
        if b.kind == "start":
            parts.append(
                f'<polygon points="{x+bw/2:.0f},{y:.0f} {x+bw:.0f},{y+bh/2:.0f} '
                f'{x+bw/2:.0f},{y+bh:.0f} {x:.0f},{y+bh/2:.0f}" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2"/>'
            )
            parts.append(f'<text x="{x+bw/2:.0f}" y="{y+bh/2+4:.0f}" text-anchor="middle" font-size="14" font-weight="bold">START</text>')
        elif b.kind == "stop":
            parts.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bw:.0f}" height="{bh:.0f}" rx="4" fill="#ffebee" stroke="#c62828" stroke-width="2"/>')
            parts.append(f'<text x="{x+bw/2:.0f}" y="{y+bh/2+4:.0f}" text-anchor="middle" font-size="14" font-weight="bold">STOP</text>')
        else:
            pred = b.kind in ("predicate", "multi")
            fill, stroke = ("#fff8e1", "#f9a825") if pred else ("#e3f2fd", "#1565c0")
            if pred:
                parts.append(
                    f'<polygon points="{x+bw/2:.0f},{y:.0f} {x+bw:.0f},{y+bh/2:.0f} '
                    f'{x+bw/2:.0f},{y+bh:.0f} {x:.0f},{y+bh/2:.0f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
                )
            else:
                parts.append(
                    f'<rect x="{x:.0f}" y="{y:.0f}" width="{bw:.0f}" height="{bh:.0f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
                )
            texts = [nm] + b.stmts[:4] + (["…"] if len(b.stmts) > 4 else [])
            sy0 = y + bh / 2 - (len(texts) - 1) * 7
            for i, tx in enumerate(texts):
                clip = tx if len(tx) < 28 else tx[:25] + "…"
                wt = "bold" if i == 0 else "normal"
                parts.append(
                    f'<text x="{x+bw/2:.0f}" y="{sy0 + i * 14:.0f}" text-anchor="middle" font-size="11" font-weight="{wt}">{html.escape(clip)}</text>'
                )
    parts.append("</svg>")
    svg = "\n".join(parts)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>CFG "
        f"{html.escape(cfg.name)}</title></head><body>"
        f"<h1>{html.escape(cfg.name)}</h1><p>Reduced CFG. V(G) = {vg(cfg)}.</p>"
        f"<div>{svg}</div><pre>{html.escape(text)}</pre></body></html>"
    )


def parse_methods(src: str) -> List[AST]:
    return Parser(Lexer(src).tokenize()).parse_file()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args(argv)
    files = []
    if os.path.isfile(args.path):
        files = [args.path]
    else:
        for root, _, names in os.walk(args.path):
            files += [os.path.join(root, n) for n in sorted(names) if n.endswith(".java")]
    report = []
    for fp in files:
        src = open(fp, encoding="utf-8").read()
        cfgs = [build_cfg(m) for m in parse_methods(src)]
        for cfg in cfgs:
            text = format_text(cfg)
            print("=" * 72)
            print(f"File: {fp}")
            print(text)
            report.append(f"{'=' * 72}\nFile: {fp}\n{text}")
            if args.out:
                os.makedirs(args.out, exist_ok=True)
                stem = os.path.splitext(os.path.basename(fp))[0]
                open(os.path.join(args.out, stem + ".txt"), "w").write(text)
                open(os.path.join(args.out, stem + ".html"), "w").write(format_html(cfg, text))
    if args.out:
        open(os.path.join(args.out, "ALL.txt"), "w").write("\n".join(report))
        print(f"Wrote outputs to {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

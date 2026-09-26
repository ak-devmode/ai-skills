#!/usr/bin/env python3
"""resolve-identifiers.py — the invented-reality check: every env var, SSM path, proto
field and route a change references must resolve to a real declaration.

Approach: collect references — from the added lines of source files in an explicit
revision range, or from a JSONL list the judge supplies — then look each one up in its
kind's authoritative declaration files, read from the range's HEAD tree (so a
declaration added in the same change resolves). Lookups are namespace-aware: an env var
must be declared beside the using file or in an ancestor directory, not in a sibling
service, or as the last segment of an SSM path under `shared/` or the using repo's
service segment (`/…/gateway-go/PORT` declares PORT for `wellmed-gateway-go` — the way an
SSM loader injects env); a proto field must belong to the message it is set on, in a
`.proto` or in the generated `.pb.go` struct a Go caller actually imports; SSM paths and
routes match segment by segment with placeholders. Env reads inside test files are
test-only switches, not deployed config, and are skipped. Comment lines and fixture paths count
neither as uses nor as declarations. A kind this script cannot check is reported as
unsupported and is never a pass — found, resolved and unsupported are always printed.

Heuristics, stated so nobody mistakes them for a parser: references are regex-extracted
(Go composite literals opened on an added line, Python `_pb2` kwargs, fetch/axios/http
client calls, the common env accessors); route declarations are gin/echo/express-style
`<router>.<verb>("/path"`, Go `Handle[Func]`, and Laravel `Route::<verb>`. A route that
only matches as a suffix of the used path (a group prefix the script can't see) resolves
but is labelled `suffix`.

Usage:
  resolve-identifiers.py --repo PATH --range BASE..HEAD [--decl-repo PATH ...] [--json]
  resolve-identifiers.py --repo PATH --ids FILE [--rev REV] [--decl-repo PATH ...] [--json]
    --ids FILE    JSONL, one {"kind", "name", "namespace"?, "file"?, "line"?} per line;
                  kinds: env · ssm · proto (name "Message.field") · route (name "/path",
                  namespace = HTTP method or omitted)
    --decl-repo   extra repos searched for ssm / proto / route declarations (cross-repo)
Output: one line per reference, a §10 message per failure, then
        `found N · resolved M · unresolved U · unsupported kinds K`.
Exit:   0 every reference resolved · 1 anything unresolved or unsupported · 2 usage
        · 3 could not evaluate (git error, empty range)
"""

import argparse
import json
import os
import re
import subprocess
import sys

DOCS = "templates/verify-contracts.md §10 · scripts/README.md (resolve-identifiers.py)"
KINDS = ("env", "ssm", "proto", "route")
SRC_EXT = {".go", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".php", ".sh"}
FIXTURE_DIRS = {"fixtures", "fixture", "__fixtures__", "testdata", "__mocks__", "mocks"}
TEST_FILE = re.compile(r"(_test\.go|\.(test|spec)\.[jt]sx?|(^|/)test_[^/]*\.py)$")
COMMENT_START = ("//", "#", "*", "/*", "--")

ENV_USE = [re.compile(p) for p in (
    r"process\.env\.([A-Z][A-Z0-9_]*)",
    r"process\.env\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\]",
    r"import\.meta\.env\.([A-Z][A-Z0-9_]*)",
    r"os\.(?:Getenv|LookupEnv)\(\s*\"([A-Z][A-Z0-9_]*)\"",
    r"os\.environ(?:\.get)?[\[(]\s*['\"]([A-Z][A-Z0-9_]*)['\"]",
    r"\b(?:os\.)?getenv\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]",
    r"\benv\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]",
)]
ENV_DECL_FILE = re.compile(r"(^|/)(\.env(\.[\w-]+)?\.(example|sample|template|dist)"
                           r"|[\w-]+\.env\.example|(docker-)?compose[\w.-]*\.ya?ml)$")
ENV_DECL_LINE = re.compile(r"^\s*(?:export\s+|-\s*)?([A-Z][A-Z0-9_]*)\s*[:=]")

SEG = r"[A-Za-z0-9_.{}$%<>:-]+"
SSM_LITERAL = re.compile(r"['\"`](/" + SEG + r"(?:/" + SEG + r")+)['\"`]")
SSM_FLAG = re.compile(r"--names?\s+['\"]?(/" + SEG + r"(?:/" + SEG + r")+)")
SSM_HINT = re.compile(r"(?i)ssm|parameter")
SSM_DECL_FILE = re.compile(r"(\.tf$|(^|/)FLEET\.md$|(^|/)ssm[^/]*/(.*/)?[^/]+\.(md|json|ya?ml|txt)$"
                           r"|(^|/)ssm[\w.-]*\.(md|json|ya?ml|txt)$)")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
SSM_DECL_TF = re.compile(r"\bname\s*=\s*\"(/[^\"]+)\"")
SSM_DECL_ANY = re.compile(r"(/" + SEG + r"(?:/" + SEG + r")+)")

GO_LIT_OPEN = re.compile(r"&?\b(\w*(?:pb|proto|v\d+))\.([A-Z]\w*)\{")
GO_LIT_KEY = re.compile(r"(?:^|[{,])\s*([A-Z]\w*)\s*:")
PY_PB2 = re.compile(r"\b\w+_pb2\.([A-Z]\w*)\(([^)]*)\)")
PY_KWARG = re.compile(r"\b([a-z_]\w*)\s*=")

VERBS = "get|post|put|patch|delete|head|options|all|any"
ROUTE_FETCH = re.compile(r"\bfetch\(\s*[`'\"]([^`'\"]+)")
ROUTE_AXIOS = re.compile(r"\baxios(?:\.(" + VERBS + r"))?\(\s*[`'\"]([^`'\"]+)", re.I)
ROUTE_GOHTTP = re.compile(r"\bhttp\.(Get|Post|Head)\(\s*\"([^\"]+)")
ROUTE_CLIENT = re.compile(r"\b(\w*(?:[Aa]pi|[Cc]lient)\w*)\.(" + VERBS + r")\(\s*[`'\"]([^`'\"]+)")
ROUTE_DECL = re.compile(r"\b([A-Za-z_]\w*)\.(" + VERBS + r"|Handle|HandleFunc)\(\s*[`'\"]([^`'\"]*)",
                        re.I)
ROUTE_LARAVEL = re.compile(r"Route::(" + VERBS + r"|match)\(\s*['\"]([^'\"]*)", re.I)
DECL_RECV = re.compile(r"^(router|app|r|e|g|rg|grp|group|mux|srv|server|routes?|v\d+|\w*Router|"
                       r"\w*Group|\w*router|\w*group)$")


# ---------- git access -------------------------------------------------------------

class GitError(Exception):
    pass


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise GitError(f"git -C {repo} {' '.join(args)}: {p.stderr.strip() or 'exit ' + str(p.returncode)}")
    return p.stdout


class Tree:
    """Files of one repo at one revision, read in a single `git cat-file --batch`."""

    def __init__(self, repo, rev):
        self.repo, self.rev = repo, rev
        self.paths = [p for p in git(repo, "ls-tree", "-r", "--name-only", rev).splitlines() if p]
        self._cache = {}

    def read(self, paths):
        want = [p for p in paths if p not in self._cache]
        if want:
            proc = subprocess.run(["git", "-C", self.repo, "cat-file", "--batch"],
                                  input="".join(f"{self.rev}:{p}\n" for p in want).encode(),
                                  capture_output=True)
            if proc.returncode != 0:
                raise GitError(f"git cat-file in {self.repo}: {proc.stderr.decode().strip()}")
            out, i = proc.stdout, 0
            for p in want:
                nl = out.index(b"\n", i)
                header = out[i:nl].split()
                if len(header) < 3 or header[1] != b"blob":
                    self._cache[p] = ""
                    i = nl + 1
                    continue
                size = int(header[2])
                self._cache[p] = out[nl + 1:nl + 1 + size].decode("utf-8", "replace")
                i = nl + 1 + size + 1
        return {p: self._cache[p] for p in paths}


# ---------- classification helpers -------------------------------------------------

def is_fixture(path):
    return bool(set(path.split("/")[:-1]) & FIXTURE_DIRS)


def is_comment(line):
    s = line.strip()
    return s.startswith(COMMENT_START) or s.startswith('"_comment')


def is_source(path):
    return os.path.splitext(path)[1] in SRC_EXT and not is_fixture(path)


def is_placeholder(seg):
    return seg.startswith(":") or any(c in seg for c in "{}$%<>")


def segments(path):
    return [s for s in path.split("/") if s]


def seg_match(a, b):
    return len(a) == len(b) and all(x == y or is_placeholder(x) or is_placeholder(y)
                                    for x, y in zip(a, b))


def go_name(proto_field):
    return "".join(p[:1].upper() + p[1:] for p in proto_field.split("_"))


def route_path(raw):
    """Client URL → path: strip scheme+host, a leading ${base}, and the query."""
    s = re.sub(r"^https?://[^/]+", "", raw.strip())
    s = re.sub(r"^\$\{[^}]*\}", "", s)
    s = s.split("?", 1)[0].split("#", 1)[0]
    return s if s.startswith("/") else None


# ---------- reference extraction ---------------------------------------------------

def ref(kind, name, namespace, file, line):
    return {"kind": kind, "name": name, "namespace": namespace, "file": file, "line": line}


def added_lines(repo, base, head):
    """{path: [(lineno, text), ...]} for lines added in base..head."""
    out = git(repo, "diff", "-U0", "--no-color", "--no-ext-diff", f"{base}..{head}")
    files, cur, n = {}, None, 0
    for line in out.splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
            if cur is not None:
                files.setdefault(cur, [])
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) if m else 0
        elif cur is not None and line.startswith("+") and not line.startswith("+++"):
            files[cur].append((n, line[1:]))
            n += 1
    return files


def extract(files):
    refs = []
    for path, lines in files.items():
        if not is_source(path):
            continue
        open_msg = None  # (message, depth) for a Go literal opened on an added line
        for lineno, text in lines:
            if is_comment(text):
                continue
            for rx in ENV_USE if not TEST_FILE.search(path) else ():
                for m in rx.finditer(text):
                    refs.append(ref("env", m.group(1), None, path, lineno))
            if SSM_HINT.search(text):
                for rx in (SSM_LITERAL, SSM_FLAG):
                    for m in rx.finditer(text):
                        refs.append(ref("ssm", m.group(1), None, path, lineno))
            for m in PY_PB2.finditer(text):
                for k in PY_KWARG.finditer(m.group(2)):
                    refs.append(ref("proto", f"{m.group(1)}.{k.group(1)}", "python", path, lineno))
            m = GO_LIT_OPEN.search(text)
            if m:
                open_msg = [m.group(2), 0]
                text_after = text[m.end() - 1:]
            else:
                text_after = text
            if open_msg:
                for k in GO_LIT_KEY.finditer(text_after if m else "{" + text_after):
                    refs.append(ref("proto", f"{open_msg[0]}.{k.group(1)}", "go", path, lineno))
                open_msg[1] += text_after.count("{") - text_after.count("}")
                if open_msg[1] <= 0:
                    open_msg = None
            for m in ROUTE_FETCH.finditer(text):
                p = route_path(m.group(1))
                if p:
                    refs.append(ref("route", p, None, path, lineno))
            for m in ROUTE_AXIOS.finditer(text):
                p = route_path(m.group(2))
                if p:
                    refs.append(ref("route", p, (m.group(1) or "").upper() or None, path, lineno))
            for m in ROUTE_GOHTTP.finditer(text):
                p = route_path(m.group(2))
                if p:
                    refs.append(ref("route", p, m.group(1).upper(), path, lineno))
            for m in ROUTE_CLIENT.finditer(text):
                if DECL_RECV.match(m.group(1)):
                    continue
                p = route_path(m.group(3))
                if p:
                    refs.append(ref("route", p, m.group(2).upper(), path, lineno))
    return refs


# ---------- declaration indexes (built lazily, per kind) ---------------------------

class Index:
    def __init__(self, repo_tree, decl_trees):
        self.repo = repo_tree
        self.all = [repo_tree] + decl_trees
        self._env = self._ssm = self._proto = self._route = None

    def env(self):
        """[(dir, name, where, is_ignored)] from the using repo only."""
        if self._env is None:
            self._env = []
            paths = [p for p in self.repo.paths if ENV_DECL_FILE.search(p)]
            for p, text in self.repo.read(paths).items():
                d = os.path.dirname(p)
                for i, line in enumerate(text.splitlines(), 1):
                    s = line.lstrip()
                    if s.startswith("#"):
                        m = ENV_DECL_LINE.match(s.lstrip("# "))
                        if m:
                            self._env.append((d, m.group(1), f"{p}:{i}", True))
                        continue
                    m = ENV_DECL_LINE.match(line)
                    if m:
                        self._env.append((d, m.group(1), f"{p}:{i}", is_fixture(p)))
        return self._env

    def ssm(self):
        if self._ssm is None:
            self._ssm = []
            for tree in self.all:
                paths = [p for p in tree.paths if SSM_DECL_FILE.search(p)]
                for p, text in tree.read(paths).items():
                    rx = SSM_DECL_TF if p.endswith(".tf") else SSM_DECL_ANY
                    for i, line in enumerate(text.splitlines(), 1):
                        ignored = is_comment(line) or is_fixture(p)
                        for m in rx.finditer(line):
                            self._ssm.append((m.group(1).rstrip(".,;:"), f"{tree_label(tree)}{p}:{i}", ignored))
        return self._ssm

    def proto(self):
        """{message: {field names + Go names + oneof names}} across every *.proto, plus the
        exported fields of structs in generated *.pb.go files."""
        if self._proto is None:
            self._proto = {}
            for tree in self.all:
                paths = [p for p in tree.paths if p.endswith((".proto", ".pb.go")) and not is_fixture(p)]
                for p, text in tree.read(paths).items():
                    parsed = parse_pb_go(text) if p.endswith(".pb.go") else parse_proto(text)
                    for msg, fields in parsed:
                        self._proto.setdefault(msg, set()).update(fields)
        return self._proto

    def route(self):
        """[(method or None, path, where)] from router registrations."""
        if self._route is None:
            self._route = []
            for tree in self.all:
                paths = [p for p in tree.paths if is_source(p) and not TEST_FILE.search(p)]
                for p, text in tree.read(paths).items():
                    for i, line in enumerate(text.splitlines(), 1):
                        if is_comment(line):
                            continue
                        where = f"{tree_label(tree)}{p}:{i}"
                        for m in ROUTE_DECL.finditer(line):
                            recv, verb, raw = m.groups()
                            if verb.lower() not in ("handle", "handlefunc") and not DECL_RECV.match(recv):
                                continue
                            method = None
                            if verb.lower() in ("handle", "handlefunc"):
                                mm = re.match(r"^([A-Z]+)\s+(/.*)$", raw)
                                if mm:
                                    method, raw = mm.groups()
                            elif verb.lower() not in ("all", "any"):
                                method = verb.upper()
                            if raw.startswith("/"):
                                self._route.append((method, raw, where))
                        for m in ROUTE_LARAVEL.finditer(line):
                            verb, raw = m.groups()
                            method = None if verb.lower() in ("any", "match") else verb.upper()
                            self._route.append((method, "/" + raw.lstrip("/"), where))
        return self._route


def tree_label(tree):
    return "" if getattr(tree, "is_primary", False) else os.path.basename(tree.repo.rstrip("/")) + ":"


def parse_proto(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    for m in re.finditer(r"\bmessage\s+(\w+)\s*\{", text):
        depth, i, body = 1, m.end(), []
        while i < len(text) and depth:
            c = text[i]
            depth += (c == "{") - (c == "}")
            body.append(c)
            i += 1
        b = "".join(body[:-1])
        b = re_strip_blocks(b)
        fields = set()
        for f in re.finditer(r"(\w+)\s*=\s*\d+\s*[;\[]", b):
            fields.update({f.group(1), go_name(f.group(1))})
        for o in re.finditer(r"\boneof\s+(\w+)", b):
            fields.update({o.group(1), go_name(o.group(1))})
        yield m.group(1), fields


def parse_pb_go(text):
    for m in re.finditer(r"^type (\w+) struct \{\n(.*?)^\}", text, re.M | re.S):
        yield m.group(1), set(re.findall(r"^\t([A-Z]\w*)\s", m.group(2), re.M))


def re_strip_blocks(body):
    """Drop nested message/enum blocks so their fields don't count for the outer message."""
    out, i = [], 0
    for m in re.finditer(r"\b(message|enum)\s+\w+\s*\{", body):
        if m.start() < i:
            continue
        out.append(body[i:m.start()])
        depth, j = 1, m.end()
        while j < len(body) and depth:
            depth += (body[j] == "{") - (body[j] == "}")
            j += 1
        i = j
    out.append(body[i:])
    return "".join(out)


# ---------- resolution -------------------------------------------------------------

def resolve(r, idx):
    """Return (status, detail): status in resolved | unresolved; detail = where / why."""
    kind, name = r["kind"], r["name"]
    if kind == "env":
        use_dir = os.path.dirname(r["file"]) if r.get("file") else None
        hits, ignored = [], 0
        for d, n, where, ign in idx.env():
            if n != name:
                continue
            in_scope = use_dir is None or d == "" or use_dir == d or use_dir.startswith(d + "/")
            if ign:
                ignored += 1
            elif in_scope:
                hits.append(where)
        if hits:
            return "resolved", hits[0]
        repo_base = os.path.basename(idx.repo.repo.rstrip("/"))
        for path, where, ign in idx.ssm():
            segs = segments(path)
            if len(segs) < 2 or segs[-1] != name or not ENV_NAME.match(name):
                continue
            svc = segs[-2]
            if svc == "shared" or repo_base == svc or repo_base.endswith("-" + svc):
                if ign:
                    ignored += 1
                    continue
                return "resolved", f"{where} (SSM {svc}/)"
        return "unresolved", ("env declaration files (.env*.example|sample|template, compose "
                              "environment:) in the using file's directory or an ancestor, or an "
                              f"SSM path `/…/shared/{name}` or `/…/<{repo_base} service>/{name}`", ignored)
    if kind == "ssm":
        want, ignored = segments(name), 0
        for path, where, ign in idx.ssm():
            if seg_match(want, segments(path)):
                if ign:
                    ignored += 1
                    continue
                return "resolved", where
        return "unresolved", ("*.tf `name = \"...\"`, FLEET.md, or ssm* files", ignored)
    if kind == "proto":
        if "." not in name:
            return "unresolved", ("a `Message.field` name", 0)
        msg, field = name.rsplit(".", 1)
        fields = idx.proto().get(msg)
        if fields is None:
            return "unresolved", (f"a `message {msg}` in *.proto", 0)
        if field in fields:
            return "resolved", f"message {msg}"
        return "unresolved", (f"field `{field}` in `message {msg}` (it has: "
                              f"{', '.join(sorted(f for f in fields if f[:1].islower())) or 'no fields'})", 0)
    if kind == "route":
        want, method = segments(name), (r.get("namespace") or "").upper() or None
        suffix = None
        for m, path, where in idx.route():
            if method and m and m != method:
                continue
            have = segments(path)
            if seg_match(want, have):
                return "resolved", where
            if have and len(have) < len(want) and seg_match(want[-len(have):], have) and suffix is None:
                suffix = where
        if suffix:
            return "resolved", f"{suffix} (suffix — group prefix assumed)"
        return "unresolved", (f"a router registration for {method or 'any method'} {name}", 0)
    raise ValueError(kind)


# ---------- output -----------------------------------------------------------------

def message(level, what, expected, found, where, cause, nxt):
    return (f"  [{level}] {what}\n"
            f"      expected · {expected}\n"
            f"      found    · {found}\n"
            f"      where    · {where}\n"
            f"      cause    · {cause}\n"
            f"      next     · {nxt}\n"
            f"      docs     · {DOCS}")


def loc(r):
    return f"{r['file']}:{r['line']}" if r.get("file") else r.get("_src", "--ids")


def main(argv):
    ap = argparse.ArgumentParser(description="Resolve referenced identifiers against declarations.")
    ap.add_argument("--repo", required=True)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--range", dest="rng")
    src.add_argument("--ids")
    ap.add_argument("--rev", default="HEAD", help="tree to resolve against in --ids mode")
    ap.add_argument("--decl-repo", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        if a.rng:
            if ".." not in a.rng or a.rng.count("..") != 1 or "..." in a.rng:
                print(message("ERROR", f"range `{a.rng}` is not BASE..HEAD", "an explicit BASE..HEAD range",
                              a.rng, "--range", "tooling", "pass e.g. --range abc1234..HEAD"), file=sys.stderr)
                return 2
            base, head = a.rng.split("..")
            files = added_lines(a.repo, base, head)
            if not files:
                print(message("ERROR", "the range has no changes", f"at least one changed file in {a.rng}",
                              "an empty diff", f"{a.repo} {a.rng}", "tooling",
                              "check the unit's base SHA — an empty range is a failure, not a clean pass"),
                      file=sys.stderr)
                return 3
            refs, rev = extract(files), head
        else:
            refs, rev = [], a.rev
            with open(a.ids, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    if line.strip():
                        d = json.loads(line)
                        d.setdefault("namespace", None)
                        d["_src"] = f"{a.ids}:{i}"
                        refs.append(d)
        tree = Tree(a.repo, rev)
        tree.is_primary = True
        idx = Index(tree, [Tree(d, "HEAD") for d in a.decl_repo])
    except GitError as exc:
        print(message("ERROR", "git could not read the repo", "a readable git repo and revision",
                      str(exc), a.repo, "environment", f"git -C {a.repo} status"), file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        print(message("ERROR", "could not read --ids", "JSONL, one object per line", str(exc),
                      a.ids or "--ids", "tooling", "fix the file and re-run"), file=sys.stderr)
        return 2

    results, unsupported = [], []
    seen = set()
    for r in refs:
        key = (r["kind"], r["name"], r.get("namespace"), r.get("file"))
        if key in seen:
            continue
        seen.add(key)
        if r["kind"] not in KINDS:
            unsupported.append(r)
            continue
        status, detail = resolve(r, idx)
        results.append((r, status, detail))

    resolved = [x for x in results if x[1] == "resolved"]
    unresolved = [x for x in results if x[1] == "unresolved"]
    kinds_unsup = sorted({r["kind"] for r in unsupported})

    if a.json:
        print(json.dumps({
            "found": len(results) + len(unsupported), "resolved": len(resolved),
            "unresolved": [dict(r, why=d[0]) for r, _, d in unresolved],
            "unsupported": [r for r in unsupported],
            "refs": [dict(r, status=s, detail=d if isinstance(d, str) else d[0]) for r, s, d in results],
        }, default=str))
    else:
        for r, _, where in resolved:
            print(f"resolved    {r['kind']:<5} {r['name']}  {loc(r)} <- {where}")
        for r, _, (expected, ignored) in unresolved:
            found = "no declaration"
            if ignored:
                found += f"; {ignored} hit(s) in comments or fixtures ignored"
            print(message("FAIL", f"{r['kind']} `{r['name']}` does not resolve", expected, found, loc(r),
                          "code", f"grep -rn '{r['name'].split('.')[-1]}' {a.repo} — declare it, or fix "
                          "the name if it was assumed rather than looked up"))
        for r in unsupported:
            print(message("FAIL", f"kind `{r['kind']}` is not supported — `{r['name']}` was not checked",
                          f"one of {', '.join(KINDS)}", r["kind"], loc(r), "tooling",
                          "resolve it by hand and record the evidence, or add the kind to "
                          "scripts/resolve-identifiers.py"))
    summary = (f"found {len(results) + len(unsupported)} · resolved {len(resolved)} · "
               f"unresolved {len(unresolved)} · unsupported kinds {len(kinds_unsup)}"
               + (f" ({', '.join(kinds_unsup)})" if kinds_unsup else ""))
    print(summary, file=sys.stderr if a.json else sys.stdout)
    return 1 if unresolved or unsupported else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

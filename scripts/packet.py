#!/usr/bin/env python3
"""packet.py — decision-queue packets from a lane (scope 10 §4.1, plan 10.1 task 1.2).

Approach: every packet is written to an outbox in the lane's own worktree
(<repo>/.decision-queue/outbox/, self-ignoring) and `PACKET <id>` is printed; that is
the one path for every lane (Claude, codex, review). Only a DRIVER (`--driver`, or
$HERDR_AGENT_NAME == driver) POSTs, and only when $DECISION_QUEUE_URL is set: packets to
/packets, events to /events, 3 s timeout, idempotent on the client-generated id. A dead
queue never fails the caller: the packet is printed with a `Blocked` note, exit 0, and
`flush` re-sends later. A one-way door still stops the lane — that is a decision, not a
harness error; the stop is the caller's (`PARKED <id>`), not this script's.

Lane identity = machine/workspace/agent. In herdr: hostname, $HERDR_WORKSPACE_ID,
$HERDR_AGENT_NAME (else $HERDR_PANE_ID). Outside herdr: hostname, cwd-<name>-<hash of the
repo toplevel>, session-<$CLAUDE_CODE_SESSION_ID | $CLAUDE_SESSION_ID | $CODEX_SESSION_ID>.
With no session id the agent is `session-none`, which two lanes can share: `new` warns on
stderr, `check-reply` refuses unless --lane names the lane (cannot prove whose reply it is). The reply the page hands Alex opens with
`[lane <machine>/<workspace>/<agent> <packet-id>]`; `check-reply` refuses anything else.

Failure stances (each is fail-closed unless it says otherwise):
  * invalid packet / unreadable state or packet file -> refuse, exit 1, write nothing
  * check-reply: wrong or missing tag, unknown packet, another lane's, closed, stale,
    two different lane tags in one reply -> refuse, exit 1
  * POST failure -> FAIL-OPEN by design (Blocked note, exit 0): the queue is a convenience
    channel; stopping Alex's two-way work for a harness error is worse than a late card.
    The POST has a hard 3 s wall-clock deadline (a worker thread, not just a socket
    timeout) and refuses redirects: a 3xx is a failure, never a send
  * queue verdicts per item: 409 (id reused with different content) -> `<id>.conflict`;
    400/413/415/422 (definitive content refusals) -> `<id>.rejected`; each printed once and
    never retried (flush lists them). Every other 4xx (401/403/408/429, 404 on /packets) and
    5xx / network -> Blocked as above: keep, break the flush, retry next time (a credential,
    rate or URL problem must not make packets permanent). 404 on an event (packet not on the
    queue yet) -> kept unsent, retried next flush. All exit 0 (a harness error never stops
    the caller). To clear a marker once the cause is fixed: delete `<id>.rejected` /
    `<id>.conflict` in the outbox (and its events' `evt-*.rejected`); flush re-sends.
  * events of a refused packet (its `.conflict` or `.rejected` in the same outbox): never
    POSTed, marked `evt-<id>.rejected` ("packet refused"). Conflict too: the queue holds
    other content under that id, so a lane's close/stale must not apply to it
  * flush --outbox DIR that does not exist -> `Skipped: outbox DIR does not exist`, exit 0
  * flush: an unreadable item is reported and skipped, the rest of the outbox still goes
  * stale: git cannot be read -> exit 1 without marking. Fail-open on purpose: marking
    stale discards a pending decision
  * check-reply on a ONE-WAY packet also compares the lane repo's HEAD with the packet's
    head_sha (the lane is parked): HEAD may advance only by commits touching plans/ alone
    (bookkeeping); a code path, a non-ancestor HEAD or unreadable git refuses. Two-way packets skip this: work continues past them by design (see `touch`)
  * --range classification failure -> door.py returns one-way (promote-only)

  packet.py new --door D --type T --title QUESTION --unit U --context S
                [--option "LABEL::WHY" ...] [--recommended N] [--evidence S | --evidence-file F]
                [--payload-file F] [--blocks S] [--continues-on S] [--range BASE..HEAD] [--id ID] [--driver]
  packet.py new --schema-version 1 ... --option LABEL (--body TEXT|--body-file F|--payload-file F)
                (legacy v1 card; review/verify emitters still write it)

  Schema v2 (the default, 10.4 cards lane) caps the card so it reads faster than the terminal:
  title = the question <= 100 chars, --context <= 400, each option label <= 60 (no
  "(recommended)" text: --recommended marks it) + why <= 140, --evidence <= 4000 (file:line, ADR
  refs, SHAs — collapsed on the card). Over a cap -> refused, "cut <field> to N chars (now M)".
  --body on v2 is refused (v2 has no body), as are --context/--evidence on v1.
  packet.py close ID | stale ID [--force] | touch ID | event --kind K --body S [--packet-id ID]
  packet.py check-reply (--reply TEXT | --file F | -) [--lane M/W/A]
  packet.py flush [--driver]
  common: --outbox DIR (repeatable; first is where this lane writes)
  exit: 0 ok (a blocked POST is ok) · 1 refused / error · 2 usage
"""
import argparse
import datetime
import hashlib
import http.client
import importlib.util
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def post_timeout():
    """PACKET_POST_TIMEOUT (tests only), read where used; a bad value falls back to 3 so a
    harness setting can never stop the caller."""
    try:
        v = float(os.environ.get("PACKET_POST_TIMEOUT") or 3)
    except ValueError:
        return 3.0
    return v if v > 0 else 3.0
REFUSED = (400, 413, 415, 422)  # 4xx that mean "this content is refused"; all other 4xx retry
SKIP = "Skipped: "
HELD = "Held: "
NOT_SENT = (SKIP, HELD, "Conflict: ", "Rejected: ")  # per-item outcomes: report, never stop the flush
TAG_RE = re.compile(r"\[lane ([^/\]\[\n]+)/([^/\]\[\n]+)/([^/\]\[\n]+) ([A-Za-z0-9_-]{8,64})\]")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


schema_check = _load("schema_check")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean(part):
    part = re.sub(r"[/\[\]\n\r]+", "-", str(part)).strip()
    return part or "unknown"


def lane_identity():
    machine = clean(os.environ.get("PACKET_MACHINE") or socket.gethostname().split(".")[0])
    agent = os.environ.get("HERDR_AGENT_NAME")
    ws = os.environ.get("HERDR_WORKSPACE_ID")
    if os.environ.get("PACKET_WORKSPACE"):
        ws = os.environ["PACKET_WORKSPACE"]
    if os.environ.get("PACKET_AGENT"):
        agent = os.environ["PACKET_AGENT"]
    if not agent and os.environ.get("HERDR_PANE_ID"):
        agent = os.environ["HERDR_PANE_ID"]
    if not ws or not agent:  # outside herdr: machine + repo toplevel + session id
        top = toplevel()  # not cwd: a subdirectory must resolve to the same lane
        sid = (os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
               or os.environ.get("CODEX_SESSION_ID") or "")
        ws = ws or f"cwd-{os.path.basename(top)}-{hashlib.sha1(top.encode()).hexdigest()[:6]}"
        agent = agent or f"session-{sid[:12] or 'none'}"
    return machine, clean(ws), clean(agent)


def lane_tag(m, w, a, pid):
    return f"[lane {m}/{w}/{a} {pid}]"


def git(*args, cwd=None):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[:200] or f"git {args[0]} failed")
    return p.stdout.strip()


def toplevel():
    try:
        return git("rev-parse", "--show-toplevel")
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return os.getcwd()


def outboxes(args):
    dirs = [Path(d) for d in (args.outbox or [])]
    env = os.environ.get("PACKET_OUTBOX")
    if env:
        dirs.append(Path(env))
    if not dirs:
        dirs = [Path(toplevel()) / ".decision-queue" / "outbox"]
    return dirs


def ensure_outbox(d):
    d.mkdir(parents=True, exist_ok=True)
    marker = d.parent / ".gitignore"
    if d.name == "outbox" and d.parent.name == ".decision-queue" and not marker.exists():
        marker.write_text("*\n")  # the outbox must never be committed
    return d


def write_json(path, doc):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2) + "\n")
    os.replace(tmp, path)


def read_json(path):
    return json.loads(path.read_text())


def find_packet(dirs, pid):
    """(outbox, doc, state) or raise LookupError. Corrupt files raise ValueError (fail closed)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", pid or ""):
        raise LookupError(f"malformed packet id {pid!r}")
    for d in dirs:
        f = d / f"{pid}.json"
        if f.exists():
            try:
                doc, state = read_json(f), read_json(d / f"{pid}.state.json")
            except (OSError, ValueError) as e:
                raise ValueError(f"packet {pid} unreadable ({e})")
            return d, doc, state
    raise LookupError(f"packet {pid} not found in this lane's outbox")


def repo_of(d):
    """The lane repo an outbox belongs to (<repo>/.decision-queue/outbox), else the cwd's."""
    if d.name == "outbox" and d.parent.name == ".decision-queue":
        return str(d.parent.parent)
    return None


def is_driver(args):
    return bool(getattr(args, "driver", False)) or os.environ.get("HERDR_AGENT_NAME") == "driver"


def queue_url():
    url = (os.environ.get("DECISION_QUEUE_URL") or "").strip().rstrip("/")
    return url if url.startswith(("http://", "https://")) else ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # a 3xx surfaces as HTTPError: urllib would re-issue the POST as a body-less GET


def post(path, doc):
    """(kind, note); kind is ok | conflict | missing | rejected | blocked.
    200/201/204 are ok (a 200 `duplicate` is the queue confirming an identical retry);
    409 = the queue holds DIFFERENT content for this id (conflict, never sent);
    404 on /events = an event whose packet the queue lacks (missing: keep, retry after the packet);
    400/413/415/422 = definitive content refusals (rejected, permanent);
    everything else (401/403/408/429, 404 on /packets, other 4xx, 5xx, 3xx, network,
    timeout) = blocked: a credential, rate or URL problem is not the packet's fault, so retry.
    Hard post_timeout() wall clock: DNS and slow-drip servers defeat a per-socket timeout."""
    req = urllib.request.Request(queue_url() + path, data=json.dumps(doc).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    opener = urllib.request.build_opener(_NoRedirect)
    box = []
    timeout = post_timeout()

    def work():
        try:
            with opener.open(req, timeout=timeout) as r:
                box.append(("ok" if r.status in (200, 201, 204) else "blocked", f"HTTP {r.status}"))
        except urllib.error.HTTPError as e:
            if e.code == 404 and path == "/events":
                kind = "missing"
            else:
                kind = {409: "conflict"}.get(e.code, "rejected" if e.code in REFUSED else "blocked")
            box.append((kind, f"HTTP {e.code}"))
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
            box.append(("blocked", str(getattr(e, "reason", e))))

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout)
    return box[0] if box and not t.is_alive() else ("blocked", f"timed out after {timeout:g}s")


def new_id(prefix):
    return prefix + secrets.token_hex(6)


def emit_event(d, kind, body, packet_id=None, reversal_cost=None):
    ident = lane_identity()
    ev = {"schema_version": 1, "id": new_id("ev"), "kind": kind, "created_at": now(),
          "machine": ident[0], "workspace": ident[1], "agent": ident[2], "body": body}
    if packet_id:
        ev["packet_id"] = packet_id
    if reversal_cost:
        ev["reversal_cost"] = reversal_cost
    errs = schema_check.validate(ev, "event")
    if errs:
        raise ValueError("; ".join(errs))
    write_json(ensure_outbox(d) / f"evt-{ev['id']}.json", ev)
    return ev


def sent_marker(d, pid):
    return d / f"{pid}.sent"


def is_sent(d, pid):
    return sent_marker(d, pid).exists()


def _refusal(d, stem, kind, note, what):
    """Write <stem>.conflict / <stem>.rejected so the item is never retried forever."""
    (d / f"{stem}.{kind}").write_text(note + "\n")
    if kind == "conflict":
        return f"Conflict: {what} id was reused with different content ({note}); not sent, marked {stem}.conflict"
    return f"Rejected: queue refused {what} ({note}); not sent, marked {stem}.rejected"


def _refuse_event(d, ev):
    """An event of a packet the queue refused is never POSTed (10.1-r7-02/03)."""
    stem = f"evt-{ev['id']}"
    (d / f"{stem}.rejected").write_text("packet refused\n")
    return f"Rejected: event {ev['id']} not sent: its packet {ev['packet_id']} was refused by the queue (packet refused); marked {stem}.rejected"


def _clear_refusals(d, pid):
    """A delivered packet never coexists with a refusal marker (10.1-r10-01). Every packet POST
    goes through try_send, so clearing here covers `new --id` and flush alike. Events of this
    packet that were only marked "packet refused" are released so flush POSTs them; an event's
    own refusal (a verdict on its content) is left alone. Harness errors never stop the caller
    (10.1-r12-01): an unreadable or undeletable marker is reported in one line and left in place
    (fail closed: never guess), and flush retries this for every sent packet on each run."""
    bad = []

    def drop(f):
        try:
            f.unlink(missing_ok=True)
        except OSError as e:
            bad.append(f"{f.name} ({e})")

    for k in ("conflict", "rejected"):
        drop(d / f"{pid}.{k}")
    for f in sorted(d.glob("evt-*.rejected")):
        try:
            if f.read_text() != "packet refused\n":
                continue
            mine = read_json(f.with_suffix(".json")).get("packet_id") == pid
        except (OSError, ValueError) as e:
            bad.append(f"{f.name} unreadable ({e})")
            continue
        if mine:
            drop(f)
    if bad:
        print(f"packet.py: warning: packet {pid} delivered but refusal markers not cleared: "
              f"{'; '.join(bad)}; `packet.py flush` retries", file=sys.stderr)


def try_send(args, d, ev=None, pid=None):
    """POST a stored item if this caller may. Returns a human note ('' when not attempted).
    "sent" lives in a marker file, never in the state file: a concurrent close/stale must not
    be overwritten by a write-back that spans the network call (10.1-r1-02)."""
    if not (queue_url() and is_driver(args)):
        return ""
    if ev is not None:
        pk = ev.get("packet_id")
        if pk and any((d / f"{pk}.{k}").exists() for k in ("conflict", "rejected")):
            return _refuse_event(d, ev)
        kind, note = post("/events", ev)
        if kind == "ok":
            (d / f"evt-{ev['id']}.sent").write_text(note + "\n")
            return ""
        if kind in ("conflict", "rejected"):
            return _refusal(d, f"evt-{ev['id']}", kind, note, f"event {ev['id']}")
        if kind == "missing":
            return f"{HELD}event {ev['id']} kept: its packet is not on the queue yet ({note}); `packet.py flush` retries after the packet"
        return f"Blocked: queue unreachable ({note}); event kept in outbox, `packet.py flush` re-sends"
    try:
        doc = read_json(d / f"{pid}.json")
    except (OSError, ValueError) as e:
        return f"{SKIP}packet {pid} unreadable ({e}); not sent"
    kind, note = post("/packets", doc)
    if kind == "ok":
        sent_marker(d, pid).write_text(note + "\n")
        _clear_refusals(d, pid)
        return ""
    if kind in ("conflict", "rejected"):
        return _refusal(d, pid, kind, note, f"packet {pid}")
    return f"Blocked: queue unreachable ({note}); packet kept in outbox, `packet.py flush` re-sends"


REC_TEXT = re.compile(r"\s*\(recommended\)", re.I)


def show(doc, extra=""):
    print(f"PACKET {doc['id']}")
    print(f"  [{doc['door']}] {doc['title']}  ({doc['unit']} @ {doc['head_sha'][:7]})")
    for i, o in enumerate(doc["options"], 1):
        label = REC_TEXT.sub("", o["label"])  # the flag is the only marker: a v1 label may say it on any option
        print(f"  {i}. {label}{'  (recommended)' if o['recommended'] else ''}")
        if o.get("why"):
            print(f"     {o['why']}")
    # v2: the terminal is the card when the queue is unset or down, so it carries the same
    # decision-order text as the queue's detail page — context, then evidence (10.4-r14-04)
    for head, text in (("context", doc.get("context")), ("evidence", doc.get("evidence"))):
        if text:
            print(f"  {head}:")
            for line in str(text).splitlines():
                print(f"    {line}")
    print(f"  reply: {doc['reply']}")
    if extra:
        print(f"  {extra}")


# --- commands -------------------------------------------------------------------

PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_CAP_BYTES = 1_500_000  # 2,000,000 base64 chars; same cap as the schema and the queue


def ui_payload_errors(payload):
    """Fail-closed checks the schema pattern cannot make: strict base64, PNG signature, byte cap,
    and the demo-tenant declaration check (tenant must equal $DQ_UI_DEMO_TENANT; unset -> refuse). It catches a missing or wrong declaration, not a mislabelled shot."""
    import base64
    import binascii
    errs = []
    demo = os.environ.get("DQ_UI_DEMO_TENANT", "")
    if not demo:
        errs.append("DQ_UI_DEMO_TENANT is not set: no UI packet without a declared demo tenant")
    elif not isinstance(payload, dict) or payload.get("tenant") != demo:
        errs.append("payload tenant does not equal $DQ_UI_DEMO_TENANT (shots must be declared from the demo tenant)")
    for k in ("old", "new"):
        shot = payload.get(k) if isinstance(payload, dict) else None
        img = shot.get("image") if isinstance(shot, dict) else None
        if not isinstance(img, str) or not img.startswith("data:image/png;base64,"):
            errs.append(f"/payload/{k}/image: not a PNG data URI")
            continue
        try:
            raw = base64.b64decode(img.split(",", 1)[1], validate=True)
        except (binascii.Error, ValueError):
            errs.append(f"/payload/{k}/image: invalid base64")
            continue
        if not raw.startswith(PNG_SIG):
            errs.append(f"/payload/{k}/image: decoded bytes are not a PNG")
        elif len(raw) > PNG_CAP_BYTES:
            errs.append(f"/payload/{k}/image: {len(raw)} bytes exceeds the {PNG_CAP_BYTES}-byte cap")
    return errs


# v2 caps — the same numbers as schemas/packet.schema.json's bounded-repeat patterns
# (test_packet.py checks they agree). Checked here first so the refusal says what to cut.
V2_CAPS = {"title": 100, "context": 400, "evidence": 4000, "label": 60, "why": 140}


def _cut(field, text):
    cap = V2_CAPS[field.split()[-1]]
    return f"cut {field} to {cap} chars (now {len(text)})" if len(text) > cap else None


def v2_errors(args, options, evidence):
    """Refusals for a v2 `new`, each naming what to change. Empty list = go on to the schema."""
    errs = []
    if args.body is not None or args.body_file:
        errs.append("v2 has no body: put the situation in --context (<= 400 chars) and file:line, "
                    "doc refs and SHAs in --evidence; --schema-version 1 writes the legacy card")
    if not args.context:
        errs.append("--context is required: the situation in plain words, about 3 sentences")
    if "\n" in args.title:
        errs.append("title must be one line: the question")
    for field, text in (("title", args.title), ("context", args.context or ""), ("evidence", evidence or "")):
        errs += [e for e in [_cut(field, text)] if e]
    for i, o in enumerate(options, 1):
        if not o["why"]:
            errs.append(f"option {i} needs a why: --option \"label::what changes for Alex if he picks it\"")
        if REC_TEXT.search(o["label"]):
            errs.append(f"drop \"(recommended)\" from option {i}'s label: --recommended N marks it")
        if "\n" in o["label"]:
            errs.append(f"option {i} label must be one line")
        errs += [e for e in (_cut(f"option {i} label", o["label"]), _cut(f"option {i} why", o["why"])) if e]
    return errs


def cmd_new(args):
    dirs = outboxes(args)
    if args.id:
        try:
            d, doc, _ = find_packet(dirs, args.id)
            note = try_send(args, d, pid=args.id)
            show(doc, note or "(existing packet re-sent: idempotent on id)")
            return 0
        except LookupError:
            pass
        except ValueError as e:
            print(f"packet.py: {e}", file=sys.stderr)
            return 1
    try:
        head = git("rev-parse", "HEAD")
        repo = os.path.basename(toplevel())
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"packet.py: cannot read repo state ({e}); run inside a git worktree", file=sys.stderr)
        return 1
    door, door_note = args.door, ""
    if args.range:
        res = _load("door").classify(toplevel(), args.range, args.door)
        if res["door"] != args.door:
            door_note = f"door promoted to {res['door']} by door.py: {res['reason']}"
        door = res["door"]
    pid = args.id or new_id("pk")
    m, w, a = lane_identity()
    if a == "session-none":
        print("packet.py: warning: no session id in the environment; this lane's identity is "
              "shared with any other session-none lane in this repo", file=sys.stderr)
    v2 = args.schema_version == 2
    if v2:
        options = []
        for i, raw in enumerate(args.option, 1):
            label, _, why = raw.partition("::")
            options.append({"id": str(i), "label": label.strip(), "why": why.strip(),
                            "recommended": i == args.recommended})
        try:
            evidence = args.evidence if args.evidence is not None else (
                Path(args.evidence_file).read_text() if args.evidence_file else None)
        except (OSError, ValueError) as e:
            print(f"packet.py: evidence file unreadable ({e})", file=sys.stderr)
            return 1
        errs = v2_errors(args, options, evidence)
    else:
        options = [{"id": str(i), "label": lab, "recommended": i == args.recommended}
                   for i, lab in enumerate(args.option, 1)]
        evidence = None
        errs = ["v1 has no --context/--evidence: drop --schema-version 1 to write a v2 card"] \
            if (args.context or args.evidence is not None or args.evidence_file) else []
        # 10.4-r16-03: a marker on a non-selected option is a recommendation conflict; refuse, as v2 does
        errs += [f"drop \"(recommended)\" from option {o['id']}'s label: --recommended N marks it"
                 for o in options if REC_TEXT.search(o["label"]) and not o["recommended"]]
    if errs:
        print("packet.py: refused:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1
    if args.payload_file:
        try:
            payload = json.loads(Path(args.payload_file).read_text())
        except (OSError, ValueError) as e:
            print(f"packet.py: payload file unreadable ({e})", file=sys.stderr)
            return 1
    elif v2:
        payload = {}  # generic v2: the card is title + options + context (+ evidence)
    else:
        try:
            body = args.body if args.body is not None else (
                Path(args.body_file).read_text() if args.body_file else "")
        except (OSError, ValueError) as e:
            print(f"packet.py: body file unreadable ({e})", file=sys.stderr)
            return 1
        payload = {"body": body}
    rec = next((o for o in options if o["recommended"]), None)
    prefill = f"Option {rec['id']}: {REC_TEXT.sub('', rec['label'])}." if rec else "ack"
    doc = {"schema_version": args.schema_version, "id": pid, "created_at": now(), "machine": m, "workspace": w,
           "agent": a, "repo": repo, "branch": branch, "head_sha": head, "unit": args.unit,
           "door": door, "type": args.type, "title": args.title, "options": options,
           "blocks": args.blocks, "continues_on": args.continues_on, "payload": payload,
           "reply": f"{lane_tag(m, w, a, pid)} {prefill}"}
    if v2:
        doc["context"] = args.context
        if evidence:
            doc["evidence"] = evidence
    if door == "two-way":
        doc["reversal_cost"] = {"commits_stacked": 0, "as_of": now()}
    errs = schema_check.validate(doc)
    if args.type == "ui":
        errs = errs + ui_payload_errors(payload)
    if errs:
        print("packet.py: refused, packet is invalid:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1
    d = ensure_outbox(dirs[0])
    write_json(d / f"{pid}.json", doc)
    write_json(d / f"{pid}.state.json", {"status": "open"})
    note = try_send(args, d, pid=pid)
    if not note and not queue_url():
        note = "queue: DECISION_QUEUE_URL not set (outbox only)"
    elif not note and not is_driver(args):
        note = "queue: lane writes the outbox; the driver POSTs"
    show(doc, " | ".join(x for x in (door_note, note) if x))
    return 0


def _set_status(args, pid, status, kind, body):
    try:
        d, doc, state = find_packet(outboxes(args), pid)
    except (LookupError, ValueError) as e:
        print(f"packet.py: {e}", file=sys.stderr)
        return 1
    if state.get("status") == status:
        print(f"packet {pid} already {status}")
        return 0
    if state.get("status") != "open":
        print(f"packet.py: packet {pid} is {state.get('status')}, cannot become {status}", file=sys.stderr)
        return 1
    state["status"] = status
    write_json(d / f"{pid}.state.json", state)
    ev = emit_event(d, kind, body, packet_id=pid)
    note = try_send(args, d, ev=ev)
    print(f"{status.upper()} {pid}" + (f"\n  {note}" if note else ""))
    return 0


def cmd_close(args):
    return _set_status(args, args.id, "closed", "closed", "closed by lane after reply")


def cmd_stale(args):
    try:
        d, doc, state = find_packet(outboxes(args), args.id)
    except (LookupError, ValueError) as e:
        print(f"packet.py: {e}", file=sys.stderr)
        return 1
    if not args.force:
        try:
            head = git("rev-parse", "HEAD", cwd=repo_of(d))
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            print(f"packet.py: cannot read HEAD ({e}); not marking stale (use --force)", file=sys.stderr)
            return 1
        if head.startswith(doc["head_sha"]) or doc["head_sha"].startswith(head):
            print(f"packet {args.id} current (head unchanged)")
            return 0
    return _set_status(args, args.id, "stale", "stale", f"head moved past {doc['head_sha'][:7]}")


def cmd_touch(args):
    try:
        d, doc, state = find_packet(outboxes(args), args.id)
    except (LookupError, ValueError) as e:
        print(f"packet.py: {e}", file=sys.stderr)
        return 1
    if doc["door"] != "two-way" or state.get("status") != "open":
        print("packet.py: touch refreshes an open two-way card only", file=sys.stderr)
        return 1
    try:
        n = int(git("rev-list", "--count", f"{doc['head_sha']}..HEAD", cwd=repo_of(d)))
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as e:
        print(f"packet.py: cannot count commits ({e}); reversal cost not refreshed", file=sys.stderr)
        return 1
    rc = {"commits_stacked": n, "as_of": now()}
    doc["reversal_cost"] = rc
    write_json(d / f"{args.id}.json", doc)
    ev = emit_event(d, "touch", f"{n} commits stacked since {doc['head_sha'][:7]}",
                    packet_id=args.id, reversal_cost=rc)
    note = try_send(args, d, ev=ev)
    print(f"TOUCH {args.id} commits_stacked={n}" + (f"\n  {note}" if note else ""))
    return 0


def cmd_event(args):
    d = ensure_outbox(outboxes(args)[0])
    try:
        ev = emit_event(d, args.kind, args.body, packet_id=args.packet_id)
    except ValueError as e:
        print(f"packet.py: refused, event invalid: {e}", file=sys.stderr)
        return 1
    note = try_send(args, d, ev=ev)
    print(f"EVENT {ev['id']} {args.kind}" + (f"\n  {note}" if note else ""))
    return 0


def cmd_check_reply(args):
    if args.reply == "-" or (args.reply is None and not args.file):
        text = sys.stdin.read()
    elif args.file:
        try:
            text = Path(args.file).read_text()
        except (OSError, ValueError) as e:
            print(f"packet.py: reply refused: reply file unreadable ({e})", file=sys.stderr)
            return 1
    else:
        text = args.reply
    refuse = lambda why: (print(f"packet.py: reply refused: {why}", file=sys.stderr), 1)[1]
    tags = TAG_RE.findall(text)
    if not text.lstrip().startswith("[lane ") or not tags:
        return refuse("does not open with a lane tag [lane <machine>/<workspace>/<agent> <packet-id>]")
    if len(set(tags)) > 1:
        return refuse("more than one lane tag (ambiguous)")
    m, w, a, pid = tags[0]
    if not TAG_RE.match(text.lstrip()):
        return refuse("lane tag malformed")
    me = tuple(args.lane.split("/")) if args.lane else lane_identity()
    if not args.lane and me[2] == "session-none":
        return refuse("this lane has no session id, so its identity is shared; pass --lane M/W/A")
    if len(me) != 3:
        return refuse("--lane must be machine/workspace/agent")
    if (m, w, a) != tuple(me):
        return refuse(f"tag is for lane {m}/{w}/{a}, this lane is {'/'.join(me)}")
    try:
        d, doc, state = find_packet(outboxes(args), pid)
    except (LookupError, ValueError) as e:
        return refuse(str(e))
    if (doc.get("machine"), doc.get("workspace"), doc.get("agent")) != (m, w, a):
        return refuse(f"packet {pid} was emitted by another lane")
    if state.get("status") != "open":
        return refuse(f"packet {pid} is {state.get('status')}")
    if doc["door"] == "one-way":  # the lane is parked: HEAD moving means the decision is stale
        try:
            head = git("rev-parse", "HEAD", cwd=repo_of(d))
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            return refuse(f"cannot read HEAD to confirm the one-way packet is current ({e})")
        if not (head.startswith(doc["head_sha"]) or doc["head_sha"].startswith(head)):
            # bookkeeping commits (plans/ lives in the same repo) may land while parked;
            # anything else, a non-ancestor, or an unreadable git refuses (fail closed)
            try:
                git("merge-base", "--is-ancestor", doc["head_sha"], "HEAD", cwd=repo_of(d))
                moved = git("diff", "--name-only", "--no-renames", "-z", f"{doc['head_sha']}..HEAD",
                            cwd=repo_of(d)).split("\0")
            except (RuntimeError, OSError, subprocess.SubprocessError) as e:
                return refuse(f"one-way packet {pid} is stale: HEAD is not a descendant of "
                              f"{doc['head_sha'][:7]} or git is unreadable ({e}); run `stale`")
            other = [x for x in moved if x and not x.startswith("plans/")]
            if other:
                return refuse(f"one-way packet {pid} is stale: paths outside plans/ moved since "
                              f"{doc['head_sha'][:7]}: {', '.join(other[:5])}; run `stale`")
    print(f"OK {pid}")
    return 0


def cmd_flush(args):
    if not is_driver(args):
        print("flush: not a driver; nothing sent (lanes write the outbox, the driver POSTs)")
        return 0
    if not queue_url():
        print("flush: DECISION_QUEUE_URL not set; nothing sent")
        return 0
    sent = {"packets": 0, "events": 0}
    blocked, skipped = "", []
    for d in outboxes(args):
        if not d.is_dir():
            if args.outbox or os.environ.get("PACKET_OUTBOX"):  # the default outbox may just be empty
                skipped.append(f"{SKIP}outbox {d} does not exist")
            continue
        for f in sorted(d.glob("*.state.json")):
            pid = f.name[: -len(".state.json")]
            if is_sent(d, pid):
                _clear_refusals(d, pid)  # retry a cleanup that failed after the POST (10.1-r12-01)
                continue
            marked = next((k for k in ("conflict", "rejected") if (d / f"{pid}.{k}").exists()), "")
            if marked:
                skipped.append(f"{SKIP}packet {pid} is marked .{marked}; not retried")
                continue
            note = try_send(args, d, pid=pid)
            if note.startswith(NOT_SENT):  # one bad item never strands the rest of the outbox
                skipped.append(note)
                continue
            if note:
                blocked = note
                break
            sent["packets"] += 1
        if blocked:
            break
        for f in sorted(d.glob("evt-*.json")):
            if f.with_suffix(".sent").exists():
                continue
            marked = next((k for k in ("conflict", "rejected") if f.with_suffix("." + k).exists()), "")
            if marked:
                skipped.append(f"{SKIP}{f.name} is marked .{marked}; not retried")
                continue
            try:
                ev = read_json(f)
            except (OSError, ValueError) as e:
                skipped.append(f"{SKIP}{f.name} unreadable ({e}); not sent")
                continue
            note = try_send(args, d, ev=ev)
            if note.startswith(NOT_SENT):
                skipped.append(note)
                continue
            if note:
                blocked = note
                break
            sent["events"] += 1
        if blocked:
            break
    print(f"FLUSHED {sent['packets']} packets, {sent['events']} events")
    for note in skipped:
        print(f"  {note}")
    if blocked:
        print(f"  {blocked}")
    return 0


def main(argv):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--outbox", action="append")
    common.add_argument("--driver", action="store_true")
    ap = argparse.ArgumentParser(prog="packet.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", parents=[common])
    n.add_argument("--door", required=True, choices=["one-way", "two-way", "info"])
    n.add_argument("--type", default="generic", choices=["data-model", "generic", "ui"])
    n.add_argument("--title", required=True)
    n.add_argument("--unit", required=True)
    n.add_argument("--schema-version", type=int, default=2, choices=[1, 2])
    n.add_argument("--option", action="append", default=[], help='v2: "LABEL::WHY"; v1: LABEL')
    n.add_argument("--recommended", type=int, default=1)
    n.add_argument("--context")
    n.add_argument("--evidence")
    n.add_argument("--evidence-file")
    n.add_argument("--body")
    n.add_argument("--body-file")
    n.add_argument("--payload-file")
    n.add_argument("--blocks", default="")
    n.add_argument("--continues-on", default="")
    n.add_argument("--range")
    n.add_argument("--id")
    for name in ("close", "touch"):
        sub.add_parser(name, parents=[common]).add_argument("id")
    s = sub.add_parser("stale", parents=[common])
    s.add_argument("id")
    s.add_argument("--force", action="store_true")
    e = sub.add_parser("event", parents=[common])
    e.add_argument("--kind", required=True, choices=["done", "merged", "closed", "stale", "touch"])
    e.add_argument("--body", default="")
    e.add_argument("--packet-id")
    c = sub.add_parser("check-reply", parents=[common])
    c.add_argument("--reply")
    c.add_argument("--file")
    c.add_argument("--lane")
    sub.add_parser("flush", parents=[common])
    args = ap.parse_args(argv)
    if args.cmd == "new" and args.door != "info" and not args.option:
        ap.error("new: at least one --option is required for a one-way/two-way packet")
    return {"new": cmd_new, "close": cmd_close, "stale": cmd_stale, "touch": cmd_touch,
            "event": cmd_event, "check-reply": cmd_check_reply, "flush": cmd_flush}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""SafePlate server — serves the UI + runs local Gemma (llama.cpp) 100% offline.

Usage:  python server.py  ->  open http://localhost:8765/
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.environ.get(
    "SAFEPLATE_MODEL",
    r"C:\Users\duchu\AppData\Local\Temp\opencode\models\gemma-3-1b-it-Q4_K_M.gguf",
)
PORT = 8765

LLAMA_SERVER = os.environ.get("SAFEPLATE_LLAMA", "http://127.0.0.1:8080")

_llm = None


def llm():
    raise RuntimeError("unused: inference goes through llama-server")


AUDIENCES = {
    "sinh vien": "cheap market ingredients, cook in under 30 minutes",
    "gym": "high protein (thit, trung, ca, dau phu), note protein per day",
    "nguoi lon tuoi": "soft easy-to-chew foods, low salt and low sugar",
}


def make_prompt(allergies, servings, note, days=7, audience="sinh vien"):
    aller = ", ".join(allergies) if allergies else "nothing in particular"
    aud = AUDIENCES.get(audience, AUDIENCES["sinh vien"])
    return (
        "You are SafePlate, a Vietnamese meal-planning assistant. "
        "Write EVERYTHING in Vietnamese. "
        "The user is allergic to: " + aller + ". "
        "RULE 1 (safety): NEVER suggest any dish containing those allergens. "
        "RULE 2: dish names must be REAL Vietnamese home dishes "
        "(examples: thit kho tau, canh chua ca loc, ga rang gung, dau phu sot ca chua, "
        "trung chien thit bam, rau muong xao toi, canh bi do nau thit bam). "
        "RULE 3: ingredients must be real foods from a market "
        "(never generic words like chat beo, gia vi chung chung). "
        "RULE 4: list each day number from 1 to %d exactly once, no repeats. "
        "Audience: %s (%s). Add one short 'nutrition' note per day "
        "(e.g. protein source, balance). "
        "Servings per meal: %s. Note: %s. "
        "Reply with valid JSON ONLY "
        "(no markdown, no extra text) like: "
        '{"days": [{"day": 1, "dish": "...", "ingredients": ["..."], '
        '"steps": ["..."], "nutrition": "..."}], "shopping_list": ["..."]}' % (
            days, audience, aud, servings, note)
    )


def _clean(text):
    import re
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    s, e = t.find("{"), t.rfind("}")
    t = t[s:e + 1] if s != -1 and e != -1 else t
    t = re.sub(r",\s*([}\]])", r"\1", t)  # trailing commas
    return t


SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array", "maxItems": 9,
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "dish": {"type": "string"},
                    "ingredients": {"type": "array", "items": {"type": "string"}, "maxItems": 9},
                    "steps": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                    "nutrition": {"type": "string"},
                },
                "required": ["day", "dish", "ingredients", "steps"],
            },
        },
        "shopping_list": {"type": "array", "items": {"type": "string"}, "maxItems": 25},
    },
    "required": ["days", "shopping_list"],
}


VARIANTS = {
    "dau phong": ["dau phong", "dau lac", "lac", "peanut"],
    "tom": ["tom", "shrimp", "tep"],
    "cua": ["cua", "crab"],
    "ghe": ["ghe", "crab"],
    "trung": ["trung", "egg"],
    "sua": ["sua", "milk", "bo "],
    "dau nanh": ["dau nanh", "soy", "dau hu", "dau phu"],
    "bot mi": ["bot mi", "wheat", "gluten", "banh mi"],
}


def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _safe(day, allergies):
    blob = _norm(day.get("dish", "") + " " + " ".join(day.get("ingredients", [])))
    for a in allergies:
        for v in VARIANTS.get(_norm(a), [_norm(a)]):
            if v and v in blob:
                return False
    return True


def _post(plan, allergies, days):
    seen, out = set(), []
    for d in plan.get("days", []):
        name = _norm(d.get("dish", ""))
        if not name or name in seen or not _safe(d, allergies):
            continue
        seen.add(name)
        out.append(d)
        if len(out) == days:
            break
    for i, d in enumerate(out, 1):
        d["day"] = i
    shop, seen_s = [], set()
    for d in out:
        for x in d.get("ingredients", []):
            k = _norm(x)
            if k not in seen_s:
                seen_s.add(k)
                shop.append(x)
    plan["days"], plan["shopping_list"] = out, shop
    return plan


def generate(allergies, servings, note, days=7, audience="sinh vien"):
    import urllib.request
    prompt = make_prompt(allergies, servings, note, days, audience)
    last = ""
    for _ in range(3):
        body = json.dumps({
            "prompt": prompt,
            "n_predict": 2048,
            "temperature": 0.7,
            "repeat_penalty": 1.15,
            "cache_prompt": True,
            "json_schema": SCHEMA,
        }).encode()
        req = urllib.request.Request(
            LLAMA_SERVER + "/completion", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            last = json.loads(r.read().decode()).get("content", "")
        try:
            plan = json.loads(_clean(last))
            plan = _post(plan, allergies, days)
            if len(plan["days"]) >= max(1, min(days, 3)):
                return plan
        except Exception:
            continue
    raise ValueError("model JSON failed after 3 tries: " + last[:200])


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            with open(os.path.join(HERE, "static", "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif p == "/health":
            self._send(200, json.dumps({"ok": True, "model": "gemma-3-1b-it-Q4_K_M"}))
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/plan":
            return self._send(404, "not found", "text/plain")
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        try:
            plan = generate(req.get("allergies", []),
                            req.get("servings", 2),
                            req.get("note", ""), int(req.get("days", 7)),
                            req.get("audience", "sinh vien"))
            self._send(200, json.dumps(plan, ensure_ascii=False))
        except Exception as ex:
            self._send(500, json.dumps({"error": str(ex)[:500]}))


if __name__ == "__main__":
    print(f"SafePlate on http://localhost:{PORT}/ (model: {MODEL_PATH})")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()

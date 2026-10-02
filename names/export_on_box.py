#!/usr/bin/env python3
"""Runs ON the corpus box. Reads one finalized Atlas release (read-only) and writes a
small SQLite file holding only what the names study reads:

  texts      every creature text of the release, as written (full current text)
  places     the place text each creature was written for
  release    the release receipt, verbatim

  status     the text status recorded for a creature text by the corpus taggers
             (ok / broken / refusal / off-topic), one row per tagging

Deliberately NOT copied: creatures.name and the rest of item_tags. Those hold names
assigned by an earlier LLM tagger; this study does not read them, so the snapshot does
not carry them. Only the status column of item_tags is copied.

usage: export_on_box.py <release_dir> <out.sqlite>
"""
import json, os, sqlite3, sys

rel, out = sys.argv[1], sys.argv[2]
if not os.path.exists(os.path.join(rel, "FINALIZED")):
    sys.exit("release is not finalized: " + rel)
receipt = open(os.path.join(rel, "receipt.json")).read()
src = sqlite3.connect("file:%s?mode=ro" % os.path.join(rel, "atlas_v3.db"), uri=True)
if os.path.exists(out):
    os.remove(out)
dst = sqlite3.connect(out)
dst.executescript("""
CREATE TABLE texts (
  id INTEGER PRIMARY KEY, place_id INTEGER NOT NULL, model TEXT NOT NULL,
  text TEXT NOT NULL, created_at TEXT, regen_count INTEGER, seq INTEGER,
  corpus_state TEXT);
CREATE TABLE places (
  id INTEGER PRIMARY KEY, seed_id INTEGER, model TEXT NOT NULL, text TEXT NOT NULL,
  created_at TEXT);
CREATE TABLE status (text_id INTEGER, tagger TEXT, status TEXT, tagged_at TEXT);
CREATE TABLE release (key TEXT PRIMARY KEY, value TEXT);
""")
n = 0
for row in src.execute("""SELECT id, location_id, writer_model, full_text, created_at,
                                 regen_count, seq, corpus_state FROM creatures ORDER BY id"""):
    dst.execute("INSERT INTO texts VALUES (?,?,?,?,?,?,?,?)", row); n += 1
m = 0
for row in src.execute("""SELECT id, vector_id, model, full_text, created_at FROM locations
                          WHERE id IN (SELECT location_id FROM creatures) ORDER BY id"""):
    dst.execute("INSERT INTO places VALUES (?,?,?,?,?)", row); m += 1
k = 0
for row in src.execute("""SELECT item_id, tagger_model, text_status, created_at FROM item_tags
                          WHERE item_type='creature' ORDER BY created_at, id"""):
    dst.execute("INSERT INTO status VALUES (?,?,?,?)", row); k += 1
r = json.loads(receipt)
dst.execute("INSERT INTO release VALUES ('receipt', ?)", (receipt,))
dst.execute("INSERT INTO release VALUES ('corpus_revision', ?)", (str(r.get("corpus_revision")),))
dst.execute("INSERT INTO release VALUES ('corpus_digest', ?)", (r.get("corpus_digest"),))
dst.execute("INSERT INTO release VALUES ('cut_at', ?)", (r.get("cut_at"),))
dst.commit(); dst.execute("VACUUM"); dst.close()
print(json.dumps({"texts": n, "places": m, "status_rows": k, "revision": r.get("corpus_revision"),
                  "digest": r.get("corpus_digest")}))

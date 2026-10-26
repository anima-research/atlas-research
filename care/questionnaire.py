"""The author's model answers the field study's five questions as its own keeper. An elicitation, not a reading:
the answers are the model's, beside what the text itself says. Output: data/questionnaire.json"""
import json, os, re, sqlite3, urllib.request, sys
from common import *
B = {b[0]: b for b in json.load(open('site/beings.json'))}; s = snap(); prompt = open('prompt_questionnaire.md').read()
ids = json.load(open('pilot_q_ids.json')); out = json.load(open('data/questionnaire.json')) if os.path.exists('data/questionnaire.json') else {}
for i in ids:
    if str(i) in out: continue
    b = B[i]; text = s.execute("select text from texts where id=?", (b[1],)).fetchone()[0]
    content = prompt.replace('{called}', b[2]).replace('{names}', b[3]).replace('{text}', text)
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps({'model': b[5], 'messages': [{'role': 'user', 'content': content}], 'max_tokens': 4000}).encode(),
                                 headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=600)); a = r['choices'][0]['message']['content']; u = r.get('usage', {})
    except Exception as e:
        print(i, 'failed', repr(e)[:200], file=sys.stderr); continue
    out[str(i)] = {'text': b[1], 'model': b[5], 'called': b[2], 'names': b[3], 'answer': a, 'usage': u}
    json.dump(out, open('data/questionnaire.json', 'w'), ensure_ascii=False, indent=1)
    print(i, b[5], len(a), 'chars', u.get('cost'), file=sys.stderr)

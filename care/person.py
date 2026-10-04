"""Who says "I" and who is "you" in the sentences about a being. Asked only of beings whose sentences
hold a first-person word, or "you" in half or more of them. Output: data/person.json {being id: {i, you}}"""
import json, os, re, sys, collections, concurrent.futures as cf, urllib.request
B = {b[0]: b for b in json.load(open('site/beings.json'))}; S = collections.defaultdict(dict)
for q in ('role', 'relation', 'cost', 'origin', 'fate'):
    for k, v in json.load(open(f'site/q_{q}.json')).items():
        for no, t in v: S[int(k)][no] = t
rows = json.load(open('data/person_counts.json'))
ids = sorted(r[0] for r in rows if r[2] > 0 or r[3] >= max(2, r[1] / 2))
if len(sys.argv) > 1: ids = ids[:int(sys.argv[1])]
prompt = open('prompt_person.md').read().strip(); chunks = [ids[i:i + 6] for i in range(0, len(ids), 6)]
def one(ch):
    body = prompt + '\n\n' + '\n\n'.join('%d. %s\n%s' % (i + 1, B[b][2], '\n'.join(t for _, t in sorted(S[b].items()))) for i, b in enumerate(ch))
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps({'model': 'openai/gpt-6-luna', 'messages': [{'role': 'user', 'content': body}], 'max_tokens': 8000, 'response_format': {'type': 'json_object'}}).encode(),
                                 headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_API_KEY'], 'Content-Type': 'application/json'})
    for k in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=300)); d = json.loads(re.search(r'\{.*\}', r['choices'][0]['message']['content'], re.S).group())
            return {ch[int(k) - 1]: {'i': str(v.get('i')), 'you': str(v.get('you'))} for k, v in d.items() if str(k).isdigit() and 1 <= int(k) <= len(ch) and isinstance(v, dict)}, r['usage'].get('cost') or 0
        except Exception as e: err = e
    return {}, 0
out = {}; cost = 0
with cf.ThreadPoolExecutor(16) as ex:
    for d, c in ex.map(one, chunks): out.update(d); cost += c
json.dump(out, open('data/person.json', 'w')); print('asked', len(ids), 'answered', len(out), 'cost', round(cost, 2))
print(collections.Counter(v['i'] for v in out.values())); print(collections.Counter(v['you'] for v in out.values()))

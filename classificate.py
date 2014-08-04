import json
import re
import time

# I'm not going to check for failure here.  You figure it out.
with open("docs2.json", 'r') as f: docs = json.load(f)
with open("isocodes.json", 'r') as f: upper_codes = json.load(f)

def clean(s): return \
    filter(lambda c: 0x20 <= ord(c) <= 0x7E or c in "\n\r\t", s).lower().strip()

def get_time(doc, field):
  for f in ["%Y-%m-%d", "%m/%d/%Y"]:
    try: return time.strptime(doc[field], f)
    except: pass
    pass
  raise ValueError("No good times found in %s" % doc[field])

def date(doc):
  date = get_time(doc, "release_date")
  doc["release_date"] = time.strftime("%Y-%m-%d", date)

def identify(doc):
  date = get_time(doc, "release_date")
  rel = doc["released_by"]
  title = doc["title"]

  fields = [time.strftime("%Y%m%d", date), rel, title]
  doc["id"] = clean('|'.join(fields).replace(" ", "").replace("/", ""))

def dock(cs):
  for c in ["ts", "s", "c", "pt", "cui", "u"]:
    if reduce(lambda acc, x: acc or x.startswith(c), cs, False):
      return c.upper()
    pass
  return None

def getclassification(p):
  res = dock(re.findall("(?<=\()" + ".*?" + "(?=/+.*\))", p))
  if res: return res

  res = dock(re.findall("(?<=\()" + "[a-z]*?" + "(?=\))", p))
  if res: return res

  if "topsecret" in p: return "TS"
  elif "secret" in p: return "S"
  elif "confidential" in p: return "C"
  elif "publictrust" in p: return "PT"
  elif "controlledunclassifiedinformation" in p: return "CUI"
  elif "unclassified" in p: return "U"

  return ""

def getrelto(p):
  raw = clean(''.join(re.findall("(?<=relto)" + "[^\\n\)]*", p)))
  raw = filter(lambda c: 'a' < c < 'z', raw).upper()

  shared = []
  if "FVEY" in raw:
    shared += ["AUS", "CAN", "NZL", "USA", "GBR"]
    raw = raw.replace("FVEY", " ")
    pass
  for code in upper_codes.keys():
    if upper_codes[code] in raw:
      shared.append(upper_codes[code])
      raw = raw.replace(upper_codes[code], " ")
      pass
    pass
  for code in upper_codes.keys():
    if code in raw:
      shared.append(upper_codes[code])
      raw = raw.replace(code, " ")
      pass
    pass

  return list(set(shared))

def getcaveats(p):
  # This is simple, but in practice will generate a lot of both false
  # positives and false negatives.
  #
  # The false positives occur because we are overgenerous on our matching of
  # paren-bounded slash-delimited terms.
  #
  # The false negatives occur because it is infeasible to run over the raw
  # document ignoring the parens because what the classification levels are
  # named is itself classified.

  raw = re.findall("(?<=\()" + "[a-z/]*?/[a-z/]*?" + "(?=\))", p)
  raw = map(lambda e: e.split("/")[1:], raw)
  raw = reduce(lambda acc, x: acc + x, raw, [])
  raw = filter(lambda e: not (e == "" or e == None), raw)
  raw = list(set(raw))
  return raw

def paragraphs(doc):
  ps = map(lambda p: clean(p), doc["doc_text"].splitlines())
  i = 0
  psaux = []
  while True:
    if i >= len(ps): # list modification while iterating
      break
    t = ps[i].replace(" ", "")
    if t in [None, ""]:
      del(ps[i])
      continue

    d = {}
    d["paragraph_text"] = ps[i]
    d["paragraph_classification"] = getclassification(t)
    d["paragraph_relto"] = getrelto(t)
    d["paragraph_handling_caveats"] = getcaveats(t)
    psaux.append(d)

    i += 1
    pass
  del(i)
  doc["sub_paragraphs_classifications"] = psaux

  return

def overall(doc):
  # Hopefully, the article classification is the first one.
  psaux = doc["sub_paragraphs_classifications"]

  try: doc["overall_classification"] = psaux[0]["paragraph_classification"]
  except: doc["overall_classification"] = ""

  try: doc["overall_relto"] = psaux[0]["paragraph_relto"]
  except: doc["overall_relto"] = []

  try: doc["overall_handling_caveats"] = \
     psaux[0]["paragraph_overall_handling_caveats"]
  except: doc["overall_handling_caveats"] = []

  return

ind = 0
while True:
  if ind >= len(docs): # list modification while iterating
    break

  try:
    docs[ind]["doc_text"][0]
  except:
    del(docs[ind])
    continue
    pass

  ind += 1
  pass
del(ind)

for d in docs:
  date(d)
  identify(d)
  paragraphs(d)
  overall(d)
  pass
pass
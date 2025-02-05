import json
import re

dumpfile = "dumps/dumpAPIScrutartPosts20250202.json"
with open(dumpfile, "r", encoding="UTF-8") as fdump:
    posts = json.load(fdump)

regex1 = r".*\n.*\"qid\": \"(Q[0-9]*)"
regex2 = r"p>Je vais faire dans ce billet une analyse de la présence des œuvres de <a href=\"http://www.wikidata.org/entity/(Q[0-9]*)"

posts_dict = {}

for post in posts:
    if ("content" in post) and ("raw" in post["content"]):
        qid = "???"
        match = re.search(regex1, post["content"]["raw"], re.MULTILINE)
        if match:
            qid = match.group(1)
        else:
            match = re.search(regex2, post["content"]["raw"], re.MULTILINE)
            if match:
                qid = match.group(1)
            else:
                qid = f"IDWP_{post['id']}"

        posts_dict[qid] = post

    print(f"QID: {qid}, ID: {post['id']}, Title: {post['title']['rendered']}, Status: {post['status']}")

dumpfile = "dumps/dumpDictAPIScrutartPosts20250202.json"
with open(dumpfile, "w", encoding="UTF-8") as fdump:
    json.dump(posts_dict, fdump, ensure_ascii=False)

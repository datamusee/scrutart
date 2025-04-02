import json
import re

# but: prendre un dump des post sous forme de liste, reconnaitre les QIDs concernés
# s'en servir de clé pour construire un dict avec le dump des posts liés à un QID

# fichier qui contient un dump des posts présents dans le wordpress scrutart
dumpfile = "dumps/dumpAPIScrutartPosts20250202.json"
with open(dumpfile, "r", encoding="UTF-8") as fdump:
    posts = json.load(fdump)

# regex pour voir si le champ raw d'un article contient un json de metadata d'un artiste avec son QID
regex1 = r".*\n.*\"qid\": \"(Q[0-9]*)"
# regex qui permet de tester si la phrase d'introduction d'une analyse liée à un QID est présente
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
        print(f"""{{"qid": "{qid}", "title": "{post['title']['rendered']}", "idwordpress": "{post['id']}", "status": "{post['status']}", "date": "{post['modified']}" }}""")

dumpfile = "dumps/dumpDictAPIScrutartPosts20250202.json"
with open(dumpfile, "w", encoding="UTF-8") as fdump:
    json.dump(posts_dict, fdump, ensure_ascii=False)

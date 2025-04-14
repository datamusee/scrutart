from src.generationWordpress.WikimediaAccess import WikimediaAccess

from functools import lru_cache
from  datetime import datetime
@lru_cache(maxsize=None)
def testCachedQuery(query):
    w_obj = WikimediaAccess(qid)
    res = w_obj.sparqlQuery(crtquery)
    return res

qid = "Q5597"
crtquery = f"""select ?s where {{ ?s ?p wd:{qid} }} limit 1"""
for i in range(0, 10):
    print(datetime.now())
    res = testCachedQuery(crtquery)
pass
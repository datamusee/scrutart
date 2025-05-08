from WPTools import WPTools
import configPrivee2 as configPrivee
import re

"""
TODO
par défaut, getWPPages doit récupérer toutes les pages en utilisant les spécifications ci-dessous
et donc intégrer une partie du code ci-dessous en faisant mieux grâce aux spécifications ci-dessous
Pagination Parameters
Any API response which contains multiple resources supports several common query parameters to handle paging through the response data:

?page=: specify the page of results to return.
For example, /wp/v2/posts?page=2 is the second page of posts results
By retrieving /wp/v2/posts, then /wp/v2/posts?page=2, and so on, you may access every available post through the API, one page at a time.
?per_page=: specify the number of records to return in one request, specified as an integer from 1 to 100.
For example, /wp/v2/posts?per_page=1 will return only the first post in the collection
?offset=: specify an arbitrary offset at which to start retrieving posts
For example, /wp/v2/posts?offset=6 will use the default number of posts per page, but start at the 6th post in the collection
?per_page=5&page=4 is equivalent to ?per_page=5&offset=15
Large queries can hurt site performance, so per_page is capped at 100 records. If you wish to retrieve more than 100 records, for example to build a client-side list of all available categories, you may make multiple API requests and combine the results within your application.

To determine how many pages of data are available, the API returns two header fields with every paginated response:

X-WP-Total: the total number of records in the collection
X-WP-TotalPages: the total number of pages encompassing all available records
By inspecting these header fields you can determine how much more data is available within the API.
"""
if __name__ == '__main__':
    # Exemple d'utilisation
    pagesByQID = {}
    creatorPagesByQID = {}
    notCreatorPageByQID = {}
    wpt = WPTools(configPrivee)
    pages = []
    indexpage = 1
    while True:
        if indexpage!=None:
            newpages = wpt.getWPPages(perPage=100, page=indexpage)
            if newpages:
                pages.extend(newpages)
            else:
                break
            indexpage += 1 if newpages else None

    regex1 = r".*\n.*\"qid\": \"(Q[0-9]*)"
    # todo les galeries sont catégorisées par leur parente pour savoir si c'est un artiste, un mouvement ou un genre
    # les galeries sont associées à un QID dans les données json préparatoires (et bientot dans scrutart-state)
    for page in pages:
        if """{ "qid": "Q""" in page["content"]["rendered"]:
            match = re.search(regex1, page["content"]["rendered"], re.MULTILINE)
            if match:
                qid = match.group(1)
                pagesByQID[qid] = page
                if "Où trouver" in page["title"]["rendered"]:
                    creatorPagesByQID[qid] = page
                else:
                    notCreatorPageByQID[qid]= page
    publishedCreatorsCount = 0
    for qid, page in creatorPagesByQID.items():
        publishedCreatorsCount +=1 if page["status"]=="publish" else 0
    pass
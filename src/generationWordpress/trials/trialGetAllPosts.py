import json

import requests

import src.generationWordpress.configPrivee2 as configPrivee

api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)

# WordPress site details
wordpress_site_url = "https://scrutart.grains-de-culture.fr"
api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
# api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"

auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)
username = configPrivee.WORDPRESS_O2_API2USERNAME
password = configPrivee.WORDPRESS_O2_API2PASSWORD_APP


# Function to fetch posts
def get_all_posts(api_endpoint):
    try:
        all_posts = []
        page = 1
        while True:
            # Fetch a page of posts
            data = {
                "per_page": 100,
                "page": page,
                "post_type": "post",
                "context": "edit",
                "status": "publish, future, draft, pending, private"
            }
            response = requests.get(api_endpoint, data=data, auth=auth, params=data)

            if response.status_code == 200:
                posts = response.json()
                if not posts:
                    break  # No more posts
                all_posts.extend(posts)
                page += 1
            else:
                print(f"Error: {response.status_code} - {response.text}")
                break

        return all_posts

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# Fetch all posts
posts = get_all_posts(api_endpoint)

if posts:
    print(f"Total posts fetched: {len(posts)}")
    for post in posts:
        print(f"ID: {post['id']}, Title: {post['title']['rendered']}, Status: {post['status']}")
    dumpfile = "dumps/dumpAPIScrutartPosts20250202.json"
    with open(dumpfile, "w", encoding="UTF-8") as fdump:
        json.dump(posts, fdump, ensure_ascii=False)
else:
    print("No posts retrieved.")

import html

def generate_multilang_banner(creator_name, page_slug):
    fr_text = f'Une analyse des œuvres de ce créateur peut être vue dans la page <a href="index.php?/page/{page_slug}">Analyse des œuvres de {creator_name}</a>.'
    en_text = f'An analysis of this creator\'s work can be found on the <a href="index.php?/page/{page_slug}">Analysis of {creator_name}\'s Work</a>.'

    return html.escape(f"""
        [lang=all]
        <style>
        .banniere-analyse {{
          display: flex;
          align-items: center;
          gap: 1em;
          background: #d0d8ff;
          border-left: 5px solid #007acc;
          padding: 1em;
          margin: 1.0em 0;
          border-radius: 10px;
          font-family: sans-serif;
          flex-wrap: wrap;
        }}
        .banniere-analyse-icon {{
          font-size: 2em;
          color: #007acc;
        }}
        .banniere-analyse-text {{
          flex: 1;
          min-width: 200px;
        }}
        .banniere-analyse-text a {{
          color: #007acc;
          text-decoration: underline;
        }}
        @media (max-width: 600px) {{
          .banniere-analyse {{
            flex-direction: column;
            align-items: flex-start;
          }}
        }}
        </style>
        [/lang]
        [lang=all]
        <div class="banniere-analyse">
          <div class="banniere-analyse-icon">📘</div>
        [/lang]
        [lang=fr]
          <div class="banniere-analyse-text">{fr_text}</div>
        [/lang]
        [lang=en]
          <div class="banniere-analyse-text">{en_text}</div>
        [/lang]
        [lang=all]
        </div>
        [/lang]
    """)

def update_banner_for_category(client, category_id, creator_name, page_slug):
    html = generate_multilang_banner(creator_name, page_slug)
    return client.update_category_description(category_id, html)

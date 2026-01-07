def to_html(mermaid_code: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({{
  startOnLoad:true,
  theme:"default",
  flowchart: {{ useMaxWidth: true }}
}});
</script>
</head>
<body>
<div class="mermaid">
{mermaid_code}
</div>
</body>
</html>"""

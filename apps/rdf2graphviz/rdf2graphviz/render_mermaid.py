import hashlib


def mid(text: str) -> str:
    return "n_" + hashlib.md5(text.encode()).hexdigest()[:8]


def render_neo4j(entities, relations):
    lines = [
        "graph LR",
        "classDef entity fill:#E3F2FD,stroke:#1E88E5,stroke-width:2px;",
        "classDef prop fill:#FAFAFA,stroke:#999,stroke-dasharray: 3 3;"
    ]

    for e in entities.values():
        eid = mid(e.uri)
        lines.append(f'{eid}(({e.label}))')
        lines.append(f'class {eid} entity')
        lines.append(f'click {eid} "{e.uri}"')

        if e.properties:
            pid = mid(e.uri + "_props")
            props = "<br/>".join(
                f"<b>{k}</b>: {', '.join(v)}"
                for k, v in e.properties.items()
            )
            lines.append(f'{pid}["{props}"]')
            lines.append(f'class {pid} prop')
            lines.append(f'{eid} --- {pid}')

    for r in relations:
        lines.append(
            f'{mid(r.source)} -->|"{r.predicate}"| {mid(r.target)}'
        )

    return "\n".join(lines)

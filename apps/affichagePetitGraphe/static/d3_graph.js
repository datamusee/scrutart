document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('triples-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        document.getElementById('json-code').value = JSON.stringify(data, null, 2);
        renderGraph(data, formData.get('mode'));
    });

    document.getElementById('copy-button').addEventListener('click', function() {
        const jsonCodeElement = document.getElementById('json-code');
        jsonCodeElement.select();
        document.execCommand('copy');
        alert('Données JSON copiées dans le presse-papiers !');
    });
});

function renderGraph(data, mode) {
    d3.select('#graph').selectAll('*').remove();

    const width = 800;
    const height = 600;

    const svg = d3.select('#graph').append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', `0 0 ${width} ${height}`);

    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-500))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(50));

    const link = svg.append('g')
        .selectAll('line')
        .data(data.links)
        .enter()
        .append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 1.5);

    const node = svg.append('g')
        .selectAll('g')
        .data(data.nodes)
        .enter()
        .append('g')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    node.append('rect')
        .filter(d => d.type === 'entity')
        .attr('width', 100)
        .attr('height', 30)
        .attr('x', -50)
        .attr('y', -15)
        .attr('fill', '#69b3a2')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .attr('rx', 5)
        .attr('ry', 5);

    node.append('circle')
        .filter(d => d.type === 'literal_group')
        .attr('r', d => 15 + 10 * (d.properties ? d.properties.length : 0))
        .attr('fill', '#ff9e40')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);

    node.append('text')
        .text(d => d.type === 'literal_group' ? `${d.entity}` : d.id)
        .attr('text-anchor', 'middle')
        .attr('dy', d => d.type === 'literal_group' ? '-20' : '5')
        .attr('font-size', '12px')
        .attr('fill', '#333');

    if (mode === 'cartouches') {
        data.nodes.forEach(node => {
            if (node.type === 'literal_group' && node.properties) {
                node.properties.forEach((prop, i) => {
                    svg.append('text')
                        .text(`${prop.property}: ${prop.value}`)
                        .attr('x', node.x)
                        .attr('y', node.y + 20 + i * 15)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '10px')
                        .attr('fill', '#555');
                });
            }
        });
    }

    const linkLabels = svg.append('g')
        .selectAll('text')
        .data(data.links)
        .enter()
        .append('text')
        .text(d => d.label)
        .attr('font-size', '10px')
        .attr('fill', '#666');

    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('transform', d => `translate(${d.x},${d.y})`);

        linkLabels
            .attr('x', d => (d.source.x + d.target.x) / 2)
            .attr('y', d => (d.source.y + d.target.y) / 2);

        if (mode === 'cartouches') {
            svg.selectAll('text')
                .filter((d, i, nodes) => d.property) // Filtrer les textes des propriétés
                .attr('x', d => {
                    const nodeData = data.nodes.find(n => n.id === d.id + '_props');
                    return nodeData ? nodeData.x : d.x;
                })
                .attr('y', (d, i) => {
                    const nodeData = data.nodes.find(n => n.id === d.id + '_props');
                    return nodeData ? nodeData.y + 20 + i * 15 : d.y + 20 + i * 15;
                });
        }
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

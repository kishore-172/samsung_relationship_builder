# Full updated function to support any request IDs (e.g. BD250467, RQ123, etc.)
def save_graph_with_dcs_highlight(df: pd.DataFrame, output_file: str, request_tooltips: dict = None):
    from pyvis.network import Network
    from jinja2 import Environment, FileSystemLoader
    import pyvis.network as network

    # Fix pyvis template loading
    template_dir = os.path.join(os.path.dirname(network.__file__), 'templates')
    network.template = Environment(loader=FileSystemLoader(template_dir)).get_template('template.html')

    net = Network(height="800px", width="100%", directed=True, notebook=False)

    # Node classification
    node_types, node_shapes = {}, {}
    for h, r, t in df.values:
        if request_tooltips and h in request_tooltips:
            node_types[h] = "dcs"
            node_shapes[h] = "box"
        elif r == "uses_schema":
            node_types[t] = "schema"
            node_shapes[t] = "ellipse"
        elif r == "uses_table":
            node_types[t] = "table"
            node_shapes[t] = "circle"
        elif r == "uses_column":
            node_types[t] = "column"
            node_shapes[t] = "dot"
        elif r == "has_filter":
            node_types[t] = "filter"
            node_shapes[t] = "star"
        elif r == "has_join":
            node_types[t] = "join"
            node_shapes[t] = "triangle"
        elif r == "has_temp_table":
            node_types[t] = "temp_table"
            node_shapes[t] = "database"
        elif r == "derived_from":
            node_types[t] = "source_table"
            node_shapes[t] = "hexagon"

    # Add nodes/edges
    added_nodes = set()
    for h, r, t in df.values:
        for node in [h, t]:
            if node not in added_nodes:
                tooltip = request_tooltips.get(node) if request_tooltips and node in request_tooltips else f"{node} ({node_types.get(node, 'other')})"
                net.add_node(
                    node,
                    label=node,
                    title=tooltip,
                    group=node_types.get(node, "other"),
                    shape=node_shapes.get(node, "dot")
                )
                added_nodes.add(node)
        net.add_edge(h, t, title=r, label=r)

    net.show(output_file)

    # Patch HTML with dropdown + legend + JS
    with open(output_file, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")

    # Dynamically build request list from request_tooltips
    req_ids = sorted([req_id for req_id in df['head'].unique() if request_tooltips and req_id in request_tooltips])
    options_html = '\n'.join([f'<option value="{d}">{d}</option>' for d in req_ids])

    filter_controls = f'''
    <div style="margin: 10px; font-family: sans-serif;">
      <label for="dcsFilter"><b>Highlight Requests:</b> <small>(Hold Ctrl or Cmd to multi-select)</small></label><br>
      <select id="dcsFilter" multiple size="4" onchange="highlightDCS()" style="min-width: 200px; margin-top: 5px;" title="Hold Ctrl or Cmd to multi-select">
        {options_html}
      </select>
      <br><button onclick="resetHighlight()" style="margin-top: 10px;">Reset</button>
    </div>
    '''

    legend_html = '''
    <div style="
      position: absolute;
      top: 50%;
      left: 10px;
      transform: translateY(-50%);
      background: white;
      border: 1px solid #ccc;
      border-radius: 6px;
      padding: 10px;
      font-family: sans-serif;
      font-size: 13px;
      box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
      z-index: 1000;
      width: 170px;
    ">
      <b style="font-size: 14px;">Legend</b><br><br>
      <div><span style="display:inline-block;width:15px;height:15px;background:#97C2FC;border:1px solid #000;margin-right:6px;"></span>Request ID</div>
      <div><span style="display:inline-block;width:15px;height:15px;background:#FFFF00;border-radius:50%;border:1px solid #aaa;margin-right:6px;"></span>Schema</div>
      <div><span style="display:inline-block;width:15px;height:15px;background:#D2E5FF;border-radius:50%;border:1px solid #aaa;margin-right:6px;"></span>Table</div>
      <div><span style="display:inline-block;width:12px;height:12px;background:#7BE141;border-radius:50%;border:1px solid #aaa;margin-right:6px;"></span>Column</div>
      <div><span style="display:inline-block;width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;border-bottom:14px solid #FFA807;margin-right:6px;"></span>Join</div>
      <div><span style="font-size:18px;line-height:14px;color:#ff00ff;margin-right:8px;">★</span>Filter</div>
      <div><span style="display:inline-block;width:15px;height:15px;background:#FFA500;border-radius:2px;border:1px solid #aaa;margin-right:6px;"></span>Temp Table</div>
      <div><span style="display:inline-block;width:15px;height:15px;background:#00CCCC;clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);margin-right:6px;"></span>Derived From</div>
    </div>
    '''

    highlight_script = '''
    <script>
    function highlightDCS() {
        const select = document.getElementById("dcsFilter");
        const selected = Array.from(select.selectedOptions).map(o => o.value);
        const allNodes = nodes.get();
        const allEdges = edges.get();

        const highlightNodes = new Set();
        const highlightEdges = new Set();

        function traverse(nodeId) {
            const visited = new Set();
            const queue = [nodeId];
            while (queue.length > 0) {
                const current = queue.shift();
                if (visited.has(current)) continue;
                visited.add(current);
                highlightNodes.add(current);
                edges.get().forEach(e => {
                    if (e.from === current && !visited.has(e.to)) {
                        highlightEdges.add(e.id || `${e.from}->${e.to}`);
                        queue.push(e.to);
                    }
                });
            }
        }

        selected.forEach(dcs => traverse(dcs));

        nodes.update(allNodes.map(n => {
            return Object.assign({}, n, {
                color: highlightNodes.has(n.id) ? undefined : 'rgba(200,200,200,0.3)',
                font: { color: highlightNodes.has(n.id) ? '#000000' : '#aaaaaa' }
            });
        }));

        edges.update(allEdges.map(e => {
            return Object.assign({}, e, {
                color: highlightEdges.has(e.id || `${e.from}->${e.to}`) ? undefined : 'rgba(150,150,150,0.5)',
                arrows: { to: { enabled: true } }
            });
        }));
    }

    function resetHighlight() {
        document.getElementById("dcsFilter").selectedIndex = -1;
        nodes.update(nodes.get().map(n => Object.assign({}, n, {
            color: undefined,
            font: { color: '#000000' }
        })));
        edges.update(edges.get().map(e => Object.assign({}, e, {
            color: undefined,
            arrows: { to: { enabled: true } }
        })));
    }
    </script>
    '''

    body = soup.find("body")
    if body:
        body.insert(0, BeautifulSoup(filter_controls, "html.parser"))
        body.insert(1, BeautifulSoup(legend_html, "html.parser"))
        body.append(BeautifulSoup(highlight_script, "html.parser"))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return output_file

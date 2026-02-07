.. code-block:: python

    def nfa_diagram(nfa:NFA, title:str):
    
        dot = Dot(directed=True).use_theme(nfa_theme)
        dot.graph(label=Markup(f"<b>{title}<br/></b>"))
    
        dot.node("_init_", role="init")
        dot.edge("_init_", nfa.start)
    
        for state in nfa.final:
            dot.node(state, role="final")
    
        for state, transitions in nfa.delta.items():
            merged = defaultdict(list)
            for index, targets in enumerate(transitions):
                for target in targets:
                    merged[target].append(
                        nfa.alphabet[index-1] if index > 0 else '&epsilon;')
            for target, symbols in merged.items():
                dot.edge(state, target, label=", ".join(symbols))
    
        return dot

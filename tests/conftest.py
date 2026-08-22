import networkx as nx

# NetworkX 3.4+; ignore if an older config object has no warnings_to_ignore.
try:
    nx.config.warnings_to_ignore.add("cache")
except AttributeError:
    pass

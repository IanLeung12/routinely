"""Task-graph tracker (SPEC section 7).

A task is a graph of dependencies, not a fixed sequence: "teabag in cup" has to happen
before "pour", but "fill kettle" and "get cup" may happen in either order. Each step
lists the objects allowed for it and whether it is optional (milk and sugar are).

The tracker compares the recognised step events against that graph and hands the
mismatches to the error classifier.
"""

STAGE = "task_graph"

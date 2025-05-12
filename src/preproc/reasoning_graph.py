"""
Implement the reasoning graph in networkx
"""
from typing import Optional
from pyprojroot import here
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from src.preproc.reasoning_graph_utils import get_sub_operations
import copy


class GraphBuilder:
    """
    A class to build a networkx graph based on a participant's transcript

    Example usage:
    --------
    >>> curr_state = (3, 4, 9, 9)
    >>> graph = GraphBuilder(curr_state)
    """

    G: nx.DiGraph  # a networkx graph
    start_state: tuple[int]  # the start state of the task
    node_visitation_timestep: int  # keeps track of the timestep when visiting nodes
    op_timestep: int  # keeps track of the timestep when trying operations
    actions: list[
        dict
    ]  # a list of dictionaries indicating actions taken by the participant

    def __init__(self, start_state: tuple[int]) -> None:
        # initialize a graph
        self.G = nx.DiGraph()

        if isinstance(start_state, list):
            start_state = tuple(start_state)

        self.start_state = tuple(sorted(start_state))
        # add a node to the graph corresponding to the start state
        self.G.add_node(self.start_state)
        self.G.nodes[self.start_state]["state"] = self.start_state
        self.G.nodes[self.start_state]["visitation_timesteps"] = [0]
        self.G.add_node((24,))
        self.G.nodes[(24,)]["state"] = (24,)
        self.G.nodes[(24,)]["visitation_timesteps"] = []

        # initialize counters for the number of nodes visited and operations tried
        self.node_visitation_timestep = 1
        self.op_timestep = 1
        self.actions = [{"type": "start", "state": start_state}]

    def explore_operation(
        self,
        curr_state: tuple[int],
        operation: str,
        resulting_state: tuple[int],
        result_calc_error: bool = False,
        comment: Optional[str] = None,
    ) -> tuple[int]:
        """
        This method represents a participant trying out an operation in the task. It takes a current state,
        an operation, and the resulting state. The `comment` argument should contain any text explaining
        the operation, often quoting the transcript.

        The method adds a new node to the graph if the operation creates a new state,
        and an edge from the current state to the new state. It returns the resulting node from the operation.

        Example usage:
        --------
        >>> curr_state = (3, 4, 9, 9)
        >>> graph = GraphBuilder(curr_state)
        >>> # "nine minus nine, minus nine minus three is six" seems to be a transcription error. The participant likely meant 9-3=6
        >>> new_state = graph.explore_operation(
                curr_state,
                operation="9-3=6",
                resulting_state=(4, 6, 9),
                comment='"nine minus nine, minus nine minus three is six" seems to be a transcription error. The participant likely meant 9-3=6',
            )


        Guidelines for use:
        --------
        **Operation Rules**:
        Every operation replaces numbers in the current state with a new number. The numbers on the
        left side of the equation *MUST BE PRESENT* in the current state for an operation to be
        explored.

        **Inferred Steps**:
        If the participant doesn't state the operation explicitly, infer the steps from the numbers and result, and write them out.
        For example: If the current state is `(12, 2)` and the participant says "We have 24 now,"
        you might infer that the operation should be '12 * 2 = 24' and  resulting_state should be (24,).
        Thus, you should call the operation function as follows:
        >>> new_state = graph.explore_operation(
                curr_state,
                operation="12*2=24",
                resulting_state=(24,),
                comment='"we have 24 now" participant is implicitly multiplying 12 and 2 to get 24.',
            )

        **Incorrect Calculations**:
        If the participant makes an incorrect calculation, simply write the `operation` and the `resulting_state`
        arguments with the participant's error included, and set `result_calc_error` to True. Do not correct the error.
        For example:
        >>> curr_state = (3, 4, 9, 9)
        >>> graph = GraphBuilder(curr_state)
        >>> # "so 9 times 9 is 80" the participant made a calculation error.
        >>> new_state = graph.explore_operation(
                curr_state,
                operation="9*9=80",
                resulting_state=(3,4,80),
                comment='"so 9 times 9 is 80" the participant made a calculation error.',
                result_calc_error=True,
            )
        """
        curr_state = tuple(sorted(curr_state))
        resulting_state = tuple(sorted(resulting_state))
        sub_operations = get_sub_operations(operation[: operation.rfind("=")])
        final_result = operation[operation.rfind("=") + 1 :]

        # add an action
        action = {
            "type": "explore_operation",
            "curr_state": curr_state,
            "operation": operation,
            "resulting_state": resulting_state,
            "comment": comment,
            "result_calc_error": result_calc_error,
            "sub_operations": None,
        }
        if len(sub_operations) > 1:
            action["sub_operations"] = sub_operations

        sub_operations_dict = {"operation": [], "resulting_state": []}
        for sub_operation in sub_operations:
            # iterate to allow a multi-operation containing multiple sub operations
            # sub operation is defined as an operation between only two elements
            # find resulting state from sub operation
            if sub_operation != sub_operations[-1]:
                element1, element2, result = (
                    sub_operation[0],
                    sub_operation[2],
                    sub_operation[-1],
                )
                mid_result_state = list(curr_state) + [result]
                if element1 in mid_result_state:
                    mid_result_state.remove(element1)
                if element2 in mid_result_state:
                    mid_result_state.remove(element2)
                mid_result_state = tuple(sorted(mid_result_state))
                # add the connected node
                sub_operation_str = f"{element1}{sub_operation[1]}{element2}={result}"
                curr_state = self.add_connected_node(
                    curr_state, mid_result_state, sub_operation_str, comment
                )
                sub_operations_dict["operation"].append(sub_operation_str)
                sub_operations_dict["resulting_state"].append(mid_result_state)
            else:
                # connect node with the final state
                sub_operation_str = f"{sub_operation[0]}{sub_operation[1]}{sub_operation[2]}={final_result}"
                curr_state = self.add_connected_node(
                    curr_state,
                    resulting_state,
                    sub_operation_str,
                    comment,
                    result_calc_error
                )
                sub_operations_dict["operation"].append(sub_operation_str)
                sub_operations_dict["resulting_state"].append(resulting_state)

        if len(sub_operations) > 1:
            action["sub_operations_dict"] = sub_operations_dict
        else:
            action["sub_operations_dict"] = None
        self.actions.append(action)

        return resulting_state

    def add_connected_node(self, curr_state, resulting_state, operation, comment, result_calc_error=False):
        """Helper function for explore operation. Adds a connected node to the graph"""
        # add a node to the graph for the new state
        curr_state = tuple(sorted(curr_state))
        resulting_state = tuple(sorted(resulting_state))
        if resulting_state not in self.G.nodes:
            self.G.add_node(resulting_state)
            self.G.nodes[resulting_state]["state"] = resulting_state
            self.G.nodes[resulting_state]["visitation_timesteps"] = [
                self.node_visitation_timestep
            ]
        else:
            self.G.nodes[resulting_state]["visitation_timesteps"].append(
                self.node_visitation_timestep
            )

        if (curr_state, resulting_state) not in self.G.edges:
            # add an edge from the old state to the new state
            self.G.add_edge(
                curr_state,
                resulting_state,
                operation=operation,
                is_correct=eval(f"np.isclose({operation.replace('=', ',')},atol=0.01)") and not result_calc_error,
            )
            self.G.edges[(curr_state, resulting_state)]["op_timesteps"] = [
                self.op_timestep
            ]
        else:
            self.G.edges[(curr_state, resulting_state)]["op_timesteps"].append(
                self.op_timestep
            )

        if "comment" in self.G.edges[(curr_state, resulting_state)]:
            self.G.edges[(curr_state, resulting_state)]["comment"].append(comment)
        else:
            self.G.edges[(curr_state, resulting_state)]["comment"] = [comment]

        # increment the timesteps
        self.op_timestep += 1
        self.node_visitation_timestep += 1

        return resulting_state

    def move_to_node(self, new_state) -> tuple[int]:
        """
        This function represents a participant moving to a different state. It adds a new visitation time to
        the node corresponding to the new state.

        Example usage:
        --------
        >>> curr_state = graph.move_to_node(new_state)

        Guidelines for use:
        --------
        **General usage**:
        While the `explore_operation` method creates a new node, the `move_to_node` method
        is required for the participant to explore new operations from that node.
        For example:
        >>> new_state = graph.explore_operation(
                curr_state,
                operation="9-4=5",
                resulting_state=(3, 5, 9),
                comment='"nine minus four is five" seems to refer to the numbers in the start state',
            )
        >>> # "Five times three is", the participant seems to be computing 5*3 from the new state
        >>> curr_state = graph.move_to_node(new_state)
        >>> new_state = graph.explore_operation(
                curr_state,
                operation="5*3=15",
                resulting_state=(9, 15),
                comment='"Five times three is", the participant seems to be computing 5*3 from the previous state',
            )

        **Backtracking**:
        If the participant backtracks, you can call `move_to_node` to move back to a previous state.
        """
        # If we were not just in this state, add another visitation timestep to the list
        new_state = tuple(sorted(new_state))
        if (
            self.G.nodes[new_state]["visitation_timesteps"][-1] + 1
            != self.node_visitation_timestep
        ):
            self.G.nodes[new_state]["visitation_timesteps"].append(
                self.node_visitation_timestep
            )
            self.node_visitation_timestep += 1
        # add an action
        self.actions.append({"type": "move_to_node", "new_state": new_state})
        return new_state

    def set_subgoal(
        self,
        subgoal_state: tuple[int],
        state_after_subgoal: tuple[int] = (24,),
        comment: Optional[str] = None,
    ):
        """
        Create a new state for a subgoal that a participant set and add a backward edge from the
        state the participant is working backward from to the subgoal.

        This takes a subgoal state (the state the participant is trying to reach) and a state
        after the subgoal (the state the participant is working backward from).
        """
        subgoal_state = tuple(sorted(subgoal_state))
        state_after_subgoal = tuple(sorted(state_after_subgoal))

        # Add the subgoal state as a node to the graph if it's not there already
        if subgoal_state not in self.G.nodes:
            self.G.add_node(subgoal_state, initialized_as_subgoal=True)
            self.G.nodes[subgoal_state]["state"] = subgoal_state
            self.G.nodes[subgoal_state]["visitation_timesteps"] = []

        if state_after_subgoal not in self.G.nodes:
            self.G.add_node(state_after_subgoal, initialized_as_subgoal=False)
            self.G.nodes[state_after_subgoal]["state"] = state_after_subgoal
            self.G.nodes[state_after_subgoal]["visitation_timesteps"] = []

        # add a "backward" edge from the state after the subgoal
        self.G.add_edge(state_after_subgoal, subgoal_state)
        self.G.edges[(state_after_subgoal, subgoal_state)]["op_timesteps"] = [
            self.op_timestep
        ]
        self.G.edges[(state_after_subgoal, subgoal_state)]["operation"] = "subgoal"
        self.op_timestep += 1

        # attach any comment relevant to the subgoal
        if comment is not None:
            if "comment" in self.G.edges()[(state_after_subgoal, subgoal_state)]:
                self.G.edges()[(state_after_subgoal, subgoal_state)]["comment"].append(
                    comment
                )
            else:
                self.G.edges()[(state_after_subgoal, subgoal_state)]["comment"] = [
                    comment
                ]
        # add an action
        self.actions.append(
            {
                "type": "set_subgoal",
                "subgoal_state": subgoal_state,
                "state_after_subgoal": state_after_subgoal,
                "comment": comment,
            }
        )


    def draw_graph(self, prog="dot", mode="steps", target=(24,), node_size=7000, colors=None, figsize=(16, 12), fontsize_node_labels=14, fontsize_edge_labels=14, edge_vis_dict=None):
        """
        This function draws the graph.
        3 possible modes:
        - "steps": provide steps and operations for edge labels
        - "aggregate": increase edge width proportional to number of visits, don't show steps
        - "minimal": minimalistic style, no steps, no operations, no states except for target and start_state
        """
        G = self.G.copy()
        start_state = self.start_state

        # Position nodes using a hierarchical layout
        pos = nx.nx_agraph.graphviz_layout(G, prog=prog)

        fig, ax = plt.subplots(figsize=figsize)

        # Color schemes - Colorblind friendly palette
        if colors is None:
            colors = {
            'edge': '#2F4858',       # Dark blue/grey for forward transitions
            'incorrect': '#E69F00',   # Orange for incorrect transitions 
            'node_fill': '#F5F5F5',   # Very light grey for node fill
            'subgoal_border': '#a6bddb',     # Sky blue for subgoal border 
            'subgoal_fill': '#a6bddb', # subgoal color for minimalistic style
            'start_state_border': '#d0d1e6', # start state color for minimalistic style
            'start_state_fill': '#d0d1e6', # start state color for minimalistic style
            'target_border': '#67a9cf', # target color for minimalistic style
            'target_fill': '#67a9cf',      # Medium purple for target border
        }

        # Draw edges with arrows
        for u, v, attrs in G.edges(data=True):
            
            edge_color = colors['incorrect'] if not attrs.get('is_correct', True) else colors['edge']
            edge_style = 'solid'
            
            # In operations mode, make edge width proportional to number of visits
            if mode == "aggregate":
                visits = len(attrs.get('op_timesteps', []))
                edge_width = 3 + visits * 2
                arrow_style = '-'
            else:
                edge_width = 3.0
                arrow_style = '-|>'

            if edge_vis_dict is None:
                arrowsize = 35
                connection_style = f'arc3,rad={0.1}'
                if mode == "steps":
                    min_source_margin = 40
                    min_target_margin = 40
                elif mode == "minimal":
                    min_source_margin = 4
                    min_target_margin = 4
                else:
                    min_source_margin = 0
                    min_target_margin = 0
            else:
                min_source_margin = edge_vis_dict.get('min_source_margin', 0)
                min_target_margin = edge_vis_dict.get('min_target_margin', 0)
                arrowsize = edge_vis_dict.get('arrowsize', 35)
                connection_style = edge_vis_dict.get('connectionstyle', 'arc3,rad=0.1')
                arrow_style = edge_vis_dict.get('arrowstyle', '-|>')

            nx.draw_networkx_edges(
                G, pos,
                edgelist=[(u, v)],
                edge_color=edge_color,
                width=edge_width,
                style=edge_style,
                arrows=True,
                arrowsize=arrowsize,
                arrowstyle=arrow_style,
                connectionstyle=connection_style,
                ax=ax,
                min_source_margin=min_source_margin,
                min_target_margin=min_target_margin,
            )

        # Draw nodes
        node_size = node_size 
   
        # Draw regular nodes (not subgoal or target)
        regular_nodes = [node for node, attrs in G.nodes(data=True) 
                        if not attrs.get('initialized_as_subgoal') and node != target and node != start_state]
    
        if regular_nodes:
            nx.draw_networkx_nodes(
                G, pos,
                nodelist=regular_nodes,
                node_color=colors['node_fill'],
                node_size=node_size,
                linewidths=3,
                edgecolors=colors['edge'],
                ax=ax,
            )

        # Draw subgoal nodes
        subgoal_nodes = [node for node, attrs in G.nodes(data=True) 
                        if attrs.get('initialized_as_subgoal') and node != target and node != start_state]
        if subgoal_nodes:
            nx.draw_networkx_nodes(
                G, pos,
                nodelist=subgoal_nodes,
                node_color=colors['subgoal_fill'],
                node_size=node_size,
                linewidths=3,
                edgecolors=colors['subgoal_border'],
                ax=ax,
            )

        # find whether target node was visited
        target_visited = any(attrs.get('visitation_timesteps', []) for node, attrs in G.nodes(data=True) if node == target)
        plot_target = target_visited or (subgoal_nodes != [] and G.out_degree(target) > 0)
        # plot the target only if it was visited or if there are subgoals
        if plot_target:
            nx.draw_networkx_nodes(
            G, pos,
            nodelist=[target],
            node_color=colors['target_fill'],
            node_size=node_size,
            linewidths=6,  # Thicker border for target nodes
            edgecolors=colors['target_border'],
            ax=ax,
            )   

        nx.draw_networkx_nodes(
            G, pos,
            nodelist=[start_state],
            node_color=colors['start_state_fill'],
            node_size=node_size,
            linewidths=3,
            edgecolors=colors['start_state_border'],
            ax=ax,
        )
        
        if mode == "steps":
            edge_labels = {}
            for u, v, d in G.edges(data=True):
                if "=" in d.get('operation', ''):
                    operation = d.get('operation', '')[:d.get('operation', '').rfind("=")]
                else:
                    operation = d.get('operation', '')
                steps = d.get('op_timesteps', [''])
                if steps:
                    steps = ", ".join([str(s) for s in steps])
                steps = f"Step {steps}\n"
                edge_labels[(u, v)] = f"{steps}{operation}"

            # Draw all non-subgoal edge labels
            regular_edges = {(u,v): label for (u,v), label in edge_labels.items() 
                            if not d.get('operation', '') == 'subgoal'}
            if regular_edges:
                nx.draw_networkx_edge_labels(
                    G, pos,
                    edge_labels=regular_edges,
                    font_size=fontsize_edge_labels,
                    font_color=colors['edge'],
                    ax=ax,
                    label_pos=0.65,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7),
                    rotate=False
                )

        # Draw node labels
        node_labels = {}            
        for node, attrs in G.nodes(data=True):
            if mode != "steps" or node == target:
                continue
            state = attrs.get('state', 'N/A')
            if isinstance(state, tuple):
                # Convert tuple (1, 2, 3) to "1, 2, 3"
                node_labels[node] = ", ".join(str(x) for x in state)
            else:
                node_labels[node] = str(state)

        nx.draw_networkx_labels(
            G, pos,
            labels=node_labels,
            font_size=fontsize_node_labels,
            font_color='black',
            font_weight='bold',
            ax=ax,
            horizontalalignment="center",
            verticalalignment="center"
        )

        # use bigger font for target node
        if plot_target and mode == "steps":
            nx.draw_networkx_labels(
                G, pos,
                labels={target: "24"},
                font_size=fontsize_node_labels + 2,
                font_color='black',
                font_weight='bold',
                ax=ax,
                horizontalalignment="center",
                verticalalignment="center"
            )


        ax.axis('off')
        plt.tight_layout()
        return fig, ax

    def unite_graphs(self, other_graph: 'GraphBuilder') -> None:
        """
        Unites this graph with another GraphBuilder object by merging their nodes and edges.
        For overlapping nodes/edges, combines visitation timesteps and operation timesteps.
        Both graphs must have the same start state.
        
        Args:
            other_graph: Another GraphBuilder object to merge with this one
            
        Raises:
            ValueError: If the start states of the two graphs don't match
        
        Example usage:
        --------
        >>> graph1 = GraphBuilder((3, 4, 9))
        >>> graph2 = GraphBuilder((3, 4, 9))
        >>> # Create some paths in both graphs...
        >>> graph1.unite_graphs(graph2)
        """
        # Check if start states match
        if self.start_state != other_graph.start_state:
            raise ValueError(f"Cannot unite graphs with different start states: {self.start_state} vs {other_graph.start_state}")

        # Merge nodes
        for node, attrs in other_graph.G.nodes(data=True):
            # check if node is already in self.G
            if not self.G.has_node(node):
                # Add new node with all its attributes
                new_node = copy.deepcopy(node)
                new_attrs = copy.deepcopy(attrs)
                self.G.add_node(new_node, **new_attrs)
            else:
                # Combine visitation timesteps for existing nodes
                self.G.nodes[node]['visitation_timesteps'].extend(
                    attrs.get('visitation_timesteps', [])
                )

        # Merge edges
        for u, v, attrs in other_graph.G.edges(data=True):
            if not self.G.has_edge(u, v):
                # Add new edge with all its attributes
                self.G.add_edge(u, v, **attrs)
            else:
                # Combine op_timesteps
                if 'op_timesteps' in attrs:
                    self.G.edges[(u, v)]['op_timesteps'].extend(attrs['op_timesteps'])
                
                # Combine comments if they exist
                if 'comment' in attrs:
                    if 'comment' not in self.G.edges[(u, v)]:
                        self.G.edges[(u, v)]['comment'] = []
                    self.G.edges[(u, v)]['comment'].extend(attrs['comment'])

        # Update the timestep counters to be the max of both graphs
        self.node_visitation_timestep = max(self.node_visitation_timestep, other_graph.node_visitation_timestep)
        self.op_timestep = max(self.op_timestep, other_graph.op_timestep)

        # Combine actions lists
        self.actions.extend(other_graph.actions)


    def copy(self):
        """
        Returns a deep copy of the graph builder.
        """
        return copy.deepcopy(self)

if __name__ == "__main__":

    start_state = (3, 4, 8, 10)
    curr_state = start_state
    graph = GraphBuilder(curr_state)

    # ""10 plus 8 plus 4 plus 3 is 25""
    new_state = graph.explore_operation(
        curr_state,
        operation="10+8+4+3=25",
        resulting_state=(25,),
        comment="10 plus 8 plus 4 plus 3 is 25",
    )

    new_state = graph.explore_operation(
        curr_state,
        operation="4*3=12",
        resulting_state=(8, 10, 12),
        comment="4 times 3",
    )

    # Then the participant uses the 12 from the previous computation so we need to move to new_state

    curr_state = graph.move_to_node(new_state)
    # ""12 plus 8 plus 10 is 30""
    new_state = graph.explore_operation(
        curr_state,
        operation="12+8+10=30",
        resulting_state=(30,),
        comment="12 plus 8 plus 10 is 30",
    )

    # Then the participant tries ""10 times 8"", which doesn't use the 12 from the last state
    curr_state = graph.move_to_node(start_state)
    new_state = graph.explore_operation(
        curr_state,
        operation="10*8=80",
        resulting_state=(3, 4, 80),
        comment="10 times 8",
    )

    # ""10 times 4 is 40 minus 8 is 32 minus 3 is 29"" participant tries a different path
    new_state = graph.explore_operation(
        curr_state,
        operation="(10*4)-8-3=29",
        resulting_state=(29,),
        comment="10 times 4 is 40 minus 8 is 32 minus 3 is 29",
    )

    # ""divided by 3 no, divided by 8 is 5"" possibly dividing 40 by 8 and making 40 from 4*10
    new_state = graph.explore_operation(
        curr_state,
        operation="4*10/8=5",
        resulting_state=(5, 3),
        comment="divided by 3 no, divided by 8 is 5",
    )

    # ""10 times 8""
    new_state = graph.explore_operation(
        curr_state,
        operation="10*8=80",
        resulting_state=(3, 4, 80),
        comment="10 times 8",
    )

    # Then the participant seems to be responding to a reminder notification to speak out loud, which isn't part of their search

    # Then the participant lists the operations that they've already tried -- saying ""already done"" -- which doesn't count as exploring an operation

    # ""8 plus 10 is 18""
    new_state = graph.explore_operation(
        curr_state,
        operation="8+10=18",
        resulting_state=(3, 4, 18),
        comment="8 plus 10 is 18",
    )

    # ""3 times 4""
    new_state = graph.explore_operation(
        curr_state,
        operation="3*4=12",
        resulting_state=(8, 10, 12),
        comment="3 times 4",
    )

    # It's not clear what the ""4 36 9 so it was 15 times"" means

    # The participant submitted (3x4)x(10-8), so they must have multiplied the 12 they just computed by (10-8)

    curr_state = graph.move_to_node(new_state)
    new_state = graph.explore_operation(
        curr_state,
        operation="12*(10-8)=24",
        resulting_state=(24,),
        comment="Based on the response",
    )

    fig, ax = graph.draw_graph(mode="steps", node_size=25_000, figsize=(22, 20), fontsize_node_labels=30, fontsize_edge_labels=35)
    # save the figure
    fig.savefig("example_graph.png")
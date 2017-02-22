import logging
import math
import re
import sys
import os
import errno
from collections import defaultdict
import glob

logger = logging.getLogger(__name__)


def terminate_with_error(msg):
    logger.error(msg)
    logger.error("Scorer terminate with error.")
    sys.exit(1)


def natural_order(key):
    """
    Compare order based on the numeric values in key, for example, 't1 < t2'
    :param key:
    :return:
    """
    if type(key) is int:
        return key
    convert = lambda text: int(text) if text.isdigit() else text
    return [convert(c) for c in re.split('([0-9]+)', key)]


def nan_as_zero(v):
    """
    Treat NaN as zero, should only be used for printing.
    :param v:
    :return:
    """
    return 0 if math.isnan(v) else v


def get_or_else(dictionary, key, value):
    if key in dictionary:
        return dictionary[key]
    else:
        return value


def get_or_terminate(dictionary, key, error_msg):
    if key in dictionary:
        return dictionary[key]
    else:
        terminate_with_error(error_msg)


def check_unique(keys):
    return len(keys) == len(set(keys))


def put_or_increment(table, key, value):
    try:
        table[key] += value
    except KeyError:
        table[key] = value


def transitive_not_resolved(clusters):
    """
    Check whether transitive closure is resolved between clusters.
    :param clusters:
    :return: False if not resolved
    """
    ids = clusters.keys()
    for i in range(0, len(ids) - 1):
        for j in range(i + 1, len(ids)):
            if len(clusters[i].intersection(clusters[j])) != 0:
                logger.error(
                    "Non empty intersection between clusters found. Please resolve transitive closure before submit.")
                logger.error(clusters[i])
                logger.error(clusters[j])
                return True
    return False


def add_to_multi_map(multi_map, key, val):
    """
    Utility class to make the map behave like a multi-map, a key is mapped to multiple values
    :param multi_map: A map to insert to
    :param key:
    :param val:
    :return:
    """
    if key not in multi_map:
        multi_map[key] = []
    multi_map[key].append(val)


def within_cluster_span_duplicate(cluster, event_mention_id_2_sorted_tokens):
    """
    Check whether there is within cluster span duplication, i.e., two mentions in the same cluster have the same span,
    this is not allowed.
    :param cluster: The cluster
    :param event_mention_id_2_sorted_tokens: A map from mention id to span (in terms of tokens)
    :return:
    """
    span_map = {}
    for eid in cluster:
        span = tuple(get_or_terminate(event_mention_id_2_sorted_tokens, eid,
                                      "Cluster contains event that is not in mention list : [%s]" % eid))
        if span in span_map:
            if span is not ():
                logger.error("Span within the same cluster cannot be the same.")
                logger.error("%s->[%s]" % (eid, ",".join(str(x) for x in span)))
                logger.error("%s->[%s]" % (span_map[span], ",".join(str(x) for x in span)))
            return True
        else:
            span_map[span] = eid


def supermakedirs(path, mode=0775):
    """
    A custom makedirs method that get around the umask exception.
    :param path: The path to make directories
    :param mode: The mode of the directory
    :return:
    """
    if not path or os.path.exists(path):
        return []
    (head, tail) = os.path.split(path)
    res = supermakedirs(head, mode)
    os.mkdir(path)
    os.chmod(path, mode)
    res += [path]
    return res


def remove_file_by_extension(folder, ext):
    for path in glob.glob(os.path.join(folder, "*" + ext)):
        os.remove(path)


def create_parent_dir(p):
    """
    Create parent directory if not exists.
    :param p: path to file
    :raise:
    """
    try:
        head, tail = os.path.split(p)
        if head != "":
            supermakedirs(head)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


class DisjointSet(object):
    def __init__(self):
        self.leader = {}  # maps a member to the group's leader
        self.group = {}  # maps a group leader to the group (which is a set)

    def add(self, a, b):
        leader_a = self.leader.get(a)
        leader_b = self.leader.get(b)
        if leader_a is not None:
            if leader_b is not None:
                if leader_a == leader_b:
                    return  # nothing to do
                group_a = self.group[leader_a]
                group_b = self.group[leader_b]
                if len(group_a) < len(group_b):
                    a, leader_a, group_a, b, leader_b, group_b = b, leader_b, group_b, a, leader_a, group_a
                group_a |= group_b
                del self.group[leader_b]
                for k in group_b:
                    self.leader[k] = leader_a
            else:
                self.group[leader_a].add(b)
                self.leader[b] = leader_a
        else:
            if leader_b is not None:
                self.group[leader_b].add(a)
                self.leader[a] = leader_b
            else:
                self.leader[a] = self.leader[b] = a
                self.group[a] = {a, b}


def get_nodes(relations):
    nodes = set()
    node_index = {}

    for arg1, arg2, relation in relations:
        nodes.add(arg1)
        nodes.add(arg2)

    for index, n in enumerate(list(nodes)):
        node_index[n] = index

    return node_index


class TransitiveGraph:
    def __init__(self, vertices):
        # No. of vertices
        self.V = vertices

        # default dictionary to store graph
        self.graph = defaultdict(list)

        # To store transitive closure
        self.tc = [[0 for j in range(self.V)] for i in range(self.V)]

    # function to add an edge to graph
    def add_edge(self, u, v):
        self.graph[u].append(v)

    # A recursive DFS traversal function that finds
    # all reachable vertices for s
    def dfs_until(self, s, v):

        # Mark reachability from s to v as true.
        self.tc[s][v] = 1

        # Find all the vertices reachable through v
        for i in self.graph[v]:
            if self.tc[s][i] == 0:
                self.dfs_until(s, i)

    # The function to find transitive closure. It uses
    # recursive DFSUtil()
    def transitive_closure(self):
        # Call the recursive helper function to print DFS
        # traversal starting from all vertices one by one
        for i in range(self.V):
            self.dfs_until(i, i)
        return self.tc

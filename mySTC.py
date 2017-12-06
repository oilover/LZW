import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import copy
import time
import os.path
import pickle
import sys

''' 
    Use Mininum Spanning Tree..
'''   
def CN(G,u,v):
    return len(list(nx.common_neighbors(G, u, v)))  
def AA(G,u,v):
    return sum(1 / log(G.degree(w)+0.1) for w in nx.common_neighbors(G, u, v))
def RA(G,u,v):
    return sum(1 / G.degree(w) for w in nx.common_neighbors(G, u, v))
def JA(G,u,v):
    union_size = len(set(G[u]) | set(G[v]))
    if union_size == 0: return 0
    return len(list(nx.common_neighbors(G, u, v))) / union_size 
def AllToSet(teams):
    for K in teams: teams[K] = set(teams[K])
def _info(teams):
    v = teams.values()
    v = [len(x) for x in v]
    print max(v),min(v),sum(v)*1.0/len(v)
def get_open_set(G,v,w):
    open_set = set()
    s1, s2 = set(G[v]), set(G[w])
    open_set |= set([(i,v) if i < v else (v,i) for i in (s1 - s2 - set([w]))])
    open_set |= set([(i,w) if i < w else (w,i) for i in (s2 - s1 - set([v]))])
    return open_set

def contribution(G,u,v):
    return CN(G,u,v) - len(get_open_set(G,u,v))

def MergeTeams(teams):
    AllToSet(teams)
    teams = sorted(teams.items(), key=lambda x:len(x[-1]), reverse=True)
    N = len(teams)
    i = 0
    merged = {}
    for i in range(N): merged[i] = False
    for i in range(N):
        if merged[i]: continue
        t1 = teams[i][-1]
        for j in range(i+1,N):
            if merged[j]: continue 
            t2 = teams[j][-1]
            tt = t1&t2
            if len(tt)>0:
                merged[j] = True
                t1 |= t2
            # if t2.issubset(t1): 
            #     merged[j] = True
            #     t1 |= t2
    new_teams = {}
    for i in range(N):
        if merged[i]: continue
        ID, team = teams[i]
        new_teams[ID] = team
    return new_teams

def getDataGraph(sets, G):
    AllToSet(sets)
    
    new_ID = max(sets.keys())
    Gteams = {}
    for k in sets.keys():
        g = G.subgraph(sets[k])
        if g.number_of_nodes() >= 2:
            if nx.is_connected(g):
                 Gteams[k] = copy.deepcopy(g)
                 sets[k] = copy.deepcopy(g.nodes())
            else:
                flag = False
                del sets[k]
                for Gc in nx.connected_component_subgraphs(g):
                    if Gc.number_of_nodes() >= 2:
                        flag = True
                        new_ID += 1
                        Gteams[new_ID] = copy.deepcopy(Gc)
                        sets[new_ID] = copy.deepcopy(Gc.nodes())
                # if not flag:
                #     del sets[k]
        else:
            del sets[k]    
    return sets, Gteams


def getAllOpen(G):
    opens = {}
    for e in G.edges():
        v,w = e[:2]
        pair = (v,w) if v < w else (w,v)
        
        opens[pair] = get_open_set(G,v,w)
                  
    return opens

def hasCycles(Gteams, index, e):
    out = True
    
    if e in index:
        for k in index[e]:
            g = Gteams[k]
            if g.has_edge(*e): g.remove_edge(*e)
            out =  nx.has_path(g, e[0], e[1])
            g.add_edge(*e)            
            if out == False:
                return out               
    return out

def updateOpens(opens, e):
    for k in opens[e]:
        opens[k].remove(e)
    del opens[e]
    return opens

 
def find_root(u, disjoint_set):
    if disjoint_set[u]==u: return u
    disjoint_set[u] = find_root(disjoint_set[u], disjoint_set)
    return disjoint_set[u]

def compute(G):
    # global disjoint_set
    disjoint_set = {}
    for u in G: disjoint_set[u] = u
    edges = [(i,j,CN(G,i,j)) if i < j else (j,i) for (i,j) in G.edges()]
    edges.sort(key=lambda x:x[-1], reverse=True)
    
    for e in edges:
        u,v = e[:2]
        ru,rv = find_root(u,disjoint_set),find_root(v,disjoint_set)
        if ru!=rv:
            disjoint_set[ru] = rv
            new_G.add_edge(u,v)
        else:
            if contribution(new_G,u,v)>0:
                new_G.add_edge(u,v)

if __name__ == '__main__':
    global new_G
    new_G = nx.Graph()
    #
    name = 'BM_tags' #'youtube_10000' #'BM_tags' #'lastFM_tags'                
    name = sys.argv[1]
    G, init_sets = pickle.load(open(os.path.join('UnderlyingNetwork', name +'.pkl'),'rb'))
    print 'Data: ', name
    print 'number of nodes and edges in the graph:'
    print G.number_of_nodes(), G.number_of_edges()
    AllToSet(init_sets)

    sets = init_sets
    sets, Gteams = getDataGraph(sets, G)
    sets = MergeTeams(sets)
    sets, Gteams = getDataGraph(sets, G)
    print 'number of sets:', len(sets)
    
    all_opens = getAllOpen(G)
    all_open_sum = sum([len(i) for i in all_opens.values()])/2
    print 'initial number of open (violated) triangles:', all_open_sum
        
    
    tic = time.time()
    print 'Begin Greedy...'
    new_G = nx.Graph()
    for g in Gteams.values():
        compute(g)
    print 'running time:', time.time() - tic

    opens = getAllOpen(new_G)
    res = sum([len(i) for i in opens.values()])/2
    print 'resulting number of violations: ', res
    print 'violation rate: (b in paper):', 1.0*res / all_open_sum

    Strong = set(new_G.edges())
    Weak = set([(i,j) if i < j else (j,i) for (i,j) in G.edges()])-Strong
    
    print 'number of strong and weak edges:'
    print len(Strong), len(Weak)
    print 'Strong edge ratio (s in paper): ', 1.0*len(Strong) / (len(Strong) + len(Weak))
    pickle.dump((Gteams, sets, Strong, Weak), open('out/' + name + ' ' + \
        time.ctime(time.time()).replace(':','_') + '.p2', "wb"))

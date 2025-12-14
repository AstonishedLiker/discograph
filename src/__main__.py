import argparse
import asyncio
import aiohttp
from pyvis.network import Network
from tqdm import tqdm
import time
import networkx as nx
import community as community_louvain

URL_TEMPLATE = 'https://manti.vendicated.dev/api/reviewdb/users/{id}/reviews'
USERID_BLACKLIST = ["1134864775000629298"]
MAX_RETRIES = 10
SIMULTANEOUS_REQUESTS = 40

async def fetch_connections(session, semaphore, targetUserId: int):
    url = URL_TEMPLATE.format(id=targetUserId)
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(1)
                        continue

                    data = await resp.json()
                    connections = []

                    for review in data.get("reviews", []):
                        sender = review["sender"]
                        if sender["discordID"] in USERID_BLACKLIST:
                            continue
                        connections.append((
                            sender["discordID"],
                            sender["username"],
                            sender["profilePhoto"],
                        ))

                    return connections

            except Exception:
                await asyncio.sleep(4)

    print(f"[!] Failed permanently for {targetUserId}")
    return []

async def crawl_graph(rootUserId, maxDepth):
    G = nx.Graph()
    nodeData = {rootUserId: ("Root User", "https://cdn.discordapp.com/embed/avatars/0.png")}

    visited = set([str(rootUserId)])
    toVisit = [(rootUserId, "Root User")]
    usernameToUserId = {}

    async with aiohttp.ClientSession() as session:
        for depth in range(maxDepth):
            nextToVisit = []
            start = time.time()

            semaphore = asyncio.Semaphore(SIMULTANEOUS_REQUESTS)
            tasks = [fetch_connections(session, semaphore, uid) for (uid, _) in toVisit]

            results = []
            for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f"Depth {depth+1}/{maxDepth}"):
                results.append(await coro)

            idx = 0
            for (currentUserId, _) in toVisit:
                connections = results[idx]
                idx += 1

                for (uid, username, pfp) in connections:
                    if uid == str(rootUserId):
                        continue

                    if uid not in visited:
                        visited.add(uid)
                        nodeData[uid] = (username, pfp)

                    G.add_edge(currentUserId, uid)
                    usernameToUserId[username] = uid
                    nextToVisit.append((uid, username))

            print(f"[+] Depth {depth+1}: found {len(nextToVisit)} new nodes in {time.time() - start:.2f}s")
            toVisit = nextToVisit

    return G, nodeData, usernameToUserId

def generate_palette(n):
    colors = []
    for i in range(n):
        hue = i / n
        colors.append(f"hsl({int(hue*360)}, 70%, 55%)")
    return colors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-id", "--userid", required=True)
    parser.add_argument("-d", "--depth", required=True)
    parser.add_argument("-cross", "--show-cross-communities", action='store_true', default=False)
    args = parser.parse_args()

    root = int(args.userid)
    depth = int(args.depth)

    G, nodeData, usernameToUserId = asyncio.run(crawl_graph(root, depth))

    print("[*] Detecting communities using Louvain…")
    partition = community_louvain.best_partition(G)

    communities = {}
    for node, comm in partition.items():
        communities.setdefault(comm, []).append(node)

    numCommunities = len(communities)
    print(f"[+] Found {numCommunities} communities")
    print(f"[+] Louvain modularity score: {community_louvain.modularity(partition, G):.4f}")

    communityColors = generate_palette(numCommunities)

    bfsTree = nx.bfs_tree(G, root)
    bfsLevels = nx.single_source_shortest_path_length(bfsTree, root)
    communityHubs = {
        comm: f"community_{comm}"
        for comm in communities.keys()
    }

    net = Network()
    rootLabel, rootImg = nodeData.get(root, (str(root), None))
    net.add_node(
        root,
        label=f"{rootLabel} ({root})",
        image=rootImg,
        shape="image",
        level=0,
        group=str(partition.get(root, -1)),
        color=communityColors[partition[root]] if root in partition else "#444444",
        size=32
    )

    for commId, hubId in communityHubs.items():
        net.add_node(
            hubId,
            label=f"Community {commId + 1} ({len(communities[commId])} users)",
            shape="box",
            level=1,
            group=str(commId),
            color=communityColors[commId],
            font={"color": "#111", "size": 18},
            size=28
        )
        net.add_edge(root, hubId, color=communityColors[commId], width=3)

    for node in G.nodes:
        if node == root:
            continue

        label, img = nodeData.get(node, (str(node), None))
        comm = partition[node]
        level = bfsLevels.get(node, 1) + 2

        net.add_node(
            node,
            label=f"{label} ({node})",
            image=img,
            shape="image",
            level=level,
            group=str(comm),
            color=communityColors[comm]
        )

    for node in bfsTree.nodes:
        if node == root:
            continue
        parent = next(bfsTree.predecessors(node))
        nodeComm = partition[node]
        parentComm = partition[parent]

        if nodeComm == parentComm:
            net.add_edge(parent, node, color=communityColors[nodeComm], width=2)
        else:
            hub = communityHubs[nodeComm]
            net.add_edge(hub, node, color=communityColors[nodeComm], width=2)

    if args.show_cross_communities:
        for u, v in G.edges:
            if bfsTree.has_edge(u, v) or bfsTree.has_edge(v, u):
                continue
            if partition[u] != partition[v]:
                net.add_edge(u, v, color="#C0C0C0", dashes=True, width=1, physics=False, smooth=True)

    net.show("discograph.html", notebook=False)

if __name__ == "__main__":
    main()
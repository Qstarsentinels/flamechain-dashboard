
import socket

import threading

import json

import os



PORT = 9000

PEERS = []  # List of public peer IPs (e.g., ["192.168.1.50:9000"])



def listen_for_peers():

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind(("0.0.0.0", PORT))

    server.listen(5)

    print(f"[*] FlameChain Mainnet Peer Node Listening on Port {PORT}...")

    while True:

        conn, addr = server.accept()

        threading.Thread(target=handle_peer, args=(conn, addr)).start()



def handle_peer(conn, addr):

    print(f"[+] Connected to Peer Node: {addr[0]}")

    data = conn.recv(4096)

    if data:

        print(f"[*] Received Mesh Propagation Data: {data.decode()[:50]}...")

    conn.close()



if __name__ == "__main__":

    listen_for_peers()


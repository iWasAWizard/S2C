import socket
import threading
import argparse
import struct
import sys

# Server Configuration Defaults
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000       # Default port number
PACKET_SIZE = 1024

def handle_client(conn, addr, packet_size):
    """
    Handles incoming client connections.

    Args:
        conn (socket.socket): The client socket.
        addr (tuple): The client's address.
        packet_size (int): The size of each packet to receive.
    """
    try:
        while True:
            # Receive packet header (sequence number and checksum)
            header = conn.recv(8)
            if not header:
                break
            seq_num, checksum = struct.unpack('!II', header)

            # Receive the rest of the packet based on packet size
            data = conn.recv(packet_size)
            if not data:
                break

            # Echo back the data
            conn.sendall(header + data)
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        conn.close()

def print_help():
    """
    Prints detailed help information for the server script.
    """
    help_text = """
    Network Measurement Tool Server

    Usage:
        python3 server.py [options]

    Options:
        --port PORT          Port to listen on (default: 5000)
        --packet_size SIZE   Packet size in bytes (default: 1024)
        -h, --help           Show this help message and exit

    Examples:
        python3 server.py
        python3 server.py --port 8000 --packet_size 2048
    """
    print(help_text)

if __name__ == '__main__':
    # Check for help flag or no arguments
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Network Measurement Tool Server', add_help=False)
    parser.add_argument('--port', type=int, default=PORT, help='Port to listen on (default: 5000)')
    parser.add_argument('--packet_size', type=int, default=PACKET_SIZE, help='Packet size in bytes (default: 1024)')
    args, unknown = parser.parse_known_args()

    # Check for unrecognized arguments
    if unknown:
        print(f"Unrecognized arguments: {' '.join(unknown)}\n")
        print_help()
        sys.exit(1)

    PORT = args.port
    packet_size = args.packet_size

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"Server listening on port {PORT}...")

    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, packet_size))
            client_thread.start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server_socket.close()
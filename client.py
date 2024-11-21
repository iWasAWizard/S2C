import socket
import threading
import time
import argparse
import struct
import csv
import hashlib
import os
import sys

# Client Configuration Defaults
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000
PACKET_SIZE = 1024
DURATION = 60  # in seconds
MEASUREMENT_INTERVAL = 1  # in seconds
OUTPUT_FILE = 'metrics.csv'

class NetworkTester:
    """
    NetworkTester handles sending packets to the server and measuring network metrics.

    Attributes:
        server_ip (str): The server's IP address.
        server_port (int): The server's port number.
        packet_size (int): The size of each packet in bytes.
        duration (int): The duration of the test in seconds.
        measurement_interval (int): The interval at which metrics are recorded.
        output_file (str): The CSV file to store metrics.
    """
    def __init__(self, server_ip, server_port, packet_size, duration, measurement_interval, output_file):
        self.server_ip = server_ip
        self.server_port = server_port
        self.packet_size = packet_size
        self.duration = duration
        self.measurement_interval = measurement_interval
        self.output_file = output_file
        self.metrics = []
        self.start_time = time.time()
        self.sequence_number = 0
        self.lock = threading.Lock()
        self.received_packets = {}
        self.sent_packets = {}
        self.stop_event = threading.Event()

    def send_packets(self):
        """
        Sends packets to the server and records the send time.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.server_port))

            while not self.stop_event.is_set():
                current_time = time.time()
                if current_time - self.start_time >= self.duration:
                    break

                # Prepare packet data
                data = os.urandom(self.packet_size)
                checksum = struct.unpack('!I', hashlib.md5(data).digest()[:4])[0]
                header = struct.pack('!II', self.sequence_number, checksum)
                packet = header + data

                # Record send time
                with self.lock:
                    self.sent_packets[self.sequence_number] = current_time

                try:
                    sock.sendall(packet)
                except Exception as e:
                    print(f"Send error: {e}")
                    break

                self.sequence_number += 1
                time.sleep(0)  # Yield control

            sock.close()
        except Exception as e:
            print(f"Connection error: {e}")
            self.stop_event.set()

    def receive_packets(self):
        """
        Receives packets from the server and records the receive time.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))  # Bind to an available port
            sock.listen()
            conn, addr = sock.accept()
            with conn:
                while not self.stop_event.is_set():
                    # Receive packet header
                    header = conn.recv(8)
                    if not header:
                        break
                    seq_num, checksum = struct.unpack('!II', header)

                    # Receive packet data
                    data = conn.recv(self.packet_size)
                    if not data:
                        break

                    recv_time = time.time()

                    # Record receive time and verify checksum
                    with self.lock:
                        self.received_packets[seq_num] = {
                            'recv_time': recv_time,
                            'checksum': checksum,
                            'data': data
                        }
            conn.close()
            sock.close()
        except Exception as e:
            print(f"Receive error: {e}")

    def measure_metrics(self):
        """
        Calculates and records network metrics at specified intervals.
        """
        while not self.stop_event.is_set():
            time.sleep(self.measurement_interval)
            current_time = time.time()
            elapsed_time = current_time - self.start_time

            with self.lock:
                # Calculate metrics
                sent_packets = len(self.sent_packets)
                received_packets = len(self.received_packets)
                packet_loss = (sent_packets - received_packets) / sent_packets if sent_packets > 0 else 0

                latencies = []
                out_of_order = 0
                corrupt_packets = 0
                last_seq_num = -1

                for seq_num, send_time in self.sent_packets.items():
                    if seq_num in self.received_packets:
                        recv_info = self.received_packets[seq_num]
                        latency = recv_info['recv_time'] - send_time
                        latencies.append(latency)

                        # Check for corruption
                        data_checksum = struct.unpack('!I', hashlib.md5(recv_info['data']).digest()[:4])[0]
                        if data_checksum != recv_info['checksum']:
                            corrupt_packets += 1

                        # Check for out-of-order packets
                        if seq_num < last_seq_num:
                            out_of_order += 1
                        last_seq_num = seq_num

                avg_latency = sum(latencies) / len(latencies) if latencies else 0
                jitter = self.calculate_jitter(latencies)
                bandwidth = (received_packets * self.packet_size * 8) / elapsed_time if elapsed_time > 0 else 0  # in bits per second

                # Record metrics
                self.metrics.append({
                    'Time': elapsed_time,
                    'Bandwidth(bps)': bandwidth,
                    'Latency(s)': avg_latency,
                    'Jitter(s)': jitter,
                    'Packet Loss(%)': packet_loss * 100,
                    'Corrupt Packets': corrupt_packets,
                    'Out-of-Order Packets': out_of_order
                })

                # Real-time monitoring output
                print(f"[{elapsed_time:.2f}s] Bandwidth: {bandwidth:.2f}bps, Latency: {avg_latency*1000:.2f}ms, "
                      f"Jitter: {jitter*1000:.2f}ms, Packet Loss: {packet_loss*100:.2f}%")

    def calculate_jitter(self, latencies):
        """
        Calculates jitter as the average deviation from the mean latency.

        Args:
            latencies (list): List of latency measurements.

        Returns:
            float: The calculated jitter.
        """
        if not latencies or len(latencies) < 2:
            return 0.0
        mean_latency = sum(latencies) / len(latencies)
        return sum(abs(latency - mean_latency) for latency in latencies) / len(latencies)

    def save_metrics(self):
        """
        Saves the recorded metrics to a CSV file.
        """
        if self.metrics:
            keys = self.metrics[0].keys()
            with open(self.output_file, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.metrics)

    def run(self):
        """
        Starts the network test.
        """
        try:
            sender_thread = threading.Thread(target=self.send_packets)
            metrics_thread = threading.Thread(target=self.measure_metrics)

            sender_thread.start()
            metrics_thread.start()

            sender_thread.join()
            self.stop_event.set()
            metrics_thread.join()
        except KeyboardInterrupt:
            print("\nTest interrupted by user.")
            self.stop_event.set()
        finally:
            self.save_metrics()
            print(f"\nMetrics saved to {self.output_file}")

def print_help():
    """
    Prints detailed help information for the client script.
    """
    help_text = """
    Network Measurement Tool Client

    Usage:
        python3 client.py [options]

    Options:
        --server_ip IP            Server IP address (default: 127.0.0.1)
        --server_port PORT        Server port number (default: 5000)
        --packet_size SIZE        Packet size in bytes (default: 1024)
        --duration SECONDS        Duration of the test in seconds (default: 60)
        --interval SECONDS        Measurement interval in seconds (default: 1)
        --output FILE             Output CSV file for metrics (default: metrics.csv)
        -h, --help                Show this help message and exit

    Examples:
        python3 client.py
        python3 client.py --server_ip 192.168.1.10 --server_port 8000 --packet_size 2048 --duration 120 --interval 2 --output test_metrics.csv
    """
    print(help_text)

if __name__ == '__main__':
    # Check for help flag or no arguments
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Network Measurement Tool Client', add_help=False)
    parser.add_argument('--server_ip', type=str, default=SERVER_IP, help='Server IP address (default: 127.0.0.1)')
    parser.add_argument('--server_port', type=int, default=SERVER_PORT, help='Server port number (default: 5000)')
    parser.add_argument('--packet_size', type=int, default=PACKET_SIZE, help='Packet size in bytes (default: 1024)')
    parser.add_argument('--duration', type=int, default=DURATION, help='Duration of the test in seconds (default: 60)')
    parser.add_argument('--interval', type=int, default=MEASUREMENT_INTERVAL, help='Measurement interval in seconds (default: 1)')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, help='Output CSV file for metrics (default: metrics.csv)')
    args, unknown = parser.parse_known_args()

    # Check for unrecognized arguments
    if unknown:
        print(f"Unrecognized arguments: {' '.join(unknown)}\n")
        print_help()
        sys.exit(1)

    tester = NetworkTester(
        server_ip=args.server_ip,
        server_port=args.server_port,
        packet_size=args.packet_size,
        duration=args.duration,
        measurement_interval=args.interval,
        output_file=args.output
    )
    tester.run()
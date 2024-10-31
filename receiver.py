import socket
import threading
import signal
import time
import csv
import os
import sys
import platform
import statistics

LINK_1 = "10.1.1.1"
LINK_2 = "192.168.127.30"
# LINK_3 = "192.168.227.30"

PORT_1 = 500
PORT_2 = 501
# PORT_3 = 502


stop_event = threading.Event()

def calculate_statistics(csv_filename):
    differences = []

    with open(csv_filename, mode='r') as csvfile:
        csv_reader = csv.reader(csvfile)
        next(csv_reader)
        for row in csv_reader:
            difference = int(row[2])
            differences.append(difference)

    if differences:
        avg = statistics.mean(differences) / 1000000
        min_diff = min(differences) / 1000000
        max_diff = max(differences) / 1000000
        std_dev = statistics.stdev(differences) / 1000000

        stats_filename = csv_filename.replace("udp_listener_", "statistics_")
        
        write_header = not os.path.isfile(stats_filename)

        with open(stats_filename, mode='a', newline='') as stats_file:
            stats_writer = csv.writer(stats_file, delimiter=';')
            if write_header:
                stats_writer.writerow(['Average Difference (ms)', 'Minimum Difference (ms)', 'Maximum Difference (ms)', 'Standard Deviation (ms)'])
            stats_writer.writerow([str(avg).replace('.', ','), str(min_diff).replace('.', ','), str(max_diff).replace('.', ','), str(std_dev).replace('.', ',')])

        print(f"Statistics appended to {stats_filename}.")
    else:
        print("No differences recorded.")

def signal_handler(sig, frame):
    print("\nReceived interrupt signal, shutting down gracefully...")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)

def get_char():
    if platform.system() == 'Windows':
        import msvcrt
        return msvcrt.getch()
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

def listen_for_keypress():
    char = get_char()
    if char:
        stop_event.set()

def listen_udp(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    print(f"Listening for UDP messages on {ip}:{port}")

    csv_filename = f"udp_listener_{ip.replace('.', '_')}.csv"

    if os.path.isfile(csv_filename):
        os.remove(csv_filename)
        print(f"Deleted existing file: {csv_filename}")
    
    with open(csv_filename, mode='a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Received Timestamp (ns)', 'Sent Timestamp (ns)', 'Difference (ns)'])

        while not stop_event.is_set():
            try:
                sock.settimeout(1.0)
                data, addr = sock.recvfrom(1024)
                end = int(time.time_ns())
                start = int(data.decode())
                difference = abs(end - start)
                ms = difference / 1000000
                
                print(f"{ip}:\t\t{ms:.2f} ms")
                
                csv_writer.writerow([end, start, difference])
                csvfile.flush()

            except socket.timeout:
                continue
            except Exception as e:
                if not stop_event.is_set():
                    print(f"Error on {ip}:{port} -> {e}")

    sock.close()
    print(f"Stopped listening on {ip}:{port}")
    calculate_statistics(csv_filename)

thread_1 = threading.Thread(target=listen_udp, args=(LINK_1, PORT_1))
thread_2 = threading.Thread(target=listen_udp, args=(LINK_2, PORT_2))
# thread_3 = threading.Thread(target=listen_udp, args=(LINK_3, PORT_3))

keypress_thread = threading.Thread(target=listen_for_keypress)

thread_1.start()
thread_2.start()
# thread_3.start()

keypress_thread.start()

thread_1.join()
thread_2.join()
# thread_3.join()

keypress_thread.join()

print("UDP receiver has been gracefully shut down.")

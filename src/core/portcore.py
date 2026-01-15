import subprocess
import psutil
import socket
import os
import json
import time
import zmq
from datetime import datetime

class PortManagerCore:
    def __init__(self, config_file=r"E:\S.I.M.O.N\thalamus\portmaster\port_reservations.json"):
        self.config_file = config_file
        self.server_socket = None
        self.log_file = r"E:\S.I.M.O.N\thalamus\portmaster\port_logs.txt"

    def log(self, message):
        """Log message to port_logs.txt"""
        with open(self.log_file, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

    def list_connections(self):
        """List active network connections as structured data."""
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr:
                    process_name = "System Idle Process"
                    if conn.pid:
                        try:
                            process_name = psutil.Process(conn.pid).name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            process_name = "N/A"
                    
                    conn_data = {
                        "Protocol": 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP',
                        "Local Address": f"{conn.laddr.ip}:{conn.laddr.port}",
                        "Remote Address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                        "Status": conn.status if conn.type == socket.SOCK_STREAM else 'N/A',
                        "PID": conn.pid or 0,
                        "Process Name": process_name
                    }
                    connections.append(conn_data)
            self.log(f"Listed {len(connections)} connections")
            return connections
        except Exception as e:
            self.log(f"List connections failed: {str(e)}")
            raise

    def check_port(self, port):
        """Check if a port is in use"""
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                self.log(f"Invalid port {port}: must be 1-65535")
                return f"Error: Port must be an integer between 1 and 65535", 1
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == port:
                    self.log(f"Port {port} in use by PID {conn.pid}")
                    return f"Port {port} is in use by PID {conn.pid} ({psutil.Process(conn.pid).name()})", 0
            self.log(f"Port {port} is not in use")
            return f"Port {port} is not in use", 0
        except ValueError:
            self.log(f"Invalid port format: {port}")
            return "Error: Port must be an integer", 1
        except Exception as e:
            self.log(f"Check port {port} failed: {str(e)}")
            return f"Error: Failed to check port {port}: {str(e)}", 1

    def kill_process(self, pid, confirm=False):
        """Kill a process by PID"""
        try:
            pid = int(pid)
            if pid == 0:
                self.log("Cannot terminate system process (PID 0)")
                return "Error: Cannot terminate system process or invalid PID", 1
            if not psutil.pid_exists(pid):
                self.log(f"PID {pid} does not exist")
                return f"Error: PID {pid} does not exist", 1
            if confirm:
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=5)
                self.log(f"Terminated process {pid} ({process.name()})")
                return f"Terminated process {pid}", 0
            else:
                self.log(f"Kill process {pid} requires confirmation")
                return "Confirmation required (use -y flag or input 'y')", 2
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
            self.log(f"Kill process {pid} failed: {str(e)}")
            return f"Error: Failed to terminate PID {pid}: {str(e)}", 1
        except ValueError:
            self.log(f"Invalid PID format: {pid}")
            return "Error: PID must be an integer", 1

    def block_port(self, port, protocol, confirm=False):
        """Block a port using firewall rules"""
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                self.log(f"Invalid port {port}: must be 1-65535")
                return f"Error: Port must be an integer between 1 and 65535", 1
            if protocol not in ['TCP', 'UDP']:
                self.log(f"Invalid protocol: {protocol}")
                return f"Error: Protocol must be TCP or UDP", 1
            if confirm:
                rule_name = f"Portmaster_{protocol}_{port}"
                cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule', f'name={rule_name}',
                       'dir=in', 'action=block', f'protocol={protocol}', f'localport={port}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log(f"Blocked {protocol} port {port}")
                    return f"Blocked {protocol} port {port}", 0
                else:
                    self.log(f"Failed to block {protocol} port {port}: {result.stderr}")
                    return f"Error: Failed to block {protocol} port {port}: {result.stderr}", 1
            else:
                self.log(f"Block {protocol} port {port} requires confirmation")
                return "Confirmation required (use -y flag or input 'y')", 2
        except ValueError:
            self.log(f"Invalid port format: {port}")
            return "Error: Port must be an integer", 1
        except Exception as e:
            self.log(f"Block {protocol} port {port} failed: {str(e)}")
            return f"Error: Failed to block {protocol} port {port}: {str(e)}", 1

    def unblock_port(self, port, protocol, confirm=False):
        """Unblock a port by removing firewall rule"""
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                self.log(f"Invalid port {port}: must be 1-65535")
                return f"Error: Port must be an integer between 1 and 65535", 1
            if protocol not in ['TCP', 'UDP']:
                self.log(f"Invalid protocol: {protocol}")
                return f"Error: Protocol must be TCP or UDP", 1
            if confirm:
                rule_name = f"Portmaster_{protocol}_{port}"
                cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and "Ok" in result.stdout:
                    self.log(f"Unblocked {protocol} port {port}")
                    return f"Unblocked {protocol} port {port}", 0
                else:
                    self.log(f"Failed to unblock {protocol} port {port}: {result.stderr}")
                    return f"Error: Failed to unblock {protocol} port {port}: {result.stderr}", 1
            else:
                self.log(f"Unblock {protocol} port {port} requires confirmation")
                return "Confirmation required (use -y flag or input 'y')", 2
        except ValueError:
            self.log(f"Invalid port format: {port}")
            return "Error: Port must be an integer", 1
        except Exception as e:
            self.log(f"Unblock {protocol} port {port} failed: {str(e)}")
            return f"Error: Failed to unblock {protocol} port {port}: {str(e)}", 1

    def check_firewall_rule(self, rule_name):
        """Check if a firewall rule exists"""
        try:
            cmd = ['netsh', 'advfirewall', 'firewall', 'show', 'rule', f'name={rule_name}']
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            self.log(f"Checked firewall rule {rule_name}: {'Found' if 'Rule Name' in result.stdout else 'Not found'}")
            return rule_name in result.stdout and "Rule Name:" in result.stdout
        except Exception as e:
            self.log(f"Check firewall rule {rule_name} failed: {str(e)}")
            return False

    def start_server(self, port, protocol, confirm=False):
        """Start a server on a specified port"""
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                self.log(f"Invalid port {port}: must be 1-65535")
                return f"Error: Port must be an integer between 1 and 65535", 1
            if protocol not in ['TCP', 'UDP']:
                self.log(f"Invalid protocol: {protocol}")
                return f"Error: Protocol must be TCP or UDP", 1
            if confirm:
                if self.bind_and_verify(port, protocol):
                    self.log(f"Started server on {protocol} port {port}")
                    return f"Started server on {protocol} port {port}", 0
                else:
                    self.log(f"Failed to bind {protocol} port {port}")
                    return f"Error: Failed to bind {protocol} port {port}", 1
            else:
                self.log(f"Start server on {protocol} port {port} requires confirmation")
                return "Confirmation required (use -y flag or input 'y')", 2
        except ValueError:
            self.log(f"Invalid port format: {port}")
            return "Error: Port must be an integer", 1
        except Exception as e:
            self.log(f"Start server on {protocol} port {port} failed: {str(e)}")
            return f"Error: Failed to start server on {protocol} port {port}: {str(e)}", 1

    def stop_server(self, confirm=False):
        """Stop the running server"""
        if not confirm:
            self.log("Stop server requires confirmation")
            return "Confirmation required (use -y flag or input 'y')", 2
        if self.server_socket:
            try:
                self.server_socket.close()
                self.server_socket = None
                self.log("Stopped server")
                return "Stopped server", 0
            except Exception as e:
                self.log(f"Stop server failed: {str(e)}")
                return f"Error: Failed to stop server: {str(e)}", 1
        else:
            self.log("No server running")
            return "Error: No server running", 1

    def bind_and_verify(self, port, protocol):
        """Bind a port and verify it's bound"""
        try:
            if protocol == 'TCP':
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('0.0.0.0', port))
                self.server_socket.listen(1)
            else:  # UDP
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('0.0.0.0', port))
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == port and conn.pid == os.getpid():
                    return True
            self.server_socket.close()
            self.server_socket = None
            return False
        except Exception as e:
            self.log(f"Bind and verify {protocol} port {port} failed: {str(e)}")
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            return False

    def reserve_port(self, port, protocol, exe_path, confirm=False):
        """Reserve a port for a specific executable"""
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                self.log(f"Invalid port {port}: must be 1-65535")
                return f"Error: Port must be an integer between 1 and 65535", 1
            if protocol not in ['TCP', 'UDP']:
                self.log(f"Invalid protocol: {protocol}")
                return f"Error: Protocol must be TCP or UDP", 1
            if not os.path.exists(exe_path):
                self.log(f"Executable path {exe_path} does not exist")
                return f"Error: Executable path {exe_path} does not exist", 1
            if confirm:
                rule_name = f"Portmaster_{protocol}_{port}"
                cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule', f'name={rule_name}',
                       'dir=in', 'action=allow', f'protocol={protocol}', f'localport={port}',
                       f'program={exe_path}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.log(f"Failed to reserve {protocol} port {port}: {result.stderr}")
                    return f"Error: Failed to reserve {protocol} port {port}: {result.stderr}", 1
                config = {}
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                config[str(port)] = {'protocol': protocol, 'exe_path': exe_path}
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)
                self.log(f"Reserved {protocol} port {port} for {exe_path}")
                return f"Reserved {protocol} port {port}", 0
            else:
                self.log(f"Reserve {protocol} port {port} requires confirmation")
                return "Confirmation required (use -y flag or input 'y')", 2
        except ValueError:
            self.log(f"Invalid port format: {port}")
            return "Error: Port must be an integer", 1
        except Exception as e:
            self.log(f"Reserve {protocol} port {port} failed: {str(e)}")
            return f"Error: Failed to reserve {protocol} port {port}: {str(e)}", 1

    def release_port(self, port, confirm=False):
        """Release a reserved port"""
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                self.log(f"Invalid port {port}: must be 1-65535")
                return f"Error: Port must be an integer between 1 and 65535", 1
            if confirm:
                config = {}
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                if str(port) not in config:
                    self.log(f"Port {port} is not reserved")
                    return f"Error: Port {port} is not reserved", 1
                protocol = config[str(port)]['protocol']
                rule_name = f"Portmaster_{protocol}_{port}"
                cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.log(f"Failed to release {protocol} port {port}: {result.stderr}")
                    return f"Error: Failed to release {protocol} port {port}: {result.stderr}", 1
                del config[str(port)]
                with open(self.config_file, 'w') as f:
                    json.dump(config, f)
                self.log(f"Released {protocol} port {port}")
                return f"Released {protocol} port {port}", 0
            else:
                self.log(f"Release port {port} requires confirmation")
                return "Confirmation required (use -y flag or input 'y')", 2
        except ValueError:
            self.log(f"Invalid port format: {port}")
            return "Error: Port must be an integer", 1
        except Exception as e:
            self.log(f"Release port {port} failed: {str(e)}")
            return f"Error: Failed to release port {port}: {str(e)}", 1

    def save_connections(self, filename):
        """Save connections to a file"""
        try:
            connections_data = self.list_connections()
            count = len(connections_data)
            
            # Create a formatted string for the file
            header = f"{'Protocol':<10}{'Local Address':<25}{'Remote Address':<25}{'Status':<15}{'PID':<10}{'Process Name'}\n"
            divider = "=" * 120 + "\n"
            
            content = ""
            for conn in connections_data:
                content += f"{conn['Protocol']:<10}{conn['Local Address']:<25}{conn['Remote Address']:<25}{conn['Status']:<15}{conn['PID']:<10}{conn['Process Name']}\n"

            with open(filename, 'w') as f:
                f.write("Portmaster Network Connections\n")
                f.write(divider)
                f.write(header)
                f.write(divider)
                f.write(content)
                
            self.log(f"Saved {count} connections to {filename}")
            return f"Saved {count} connections to {filename}", 0
        except Exception as e:
            self.log(f"Save connections to {filename} failed: {str(e)}")
            return f"Error: Failed to save connections to {filename}: {str(e)}", 1

def find_free_port(start_port=49152, max_retries=300):
    """Find a free port in the ephemeral range"""
    log_file = r"E:\S.I.M.O.N\thalamus\portmaster\port_logs.txt"
    for attempt in range(max_retries):
        port = start_port + (attempt % (65535 - start_port + 1))
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == port:
                    break
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('0.0.0.0', port))
                with open(log_file, 'a') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Found free port {port}\n")
                return port
        except (socket.error, psutil.AccessDenied):
            pass
        time.sleep(1)
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to find free port after {max_retries} attempts\n")
    raise RuntimeError(f"Failed to find free port after {max_retries} attempts")

def simulate_zeromq_pub_sub(pub_port, sub_port=None, test_mode=False):
    """Simulate ZeroMQ PUB-SUB binding and connection"""
    log_file = r"E:\S.I.M.O.N\thalamus\portmaster\port_logs.txt"
    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    sub_socket = context.socket(zmq.SUB)
    try:
        pub_socket.setsockopt(zmq.LINGER, 0)
        pub_socket.bind(f"tcp://*:{pub_port}")
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Bound PUB socket to tcp://*:{pub_port}\n")
        
        sub_port = sub_port or pub_port
        sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        sub_socket.setsockopt(zmq.LINGER, 0)
        sub_socket.connect(f"tcp://localhost:{sub_port}")
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Connected SUB socket to tcp://localhost:{sub_port}\n")
        
        time.sleep(0.2)
        pub_socket.send(b"Test message")
        poller = zmq.Poller()
        poller.register(sub_socket, zmq.POLLIN)
        events = dict(poller.poll(2000))
        if sub_socket in events and events[sub_socket] == zmq.POLLIN:
            message = sub_socket.recv()
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Received message: {message.decode()}\n")
            if message != b"Test message":
                raise RuntimeError("Failed to receive correct message")
        else:
            raise RuntimeError("Failed to receive message")
        
        if test_mode:
            time.sleep(5)  # Keep socket open for tests
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Extended PUB socket lifetime for test\n")
    except zmq.error.ZMQError as e:
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ZeroMQ error: {str(e)}\n")
        raise
    finally:
        pub_socket.close()
        sub_socket.close()
        context.term()
        time.sleep(30)  # Increased cleanup sleep
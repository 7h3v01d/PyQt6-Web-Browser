import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QTabWidget,
    QRadioButton, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt
from core.portcore import PortManagerCore
import argparse

class PortmasterPlugin(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.core = PortManagerCore(config_file=r"E:\Projects\_webbrowser\src\configs\port_reservations.json")
        self.setWindowTitle("Portmaster Plugin")
        self.setGeometry(100, 100, 1100, 750)
        self.setup_ui()

    def setup_ui(self):
        """Set up the plugin UI with tabs for connections, port management, server, and CLI."""
        main_layout = QVBoxLayout(self)

        # Tabbed interface
        self.notebook = QTabWidget()
        main_layout.addWidget(self.notebook)
        self.setup_connections_tab()
        self.setup_port_management_tab()
        self.setup_server_tab()
        self.setup_reservations_tab()
        self.setup_cli_tab()

    def setup_connections_tab(self):
        """Connections tab: List connections and save to file."""
        tab = QGroupBox("Connections")
        layout = QVBoxLayout(tab)
        self.notebook.addTab(tab, "Connections")

        # Controls
        controls_layout = QHBoxLayout()
        list_btn = QPushButton("List Connections")
        list_btn.clicked.connect(self.list_connections)
        controls_layout.addWidget(list_btn)
        controls_layout.addStretch(1)
        save_label = QLabel("File Path:")
        self.save_file_entry = QLineEdit(r"E:\Projects\_webbrowser\src\configs\output.txt")
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_connections)
        controls_layout.addWidget(save_label)
        controls_layout.addWidget(self.save_file_entry)
        controls_layout.addWidget(save_btn)
        layout.addLayout(controls_layout)

        # Table
        self.connections_table = QTableWidget()
        self.connections_table.setColumnCount(6)
        self.connections_table.setHorizontalHeaderLabels([
            "Protocol", "Local Address", "Remote Address", "Status", "PID", "Process Name"
        ])
        self.connections_table.setSortingEnabled(True)
        self.connections_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.connections_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.connections_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.connections_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.connections_table)

    def setup_port_management_tab(self):
        """Port Management tab: Check port, kill process, block/unblock port."""
        tab = QGroupBox("Port Management")
        layout = QHBoxLayout(tab)
        self.notebook.addTab(tab, "Port Management")

        # Controls
        controls_container = QGroupBox()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(controls_container)

        # Check Port
        check_group = QGroupBox("Check Port")
        check_layout = QHBoxLayout(check_group)
        self.port_entry = QLineEdit()
        self.port_entry.setPlaceholderText("Port")
        check_btn = QPushButton("Check")
        check_btn.clicked.connect(self.check_port)
        check_layout.addWidget(QLabel("Port:"))
        check_layout.addWidget(self.port_entry)
        check_layout.addWidget(check_btn)
        controls_layout.addWidget(check_group)

        # Kill Process
        kill_group = QGroupBox("Kill Process")
        kill_layout = QHBoxLayout(kill_group)
        self.pid_entry = QLineEdit()
        self.pid_entry.setPlaceholderText("PID")
        kill_btn = QPushButton("Kill")
        kill_btn.clicked.connect(self.kill_process)
        kill_layout.addWidget(QLabel("PID:"))
        kill_layout.addWidget(self.pid_entry)
        kill_layout.addWidget(kill_btn)
        controls_layout.addWidget(kill_group)

        # Block/Unblock Port
        block_group = QGroupBox("Block/Unblock Port")
        block_layout = QGridLayout(block_group)
        self.block_port_entry = QLineEdit()
        self.block_port_entry.setPlaceholderText("Port")
        self.pm_tcp_radio = QRadioButton("TCP")
        self.pm_udp_radio = QRadioButton("UDP")
        self.pm_tcp_radio.setChecked(True)
        block_btn = QPushButton("Block")
        unblock_btn = QPushButton("Unblock")
        block_btn.clicked.connect(self.block_port)
        unblock_btn.clicked.connect(self.unblock_port)
        block_layout.addWidget(QLabel("Port:"), 0, 0)
        block_layout.addWidget(self.block_port_entry, 0, 1, 1, 2)
        block_layout.addWidget(self.pm_tcp_radio, 1, 1)
        block_layout.addWidget(self.pm_udp_radio, 1, 2)
        block_layout.addWidget(block_btn, 2, 1)
        block_layout.addWidget(unblock_btn, 2, 2)
        controls_layout.addWidget(block_group)

        # Output
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.pm_output_text = QTextEdit()
        self.pm_output_text.setReadOnly(True)
        output_layout.addWidget(self.pm_output_text)
        layout.addWidget(output_group, 1)

    def setup_server_tab(self):
        """Server tab: Start/stop server."""
        tab = QGroupBox("Server")
        layout = QHBoxLayout(tab)
        self.notebook.addTab(tab, "Server")

        # Controls
        controls_container = QGroupBox()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(controls_container)

        # Start Server
        server_group = QGroupBox("Start Server")
        server_layout = QGridLayout(server_group)
        self.server_port_entry = QLineEdit()
        self.server_port_entry.setPlaceholderText("Port")
        self.server_tcp_radio = QRadioButton("TCP")
        self.server_udp_radio = QRadioButton("UDP")
        self.server_tcp_radio.setChecked(True)
        start_btn = QPushButton("Start")
        stop_btn = QPushButton("Stop")
        start_btn.clicked.connect(self.start_server)
        stop_btn.clicked.connect(self.stop_server)
        server_layout.addWidget(QLabel("Port:"), 0, 0)
        server_layout.addWidget(self.server_port_entry, 0, 1, 1, 2)
        server_layout.addWidget(self.server_tcp_radio, 1, 1)
        server_layout.addWidget(self.server_udp_radio, 1, 2)
        server_layout.addWidget(start_btn, 2, 1)
        server_layout.addWidget(stop_btn, 2, 2)
        controls_layout.addWidget(server_group)

        # Output
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.server_output_text = QTextEdit()
        self.server_output_text.setReadOnly(True)
        output_layout.addWidget(self.server_output_text)
        layout.addWidget(output_group, 1)

    def setup_reservations_tab(self):
        """Reservations tab: Reserve/release ports."""
        tab = QGroupBox("Reservations")
        layout = QHBoxLayout(tab)
        self.notebook.addTab(tab, "Reservations")

        # Controls
        controls_container = QGroupBox()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(controls_container)

        # Reserve Port
        reserve_group = QGroupBox("Reserve Port")
        reserve_layout = QGridLayout(reserve_group)
        self.reserve_port_entry = QLineEdit()
        self.reserve_port_entry.setPlaceholderText("Port")
        self.exe_path_entry = QLineEdit()
        self.exe_path_entry.setPlaceholderText("Executable Path")
        self.reserve_tcp_radio = QRadioButton("TCP")
        self.reserve_udp_radio = QRadioButton("UDP")
        self.reserve_tcp_radio.setChecked(True)
        reserve_btn = QPushButton("Reserve")
        release_btn = QPushButton("Release")
        reserve_btn.clicked.connect(self.reserve_port)
        release_btn.clicked.connect(self.release_port)
        reserve_layout.addWidget(QLabel("Port:"), 0, 0)
        reserve_layout.addWidget(self.reserve_port_entry, 0, 1, 1, 2)
        reserve_layout.addWidget(QLabel("Exe Path:"), 1, 0)
        reserve_layout.addWidget(self.exe_path_entry, 1, 1, 1, 2)
        reserve_layout.addWidget(self.reserve_tcp_radio, 2, 1)
        reserve_layout.addWidget(self.reserve_udp_radio, 2, 2)
        reserve_layout.addWidget(reserve_btn, 3, 1)
        reserve_layout.addWidget(release_btn, 3, 2)
        controls_layout.addWidget(reserve_group)

        # Output
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.res_output_text = QTextEdit()
        self.res_output_text.setReadOnly(True)
        output_layout.addWidget(self.res_output_text)
        layout.addWidget(output_group, 1)

    def setup_cli_tab(self):
        """CLI tab: Execute CLI commands."""
        tab = QGroupBox("CLI")
        layout = QVBoxLayout(tab)
        self.notebook.addTab(tab, "CLI")

        # Command Input
        cli_group = QGroupBox("Command Line")
        cli_layout = QHBoxLayout(cli_group)
        self.cli_input = QLineEdit()
        self.cli_input.setPlaceholderText("Enter command (e.g., list, check-port 8080)")
        cli_btn = QPushButton("Run")
        cli_btn.clicked.connect(self.run_cli_command)
        cli_layout.addWidget(QLabel("Command:"))
        cli_layout.addWidget(self.cli_input)
        cli_layout.addWidget(cli_btn)
        layout.addWidget(cli_group)

        # Output
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.cli_output_text = QTextEdit()
        self.cli_output_text.setReadOnly(True)
        output_layout.addWidget(self.cli_output_text)
        layout.addWidget(output_group, 1)

    def _confirm_action(self, title, message):
        """Show confirmation dialog."""
        reply = QMessageBox.question(self, title, message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def list_connections(self):
        """List network connections in table."""
        try:
            connections = self.core.list_connections()
            self.connections_table.setRowCount(0)
            for row, conn in enumerate(connections):
                self.connections_table.insertRow(row)
                for col, value in enumerate(conn.values()):
                    item = QTableWidgetItem(str(value))
                    if col == 4:  # PID column
                        item.setData(Qt.ItemDataRole.DisplayRole, int(value))
                    self.connections_table.setItem(row, col, item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list connections: {str(e)}")

    def check_port(self):
        """Check if a port is in use."""
        port = self.port_entry.text()
        if not port:
            QMessageBox.warning(self, "Input Error", "Please enter a port number")
            return
        output, rc = self.core.check_port(port)
        self.pm_output_text.setText(output)
        if rc != 0:
            QMessageBox.critical(self, "Error", output)

    def kill_process(self):
        """Kill a process by PID."""
        pid = self.pid_entry.text()
        if not pid:
            QMessageBox.warning(self, "Input Error", "Please enter a PID")
            return
        if self._confirm_action("Confirm Kill", f"Are you sure you want to terminate PID {pid}?"):
            output, rc = self.core.kill_process(pid, confirm=True)
            self.pm_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def block_port(self):
        """Block a port."""
        port = self.block_port_entry.text()
        protocol = "TCP" if self.pm_tcp_radio.isChecked() else "UDP"
        if not port:
            QMessageBox.warning(self, "Input Error", "Please enter a port number")
            return
        if self._confirm_action("Confirm Block", f"Are you sure you want to block {protocol} port {port}?"):
            output, rc = self.core.block_port(port, protocol, confirm=True)
            self.pm_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def unblock_port(self):
        """Unblock a port."""
        port = self.block_port_entry.text()
        protocol = "TCP" if self.pm_tcp_radio.isChecked() else "UDP"
        if not port:
            QMessageBox.warning(self, "Input Error", "Please enter a port number")
            return
        if self._confirm_action("Confirm Unblock", f"Are you sure you want to unblock {protocol} port {port}?"):
            output, rc = self.core.unblock_port(port, protocol, confirm=True)
            self.pm_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def start_server(self):
        """Start a server on a port."""
        port = self.server_port_entry.text()
        protocol = "TCP" if self.server_tcp_radio.isChecked() else "UDP"
        if not port:
            QMessageBox.warning(self, "Input Error", "Please enter a port number")
            return
        if self._confirm_action("Confirm Start", f"Are you sure you want to start a server on {protocol} port {port}?"):
            output, rc = self.core.start_server(port, protocol, confirm=True)
            self.server_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def stop_server(self):
        """Stop the running server."""
        if self._confirm_action("Confirm Stop", "Are you sure you want to stop the running server?"):
            output, rc = self.core.stop_server(confirm=True)
            self.server_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def reserve_port(self):
        """Reserve a port for an executable."""
        port = self.reserve_port_entry.text()
        protocol = "TCP" if self.reserve_tcp_radio.isChecked() else "UDP"
        exe_path = self.exe_path_entry.text()
        if not port or not exe_path:
            QMessageBox.warning(self, "Input Error", "Please enter a port number and an executable path")
            return
        if self._confirm_action("Confirm Reserve", f"Reserve {protocol} port {port} for {exe_path}?"):
            output, rc = self.core.reserve_port(port, protocol, exe_path, confirm=True)
            self.res_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def release_port(self):
        """Release a reserved port."""
        port = self.reserve_port_entry.text()
        if not port:
            QMessageBox.warning(self, "Input Error", "Please enter a port number")
            return
        if self._confirm_action("Confirm Release", f"Are you sure you want to release port {port}?"):
            output, rc = self.core.release_port(port, confirm=True)
            self.res_output_text.setText(output)
            if rc != 0:
                QMessageBox.critical(self, "Error", output)

    def save_connections(self):
        """Save connections to a file."""
        filename = self.save_file_entry.text()
        if not filename:
            QMessageBox.warning(self, "Input Error", "Please enter a file path")
            return
        try:
            output, rc = self.core.save_connections(filename)
            if rc == 0:
                QMessageBox.information(self, "Success", output)
            else:
                QMessageBox.critical(self, "Error", output)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")

    def run_cli_command(self):
        """Run a CLI command."""
        command = self.cli_input.text().strip()
        if not command:
            QMessageBox.warning(self, "Input Error", "Please enter a command")
            return
        try:
            parser = argparse.ArgumentParser(prog="portmaster")
            parser.add_argument('--yes', '-y', action='store_true', default=True)
            subparsers = parser.add_subparsers(dest='command', required=True)
            subparsers.add_parser('list')
            parser_check = subparsers.add_parser('check-port')
            parser_check.add_argument('port')
            parser_kill = subparsers.add_parser('kill')
            parser_kill.add_argument('pid')
            parser_block = subparsers.add_parser('block')
            parser_block.add_argument('port')
            parser_block.add_argument('protocol', choices=['TCP', 'UDP'])
            parser_unblock = subparsers.add_parser('unblock')
            parser_unblock.add_argument('port')
            parser_unblock.add_argument('protocol', choices=['TCP', 'UDP'])
            parser_start = subparsers.add_parser('start-server')
            parser_start.add_argument('port')
            parser_start.add_argument('protocol', choices=['TCP', 'UDP'])
            subparsers.add_parser('stop-server')
            parser_reserve = subparsers.add_parser('reserve')
            parser_reserve.add_argument('port')
            parser_reserve.add_argument('protocol', choices=['TCP', 'UDP'])
            parser_reserve.add_argument('--exe-path', required=True)
            parser_release = subparsers.add_parser('release')
            parser_release.add_argument('port')
            parser_save = subparsers.add_parser('save')
            parser_save.add_argument('filename')
            args = parser.parse_args(command.split())

            if args.command == 'list':
                self.list_connections()
                self.cli_output_text.setText("Connections listed in Connections tab")
            elif args.command == 'check-port':
                output, rc = self.core.check_port(args.port)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'kill':
                output, rc = self.core.kill_process(args.pid, confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'block':
                output, rc = self.core.block_port(args.port, args.protocol, confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'unblock':
                output, rc = self.core.unblock_port(args.port, args.protocol, confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'start-server':
                output, rc = self.core.start_server(args.port, args.protocol, confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'stop-server':
                output, rc = self.core.stop_server(confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'reserve':
                output, rc = self.core.reserve_port(args.port, args.protocol, args.exe_path, confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'release':
                output, rc = self.core.release_port(args.port, confirm=args.yes)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
            elif args.command == 'save':
                output, rc = self.core.save_connections(args.filename)
                self.cli_output_text.setText(output)
                if rc != 0:
                    QMessageBox.critical(self, "Error", output)
        except SystemExit:
            self.cli_output_text.setText("Invalid command or arguments. Use commands like: list, check-port <port>, kill <pid>, block <port> <protocol>, etc.")
            QMessageBox.warning(self, "Input Error", "Invalid command or arguments")
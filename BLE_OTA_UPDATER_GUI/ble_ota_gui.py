import sys
import asyncio
import zlib
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QListWidget, QMessageBox, QHBoxLayout, QProgressBar, QSpinBox
)

from PySide6.QtCore import Qt, QThread, Signal
from bleak import BleakScanner, BleakClient


BLE_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"  # Match the ESP32 BLE service UUID
BLE_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"     # Match the ESP32 BLE characteristic UUID

class BLEWorker(QThread):
    status_update = Signal(str)
    devices_found = Signal(list)
    connected_device = Signal(str, str)  # Pass both name and address

    def __init__(self):
        super().__init__()
        self.client = None # BLE BleakClient instance
        self.running = True # Control flag for the thread
        self.device = None # Store device address
        self.device_name = None  # Store device name
        self.notify_started = False  # Track if we've started notifications
        self.chunk_delay = 0.01  # Default 10ms delay between chunks
        self.chunk_size = 128  # Default chunk size in bytes
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def run(self):
        self.loop.run_forever()

    def stop(self):
        self.running = False
        if self.client and self.client.is_connected:
            self.loop.call_soon_threadsafe(asyncio.create_task, self.client.disconnect())
        self.loop.call_soon_threadsafe(self.loop.stop)

    def set_chunk_delay(self, delay_ms):
        """Set delay between chunks in milliseconds"""
        self.chunk_delay = delay_ms / 1000.0  # Convert to seconds

    def set_chunk_size(self, size_bytes):
        """Set chunk size in bytes"""
        self.chunk_size = max(size_bytes, 1)  # Minimum 1 byte

    def scan_devices(self):
        async def _scan():
            self.status_update.emit("Scanning for BLE devices...")
            devices = await BleakScanner.discover(timeout=5.0)
            self.devices_found.emit(devices)
            self.status_update.emit("Scan complete.")
        self.loop.call_soon_threadsafe(asyncio.create_task, _scan())

    def connect_device(self, address, name):
        async def _connect():
            self.client = BleakClient(address)
            try:
                await self.client.connect()
                if self.client.is_connected:
                    self.device = address
                    self.device_name = name
                    self.connected_device.emit(name, address)
                    self.status_update.emit(f"Connected to {name} [{address}]")
                else:
                    self.status_update.emit("Failed to connect.")
            except Exception as e:
                self.status_update.emit(f"Connection error: {str(e)}")
        self.loop.call_soon_threadsafe(asyncio.create_task, _connect())

    def disconnect(self):
        async def _disconnect():
            if self.client and self.client.is_connected:
                # Stop notifications if they were started
                if self.notify_started:
                    try:
                        await self.client.stop_notify(BLE_CHAR_UUID)
                        self.notify_started = False
                    except:
                        pass
                await self.client.disconnect()
                self.status_update.emit("Disconnected.")
                self.connected_device.emit("", "")
        self.loop.call_soon_threadsafe(asyncio.create_task, _disconnect())

    def send_ota(self, filepath):
        async def _send():
            if not self.client or not self.client.is_connected:
                self.status_update.emit("Not connected.")
                return

            path = Path(filepath)
            data = path.read_bytes()
            size = len(data)
            crc = zlib.crc32(data) & 0xFFFFFFFF

            ack_event = asyncio.Event()

            def handle_ack(_, value: bytearray):
                if value.decode().strip() == "ACK":
                    ack_event.set()
            
            await self.client.get_services()
            
            # Only start notifications if not already started
            if not self.notify_started:
                try:
                    await self.client.start_notify(BLE_CHAR_UUID, handle_ack)
                    self.notify_started = True
                    self.status_update.emit("Notifications started")
                    await asyncio.sleep(0.1)  # Allow time for setup
                except Exception as e:
                    self.status_update.emit(f"Failed to start notifications: {e}")
                    return
    
            # print("Notifications started, now sending OPEN")

            self.status_update.emit(f"Sending OPEN (size={size}, CRC={crc:#010X})")
            ack_event.clear()
            
            # print(f"Sending: OPEN,{size},{crc}")
            
            await self.client.write_gatt_char(BLE_CHAR_UUID, f"OPEN,{size},{crc}".encode(), response=True)

            try:
                await asyncio.wait_for(ack_event.wait(), timeout=2.0)  # wait for OPEN ACK
                self.status_update.emit("Received ACK for OPEN")
            except asyncio.TimeoutError:
                self.status_update.emit("No ACK for OPEN, aborting")
                await self.client.stop_notify(BLE_CHAR_UUID)
                return

            # Use the dynamic chunk size
            chunk_size = self.chunk_size
            total_chunks = (size + chunk_size - 1) // chunk_size  # Ceiling division
            
            # Now send chunks only after OPEN ACK received
            for i in range(0, size, chunk_size):
                chunk = data[i:i + chunk_size]
                chunk_num = i // chunk_size + 1
                percent = int((i + chunk_size) * 100 / size)

                ack_event.clear()
                await self.client.write_gatt_char(BLE_CHAR_UUID, chunk, response=True)

                try:
                    await asyncio.wait_for(ack_event.wait(), timeout=2.0)
                    self.status_update.emit(f"✅ Chunk {chunk_num}/{total_chunks} ({len(chunk)} bytes), {percent}%")
                except asyncio.TimeoutError:
                    self.status_update.emit(f"❌ No ACK for chunk {chunk_num}, retrying...")
                    # retry sending logic to be added here
                    # or break/abort

                await asyncio.sleep(self.chunk_delay)

            await self.client.write_gatt_char(BLE_CHAR_UUID, b"CLOSE")  # Send CLOSE command
            self.status_update.emit("Sending CLOSE command")
            
            if self.notify_started:
                await self.client.stop_notify(BLE_CHAR_UUID)
                self.notify_started = False
                
            self.status_update.emit("✅ OTA completed.")

        self.loop.call_soon_threadsafe(asyncio.create_task, _send())


class OTAGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLE OTA Updater GUI")
        self.resize(400, 650) 

        self.ble = BLEWorker()
        self.ble.start()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        layout = QVBoxLayout()

        self.device_list = QListWidget()
        self.scan_btn = QPushButton("Scan")
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)  # Initially disabled
        self.file_label = QLabel("No file selected.")
        self.file_info_label = QLabel("")
        self.select_btn = QPushButton("Select .bin File")
        self.send_btn = QPushButton("Start OTA Update")
        self.send_btn.setEnabled(False)  # Initially disabled until connected
        self.status_label = QLabel("Status: Idle")
        self.connected_label = QLabel("Connected to: None")
        
        # Add chunk size control
        chunk_size_layout = QHBoxLayout()
        chunk_size_layout.addWidget(QLabel("Chunk Size (bytes):"))
        self.chunk_size_spinbox = QSpinBox()
        self.chunk_size_spinbox.setRange(1, 1024)  # 1 to 1024 bytes
        self.chunk_size_spinbox.setValue(128)  # Default 128 bytes
        self.chunk_size_spinbox.setSuffix(" bytes")
        self.chunk_size_spinbox.valueChanged.connect(self.update_chunk_size)
        chunk_size_layout.addWidget(self.chunk_size_spinbox)
        chunk_size_layout.addStretch()  # Push everything to the left
        
        # Add delay control
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Chunk Delay (ms):"))
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 1000)  # 0 to 1000ms
        self.delay_spinbox.setValue(10)  # Default 10ms
        self.delay_spinbox.setSuffix(" ms")
        self.delay_spinbox.valueChanged.connect(self.update_chunk_delay)
        delay_layout.addWidget(self.delay_spinbox)
        delay_layout.addStretch()  # Push everything to the left
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setVisible(False)  # Hide initially

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)
        
        layout.addWidget(self.device_list)
        layout.addWidget(self.scan_btn)
        layout.addLayout(btn_layout)
        layout.addWidget(self.connected_label)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.file_label)
        layout.addWidget(self.file_info_label)
        layout.addLayout(chunk_size_layout)  # Add chunk size control
        layout.addLayout(delay_layout)  # Add delay control
        layout.addWidget(self.send_btn)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def update_chunk_size(self, value):
        """Update the chunk size when spinbox value changes"""
        self.ble.set_chunk_size(value)

    def update_chunk_delay(self, value):
        """Update the chunk delay when spinbox value changes"""
        self.ble.set_chunk_delay(value)

    def update_status(self, text):
        self.status_label.setText(f"Status: {text}")
        if "%" in text:
            # Extract the percentage number (assumes format like "Sent chunk X, 30%")
            import re
            match = re.search(r"(\d+)%", text)
            if match:
                percent = int(match.group(1))
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(percent)
        elif "✅ ota completed." in text.lower():
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
        else:
            # Hide or reset progress bar if no percentage info
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)

    def connect_signals(self):
        self.scan_btn.clicked.connect(self.ble.scan_devices)
        self.connect_btn.clicked.connect(self.connect_to_selected)
        self.disconnect_btn.clicked.connect(self.ble.disconnect)
        self.select_btn.clicked.connect(self.select_file)
        self.send_btn.clicked.connect(self.send_firmware)

        self.ble.status_update.connect(self.update_status)
        self.ble.devices_found.connect(self.populate_device_list)
        self.ble.connected_device.connect(self.update_connection_label)

    def populate_device_list(self, devices):
        self.device_list.clear()
        for dev in devices:
            self.device_list.addItem(f"{dev.name or 'Unknown'} [{dev.address}]")

    def connect_to_selected(self):
        item = self.device_list.currentItem()
        if item:
            text = item.text()
            # Extract name and address from "Name [Address]" format
            if "[" in text and "]" in text:
                name = text.split("[")[0].strip()
                address = text.split("[")[-1].replace("]", "")
                self.ble.connect_device(address, name)

    def update_connection_label(self, name, address):
        if name and address:
            # Connected
            self.connected_label.setText(f"Connected to: {name} [{address}]")
            self.disconnect_btn.setEnabled(True)  # Enable disconnect button
            self.connect_btn.setEnabled(False)    # Disable connect button
            self.send_btn.setEnabled(True)        # Enable OTA button
        else:
            # Disconnected
            self.connected_label.setText("Connected to: None")
            self.disconnect_btn.setEnabled(False) # Disable disconnect button
            self.connect_btn.setEnabled(True)     # Enable connect button
            self.send_btn.setEnabled(False)       # Disable OTA button

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select .bin File", "", "Binary Files (*.bin)")
        if file_path:
            self.file_label.setText(f"Selected: {file_path}")
            self.selected_file = file_path

            # Display size and CRC right under the selected file label
            data = Path(file_path).read_bytes()
            size = len(data)
            crc = zlib.crc32(data) & 0xFFFFFFFF
            self.file_info_label.setText(f"Size: {size} bytes, CRC32: {crc:#010X}")
        else:
            self.selected_file = None
            self.file_label.setText("No file selected.")
            self.file_info_label.setText("")

    def send_firmware(self):
        if not hasattr(self, "selected_file") or not self.selected_file:
            QMessageBox.warning(self, "Error", "Please select a .bin file first.")
            return
        self.ble.send_ota(self.selected_file)

    def closeEvent(self, event):
        self.ble.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OTAGUI()
    window.show()
    sys.exit(app.exec())
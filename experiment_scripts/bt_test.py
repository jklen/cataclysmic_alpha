import bluetooth
from bluetooth.ble import DiscoveryService

def scan_classic_bluetooth():
    print("Scanning for classic Bluetooth devices...")
    try:
        devices = bluetooth.discover_devices(duration=8, lookup_names=True, lookup_class=True)
        if devices:
            for addr, name, device_class in devices:
                print(f"Device: {name} | Address: {addr} | Class: {device_class}")
        else:
            print("No classic Bluetooth devices found.")
    except Exception as e:
        print(f"Error during classic Bluetooth scan: {e}")

def scan_ble_devices():
    print("Scanning for BLE (Bluetooth Low Energy) devices...")
    try:
        service = DiscoveryService()
        devices = service.discover(8)
        if devices:
            for addr, name in devices.items():
                print(f"Device: {name} | Address: {addr}")
        else:
            print("No BLE devices found.")
    except Exception as e:
        print(f"Error during BLE scan: {e}")

if __name__ == "__main__":
    print("Starting Bluetooth scan...\n")
    scan_classic_bluetooth()
    print("\nSwitching to BLE scan...\n")
    scan_ble_devices()

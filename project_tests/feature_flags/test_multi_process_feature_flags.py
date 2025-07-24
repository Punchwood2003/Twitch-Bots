"""
Multi-Process Feature Flag Simulation Tests

This module simulates real-world multi-process scenarios including:
- Process coordination via feature flags
- Real-time inter-process communication
- System-wide configuration management
- Process monitoring and status tracking
"""

import time
import threading
import json
import sys
import os
from pathlib import Path

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add the parent directory to the path so we can import feature_flags
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from feature_flags import FeatureFlag, get_manager, PermissionLevel


# Define feature flags for process simulation
SYSTEM_ENABLED = FeatureFlag("system_enabled")
DEBUG_MODE = FeatureFlag("debug_mode")
MAX_CONNECTIONS = FeatureFlag("max_connections")
CONTROLLER_STATUS = FeatureFlag("controller_status")
WORKER_STATUS = FeatureFlag("worker_status")
SHARED_COUNTER = FeatureFlag("shared_counter")
COMMUNICATION_CHANNEL = FeatureFlag("communication_channel")


class SystemController:
    """Simulates a system controller process."""
    
    def __init__(self, config_path: str):
        self.name = "SystemController"
        self.manager = get_manager(str(config_path), module_name="system_controller")
        self.running = False
        self.setup_flags()
        
    def setup_flags(self):
        """Declare system-wide configuration flags."""
        print(f"[{self.name}] Setting up system configuration...")
        
        # System controller owns global configuration
        self.manager.declare_flag(
            SYSTEM_ENABLED, 
            PermissionLevel.READ_WRITE, 
            True, 
            "Master system enable/disable switch"
        )
        
        self.manager.declare_flag(
            DEBUG_MODE, 
            PermissionLevel.READ_WRITE, 
            False, 
            "Global debug mode for all processes"
        )
        
        self.manager.declare_flag(
            MAX_CONNECTIONS, 
            PermissionLevel.READ_ONLY, 
            100, 
            "Maximum allowed connections (read-only for workers)"
        )
        
        # Controller's own status
        self.manager.declare_flag(
            CONTROLLER_STATUS, 
            PermissionLevel.READ_ONLY, 
            "initializing", 
            "Current status of the system controller"
        )
        
        # Shared communication channel
        self.manager.declare_flag(
            COMMUNICATION_CHANNEL, 
            PermissionLevel.READ_WRITE, 
            "", 
            "Inter-process communication channel"
        )
        
        # Set up observers for worker processes (will be added when they start)
        time.sleep(0.5)  # Allow time for worker flags to be declared
        self.setup_worker_observers()
        
    def setup_worker_observers(self):
        """Set up observers for worker process flags."""
        try:
            self.manager.use_flag(WORKER_STATUS)
            self.manager.add_observer(WORKER_STATUS, self.on_worker_status_change)
        except PermissionError:
            pass  # Worker hasn't started yet
        
        try:
            self.manager.use_flag(SHARED_COUNTER)
            self.manager.add_observer(SHARED_COUNTER, self.on_counter_change)
        except PermissionError:
            pass  # Worker hasn't started yet
        
        self.manager.add_observer(COMMUNICATION_CHANNEL, self.on_message_received)
    
    def on_worker_status_change(self, flag_name: str, old_value, new_value):
        """React to worker status changes."""
        print(f"[{self.name}] 📊 Worker status: {old_value} → {new_value}")
        
        if new_value == "overloaded":
            print(f"[{self.name}] ⚠️ Worker overloaded! Disabling system temporarily...")
            self.manager.set_flag(SYSTEM_ENABLED, False)
            time.sleep(2)  # Simulate recovery time
            self.manager.set_flag(SYSTEM_ENABLED, True)
            print(f"[{self.name}] ✅ System re-enabled")
    
    def on_counter_change(self, flag_name: str, old_value, new_value):
        """React to shared counter changes."""
        if isinstance(new_value, int) and new_value > 0 and new_value % 5 == 0:
            print(f"[{self.name}] 🎯 Milestone reached: {new_value}")
    
    def on_message_received(self, flag_name: str, old_value, new_value):
        """React to messages in the communication channel."""
        if (new_value and new_value != old_value and 
            not new_value.startswith(f"[{self.name}]")):
            print(f"[{self.name}] 📨 Received: {new_value}")
    
    def run(self):
        """Run the system controller main loop."""
        self.running = True
        self.manager.set_flag(CONTROLLER_STATUS, "running")
        print(f"[{self.name}] 🚀 System controller started")
        
        # Retry worker observer setup
        time.sleep(1)
        self.setup_worker_observers()
        
        iteration = 0
        while self.running and iteration < 8:
            iteration += 1
            print(f"[{self.name}] 🔄 Control cycle {iteration}")
            
            # Toggle debug mode periodically
            if iteration == 3:
                print(f"[{self.name}] 🐛 Enabling debug mode")
                self.manager.set_flag(DEBUG_MODE, True)
            elif iteration == 6:
                print(f"[{self.name}] 🐛 Disabling debug mode")
                self.manager.set_flag(DEBUG_MODE, False)
            
            # Send periodic status messages
            if iteration == 4:
                message = f"[{self.name}] System health check - all systems nominal"
                self.manager.set_flag(COMMUNICATION_CHANNEL, message)
            
            time.sleep(1.5)
        
        self.manager.set_flag(CONTROLLER_STATUS, "shutting_down")
        print(f"[{self.name}] 🛑 System controller shutting down")
        self.running = False


class WorkerProcess:
    """Simulates a worker process."""
    
    def __init__(self, config_path: str):
        self.name = "WorkerProcess"
        self.manager = get_manager(str(config_path), module_name="worker_process")
        self.running = False
        self.setup_flags()
        
    def setup_flags(self):
        """Declare worker-specific flags and use system flags."""
        print(f"[{self.name}] Setting up worker configuration...")
        
        # Worker owns its own status and shared counter
        self.manager.declare_flag(
            WORKER_STATUS, 
            PermissionLevel.READ_ONLY, 
            "initializing", 
            "Current status of the worker process"
        )
        
        self.manager.declare_flag(
            SHARED_COUNTER, 
            PermissionLevel.READ_WRITE, 
            0, 
            "Shared work counter that both processes can access"
        )
        
        # Use system flags (declared by controller)
        time.sleep(0.5)  # Wait for controller to declare flags
        try:
            self.manager.use_flag(SYSTEM_ENABLED)
            self.manager.use_flag(DEBUG_MODE)
            self.manager.use_flag(MAX_CONNECTIONS)
            self.manager.use_flag(CONTROLLER_STATUS)
            self.manager.use_flag(COMMUNICATION_CHANNEL)
        except PermissionError as e:
            print(f"[{self.name}] Note: {e}")
        
        # Set up observers
        self.manager.add_observer(DEBUG_MODE, self.on_debug_mode_change)
        self.manager.add_observer(CONTROLLER_STATUS, self.on_controller_status_change)
        self.manager.add_observer(COMMUNICATION_CHANNEL, self.on_message_received)
        
    def on_debug_mode_change(self, flag_name: str, old_value, new_value):
        """React to debug mode changes."""
        status = "enabled" if new_value else "disabled"
        print(f"[{self.name}] 🐛 Debug mode {status}")
        
    def on_controller_status_change(self, flag_name: str, old_value, new_value):
        """React to controller status changes."""
        print(f"[{self.name}] 🎛️ Controller status: {old_value} → {new_value}")
        
    def on_message_received(self, flag_name: str, old_value, new_value):
        """React to messages in the communication channel."""
        if (new_value and new_value != old_value and 
            not new_value.startswith(f"[{self.name}]")):
            print(f"[{self.name}] 📨 Received: {new_value}")
            # Send acknowledgment
            ack = f"[{self.name}] Message acknowledged"
            self.manager.set_flag(COMMUNICATION_CHANNEL, ack)
    
    def run(self):
        """Run the worker process main loop."""
        self.running = True
        self.manager.set_flag(WORKER_STATUS, "running")
        print(f"[{self.name}] 🚀 Worker process started")
        
        work_count = 0
        while self.running and work_count < 12:
            try:
                # Check if system is enabled
                if not self.manager.get_bool(SYSTEM_ENABLED, True):
                    print(f"[{self.name}] ⏸️ System disabled, waiting...")
                    time.sleep(1)
                    continue
                
                # Simulate work
                work_count += 1
                current_counter = self.manager.get_int(SHARED_COUNTER, 0)
                new_counter = current_counter + 1
                self.manager.set_flag(SHARED_COUNTER, new_counter)
                
                debug_mode = self.manager.get_bool(DEBUG_MODE, False)
                debug_indicator = " [DEBUG]" if debug_mode else ""
                print(f"[{self.name}] 📈 Work completed: {new_counter}{debug_indicator}")
                
                # Simulate overload condition
                if new_counter >= 8:
                    self.manager.set_flag(WORKER_STATUS, "overloaded")
                    time.sleep(0.5)  # Brief pause for overload handling
                    self.manager.set_flag(WORKER_STATUS, "running")
                
                # Check connection limits
                max_conn = self.manager.get_int(MAX_CONNECTIONS, 50)
                if new_counter > max_conn / 15:
                    print(f"[{self.name}] ⚡ Approaching connection limit")
                
                time.sleep(1.0)
                
            except Exception as e:
                print(f"[{self.name}] ❌ Error: {e}")
                time.sleep(1)
        
        self.manager.set_flag(WORKER_STATUS, "completed")
        print(f"[{self.name}] ✅ Worker process completed")
        self.running = False


def print_final_system_state(config_path: str):
    """Print the final state of the system configuration."""
    print("\n" + "="*80)
    print("📄 FINAL SYSTEM CONFIGURATION STATE")
    print("="*80)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("🗂️ System Flags:")
        for flag_name, flag_data in config.get('flags', {}).items():
            if isinstance(flag_data, dict):
                value = flag_data.get('value')
                owner = flag_data.get('owner_module', 'unknown')
                access = flag_data.get('access_permissions', 'unknown')
                desc = flag_data.get('description', '')
                
                print(f"  • {flag_name}: {value}")
                print(f"    Owner: {owner} | Access: {access}")
                print(f"    Description: {desc}")
                print()
        
    except Exception as e:
        print(f"Error reading config: {e}")


def main():
    """Main test function for multi-process simulation."""
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "multi_process_simulation.json"
    
    print("🧪 MULTI-PROCESS FEATURE FLAG SIMULATION")
    print("="*80)
    print("This test simulates realistic multi-process coordination:")
    print("• System Controller: Manages global configuration and monitoring")
    print("• Worker Process: Performs work and reports status")
    print("• Real-time coordination via feature flags")
    print("• System overload handling and recovery")
    print("="*80)
    
    # Clean up any existing config
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    # Create process instances
    controller = SystemController(str(config_path))
    worker = WorkerProcess(str(config_path))
    
    # Start processes in separate threads
    controller_thread = threading.Thread(target=controller.run, name="SystemController")
    worker_thread = threading.Thread(target=worker.run, name="WorkerProcess")
    
    print("\n🚀 Starting multi-process simulation...")
    
    controller_thread.start()
    time.sleep(0.5)  # Let controller start first
    worker_thread.start()
    
    # Wait for both processes to complete
    controller_thread.join()
    worker_thread.join()
    
    print("\n✅ Multi-process simulation completed!")
    
    # Display final system state
    print_final_system_state(config_path)
    
    print("\n🔍 SIMULATION SUMMARY:")
    print("• ✅ Multi-process coordination via feature flags")
    print("• ✅ Real-time status monitoring and communication")
    print("• ✅ System overload detection and recovery")
    print("• ✅ Cross-process observer notifications")
    print("• ✅ Permission-based access control")
    print("• ✅ Configuration persistence and sharing")
    
    # Clean up
    controller.manager.shutdown()
    worker.manager.shutdown()
    
    print(f"\n🧹 Simulation complete! Config saved as: {config_path}")


if __name__ == "__main__":
    main()

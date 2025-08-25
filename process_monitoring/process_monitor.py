"""
Process monitoring module for tracking and cleaning up threads and processes.

This module provides comprehensive monitoring and cleanup capabilities for
threads and child processes to ensure clean shutdown without orphaned resources.
"""

import logging
import psutil
import threading
import time


# Set up logger for this module
logger = logging.getLogger(__name__)


class ProcessMonitor:
    """Monitor and manage processes and threads for graceful shutdown."""
    
    def __init__(self):
        self.current_process = psutil.Process()
        self.initial_threads = None
        self.initial_processes = None
        self.child_processes = set()
        self.monitored_threads = set()
        
        # Capture initial state immediately upon creation
        self.capture_initial_state()
        
    def capture_initial_state(self):
        """Capture initial process and thread state."""
        try:
            self.initial_threads = set(thread.ident for thread in threading.enumerate())
            logger.debug(f"Initial thread count: {len(self.initial_threads)}")
            
            # Track any existing child processes
            self.initial_processes = set()
            for child in self.current_process.children(recursive=True):
                self.child_processes.add(child.pid)
                self.initial_processes.add(child.pid)
                logger.debug(f"Found existing child process: {child.pid} ({child.name()})")
                
        except Exception as e:
            logger.warning(f"Error capturing initial state: {e}")
            # Ensure attributes are initialized even on error
            if self.initial_threads is None:
                self.initial_threads = set()
            if self.initial_processes is None:
                self.initial_processes = set()
    
    def track_new_threads(self):
        """Track any new threads that have been created."""
        try:
            if self.initial_threads is None:
                logger.warning("Initial threads not captured, cannot track new threads")
                return
                
            current_threads = set(thread.ident for thread in threading.enumerate())
            new_threads = current_threads - self.initial_threads
            
            if new_threads:
                self.monitored_threads.update(new_threads)
                logger.debug(f"Tracking {len(new_threads)} new threads")
                
        except Exception as e:
            logger.warning(f"Error tracking threads: {e}")
    
    def track_child_processes(self):
        """Track any new child processes."""
        try:
            current_children = set()
            for child in self.current_process.children(recursive=True):
                current_children.add(child.pid)
                if child.pid not in self.child_processes:
                    logger.info(f"New child process detected: {child.pid} ({child.name()})")
                    self.child_processes.add(child.pid)
                    
        except Exception as e:
            logger.warning(f"Error tracking child processes: {e}")
    
    def cleanup_all(self):
        """Perform comprehensive cleanup of all tracked resources."""
        logger.info("Starting comprehensive process cleanup...")
        
        # Track final state before cleanup
        self._log_final_state()
        
        # Terminate child processes
        self._cleanup_child_processes()
        
        # Clean up threads
        self._cleanup_threads()
        
        # Final verification
        self._verify_cleanup()
        
        logger.info("Process cleanup completed")
    
    def _log_final_state(self):
        """Log the final state of processes and threads."""
        try:
            current_threads = threading.enumerate()
            active_children = list(self.current_process.children(recursive=True))
            
            logger.info(f"Pre-cleanup state:")
            logger.info(f"  - Active threads: {len(current_threads)}")
            logger.info(f"  - Child processes: {len(active_children)}")
            
            # Log thread details
            for thread in current_threads:
                if thread.ident in self.monitored_threads:
                    logger.debug(f"  - Monitored thread: {thread.name} (ID: {thread.ident})")
                    
            # Log child process details
            for child in active_children:
                logger.debug(f"  - Child process: {child.pid} ({child.name()})")
                
        except Exception as e:
            logger.warning(f"Error logging final state: {e}")
    
    def _cleanup_child_processes(self):
        """Terminate child processes gracefully."""
        try:
            children = list(self.current_process.children(recursive=True))
            
            if not children:
                logger.debug("No child processes to clean up")
                return
                
            logger.info(f"Terminating {len(children)} child processes...")
            
            # Send SIGTERM to all children
            for child in children:
                try:
                    logger.debug(f"Terminating child process: {child.pid}")
                    child.terminate()
                except psutil.NoSuchProcess:
                    logger.debug(f"Child process {child.pid} already terminated")
                except Exception as e:
                    logger.warning(f"Error terminating child {child.pid}: {e}")
            
            # Wait for graceful termination
            try:
                _, still_alive = psutil.wait_procs(children, timeout=3)
                
                # Force kill any remaining processes
                if still_alive:
                    logger.warning(f"Force killing {len(still_alive)} unresponsive child processes...")
                    for child in still_alive:
                        try:
                            child.kill()
                            logger.debug(f"Force killed child process: {child.pid}")
                        except Exception as e:
                            logger.warning(f"Error force killing child {child.pid}: {e}")
                            
            except Exception as e:
                logger.warning(f"Error waiting for child processes: {e}")
                
        except Exception as e:
            logger.error(f"Error during child process cleanup: {e}")
    
    def _cleanup_threads(self):
        """Clean up monitored threads."""
        try:
            current_threads = threading.enumerate()
            main_thread = threading.main_thread()
            
            # Count non-main threads
            active_threads = [t for t in current_threads if t != main_thread and t.is_alive()]
            
            if not active_threads:
                logger.debug("No additional threads to clean up")
                return
                
            logger.info(f"Waiting for {len(active_threads)} threads to complete...")
            
            # Log thread details
            for thread in active_threads:
                if hasattr(thread, '_target') and thread._target:
                    target_name = getattr(thread._target, '__name__', str(thread._target))
                    logger.debug(f"  - Thread: {thread.name} (target: {target_name})")
                else:
                    logger.debug(f"  - Thread: {thread.name}")
            
            # Wait for threads with timeout
            timeout = 5.0
            start_time = time.time()
            
            while True:
                current_threads = [t for t in threading.enumerate() 
                                 if t != main_thread and t.is_alive()]
                
                if not current_threads:
                    logger.debug("All threads completed successfully")
                    break
                    
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Timeout waiting for {len(current_threads)} threads to complete")
                    for thread in current_threads:
                        logger.warning(f"  - Unresponsive thread: {thread.name}")
                    break
                    
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error during thread cleanup: {e}")
    
    def _verify_cleanup(self):
        """Verify that cleanup was successful."""
        try:
            current_threads = threading.enumerate()
            main_thread = threading.main_thread()
            remaining_threads = [t for t in current_threads if t != main_thread and t.is_alive()]
            
            remaining_children = list(self.current_process.children(recursive=True))
            
            logger.info("Cleanup verification:")
            logger.info(f"  - Remaining threads: {len(remaining_threads)}")
            logger.info(f"  - Remaining child processes: {len(remaining_children)}")
            
            if remaining_threads:
                logger.warning("Some threads are still active:")
                for thread in remaining_threads:
                    logger.warning(f"  - {thread.name} (daemon: {thread.daemon})")
            
            if remaining_children:
                logger.warning("Some child processes are still active:")
                for child in remaining_children:
                    try:
                        logger.warning(f"  - PID {child.pid}: {child.name()}")
                    except Exception:
                        logger.warning(f"  - PID {child.pid}: <process info unavailable>")
                        
        except Exception as e:
            logger.warning(f"Error during cleanup verification: {e}")

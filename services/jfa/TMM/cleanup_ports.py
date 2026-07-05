#!/usr/bin/env python3
"""
Script to clean up processes using port 8001 (for ARM module tests).
"""

import subprocess
import sys
import os

def cleanup_port(port=8001):
    """Kill any process using the specified port."""
    try:
        if sys.platform.startswith('win'):
            # Windows
            cmd = f'netstat -ano | findstr :{port}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                subprocess.run(f'taskkill /PID {pid} /F', shell=True)
                                print(f"✅ Killed process {pid} using port {port}")
                            except:
                                pass
        else:
            # Linux/Mac
            cmd = f'lsof -ti:{port}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(f'kill -9 {pid}', shell=True)
                            print(f"✅ Killed process {pid} using port {port}")
                        except:
                            pass
        
        print(f"✅ Port {port} cleanup completed")
        
    except Exception as e:
        print(f"⚠️  Port cleanup warning: {e}")

if __name__ == "__main__":
    cleanup_port(8001)
    cleanup_port(11491)  # Also clean up CCU port 
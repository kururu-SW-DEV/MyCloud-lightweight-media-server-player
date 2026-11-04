import os
import sys
import paramiko

HOST = os.environ.get("NAS_HOST", "192.168.0.7")
PORT = int(os.environ.get("NAS_PORT", "22"))
USERNAME = os.environ.get("NAS_USERNAME", "root")
PASSWORD = os.environ.get("NAS_PASSWORD", "1q2w3e4r")

def get_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # WD My Cloud uses OpenSSH 6.0p1 (legacy ssh-rsa host key)
    client.connect(
        hostname=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']},
        timeout=5,
        auth_timeout=5,
        banner_timeout=5
    )
    return client

def run_command(cmd):
    client = get_ssh_client()
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        code = stdout.channel.recv_exit_status()
        return code, out, err
    finally:
        client.close()

def main():
    print(f"Connecting to {HOST}:{PORT} as {USERNAME}...")
    try:
        test_commands = [
            "uname -a",
            "uptime",
            "df -h",
            "cat /etc/debian_version"
        ]
        for cmd in test_commands:
            print(f"\n$ {cmd}")
            code, out, err = run_command(cmd)
            if out:
                print(out)
            if err:
                print(f"[STDERR] {err}")
            print(f"(Exit code: {code})")
            
        print("\nAll commands executed successfully!")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        code, out, err = run_command(cmd)
        if out:
            sys.stdout.buffer.write(out.encode('utf-8', errors='replace'))
            sys.stdout.buffer.write(b'\n')
        if err:
            sys.stderr.buffer.write(err.encode('utf-8', errors='replace'))
            sys.stderr.buffer.write(b'\n')
        sys.exit(code)
    else:
        main()

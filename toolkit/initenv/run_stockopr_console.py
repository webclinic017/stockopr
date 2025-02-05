import os
import subprocess

if __name__ == "__main__":
    # root_dir = r'D:\workspace\stockopr'
    # py = str(os.path.join(root_dir, 'venv', 'Scripts', 'python.exe'))
    root_dir = os.getenv('HOME') + '/workspace/stockopr'
    py = str(os.path.join(root_dir, 'venv', 'bin', 'python'))

    script = 'console.py'
    script_path = os.path.join(root_dir, script)
    print(py, script_path)
    print(os.path.exists(py), os.path.exists(script_path))

    os.environ['PYTHONPATH'] = root_dir
    # subprocess.Popen([py, script_path], creationflags=subprocess.DETACHED_PROCESS, cwd=root_dir)
    subprocess.Popen([py, script_path], cwd=root_dir)

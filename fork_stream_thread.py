def fork_stream_thread(tree, shot, path, timeout):
    from MDSplus import Tree
    import os
    import subprocess
    print("fork_stream_thread")
    script = f"{os.path.realpath(os.path.dirname(__file__))}/stream-basler.sh"
    proc = subprocess.run([script, tree, str(shot), path], capture_output=True, text=True, timeout=timeout)
    t = Tree(tree,shot)
    d = t.getNode(path)
    d.STDOUT.record = proc.stdout
    d.STDERR.record = proc.stderr
    if proc.returncode != 0:
        raise Exception(f"Failed to fork stream: {proc.stderr}")
    print("thread done")


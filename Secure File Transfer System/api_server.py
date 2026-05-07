"""
api_server.py - Flask API backend for the Secure File Transfer GUI
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty
from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename
import sys

sys.path.insert(0, str(Path(__file__).parent))

from crypto_utils import get_logger

BASE_DIR = Path(__file__).parent

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1 GB
UPLOAD_FOLDER = BASE_DIR / 'temp_uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

log = get_logger("API")

# Global state
server_process = None
server_running = False
logs_queue = Queue(maxsize=2000)
history = []
benchmark_results = []
lock = threading.Lock()


#  Logging 
def broadcast_log(level, msg):
    log_entry = {
        'ts': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'msg': msg
    }
    try:
        logs_queue.put_nowait(log_entry)
    except Exception:
        pass


#  Server Control 
@app.route('/api/server/start', methods=['POST'])
def start_server():
    global server_process, server_running

    with lock:
        # Check if process is still alive before reporting "already running"
        if server_process and server_process.poll() is None:
            return jsonify({'ok': False, 'error': 'Server already running'}), 400
        # Process died without us knowing — reset flag
        if server_process and server_process.poll() is not None:
            server_process = None
            server_running = False

        try:
            server_path = BASE_DIR / 'server.py'
            server_process = subprocess.Popen(
                [sys.executable, str(server_path), '--port', '9999'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # merge stderr into stdout
                text=True,
                bufsize=1
            )
            server_running = True
            broadcast_log('OK', 'Server started on 127.0.0.1:9999')
            log.info('Server process started (PID: %d)', server_process.pid)

            threading.Thread(target=_monitor_server_output, daemon=True).start()
            threading.Thread(target=_watch_server_exit, daemon=True).start()

            return jsonify({'ok': True})
        except Exception as e:
            broadcast_log('ERROR', f'Failed to start server: {e}')
            return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/server/stop', methods=['POST'])
def stop_server():
    global server_process, server_running

    with lock:
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                broadcast_log('OK', 'Server stopped')
                log.info('Server process terminated')
            except subprocess.TimeoutExpired:
                server_process.kill()
                broadcast_log('WARN', 'Server force-killed')
            except Exception as e:
                log.warning('Error stopping server: %s', e)
            finally:
                server_process = None
                server_running = False

    return jsonify({'ok': True})


def _monitor_server_output():
    """Forward server stdout to the log broadcast queue."""
    global server_process
    proc = server_process
    if not proc:
        return
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            level = 'ERROR' if '[ERROR]' in line else ('WARN' if '[WARN]' in line else 'INFO')
            broadcast_log(level, line)
    except Exception:
        pass


def _watch_server_exit():
    """Detect when the server process dies unexpectedly and update state."""
    global server_process, server_running
    proc = server_process
    if not proc:
        return
    proc.wait()
    with lock:
        if server_process is proc:  # still the same process we started
            server_running = False
            server_process = None
    broadcast_log('WARN', 'Server process exited')


#  File Transfer 
@app.route('/api/send', methods=['POST'])
def send_file_route():
    file_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        host = request.form.get('host', '127.0.0.1')
        port = int(request.form.get('port', 9999))

        if not file or file.filename == '':
            return jsonify({'ok': False, 'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        file_path = UPLOAD_FOLDER / filename
        file.save(str(file_path))

        broadcast_log('INFO', f'Sending {filename} to {host}:{port}')
        client_path = BASE_DIR / 'client.py'

        start_time = time.time()
        result = subprocess.run(
            [sys.executable, str(client_path),
             '--file', str(file_path),
             '--host', host,
             '--port', str(port)],
            capture_output=True,
            text=True,
            timeout=300
        )
        elapsed = time.time() - start_time

        if result.returncode == 0:
            file_size = file_path.stat().st_size
            throughput = (file_size / 1024 / 1024) / elapsed if elapsed > 0 else 0

            with lock:
                history.append({
                    'filename': filename,
                    'size': file_size,
                    'time': f'{elapsed:.3f}',
                    'throughput': f'{throughput:.2f}',
                    'direction': 'sent',
                    'integrity': True,
                    'hash': 'N/A',
                    'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            broadcast_log('OK', f'File transferred successfully ({throughput:.2f} MB/s)')
            return jsonify({'ok': True})
        else:
            err = (result.stderr or result.stdout or 'Unknown error').strip()
            broadcast_log('ERROR', f'Transfer failed: {err}')
            return jsonify({'ok': False, 'error': err}), 500

    except Exception as e:
        broadcast_log('ERROR', str(e))
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass


#  Key Generation 
@app.route('/api/keygen', methods=['POST'])
def keygen():
    try:
        from crypto_utils import generate_rsa_keypair
        broadcast_log('INFO', 'Regenerating RSA-2048 keypair…')
        generate_rsa_keypair(save=True, force=True)
        broadcast_log('OK', 'RSA keypair regenerated successfully')
        return jsonify({'ok': True})
    except Exception as e:
        broadcast_log('ERROR', f'Keygen failed: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500


#  Benchmarks 
@app.route('/api/benchmark', methods=['POST'])
def run_benchmark():
    def benchmark_worker():
        try:
            broadcast_log('INFO', 'Starting benchmark…')
            bench_path = BASE_DIR / 'benchmark.py'

            # Run benchmark with a separate Python process.
            # IMPORTANT: redirect stderr to DEVNULL so only JSON reaches stdout.
            result = subprocess.run(
                [sys.executable, str(bench_path), '--json'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,   # suppress log lines from stdout
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                raw = result.stdout.strip()
                # Strip any accidental log prefix lines (safety net)
                # Find the first '[' to locate the JSON array
                idx = raw.find('[')
                if idx != -1:
                    raw = raw[idx:]
                try:
                    results = json.loads(raw)
                    with lock:
                        benchmark_results.clear()
                        benchmark_results.extend(results)
                    broadcast_log('OK', 'Benchmark completed')
                except json.JSONDecodeError as e:
                    broadcast_log('ERROR', f'Could not parse benchmark output: {e}')
                    broadcast_log('ERROR', f'Raw output: {raw[:200]}')
            else:
                broadcast_log('ERROR', f'Benchmark process failed (exit {result.returncode})')
        except subprocess.TimeoutExpired:
            broadcast_log('ERROR', 'Benchmark timed out')
        except Exception as e:
            broadcast_log('ERROR', f'Benchmark error: {e}')

    threading.Thread(target=benchmark_worker, daemon=True).start()
    return jsonify({'ok': True})


@app.route('/api/benchmark/results', methods=['GET'])
def get_benchmark_results():
    with lock:
        return jsonify(list(benchmark_results))


#  Status & History 
@app.route('/api/status', methods=['GET'])
def get_status():
    global server_running, server_process
    with lock:
        # Sync flag with actual process state
        if server_process and server_process.poll() is not None:
            server_running = False
            server_process = None
        return jsonify({
            'server_running': server_running,
            'timestamp': datetime.now().isoformat()
        })


@app.route('/api/history', methods=['GET'])
def get_history():
    with lock:
        return jsonify(list(history))


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    with lock:
        history.clear()
    broadcast_log('INFO', 'History cleared')
    return jsonify({'ok': True})


#  Log Streaming (SSE) 
@app.route('/api/logs/stream', methods=['GET'])
def stream_logs():
    def generate():
        # Send a startup ping immediately so the browser knows the connection works
        yield f'data: {json.dumps({"ping": True})}\n\n'
        while True:
            try:
                log_entry = logs_queue.get(timeout=15)
                yield f'data: {json.dumps(log_entry)}\n\n'
            except Empty:
                # Keepalive every 15 s — much less noise than every 1 s
                yield f'data: {json.dumps({"ping": True})}\n\n'

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


# Health 
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'version': '1.1'})


# Serve GUI 
@app.route('/', methods=['GET'])
def serve_gui():
    gui_path = BASE_DIR / 'gui.html'
    if gui_path.exists():
        html_content = gui_path.read_text(encoding='utf-8')
        return Response(html_content, mimetype='text/html; charset=utf-8')
    return 'GUI not found — place gui.html next to api_server.py', 404
        

#  Startup 
if __name__ == '__main__':
    log.info('Starting Flask API server on http://localhost:5000')
    broadcast_log('INFO', 'API server started')
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        log.info('API server shutting down')
        # Cleanly kill child server if running
        with lock:
            if server_process:
                try:
                    server_process.terminate()
                    server_process.wait(timeout=3)
                except Exception:
                    server_process.kill()
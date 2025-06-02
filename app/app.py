from compiler import Compiler
from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

@app.route('/runCompile', methods = ['POST'])
def run_compile():
    data = request.get_json()
    program = data.get('program', '')
    
    if not program:
        return jsonify({'error' : 'No program provided'}), 400
    
    # make temporary directory for file
    os.makedirs("/tmp/sandbox", exist_ok=True)
    
    try:
        # run the compiler in strict mode so it raises an exception if there is an error
        compiler = Compiler(program, strictMode=True)
        compiler.compile('/tmp/sandbox/output.s')
        
    except Exception as e:
        return jsonify({'error' : 'Error compiling', 'message' : str(e)}), 400
    
    # run the compiled file through a mips emulator in the terminal
    result = subprocess.run(
        ["spim", "-file", "/tmp/sandbox/output.s"],
        capture_output=True,
        timeout=15
    )
    
    # if there was an error running the compiled file
    if result.stderr:
        return jsonify({'error' : 'Error running compiled file', 'message' : result.stderr.decode()}), 500
    
    # return all program outputs as a list, except for first (spim output) and last (empty string after last new line)
    output = result.stdout.decode()
    return jsonify({'ouptuts' : output.split('\n')[1:-1]}), 200

if __name__ == '__main__':
	app.run(host='127.0.0.1', port=8000, debug=True)
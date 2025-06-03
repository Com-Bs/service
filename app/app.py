from compiler import Compiler
from flask import Flask, request, jsonify
import subprocess
import os
import shutil
import tempfile
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv('PORT', 3001))
TIMEOUT = int(os.getenv('TIMEOUT', 10))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World! This is the MIPS Compiler API."

"""
This endpoint compiles a C- program into MIPS assembly code and runs it using the SPIM emulator.
It expects a JSON payload with the following structure:
{
    "program": "C- program as a string",
    "inputs": ["input1", "input2", ...]  # optional, inputs to be passed to the program
}

If the number of inputs is not what the program expects, it will default the missing inputs to 0.
"""
@app.route('/runCompile', methods = ['POST'])
def run_compile():
    data = request.get_json()
    program = data.get('program', '')
    inputs = data.get('inputs', [])
    
    if not program:
        return jsonify({'error' : 'No program provided'}), 400
    
    # make temporary directory for file 
    sandbox_dir = tempfile.mkdtemp(prefix="sandbox_", dir="/tmp")
    
    # compile the program 
    try:
        try:
            # run the compiler in strict mode so it raises an exception if there is an error
            compiler = Compiler(program, strictMode=True)
            compiler.compile(f'{sandbox_dir}/output.s')
            
        except Exception as e:
            return jsonify({'error' : 'Error compiling', 'message' : str(e)}), 400
            
        # run the compiled file through a mips emulator in the terminal
        input_data = '\n'.join(inputs) + '\n'  # join inputs with new lines
        try:
            result = subprocess.run(
                [
                    "bwrap", # creates an unprivileged sandbox environment
                    # mount the necessary directories in the sandbox
                    "--ro-bind", "/usr", "/usr",
                    "--ro-bind", "/lib", "/lib",
                    "--dev", "/dev", # create a dev directory in the sandbox (spim needs it)
                    # bind the sandbox directory to the /tmp/sandbox directory in the sandbox
                    "--bind", sandbox_dir, sandbox_dir, 
                    "--unshare-all", # unshare all namespaces to create an isolated environment
                    "--die-with-parent", # die when the parent process dies
                    "--new-session", # makes it harder for the sandbox process to interfere with the host system
                    "spim", "-file", f"{sandbox_dir}/output.s"
                ],
                input=input_data.encode(),
                capture_output=True,
                timeout=TIMEOUT
            )
        except subprocess.TimeoutExpired:
            return jsonify({'error' : 'Timeout expired while running the compiled file'}), 408
        except Exception as e:
            return jsonify({'error' : 'Error running compiled file', 'message' : str(e)}), 500
        
        # if there was an error running the compiled file
        if result.stderr:
            return jsonify({'error' : 'Error running compiled file', 'message' : result.stderr.decode()}), 500
        
        # return all program outputs as a list, except for first (spim output) and last (empty string after last new line)
        output = result.stdout.decode()
        
        # in different environments, the output is different, but what follows 'Loaded' is the actual output
        output = output[output.find('Loaded'):]  
        return jsonify({'outputs' : output.split('\n')[1:-1]}), 200
    finally:
        # clean up the sandbox directory, including files
        shutil.rmtree(sandbox_dir, ignore_errors=True)

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
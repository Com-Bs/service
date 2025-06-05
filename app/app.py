from compiler import Compiler
from compiler.parser import Parser
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
WHITELIST = os.getenv('WHITELIST', '0.0.0.0').split(',')

app = Flask(__name__)

@app.before_request
def limit_remote_addr():
    if "0.0.0.0" in WHITELIST:
        return
    
    if request.remote_addr not in WHITELIST:
        return jsonify({'error': 'Access denied'}), 403

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
@app.route('/runCompile', methods=['POST'])
def run_compile():
    data = request.get_json()
    program = data.get('program', '')
    inputs = data.get('inputs', [])
    
    if not program:
        return jsonify({'error': 'No program provided'}), 400
        
    # Limit number of inputs
    if len(inputs) > 100:
        return jsonify({'error': 'Too many inputs provided'}), 400
    
    # Validate each input
    for i, inp in enumerate(inputs):
        if len(str(inp)) > 1000:
            return jsonify({'error': f'Input {i} is too long'}), 400
    
    # make temporary directory for file 
    sandbox_dir = tempfile.mkdtemp(prefix="sandbox_", dir="/tmp")
    
    # compile the program 
    try:
        try:
            # run the compiler in strict mode so it raises an exception if there is an error
            compiler = Compiler(program, strictMode=True)
            compiler.compile(f'{sandbox_dir}/output.s')
            
        except Exception as e:
            return jsonify({'error': 'Error compiling', 'message': str(e)}), 400
            
        # run the compiled file through a mips emulator in a sandbox
        input_data = '\n'.join(str(inp) for inp in inputs) + '\n'
        try:
            # Create a more restricted sandbox with specific directory bindings
            commands = [
                "bwrap",
                # Bind all necessary system directories
                "--ro-bind", "/bin", "/bin",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib"
            ]
            
            # prod env needs /lib64, but not in debug mode
            if not DEBUG:
                print("Binding /lib64")
                commands.extend(["--ro-bind", "/lib64", "/lib64"])
            
            commands += [
                "--ro-bind", "/etc", "/etc",
                # Create necessary system directories  
                "--tmpfs", "/tmp",
                "--ro-bind", "/proc", "/proc",
                "--ro-bind", "/dev", "/dev",
                # Bind our sandbox directory
                "--bind", sandbox_dir, sandbox_dir,
                # Security options - only IPC and UTS, no network or user/pid
                "--unshare-ipc", 
                "--unshare-uts",
                "--die-with-parent",
                "--new-session",
                # The actual command
                "spim", "-file", f"{sandbox_dir}/output.s"
            ]
            
            result = subprocess.run(
                commands,
                input=input_data.encode(),
                capture_output=True,
                timeout=TIMEOUT
            )
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Timeout expired while running the compiled file'}), 408
        except Exception as e:
            return jsonify({'error': 'Error running compiled file', 'message': str(e)}), 500
        
        # if there was an error running the compiled file
        if result.stderr:
            stderr_msg = result.stderr.decode()
            # Don't expose internal paths in error messages
            stderr_msg = stderr_msg.replace(sandbox_dir, "/sandbox")
            return jsonify({'error': 'Error running compiled file', 'message': stderr_msg}), 500
        
        # return all program outputs as a list, except for first (spim output) and last (empty string after last new line)
        output = result.stdout.decode()
        
        # in different environments, the output is different, but what follows 'Loaded' is the actual output
        output = output[output.find('Loaded'):]  
        
        # Limit output size to prevent memory exhaustion
        output_lines = output.split('\n')[1:-1]
        if len(output_lines) > 1000:
            output_lines = output_lines[:1000] + ["... (output truncated)"]
        
        return jsonify({'outputs': output_lines}), 200
        
    finally:
        # clean up the sandbox directory, including files
        shutil.rmtree(sandbox_dir, ignore_errors=True)

@app.route('/checkSyntax', methods=['POST'])
def check_syntax():
    data = request.get_json()
    program = data.get('program', '')
    
    if not program:
        return jsonify({'error': 'No program provided'}), 400
    
    try:
        parser = Parser(program)
        parser.parse()
        
        if not parser.lexer.isSyntaxValid:
            return jsonify({'isSyntaxCorrect': False, 
                            'error': parser.lexer.firstErrorMessage, 
                            'line': parser.lexer.errorLine,
                            'column': parser.lexer.errorColumn}), 200
        if not parser.isSyntaxCorrect:
            return jsonify({'isSyntaxCorrect': False, 
                            'error': parser.firstErrorMessage, 
                            'line': parser.lineNumber,
                            'column': parser.columnNumber}), 200
        else:
            return jsonify({'isSyntaxCorrect': True}), 200
    except Exception as e:
        return jsonify({'error': 'Error parsing program', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG, ssl_context='adhoc')
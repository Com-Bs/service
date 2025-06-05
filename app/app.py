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
    returnDict = {'outputs': [], 'error': '', 'message': '', 'line': -1, 'column': -1}
    
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
            # run the compiler 
            compiler = Compiler(program)
            
            if not compiler.isTypingValid(prints=False):
                returnDict['error'] = 'Type checking failed'
                returnDict['message'] = compiler.typeChecker.firstErrorMessager
                return jsonify(returnDict), 400
                
            parser = compiler.typeChecker.parser
            if not parser.isSyntaxValid:
                returnDict['error'] = 'Syntax error in program'
                returnDict['message'] = parser.firstErrorMessage
                returnDict['line'] = parser.lineNumber
                returnDict['column'] = parser.columnNumber
                return jsonify(returnDict), 400
            
            lexer = parser.lexer
            if not lexer.isSyntaxValid:
                returnDict['error'] = 'Lexer syntax error'
                returnDict['message'] = lexer.firstErrorMessage
                returnDict['line'] = lexer.errorLine
                returnDict['column'] = lexer.errorColumn
                return jsonify(returnDict), 400
            
            compiler.compile(f'{sandbox_dir}/output.s')
            
        except Exception as e:
            returnDict['error'] = 'Error compiling program'
            returnDict['message'] = str(e)
            return jsonify(returnDict), 400
            
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
            returnDict['error'] = 'Timeout expired while running the compiled file'
            return jsonify(returnDict), 408
        except Exception as e:
            returnDict['error'] = 'Error running the compiled file'
            returnDict['message'] = str(e)
            return jsonify(returnDict), 500
        
        # if there was an error running the compiled file
        if result.stderr:
            stderr_msg = result.stderr.decode()
            # Don't expose internal paths in error messages
            stderr_msg = stderr_msg.replace(sandbox_dir, "/sandbox")
            
            returnDict['error'] = 'Error running compiled file'
            returnDict['message'] = stderr_msg
            return jsonify(returnDict), 500
        
        # return all program outputs as a list, except for first (spim output) and last (empty string after last new line)
        output = result.stdout.decode()
        
        # in different environments, the output is different, but what follows 'Loaded' is the actual output
        output = output[output.find('Loaded'):]  
        
        # First line is the spim output, last line is empty after last new line
        output_lines = output.split('\n')[1:-1]
        
        returnDict['outputs'] = [int(line) for line in output_lines]
        returnDict['message'] = 'Program executed successfully'
        return jsonify(returnDict), 200
        
    finally:
        # clean up the sandbox directory, including files
        shutil.rmtree(sandbox_dir, ignore_errors=True)

@app.route('/checkSyntax', methods=['POST'])
def check_syntax():
    data = request.get_json()
    program = data.get('program', '')
    
    returnDict= {'isSyntaxCorrect': False, 
                        'error': '', 
                        'line': -1, 
                        'column': -1, 
                        'message': ""}
    
    if not program:
        returnDict['error'] = 'No program provided'
        return jsonify(returnDict), 400
    
    try:
        parser = Parser(program)
        parser.parse()
        
        if not parser.lexer.isSyntaxValid:
            returnDict['error'] = parser.lexer.firstErrorMessage
            returnDict['line'] = parser.lexer.errorLine
            returnDict['column'] = parser.lexer.errorColumn
            return jsonify(returnDict), 200
        
        if not parser.isSyntaxValid:
            returnDict['error'] = parser.firstErrorMessage
            returnDict['line'] = parser.lineNumber
            returnDict['column'] = parser.columnNumber
            return jsonify(returnDict), 200

        else:
            returnDict['isSyntaxCorrect'] = True
            return jsonify(returnDict), 200

    except Exception as e:
        returnDict['error'] = 'Error parsing program'
        returnDict['message'] = str(e)
        return jsonify(returnDict), 500
    
def int_to_letters(n):
    result = ''
    while True:
        result = chr(ord('a') + (n % 26)) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result

@app.route('/performTestCases', methods=['POST'])
def check_test_cases():
    data = request.get_json()
    program = data.get('program', '')
    function_name = data.get('funName', '')
    test_cases = data.get('testCases', [])
    
    returnDict = {'results': []}
    resultTemplate = {'error': '', 'line': -1, 'column': -1, 'output': 0}
    
    # check inputs
    if not program:
        returnDict['error'] = 'No program provided'
        return jsonify(returnDict), 400
    if not function_name:
        returnDict['error'] = 'No function name provided'
        return jsonify(returnDict), 400
    if not test_cases:
        returnDict['error'] = 'No test cases provided'
        return jsonify(returnDict), 400
    
    # compile and run each test case, recording the output
    for test_case in test_cases:
        resultDict = resultTemplate.copy()
        
        mainFunction = "void main(void) {\n"
        assignments = ""
        
        # create the main function with parameters for testing
        for i, param in enumerate(test_case):
            param_ID = int_to_letters(i)
            # for an int
            if isinstance(param, int):
                mainFunction += f"int {param_ID};\n"
                if (param < 0):
                    assignments += f"{param_ID} = 0-{str(-param)};\n"
                else:
                    assignments += f"{param_ID} = {str(param)};\n"
            
            # for an array
            elif isinstance(param, list):
                mainFunction += f"int {param_ID}[{len(param)}];\n"
                for i, value in enumerate(param):
                    if value < 0:
                        assignments += f"{param_ID}[{i}] = 0-{str(-value)};\n"
                    else:
                        assignments += f"{param_ID}[{i}] = {str(value)};\n"
            else:
                returnDict['error'] = f'Invalid parameter type in test case {test_case}'
                return jsonify(returnDict), 400
        
        mainFunction += assignments
        mainFunction += f"output({function_name}({', '.join(int_to_letters(i) for i in range(len(test_case))) }));\n"
        mainFunction += "}\n"
        program_with_main = mainFunction + program
        
        sandbox_dir = tempfile.mkdtemp(prefix="sandbox_", dir="/tmp")
        try:
            try:
                # run the compiler 
                compiler = Compiler(program_with_main)
                
                if not compiler.isTypingValid(prints=False):
                    resultDict['error'] = compiler.typeChecker.firstErrorMessage
                    returnDict['results'].append(resultDict)
                    continue
                    
                parser = compiler.typeChecker.parser
                if not parser.isSyntaxValid:
                    resultDict['error'] = parser.firstErrorMessage
                    resultDict['line'] = parser.lineNumber
                    resultDict['column'] = parser.columnNumber
                    returnDict['results'].append(resultDict)
                    continue
                
                lexer = parser.lexer
                if not lexer.isSyntaxValid:
                    resultDict['error'] = lexer.firstErrorMessage
                    resultDict['line'] = lexer.errorLine
                    resultDict['column'] = lexer.errorColumn
                    returnDict['results'].append(resultDict)
                    continue
                
                compiler.compile(f'{sandbox_dir}/output.s')
                
            except Exception as e:
                resultDict['error'] = str(e)
                returnDict['results'].append(resultDict)
                continue

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
                    capture_output=True,
                    timeout=TIMEOUT
                )
            except subprocess.TimeoutExpired:
                resultDict['error'] = 'Timeout expired while running the compiled file'
                returnDict['results'].append(resultDict)
                continue
            
            except Exception as e:
                resultDict['error'] = str(e)
                returnDict['results'].append(resultDict)
                continue
            
            # if there was an error running the compiled file
            if result.stderr:
                stderr_msg = result.stderr.decode()
                # Don't expose internal paths in error messages
                stderr_msg = stderr_msg.replace(sandbox_dir, "/sandbox")
                
                resultDict['error'] = stderr_msg
                returnDict['results'].append(resultDict)
                continue
            
            # return all program outputs as a list, except for first (spim output) and last (empty string after last new line)
            output = result.stdout.decode()
            
            # in different environments, the output is different, but what follows 'Loaded' is the actual output
            output = output[output.find('Loaded'):]  
            
            # Limit output size to prevent memory exhaustion
            output_lines = output.split('\n')[1:-1]
            
            resultDict['output'] = int(output_lines[-1])
            returnDict['results'].append(resultDict)
        finally:
            # clean up the sandbox directory, including files
            shutil.rmtree(sandbox_dir, ignore_errors=True)
    
    return jsonify(returnDict), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG, ssl_context='adhoc')
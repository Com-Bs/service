from .type_checker import TypeChecker
from .code_generator import CodeGenerator

class Compiler():
    def __init__(self, program : str, strictMode=False):
        self.typeChecker = TypeChecker(program, strictMode=strictMode)
    
    def isTypingValid(self, prints=False):
        return self.typeChecker.checkTyping(prints)
    
    def printAST(self):
        self.typeChecker.printAST()
    
    def compile(self, path="output.s"):
        codeGenerator = CodeGenerator(self.typeChecker.AST, filePath=path)
        
        codeGenerator.generateCode()
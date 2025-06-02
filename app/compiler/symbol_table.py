from compiler.global_types import *

class SymbolTable():
    def __init__(self):
        self.table : list[dict[str, Symbol]] = list()
    
    # from a program or function node, it fills the symbol table with the values from that scope 
    def fill(self, node : ASTnode):
        isGlobal = len(self.table) == 0
        
        scopeTypes : dict[str : Symbol] = dict()
        pos = 1
        
        # variables can be declared both as params and in a compound statement
        if node.type == NodeTypes.FunDeclaration:
            
            for child in node.children:
                if child.type == NodeTypes.Param:
                    scopeTypes[child.label] = Symbol(Types.Array if child.isArrayParam else Types.Int, child.label, pos, isGlobal=isGlobal)
                    pos += 1
            
            node = next(child for child in node.children if child.type == NodeTypes.CompoundStmt)
        
        # look for declarations
        for child in node.children:
            if child.type == NodeTypes.VarDeclaration:
                # All variables are of type int per the grammar
                scopeTypes[child.label] = Symbol(Types.Int if child.arraySize == 0 else Types.Array, child.label, pos, child.arraySize, isGlobal=isGlobal)
                pos += 1
            
            # while compound statements can't have function declarations, program can and it's easier to have it all in the same code
            elif child.type == NodeTypes.FunDeclaration:
                params = [Types.Array if param.isArrayParam else Types.Int for param in child.children if param.type == NodeTypes.Param]
                
                compoundStmt = next(node for node in child.children if node.type == NodeTypes.CompoundStmt)
                bodyVars = [var.arraySize for var in compoundStmt.children if var.type == NodeTypes.VarDeclaration]
                
                scopeTypes[child.label] = Symbol(child.returnType, child.label, pos, isFunction=True, paramTypes=params, bodyTypes=bodyVars, isGlobal=isGlobal)
                pos += 1
                
                
        # add the current scope to the type environment
        self.table.append(scopeTypes)
        
        return self.table
    
    def getSymbol(self, label : str):
        # iterate backwards to respect scope rules
        for scope in self.table[::-1]:
            if label in scope:
                return scope[label]
        
        return None
    
    def getType(self, label : str):
        # iterate backwards to respect scope rules
        for scope in self.table[::-1]:
            if label in scope:
                return scope[label].type
        
        return None
    
    def pop(self):
        return self.table.pop()
    
    def getFunParamTypes(self, label : str):
        if label in self.table[0]:
            return self.table[0][label].paramTypes
        
        return None
    
    def getFunBodyTypes(self, label : str):
        if label in self.table[0]:
            return self.table[0][label].bodyTypes
        
        return None
    
    # returns two lists, one for variables and one for functions
    def getGlobalSymbols(self) -> tuple[list[Symbol], list[Symbol]]:
        
        if len(self.table) == 0:
            return ([], [])
        
        variables = []
        functions = []
        for symbol in self.table[0].values():
            if symbol.isFunction:
                functions.append(symbol)
            else:
                variables.append(symbol)
        
        return variables, functions
    
    def getCurrentScopeLength(self):
        return len(self.table[-1])
    
    
    def getScopeOffset(self, label : str):
        scopeOffset = 0
        for scope in self.table[::-1]:
            if label in scope:
                break
            scopeOffset += (len(scope) + 2) * 4
        
        return scopeOffset
    
    def getControlStatementOffset(self):
        offset = 0
        for i in reversed(range(len(self.table))):
            if i <= 1:
                return offset
            
            offset += (len(self.table[i]) + 2) * 4
    
    def getCurrentScope(self):
        return list(self.table[-1].values())
    
    def print(self):
        def printIndent(indent):
            for _ in range(indent):
                print("| ", end="")
        
        #self.symbolTable : list[dict[str, Types]] = list()
        for i in range(len(self.table)):
            printIndent(i)
            print("Scope " + str(i))
            
            for label in self.table[i]:
                printIndent(i)
                print(f"{label} of type {self.table[i][label].type.value}")

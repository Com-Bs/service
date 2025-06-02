from compiler.global_types import *
from .parser import *
from compiler.symbol_table import SymbolTable

class TypeChecker():
    def __init__(self, program="", AST=None, strictMode=False):
        self.st = SymbolTable()
        self.isTypingValid = True
        
        self.strictMode = strictMode
        
        self.parser = Parser(program, strictMode)
        
        self.AST = self.parser.parse(False) if AST == None else AST
        
        
    def checkTyping(self, prints=False):
        # do DFS to traverse the tree, being careful to build the symbolTable for the scope
        self._doCheckTyping(self.AST)
        
        if prints:
            print("Typing is valid" if self.isTypingValid else "Typing is NOT valid")
        
        return self.isTypingValid
    
    def printAST(self):
        self.parser.printAST()

    def _doCheckTyping(self, node : ASTnode, funLabel : str = None):
        if not self.isTypingValid or node == None: return None
        
        # check if it's a node we should have the type for in the environment
        if node.type == NodeTypes.NUM:
            return Types.Int
        
        elif node.type == NodeTypes.ID:
            idType = self.st.getType(node.label)
            
            if idType == None:
                self.parser.printErrorLine("Undeclared ID: " + node.label, node.pos, "Semantic")
                self.isTypingValid = False
                return None
            
            if node.isIdIndexed:
                if idType != Types.Array or len(node.children) == 0 or self._doCheckTyping(node.children[0], funLabel) != Types.Int:
                    self.isTypingValid = False
                    
                    if idType != Types.Array:
                        self.parser.printErrorLine("Cannot index non-array ID: " + node.label, node.pos, "Semantic")
                    else:
                        self.parser.printErrorLine("Indexing value has to be Int in ID: " + node.label, node.pos, "Semantic")
                    
                    return None
                                    
                idType = Types.Int
                    
            return idType
        
        elif node.type == NodeTypes.Call:
            callType = self.st.getType(node.label)
            
            if node.label == "input":
                callType = Types.Int
            elif node.label == "output":
                callType = Types.Void
            
            if callType == None:
                self.parser.printErrorLine("Calling undeclared function: " + node.label, node.pos, "Semantic")
                self.isTypingValid = False
                return None
            
            # we need to check params passed are also okay
            paramTypes = self.st.getFunParamTypes(node.label)
            if node.label == "input":
                paramTypes = []
            elif node.label == "output":
                paramTypes = [Types.Int]
            
            if len(node.children) != len(paramTypes):
                self.parser.printErrorLine("Wrong number of parameters in functions: " + node.label, node.pos, "Semantic")
                self.isTypingValid = False
                return None
            
            for i in range(len(node.children)):
                argType = self._doCheckTyping(node.children[i], funLabel)
                
                if argType == None:
                    self.parser.printErrorLine(f"Undeclared identifier {node.children[i].label}")
                    self.isTypingValid
                    return callType
                
                if argType != paramTypes[i]:
                    self.parser.printErrorLine(f"Param {node.children[i].label} of wrong type, expected {str(paramTypes[i].value)}", node.children[i].pos, "Semantic")
                    self.isTypingValid = False
                    return callType
                
            return callType
            
        
        # check if it's a node where a new scope starts
        elif node.type in [NodeTypes.Program, NodeTypes.FunDeclaration, NodeTypes.CompoundStmt]:
            # if it's a function declaration this method adds the params and the types of IDs in the body to the env, and we advance the node
            label = node.label if node.type == NodeTypes.FunDeclaration else funLabel
            self.st.fill(node)
            
            if node.type == NodeTypes.FunDeclaration:
                # cannot be none per the grammar of the language
                node = next(child for child in node.children if child.type == NodeTypes.CompoundStmt)

            for child in node.children:
                self._doCheckTyping(child, funLabel=label)
                
            self.st.pop()
            return None
            
        # check if it's a node we need to check the type for
        elif node.type == NodeTypes.Return:
            returnType = Types.Void if len(node.children) == 0 else self._doCheckTyping(node.children[0], funLabel)
            
            if returnType != self.st.getType(funLabel):
                self.parser.printErrorLine("Return value of wrong type, expected " + str(self.st.getType(funLabel).value), node.pos, "Semantic")
                self.isTypingValid = False
            
            return returnType
        
        elif node.type == NodeTypes.Index:
            indexType = self._doCheckTyping(node.children[0], funLabel)
            
            if indexType != Types.Int:
                # no need to add error handling here since index happens after ID and ID handles the error
                self.isTypingValid = False
            
            return indexType
        
        elif node.type == NodeTypes.BinaryOp:
            type1 = self._doCheckTyping(node.children[0], funLabel)
            type2 = self._doCheckTyping(node.children[1], funLabel)
            
            if not self.isTypingValid:
                return Types.Int
            
            if type1 != Types.Int or type2 != Types.Int:
                self.isTypingValid = False
                
                if type1 != Types.Int:
                    self.parser.printErrorLine("Int type expected in operation, not " + str(type1.value), node.children[0].pos, "Semantic")
                else:
                    self.parser.printErrorLine("Int type expected in operation, not " + str(type2.value), node.children[1].pos, "Semantic")
            
            return Types.Int
        
        elif node.type == NodeTypes.Assignment:
            leftType = self._doCheckTyping(node.children[0], funLabel)
            rightType = self._doCheckTyping(node.children[1], funLabel)
            
            if not self.isTypingValid:
                return rightType
            
            if leftType != rightType:
                self.parser.printErrorLine(f"Trying to assign {str(rightType.value)} to {str(leftType.value)} variable", node.children[1].pos, "Semantic")
                self.isTypingValid = False

            return rightType
        
        # otherwise we just check children
        else:
            for child in node.children:
                self._doCheckTyping(child, funLabel)
            
            return None
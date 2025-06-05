from .parser import *
from compiler.type_checker import *
from compiler.symbol_table import *
    
def codeGen(tree : ASTnode, file : str):
    codeGenerator = CodeGenerator(tree, file)
    codeGenerator.generateCode()
    
class CodeGenerator():
    def __init__(self, AST : ASTnode = None, program : str = "", filePath : str = "output.s"):
        self.filePath = filePath
        
        parser = Parser(program)
        self.AST = parser.parse() if AST == None else AST
        
        self.st = SymbolTable()
        
        self.controlStatementCount = 0
        self.currentFunctionLabel = ""
        
    def generateCode(self):
        if self.AST.type != NodeTypes.Program: return False
        
        # fill in the global scope
        self.st.fill(self.AST)
        variables, functions = self.st.getGlobalSymbols()
        
        if not any(fun for fun in functions if fun.label == "main"):
            self._writeAssemblyToFile("")
            return
        
        asm = ".data\n\tnewline: .asciiz \"\\n\"\n\t.align 2\n"
        
        # put the global variables in the data segment of the assembly
        heapCalls = ""
        for var in variables:
            if var.arraySize == 0:
                asm += f"\t{var.label}: .word 0\n"
            else:
                asm += f"\t{var.label}: .space {var.arraySize*4}\n"
                heapCalls += (
                    "   li $v0 9\n"
                    f"   li $a0 {var.arraySize * 4}\n"
                    "   syscall\n"
                    f"   sw $v0, {var.label}\n\n"
                )
        
        mainCallCode = self._generateCallerCode(ASTnode(label="main", children=[]))
        asm += (
            ".text\n"
            ".globl main\n"
            "main:\n"
            + heapCalls +
            f"{mainCallCode}"
            "\n"   
            "   li $v0 10\n"
            "   syscall\n\n"
        )
        
        for fun in [child for child in self.AST.children if child.type == NodeTypes.FunDeclaration]:
            asm += self._generateFunctionCode(fun)
        
        self._writeAssemblyToFile(asm)
    
    def _generateCallerCode(self, callNode : ASTnode):
        asm = ""
        if callNode.label == "output":
            asm += self._generateStatementCode(callNode.children[0])
            asm += (
                "   li $v0, 1\n"
                "   syscall\n"
                "   la $a0, newline\n"
                "   li $v0 4\n"
                "   syscall\n"
            )
            return asm
        elif callNode.label == "input":
            asm += (
                "   li $v0 5\n"
                "   syscall\n"
                "   move $a0 $v0\n"
            )
            return asm
        
        
        calleeLabel = callNode.label
        bodyVars = self.st.getFunBodyTypes(calleeLabel)
        
        
        asm += (
            "   sw $fp 0($sp)\n"
            "   addiu $sp $sp -4\n"
        )
        
        for size in bodyVars[::-1]:
            if size != 0:
                # if it's an array call the heap and store the adress in a0
                asm += (
                    "   li $v0 9\n"
                    f"   li $a0 {size * 4}\n"
                    "   syscall\n"
                    "   move $a0, $v0\n"
                )
            asm += (
                "   sw $a0 0($sp)\n"
                "   addiu $sp $sp -4\n"
            )
        
        for param in callNode.children[::-1]:
            asm += self._generateStatementCode(param)
            asm += (
                "   sw $a0 0($sp)\n"
                "   addiu $sp $sp -4\n"
            )
        
        asm += f"   jal {calleeLabel}_entry\n"
        
        return asm
    
    def _generateFunctionCode(self, function : ASTnode):
        self.st.fill(function)
        asm = (
            f"{function.label}_entry:\n"
            "   # store the return address after jumping\n"
            "   move $fp $sp\n"
            "   sw $ra 0($sp)\n"
            "   addiu $sp $sp -4\n\n"
        )
        
        self.currentFunctionLabel = function.label
        compoundStatement = next(node for node in function.children if node.type == NodeTypes.CompoundStmt)
        for child in compoundStatement.children:
            asm += self._generateStatementCode(child)
        self.currentFunctionLabel = ""
        
        asm += (
            f"{function.label}_exit:\n"
            "\n   # erase logically the AR and jump back to the return address\n"
            f"   lw $ra 4($sp)\n"
            f"   addiu $sp $sp {4 * self.st.getCurrentScopeLength() + 8}\n"
            "   lw $fp 0($sp)\n"
            #"   addiu $fp $fp 4\n"
            "   jr $ra\n\n"
        )
        self.st.pop()
        return asm
    
    def _generateStatementCode(self, node : ASTnode):
        if node.type == NodeTypes.NUM:
            return f"   li $a0 {node.label}\n"
        elif node.type == NodeTypes.ID:
            return self._genID(node)
        elif node.type == NodeTypes.Assignment:
            return self._genAssignment(node)
        elif node.type == NodeTypes.BinaryOp:
            return self._genBinaryOp(node)
        elif node.type == NodeTypes.Call:
            return self._generateCallerCode(node)
        elif node.type == NodeTypes.Index:
            return self._generateStatementCode(node.children[0])
        elif node.type in [NodeTypes.Selection, NodeTypes.Iteration]:
            return self._genControlStatement(node)
        elif node.type == NodeTypes.Return:
            asm = ""
            if len(node.children) != 0:
                asm = self._generateStatementCode(node.children[0])
            asm += f"   b {self.currentFunctionLabel}_exit\n"
            return asm
        else:
            return ""
    
    def _genControlStatement(self, node : ASTnode):
        count = str(self.controlStatementCount)
        # while
        if node.type == NodeTypes.Iteration:
            asm = "\n   # While Statement\n"
        
            compoundStatement = next(child for child in node.children if child.type == NodeTypes.Then).children[0]
            asm += self._controlStatementVariableCode(compoundStatement)
            
            asm += f"while_entry_{count}:\n"
            
            condition = next(child for child in node.children if child.type == NodeTypes.Condition)
            
            asm += self._generateStatementCode(condition.children[0])
            
            asm += (
                "   li $t1 0\n"
                f"   beq $a0 $t1 while_exit_{count}\n"
            )
            
            self.controlStatementCount += 1
            for child in compoundStatement.children:
                if child.type == NodeTypes.Return:
                    if len(child.children) != 0:
                        asm += self._generateStatementCode(child.children[0])
                        
                    offset = self.st.getControlStatementOffset()
                    asm += (
                        f"   addiu $fp $fp {offset}\n"
                        "   move $sp $fp\n"
                        "   addiu $sp $sp -4\n"
                        f"   b {self.currentFunctionLabel}_exit\n"
                    )
                    
                else:
                    asm += self._generateStatementCode(child)
                    
            self.controlStatementCount -= 1
            
            asm += (
                f"   b while_entry_{count}\n"
                f"while_exit_{count}:\n"
            )
            asm += (
                "   # erase logically the control statement variables\n"
                f"   addiu $sp $sp {4 * self.st.getCurrentScopeLength() + 8}\n"
                "   move $fp $sp\n"
                "   addiu $fp $fp 4\n\n"
            )    
            self.st.pop()
            
        else: # if
            asm = "\n   # If Statement\n"
            condition = next(child for child in node.children if child.type == NodeTypes.Condition)
            
            asm += self._generateStatementCode(condition.children[0])
            
            asm += (
                "   li $t1 0\n"
                f"   beq $a0 $t1 false_branch_{count}\n"
                f"\ntrue_branch_{count}:\n"
            )
            
            # fill variables for then, and then the body
            thenCompound = next(child for child in node.children if child.type == NodeTypes.Then).children[0]
            asm += self._controlStatementVariableCode(thenCompound)
            
            self.controlStatementCount += 1
            for child in thenCompound.children:
                if child.type == NodeTypes.Return:
                    if len(child.children) != 0:
                        asm += self._generateStatementCode(child.children[0])
                        
                    offset = self.st.getControlStatementOffset()
                    asm += (
                        f"   addiu $fp $fp {offset}\n"
                        "   move $sp $fp\n"
                        "   addiu $sp $sp -4\n"
                        f"   b {self.currentFunctionLabel}_exit\n"
                    )
                    
                else:
                    asm += self._generateStatementCode(child)
            self.controlStatementCount -= 1
            
            asm += (
                "   # erase logically the control statement variables\n"
                f"   addiu $sp $sp {4 * self.st.getCurrentScopeLength() + 8}\n"
                "   move $fp $sp\n"
                "   addiu $fp $fp 4\n\n"
            )
            self.st.pop()
            
            asm += f"   b end_if_{count}\n"
            
            # do the same for the else
            asm += f"\nfalse_branch_{count}:\n"
            elses = [child for child in node.children if child.type == NodeTypes.Else]
            if any(elses):
                elseCompound = elses[0].children[0]
                asm += self._controlStatementVariableCode(elseCompound)
                
                self.controlStatementCount += 1
                for child in elseCompound.children:
                    if child.type == NodeTypes.Return:
                        if len(child.children) != 0:
                            asm += self._generateStatementCode(child.children[0])
                            
                        offset = self.st.getControlStatementOffset()
                        asm += (
                            f"   addiu $fp $fp {offset}\n"
                            "   move $sp $fp\n"
                            "   addiu $sp $sp -4\n"
                            f"   b {self.currentFunctionLabel}_exit\n"
                        )
                        
                    else:
                        asm += self._generateStatementCode(child)
                self.controlStatementCount -= 1
                
                asm += (
                    "   # erase logically the control statement variables\n"
                    f"   addiu $sp $sp {4 * self.st.getCurrentScopeLength() + 8}\n"
                    "   move $fp $sp\n"
                    "   addiu $fp $fp 4\n\n"
                )
                self.st.pop()
            
            # finish the if
            asm += f"end_if_{count}:\n"        
        
        self.controlStatementCount += 1
        
        return asm
    
    def _controlStatementVariableCode(self, compoundStatement : ASTnode):
        asm = (
            "   sw $fp 0($sp)\n"
            "   addiu $sp $sp -4\n"
        )
        self.st.fill(compoundStatement)
            
        bodyVars : list[Symbol] = self.st.getCurrentScope()
        
        # push local variables into the stack
        for var in bodyVars[::-1]:
            if var.arraySize != 0:
                # if it's an array call the heap and store the adress in a0
                asm += (
                    "   li $v0 9\n"
                    f"   li $a0 {var.arraySize * 4}\n"
                    "   syscall\n"
                    "   move $a0, $v0\n"
                )
            asm += (
                "   sw $a0 0($sp)\n"
                "   addiu $sp $sp -4\n"
            )
        
        # move the fp and store a fake return address field to make it match an AR
        asm += (
            "   move $fp $sp\n"
            "   addiu $sp $sp -4\n\n"
        )
        return asm
        
    def _genBinaryOp(self, node : ASTnode):
        asm = ""
        
        asm += self._generateStatementCode(node.children[0])
        
        asm += (
            "   sw $a0 0($sp)\n"
            "   addiu $sp $sp -4\n"
        )
        
        asm += self._generateStatementCode(node.children[1])
        
        asm += (
            "   lw $t1 4($sp)\n"
            "   addiu $sp $sp 4\n"
        )
        
        op = node.label
        if op == "+":
            asm += "   add $a0 $t1 $a0\n"
        elif op == "-":
            asm += "   sub $a0 $t1 $a0\n"
        elif op == "*":
            asm += (
                "   mult $a0 $t1\n"
                "   mflo $a0\n"
            )
        elif op == "/":
            asm += (
                "   div $t1 $a0\n"
                "   mflo $a0\n"
            )
        elif op == "<=":
            asm += "   sle $a0 $t1 $a0\n"
        elif op == "<":
            asm += "   slt $a0 $t1 $a0\n"
        elif op == ">=":
            asm += "   sle $a0 $a0 $t1\n"
        elif op == ">":
            asm += "   slt $a0 $a0 $t1\n"
        elif op == "==":
            asm += "   seq $a0 $a0 $t1\n"
        elif op == "!=":
            asm += "   sne $a0 $a0 $t1\n"
            
        
        return asm
            
    
    def _genID(self, node):
        asm = ""
        
        idLabel = node.label
        symbol = self.st.getSymbol(idLabel)
        
        if symbol.isGlobal:
            if symbol.type == Types.Array:
                if len(node.children) == 1: # global indexed array
                    # get the value of the index in the acc
                    asm += self._generateStatementCode(node.children[0].children[0])
                    
                    asm += (
                        "   li $t1 4\n"
                        "   mult $a0, $t1\n"
                        "   mflo $a0\n"
                        f"   lw $t0, {idLabel}\n"
                        "   addu $t0 $t0 $a0\n"
                        "   lw $a0, ($t0)\n"
                    )
                else: # global un-indexed array, set the acumulator to the address of the array
                    asm += (
                        f"   lw $a0, {idLabel}\n"
                    )
            else:
                # global int
                asm += (
                    f"   lw $a0, {idLabel}\n"
                )
        else:
            scopeOffset = self.st.getScopeOffset(idLabel)
            fpOffset = (symbol.pos * 4) + scopeOffset
            if symbol.type == Types.Array:
                # local array
                if len(node.children) == 1:
                    # local indexed array
                    # get the value of the index in the acc
                    asm += self._generateStatementCode(node.children[0].children[0])
                    
                    asm += (
                        "   li $t1 4\n"
                        "   mult $a0, $t1\n"
                        "   mflo $a0\n"
                        f"   lw $t0, {fpOffset}($fp)\n"
                        "   addu $t0 $t0 $a0\n"
                        "   lw $a0, ($t0)\n"
                    )
                else:
                    # non-indexed local array
                    asm += (
                        f"   lw $a0, {fpOffset}($fp)\n"
                    )
            else:
                # local int
                asm += (
                    f"   lw $a0, {fpOffset}($fp)\n"
                )
        
        return asm
            
    def _genAssignment(self, node : ASTnode):
        # store the right of the expression in the acc
        asm = self._generateStatementCode(node.children[-1])
        
        assigneeLabel = node.children[0].label
        symbol = self.st.getSymbol(assigneeLabel)
        
        if symbol.isGlobal:
            if symbol.type == Types.Array:
                # global array
                if len(node.children[0].children) == 1:
                    # global indexed array  
                    # store the right-part in the stack
                    asm += (
                        "   sw $a0 0($sp)\n"
                        "   addiu $sp $sp -4\n"
                    )
                    # get the value of the index in the acc
                    asm += self._generateStatementCode(node.children[0].children[0])
                    
                    asm += (
                        "   li $t1 4\n"
                        "   mult $a0, $t1\n"
                        "   mflo $a0\n"
                        f"   lw $t0, {assigneeLabel}\n"
                        "   addu $t0 $t0 $a0\n"
                        "   lw $t1, 4($sp)\n"
                        "   addiu $sp $sp 4\n"
                        "   sw $t1, ($t0)\n"
                    )
                else:
                    # global, not-indexed array -> the acc holds an address to another array
                    asm += (
                        f"   sw $a0, {assigneeLabel}\n"
                    )
            else:
                # global int
                asm += (
                    f"   sw $a0, {assigneeLabel}\n"
                )
        else:
            scopeOffset = self.st.getScopeOffset(assigneeLabel)
            fpOffset = (symbol.pos * 4) + scopeOffset
            if symbol.type == Types.Array:
                # local array
                if len(node.children[0].children) == 1:
                    # locally indexed array  
                    # store the right-part in the stack
                    asm += (
                        "   sw $a0 0($sp)\n"
                        "   addiu $sp $sp -4\n"
                    )
                    # get the value of the index in the acc
                    asm += self._generateStatementCode(node.children[0].children[0])
                    
                    asm += (
                        "   li $t1 4\n"
                        "   mult $a0, $t1\n"
                        "   mflo $a0\n"
                        f"   lw $t0, {fpOffset}($fp)\n"
                        "   addu $t0 $t0 $a0\n"
                        "   lw $t1, 4($sp)\n"
                        "   addiu $sp $sp 4\n"
                        "   sw $t1, ($t0)\n"
                    )
                else:
                    # local, not-indexed array -> the acc holds an address to another array
                    asm += (
                        f"   sw $a0, {fpOffset}($fp)\n"
                    )
            else:
                # local int
                asm += f"   sw $a0, {fpOffset}($fp)\n"
                
        
        return asm
    
    def _writeAssemblyToFile(self, code: str):
        with open(self.filePath, "w") as f:
            f.write(code)
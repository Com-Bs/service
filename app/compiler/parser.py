from compiler.global_types import *
from .lexer import *

class Parser():
    def __init__(self, program, strictMode=False):
        self.AST = None
        self.isSyntaxCorrect = True
        
        self.lastTokenPosition = 0 # used to print error messages
        self.tokenPosition = 0 # is added to the node to map it to the program
        
        self.strictMode = strictMode
        
        # pasar las variables globales al lexer, y pedir el primer token
        self.lexer = Lexer(program, strictMode=strictMode)
        self._getToken()
    
    def _getToken(self):
        self.lastTokenPosition = self.lexer.getPos() - 1
        self.token, self.lexeme = self.lexer.getToken()
        self.tokenPosition = self.lexer.getPos() - 1
        
        while (self.token == TokenType.ERROR and self.token != TokenType.ENDFILE):
            self.lastTokenPosition = self.lexer.getPos() - 1
            self.token, self.lexeme = self.lexer.getToken()
            self.tokenPosition = self.lexer.getPos() - 1
            
        

    def parse(self, prints=False):
        self.AST = self._program()
        
        if self.token != TokenType.ENDFILE:
            msg = ">>> Error: Program finished prematurely"
            if self.strictMode:
                raise Exception(msg)
            else:
                self.isSyntaxCorrect = False
                print(msg)
        if self.isSyntaxCorrect:
            if prints:
                self.printAST()
        else:
            print("\n>>> AST not printed since a syntax error was found")
            
        return self.AST

    def printErrorLine(self, errorMessage="", pos=None, errorType="Syntax"):
        self.lexer.printErrorLine(errorMessage, pos, errorType)
        
    def printAST(self, AST : ASTnode = None):
        # do own AST if none is passed
        AST = AST if AST != None else self.AST
        self._doPrintAST(AST)
        
    def _doPrintAST(self, AST: ASTnode, indentation=0):
        if AST != None:
            print("| " * indentation, end='')
            print(AST.type.value, end='')
            print(": " + AST.label, end='')
            
            if AST.type == NodeTypes.FunDeclaration:
                print(" -> return type: ", end='')
                print(AST.returnType.value)
            elif AST.type == NodeTypes.Param and AST.isArrayParam:
                print(" -> array")
            elif AST.type == NodeTypes.VarDeclaration and AST.arraySize != 0:
                print(" -> array of size " + str(AST.arraySize))
            else:
                print("")
            
            
            
            for child in AST.children:
                self._doPrintAST(child, indentation + 1)
    
    def _match(self, expectedToken, errorMsg="", ignoreError=False):
        oldLexeme = self.lexeme
        if expectedToken == self.token:
            self._getToken()
        else:
            self.isSyntaxCorrect = False
            self.lexer.printErrorLine(errorMsg, self.lastTokenPosition)
            
            # when we ignore the error, we act as if it was there, and not consume any token to continue parsing from there
            # otherwise, we consume tokens until we find the one we were expecting
            if not ignoreError:
                while self.token != TokenType.ENDFILE and self.token != expectedToken:
                    self._getToken()

                # we got the token we wanted, we continue parsing from here -> more errors are likely
                oldLexeme = self.lexeme
                self._getToken()
            
        return oldLexeme # This is sometimes used in the AST, e.g. for IDs in var and fun declarations
    
    def _program(self):
        n = ASTnode(type = NodeTypes.Program, pos=self.tokenPosition)
        
        n.children.append(self._declaration())
        
        while (self.token in [TokenType.INT, TokenType.VOID]):
            n.children.append(self._declaration())
        
        return n
    
    def _declaration(self):
        if self.token == TokenType.INT:
            self._match(TokenType.INT)
            idLexeme = self._match(TokenType.ID, "Expected ID after type")
            n = self._varOrFun(idLexeme)
        else:
            self._match(TokenType.VOID, "Expected INT or VOID for declaration")
            idLexeme = self._match(TokenType.ID, "Expected ID after type")
            self._match(TokenType.LPAR, "Expected '(' for function declaration", True)
            n = self._funDeclaration(idLexeme, Types.Void)
        return n
    
    def _varOrFun(self, idLexeme):
        if self.token == TokenType.LPAR:
            self._match(TokenType.LPAR)
            n = self._funDeclaration(idLexeme, Types.Int)
        else:
            n = self._varDeclaration(idLexeme)
        return n
    
    def _varDeclaration(self, idLexeme):
        # A var declaration AST node has an ID child whose label is the var name, and an optional array child
        n = ASTnode(type = NodeTypes.VarDeclaration, label=idLexeme, pos=self.tokenPosition)
        
        if (self.token == TokenType.LBRA):
            self._match(TokenType.LBRA)
            num = self._match(TokenType.NUM, "Expected number to define array size")
            n.arraySize = int(num)
            self._match(TokenType.RBRA, "Expected ']' in array size declaration", True)
            
        
        self._match(TokenType.SEMICOLON, "Expected ';' after variable declaration", True)
        
        return n
    
    def _funDeclaration(self, idLexeme, returnType : Types):
        # A fun declaration node has an ID child, a return type child, can have param children, and a funBody child
        n = ASTnode(type = NodeTypes.FunDeclaration, label=idLexeme, pos=self.tokenPosition)
        n.returnType = returnType
        
        # add param children
        n.children.extend(self._params())
        
        self._match(TokenType.RPAR, "Expected ')' after parameter declaration", True)
        
        n.children.append(self._compoundStmt()) # function body child (called compound statement)
        
        return n
    
    def _params(self): # returns an array of nodes a function node has as children
        if (self.token == TokenType.VOID):
            self._match(TokenType.VOID)
            return []
        
        # if it's not void, there's at least one param
        params = [self._param()]
        
        while (self.token == TokenType.COMMA):
            self._match(TokenType.COMMA)
            params.append(self._param())
        
        return params
        
    def _param(self):
        self._match(TokenType.INT, "Expected type INT for parameter in function declaration")
        idLexeme = self._match(TokenType.ID, "Expected ID for parameter name")
        
        # check if it's an array param
        isArray = False
        if (self.token == TokenType.LBRA):
            self._match(TokenType.LBRA)
            self._match(TokenType.RBRA, "Expected ']' in array parameter declaration", True)
            isArray = True
            
        return ASTnode(type = NodeTypes.Param, label=idLexeme, isArrayParam=isArray, pos=self.tokenPosition)
    
    def _compoundStmt(self):
        n = ASTnode(type = NodeTypes.CompoundStmt, pos=self.tokenPosition)
        
        self._match(TokenType.LKEY, "Expected '{' for function body", True)
        
        # it's a var declaration
        while (self.token == TokenType.INT):
            self._match(TokenType.INT)
            idLexeme = self._match(TokenType.ID, "Expected ID in variable declaration")
            n.children.append(self._varDeclaration(idLexeme=idLexeme))
        
        # it's a statement
        while (self.token in STATEMENT_STARTERS):
            statement = self._statement()
            if statement == None: continue
            
            n.children.append(statement)

        self._match(TokenType.RKEY, "Expected '}' to close compound statement", True)
        return n
    
    def _statement(self): # can return none since we do not want empty statements
        if self.token in EXPRESSION_STMT_STARTERS:
            if self.token == TokenType.SEMICOLON: # if it's a semicolon, it's an empty statement, we don't want it as a child
                self._match(TokenType.SEMICOLON)
                return None
            n = self._expressionStmt()
        elif self.token == TokenType.LKEY:
            n = self._compoundStmt()
        elif self.token == TokenType.IF:
            n = self._selectionStmt()
        elif self.token == TokenType.WHILE:
            n = self._iterationStmt()
        else: # token should be return
            n = self._returnStmt()
        
        return n
    
    def _expressionStmt(self):
        n = self._expression()
        self._match(TokenType.SEMICOLON, "Expected ';' after expression", True)
        return n
    
    def _selectionStmt(self):
        n = ASTnode(type=NodeTypes.Selection, pos=self.tokenPosition)
        
        self._match(TokenType.IF)
        self._match(TokenType.LPAR, "Expected '(' to define the condition of the if statement", True)
        
        # the condition of the if is an expression
        n.children.append(ASTnode(type=NodeTypes.Condition, children=[self._expression()], pos=self.tokenPosition))
        self._match(TokenType.RPAR, "Expected ')' to close the condition", True)
        
        # the then of the if is a statement
        then = self._statement()
        if then != None:
            n.children.append(ASTnode(type=NodeTypes.Then, children=[then], pos=self.tokenPosition))
            
        # optional else
        if self.token == TokenType.ELSE:
            self._match(TokenType.ELSE)
            else_ = self._statement()
            if else_ != None:
                n.children.append(ASTnode(type=NodeTypes.Else, children=[else_], pos=self.tokenPosition))
        
        return n
    
    def _iterationStmt(self):
        n = ASTnode(type=NodeTypes.Iteration, pos=self.tokenPosition)
        
        self._match(TokenType.WHILE)
        self._match(TokenType.LPAR, "Expected '(' to define cycle condition", True)
        
        # the condition of the while is an expression
        n.children.append(ASTnode(type=NodeTypes.Condition, children=[self._expression()], pos=self.tokenPosition))
        self._match(TokenType.RPAR, "Expected ')' after cycle condition", True)
        
        # the then of the while is a statement
        then = self._statement()
        if then != None:
            n.children.append(ASTnode(type=NodeTypes.Then, children=[then], pos=self.tokenPosition))
        
        return n
    
    def _returnStmt(self):
        n = ASTnode(type=NodeTypes.Return, pos=self.tokenPosition)
        
        self._match(TokenType.RETURN)
        
        if self.token in EXPRESSION_STARTERS:
            n.children.append(self._expression())
        
        self._match(TokenType.SEMICOLON, "Expected ';' to end return statement", True)
        return n
    
    def _expression(self):
        if self.token == TokenType.ID:
            idLexeme = self._match(TokenType.ID)
            n = self._idExpression(idLexeme)
        else:
            n = self._simpleExpression()
        return n
    
    def _idExpression(self, idLexeme):
        # check if it's a call
        if self.token == TokenType.LPAR: # it's a function call
            self._match(TokenType.LPAR)
            
            n = ASTnode(type=NodeTypes.Call, label=idLexeme, pos=self.tokenPosition)
            n.children = self._args()
            
            self._match(TokenType.RPAR, "Expected ')' to close function call", True)
        else:
            # check if the id has an index
            index = None
            if self.token == TokenType.LBRA:
                self._match(TokenType.LBRA)
                index = ASTnode(type=NodeTypes.Index, children=[self._expression()], pos=self.tokenPosition)
                self._match(TokenType.RBRA, "Expected ']' after variable indexing", True)
            
            v = ASTnode(type=NodeTypes.ID, label=idLexeme, children=[] if index == None else [index], pos=self.tokenPosition)
            v.isIdIndexed = index != None
            
            n = self._idSimpleExpression(v)
            
        return n
    
    def _idSimpleExpression(self, idNode):
        if self.token == TokenType.ASSIGN:
            self._match(TokenType.ASSIGN)
            
            n = ASTnode(NodeTypes.Assignment, children=[
                idNode,
                self._expression()
            ], pos=self.tokenPosition)
        else:
            n = self._simpleExpression(idNode)
        
        return n

    def _args(self):
        # arguments can be empty
        args = []
        if self.token in EXPRESSION_STARTERS:
            args = [self._expression()]
            
            while self.token == TokenType.COMMA:
                self._match(TokenType.COMMA)
                args.append(self._expression())
        
        return args

    def _simpleExpression(self, idNode=None):
        first = self._additiveExpression(idNode)
        
        if self.token in RELOP:
            op = self._match(self.token) # we just care to advance the token and get the lexeme of operations
            n = ASTnode(type=NodeTypes.BinaryOp, label=op, pos=self.tokenPosition)
            second = self._additiveExpression()
            
            n.children = [first, second]
            return n
        
        return first
    
    def _additiveExpression(self, idNode=None):
        first = self._term(idNode)
        
        if self.token not in [TokenType.PLUS, TokenType.MINUS]: return first
        
        # build the head of the chain of operations
        op = self._match(self.token) # we just care to advance the token and get the lexeme of operations
        curr = ASTnode(type=NodeTypes.BinaryOp, label=op, pos=self.tokenPosition) # curr is used to traverse and create this subtree
        second = self._term()
        
        curr.children = [first, second]
        
        while self.token in [TokenType.PLUS, TokenType.MINUS]:
            op = self._match(self.token) # we just care to advance the token and get the lexeme of operations
            new = ASTnode(type=NodeTypes.BinaryOp, label=op, pos=self.tokenPosition)
            second = self._term()
            
            new.children = [curr, second]
            curr = new
        
        return curr

    
    def _term(self, idNode=None):
        first = self._factor(idNode)
        
        if self.token not in [TokenType.TIMES, TokenType.OVER]: return first
        
        # build the head of the chain of operations
        op = self._match(self.token) # we just care to advance the token and get the lexeme of operations
        curr = ASTnode(type=NodeTypes.BinaryOp, label=op, pos=self.tokenPosition) # curr is used to traverse and create this subtree
        second = self._factor()
        
        curr.children = [first, second]
        
        while self.token in [TokenType.TIMES, TokenType.OVER]:
            op = self._match(self.token) # we just care to advance the token and get the lexeme of operations
            new = ASTnode(type=NodeTypes.BinaryOp, label=op, pos=self.tokenPosition)
            second = self._factor()
            
            new.children = [curr, second]
            curr = new
        
        return curr
    
    def _factor(self, idNode=None):
        if idNode: return idNode
        
        if self.token == TokenType.LPAR:
            self._match(TokenType.LPAR)
            n = self._expression()
            self._match(TokenType.RPAR, "Missing ')' to match opening parenthesis in expression", True)
            return n
        elif self.token == TokenType.NUM:
            num = self._match(TokenType.NUM)
            n = ASTnode(type=NodeTypes.NUM, label=num, pos=self.tokenPosition)
        else:
            idLexeme = self._match(TokenType.ID, "Unexpected token in expression, expected ID")
            
            if self.token == TokenType.LPAR:
                self._match(TokenType.LPAR)
                n = ASTnode(type=NodeTypes.Call, label=idLexeme, pos=self.tokenPosition)
                n.children = self._args()
                self._match(TokenType.RPAR, "Expected ')' to close function call", True)
            else:
                n = ASTnode(type=NodeTypes.ID, label=idLexeme, pos=self.tokenPosition)
                
                # check if the var is indexed
                if (self.token == TokenType.LBRA):
                    self._match(TokenType.LBRA)
                    index = ASTnode(type=NodeTypes.Index, children=[self._expression()], pos=self.tokenPosition)
                    self._match(TokenType.RBRA, "Expected ']' after variable indexing", True)
                
                    n.children = [index]
                    n.isIdIndexed = True
            
        return n
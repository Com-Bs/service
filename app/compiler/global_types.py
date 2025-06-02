from enum import Enum

class TokenType(Enum):
    # Reserved words
    ELSE = "else"
    IF = "if"
    INT = "int"
    RETURN = "return"
    VOID = "void"
    WHILE = "while"
    
    # Operatros
    PLUS = "+"
    MINUS = "-"
    TIMES = "*"
    OVER = "/"
    LETH = "<"
    LETHEQ = "<="
    BITH = ">"
    BITHEQ = ">="
    EQ = "=="
    NEQ = "!="
    ASSIGN = "="
    
    # Special Symbols
    SEMICOLON = ";"
    COMMA = ","
    LPAR = "("
    RPAR = ")"
    LBRA = "["
    RBRA = "]"
    LKEY = "{"
    RKEY = "}"
    COMM = "COMMENT"
    
    # Other Tokens
    ID = "ID"
    NUM = "NUM"
    ENDFILE = "$"
    
    # Error
    ERROR = "ERROR"

"""
sets to simplify the DFA:
    Reserved words will be checked in the ID final state
    Simple symbols are symbols that share the same DFA, just changing the character
        -> it was put into one to simplify the states
"""
RESERVED_WORDS = {"else", "if", "int", "return", "void", "while"}
OPERATORS = {"+", "-", "*", "/", "<", "<=", ">", ">=", "==", "!=", "="}
SIMPLE_SYM = {"(", ")", "[", "]", "{", "}", "+", "-", "*", ";", ","}
SPECIAL_SYMBOLS = {";", ",", "(", ")", "[", "]", "{", "}", "/*", "*/"}
WHITE_SPACE = {" ", "\t", "\n", "$"}
LETTER = {'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'}
NUMBER = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}

"""
sets of tokens to simplify the parser logic
"""
STATEMENT_STARTERS = [TokenType.SEMICOLON, TokenType.ID, TokenType.LPAR, TokenType.NUM, TokenType.LKEY, TokenType.IF, TokenType.WHILE, TokenType.RETURN]
EXPRESSION_STMT_STARTERS = [TokenType.SEMICOLON, TokenType.ID, TokenType.LPAR, TokenType.NUM]
EXPRESSION_STARTERS = [TokenType.ID, TokenType.LPAR, TokenType.NUM]
RELOP = [TokenType.LETHEQ, TokenType.LETH, TokenType.BITH, TokenType.BITHEQ, TokenType.EQ, TokenType.NEQ]

class NodeTypes(Enum):
    Program = "Program"
    
    ID = "ID"
    NUM = "NUM"
    VarDeclaration = "VarDeclaration"
    
    FunDeclaration = "FunDeclaration"
    Param = "Param"
    
    CompoundStmt = "CompoundStmt"

    Selection = "Selection"
    Condition = "Condition"
    Then = "Then"
    Else = "Else"
    
    Iteration = "Iteration"
    
    Return = "Return"
    
    # Expressions related to an ID
    Index = "Index"
    Assignment = "Assignment"
    Var = "Var"
    Call = "Call"
    Args = "Args"
    
    BinaryOp = "BinaryOp"
    

class ASTnode():
    def __init__(self, type = None, label = "", children = None, pos = 0, isArrayParam = False, arraySize = 0, returnType = None, isIdIndexed = False):
        self.type : NodeTypes = type
        self.label : str = label
        self.children : list[ASTnode] = children if children != None else []
        self.pos : int = pos
        
        # special attributes used in some cases
        self.isArrayParam : bool = isArrayParam
        self.arraySize : int = arraySize
        self.returnType : Types = returnType
        self.isIdIndexed : bool = isIdIndexed
class Types(Enum):
    Int = "Int"
    Void = "Void"
    Array = "Array"

class Symbol():
    def __init__(self, type, label, pos, arraySize = 0, isFunction = False, paramTypes = [], bodyTypes = [], isGlobal = False):
        self.type : Types = type 
        self.label : str = label 
        
        """ used to access variables in the AR, params will have lower positions. 
            The first has pos 1 since it's the second element at the top of the stack. """
        self.pos : int = pos 
        
        # array size can be 0 for an array of non-zero length since if it's a param it is not declared
        self.arraySize : int = arraySize
        
        self.isFunction : bool = isFunction
        self.paramTypes : list[Types] = paramTypes
        self.bodyTypes : list[int] = bodyTypes
        
        self.isGlobal : bool = isGlobal
from compiler.global_types import *

class Lexer():
    def __init__(self, program, strictMode=False, state=0):
        # variables to iterate through the program
        self.programLength = len(program) 
        self.program = program + '$'
        self.pos = 0
        
        self.strictMode = strictMode
        
        self.firstFinalState = 15 # all final states are at and after this number
        self.state = state

    def getToken(self, prints = False):
        lexeme = ""
        
        while self.pos <= self.programLength:
            if self.state == 0:
                lexeme = ""
            c = self.program[self.pos]
            
            self._advanceState(c)
            
            # check if we have gotten to a final state
            if self.state == 19: # this is the end of a comment, we don't want to return it to the parser
                self.state = 0
            elif self.state >= self.firstFinalState:
                token, lexeme = self._returnFromFinalState(lexeme)
                self.state = 0
                
                if prints:
                    print(token," = ", lexeme)
                
                return token, lexeme
            
            # we haven't gotten to a final state
            lexeme += c
            self.pos += 1
    
    def getPos(self):
        return self.pos
    
    def printErrorLine(self, errorMessage="", pos_=None, errorType="Syntax"):
        pos = self.pos if pos_ == None else pos_
        while pos >= 0 and self.program[pos] in WHITE_SPACE:
            pos -= 1
        
        # print where the error is 
        lastNewLine = self.program.rfind('\n', 0, pos)
        lastNewLine = lastNewLine + 1 if lastNewLine != -1 else 0
        
        nextNewLine = self.program.find('\n', pos)
        nextNewLine = nextNewLine - 1 if nextNewLine != -1 else self.programLength - 1
        
        errorOutput = (
            f"\n>>> {errorType} error found at line " 
            + str(self.program[:pos].count('\n') + 1)
            + ": " + errorMessage + "\n"
            + self.program[lastNewLine:nextNewLine+1] + "\n"
            + " " * (pos - lastNewLine) + "^\n" 
        )
        if self.strictMode:
            raise Exception(errorOutput)
        else:
            print(errorOutput)
    
    def _handleErrors(self, c):        
        self.printErrorLine(self._getErrorMessage(c))
                
        # reset the lexer to the next position -> it might still lex an error
        self.state = 28
        self.pos += 1
    
    def _getErrorMessage(self, c):
        if self.state == 1:
            if c in NUMBER:
                return "A number cannot be part of an ID"
            else:
                return f"Unexpected character '{c}' in an ID creation"
        elif self.state == 2:
            if c in LETTER:
                return "A letter cannot be next to a number"
            else:
                return f"Unexpected character '{c}' after number"
        elif self.state == 13:
            return f"Invalid character '{c}' after '!', did you mean !=?"
        return f"Unexpected character '{c}'"
        
    def _advanceState(self, c):
        if self.state == 0:
            self._lex0(c)
        elif self.state == 1:
            self._lex1(c)
        elif self.state == 2:
            self._lex2(c)
        elif self.state == 3:
            self._lex3(c)
        elif self.state == 4:
            self._lex4(c)
        elif self.state == 5:
            self._lex5(c)
        elif self.state == 6:
            self._lex6(c)
        elif self.state == 7:
            self._lex7(c)
        elif self.state == 8:
            self._lex8(c)
        elif self.state == 9:
            self._lex9(c)
        elif self.state == 10:
            self._lex10(c)
        elif self.state == 11:
            self._lex11(c)
        elif self.state == 12:
            self._lex12(c)
        elif self.state == 13:
            self._lex13(c)
        elif self.state == 14:
            self._lex14(c)
    
    def _returnFromFinalState(self, lexeme):
        if self.state == 15: # ID can be a reserved word or an ID
            if lexeme in RESERVED_WORDS:
                return TokenType(lexeme), lexeme
            else:
                return TokenType.ID, lexeme
        elif self.state == 16:
            return TokenType.NUM, lexeme
        elif self.state == 17: # This is SIMPLE_SYMBOL, so using the lexeme we can get the token 
            return TokenType(lexeme), lexeme
        elif self.state == 18:
            return TokenType.OVER, '/'
        elif self.state == 20:
            return TokenType.LETH, '<'
        elif self.state == 21:
            return TokenType.LETHEQ, '<='
        elif self.state == 22:
            return TokenType.BITH, '>'
        elif self.state == 23:
            return TokenType.BITHEQ, '>='
        elif self.state == 24:
            return TokenType.ASSIGN, "="
        elif self.state == 25:
            return TokenType.EQ, "=="
        elif self.state == 26:
            return TokenType.NEQ, "!="
        elif self.state == 27:
            return TokenType.ENDFILE, "$"
        elif self.state == 28:
            return TokenType.ERROR, ""
        else:
            print(self.state)
            return None, "Error in returning the token from a final state"
        
        
    def _lex0(self, c):
        if c in LETTER:
            self.state = 1
        elif c in NUMBER:
            self.state = 2
        elif c in SIMPLE_SYM:
            self.state = 3
        elif c == '/':
            self.state = 4
        elif c == '<':
            self.state = 7
        elif c == '>':
            self.state = 9
        elif c == "=":
            self.state = 11
        elif c == "!":
            self.state = 13
        elif c == "$":
            self.state = 27
        elif c not in WHITE_SPACE:
            self._handleErrors(c)
            
    def _lex1(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS:
            self.state = 15
        elif c not in LETTER:
            self._handleErrors(c)
    
    def _lex2(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS:
            self.state = 16
        elif c not in NUMBER:
            self._handleErrors(c)
    
    def _lex3(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 17
        else:
            self._handleErrors(c)
    
    def _lex4(self, c):
        if c == "*":
            self.state = 5
        elif c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 18
        else:
            self._handleErrors(c)
    
    def _lex5(self, c):
        if c == '*':
            self.state = 6
        elif c == '$':
            self.state = 27
    
    def _lex6(self, c):
        if c == '/':
            self.state = 19
        elif c == '$':
            self.state = 27
        else:
            self.state = 5
    
    def _lex7(self, c):
        if c == '=':
            self.state = 8
        elif c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 20
        else:
            self._handleErrors(c)
    
    def _lex8(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 21
        else:
            self._handleErrors(c)

    def _lex9(self, c):
        if c == '=':
            self.state = 10
        elif c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 22
        else:
            self._handleErrors(c)
    
    def _lex10(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 23
        else:
            self._handleErrors(c)

    def _lex11(self, c):
        if c == '=':
            self.state = 12
        elif c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 24
        else:
            self._handleErrors(c)

    def _lex12(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 25
        else:
            self._handleErrors(c)
            
    def _lex13(self, c):
        if c == '=':
            self.state = 14
        else:
            self._handleErrors(c)
    
    def _lex14(self, c):
        if c in WHITE_SPACE or c in OPERATORS or c in SPECIAL_SYMBOLS or c in LETTER or c in NUMBER:
            self.state = 26
        else:
            self._handleErrors(c)

# Zack's HLSL to FlatOut 2 ps.1.1 Assembly Converter
# Version 1.2

try:
    from tkinter import filedialog
except:
    from Tkinter import filedialog

import time
import os

tstruct = time.gmtime(time.time())

filename = filedialog.askopenfilename(filetypes = (("HLSL Script","*.hlsl"),("All files","*.*")))

if not filename:
    raise Exception("Cancelled.")

newfilename = filename[:-4] + "sha"

author = ""
secondStep = True

class HVar:
    def __init__(self, name, register, value):
        self.name = name
        self.register = register
        self.value = value

    def __eq__(self, other):
        return self.name == other


    def __str__(self):
        return "[" + self.name + "]"

    def __repr__(self):
        return "[" + self.name + "]"

class FVar:
    def __init__(self, name, code):
        self.name = name
        self.code = code

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        return self.name


class AVar:
    def __init__(self, name, code):
        self.name = name
        self.code = code

linenum = 1
col = 0
scope = "global"
typeOfExpr = ""

def Error(message):
    print("Error in " + scope + " line " + str(linenum) + " (" + typeOfExpr + "): " + message)

def every(string1, string2):
    return all([(char in string2) for char in string1])
        

dhvars = [HVar("SHADOW", "c2", ""), HVar("AMBIENT", "v0", ""), HVar("FRESNEL", "v0.a", ""), HVar("BLEND", "v1.a", "")]
hvars = []
fvars = []
avars = [AVar("dot", "dp3\t%0, %1, %2"), AVar("lerp", "lrp\t%0, %3, %1, %2"), AVar("mad", "mad\t%0, %1, %2, %3"), AVar("length", "dp3\t%0, %1, %1"), AVar("distance", "sub\t%0, %1, %2\ndp3\t%0, %0, %0"), AVar("dst", "sub\t%0, %1, %2\ndp3\t%0, %0, %0")]

scopeSnapshot = []

def HVarNameToRegister(name):
    print(name)
    allhvars = dhvars + hvars
    ext = ""
    if "." in name:
        ext = "." + name.split(".")[1].strip()
        name = name.split(".")[0].strip()

    if name in allhvars:
        return allhvars[allhvars.index(name)].register + ext
    Error("Unknown Variable: [" + name + "]")
    return ""

def HVarRegisterToName(register):
    allhvars = dhvars + hvars
    for hv in allhvars:
        if hv.register == register:
            return hv.name
    return ""

def GetFVar(name):
    return fvars[fvars.index(name)]

constants = 3


def IsDef(line):
    return line.split(" ")[0] in ['float' + str(i) for i in range(2, 5)]

def IsFunc(line):
    return "(" in line
            
def IsConst(line):
    for i in range(2, 5):
        if "float" + str(i) + "(" in line:
            return True
    return False

def TokenType(char):
    if char in "01234567890":
        return "n"

    if char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return "a"

    if char in "+-*/=":
        return "o"

    return "u"

def IsOp(text):
    return "+" in text or "-" in text or "*" in text or ""

def IsCall(text):
    return "(" in text

# Split the text into strings of [token, operation, token]
def ShuntYardish(text):
    ts = []
    current = 0
    for char in text:
        if TokenType(char) != current:
            if current == 'n':
                if char in ".fF":
                    ts[-1].append(char)
                    continue
            if current == 'a':
                if TokenType(char) == 'n':
                    ts[-1].append(char)
                    continue
            ts.append("")

        ts[-1].append(char)
        current = TokenType(char)
    return ts


# returns the ) to the ( that you give it in a string, basically it skips nested parenthasis
def GetParEnd(string, index):
    layer = 0
    while True:
        if string[index] == ")":
            if not layer: break
            layer -= 1

        if string[index] == "(":
            layer += 1
        index += 1
    return index

def AllocateRegister():
    r = "r0"
    if r0 != "":
        r = "r1"
    return r

def GetOperands(string, dex):
    s = string.find(" ", dex)
    return [ string[max(string.rfind(" ", dex), 0):dex] , string[dex + 1:(s if s != -1 else len(string))]]

modifs = [("saturate", "sat"), ("d2", "d2"), ("x2", "x2"), ("x4", "x4")]

def GetFirstModif(string):
    result = ""
    dex = 999999999999
    for m in modifs:
        if m[0] + "(" in string:
            if string.index(m[0] + "(") < dex:
                result = m
                dex = string.index(m[0] + "(")
    return result
            

# Returns assembly code
def CompileOperand(string, ext="", dst=""):
    string = string.strip()
    sembly = ""
    ops = ["*mul", "-sub", "+add"]
    reg = ""
    mathed = False

    while (m := GetFirstModif(string)):
        #print(m, (m + "(") in string)
        if (m[0] + "(") in string:
            dex = string.index(m[0] + "(") + len(m[0]) + 1
            end = GetParEnd(string, dex)
            inner = string[dex:end]
            #print(inner)
            return CompileOperand(inner, "_" + m[1] + ext, dst)

    if "?" in string:
        dex = string.index("?") + 1
        inner = string[dex:].split(":")
        if dst == "":
                dst = AllocateRegister()
        return [dst, "cnd" + ext + "\t" + ", ".join([dst, "r0.a", HVarNameToRegister(inner[0].strip()), HVarNameToRegister(inner[1].strip())]) + "\n"]
    
    for av in avars:
        if av.name + "(" in string:
            dex = string.index(av.name + "(") + len(av.name) + 1
            end = GetParEnd(string, dex)
            inner = [item.strip() for item in string[dex:end].split(",")]
            end = av.code
            
            if dst == "":
                dst = AllocateRegister()

            end = end.replace("%0", dst)
            end = end.replace("\t", ext + "\t")
            for dex, item in enumerate(inner):
                end = end.replace("%" + str(dex + 1), HVarNameToRegister(item))
            return [dst, end + "\n"]

    string = string.replace("(", "").replace(")", "")
            
    if "/" in string:
        if string[string.index("/") + 1:].strip() != "2":
            Error("Dividing can only be done by 2. It has to be used like saturate() where it's an addon to a math expression or another function, such as (a + b) / 2")
        return CompileOperand(string.split("/")[0].strip(), "_d2" + ext, dst)

    if "*" in string:
        val = string[string.rfind("*") + 1:].replace(" ", "")
        
        if val == "2":
            ext = "_x2" + ext
            mathed = True
        elif val == "4":
            ext = "_x4" + ext
            mathed = True
        if mathed:
            return CompileOperand(string[:string.rfind("*")], ext, dst)

    for op in ops:
        if op[0] in string:
            if dst == "":
                dst = AllocateRegister()
            these = string.split(op[0])
            sembly += op[1:] + ext + "\t" + dst + ", " + HVarNameToRegister(these[0].strip()) + ", " + HVarNameToRegister(these[1].strip()) + "\n"
            mathed = True
            break

    

    if not mathed:
        val = HVarNameToRegister(string)
        if dst == "":
            dst = AllocateRegister()
        if val != dst:
            return [dst, "mov" + ext + "\t" + dst + ", " + val + "\n"]
        return [dst, ""]
    return [dst, sembly]

def ArrangeMad(muls, adds):
    i = adds.index(muls[0], 1)
    return (adds[0], muls[1], muls[2], adds[1 if i == 2 else 2])

# the real rfind is not working for some reason, now I have to roll my own knock-off version
def RFind(haystack, needle, start=-1):
    if start == -1:
        start = len(haystack) - len(needle)
    if needle in haystack:
        for i in range(start, 0, -2):
            if haystack[i:i+len(needle)] == needle:
                return i
    return -1

isPixelShader = True

maxR = 2
maxT = 4
maxV = 2
maxC = 5

# This function optimizes the assembly code that the compiler output.
# It turns multiplies and adds into mads, and skips the middle man when a result is mov'd somewhere
def SecondPass(script):
    r0Read = 0
    r1Read = 0
    tempScript = ""
    dex = 0

    # Checking for shader validation
    # Compilation in FO2 will fail if a temporary register (a variable in this case) is read from twice in a row without being written to.
    for line in script.split("\n"):
        args = [item.strip() for item in script[script.index("\t") + 1:].split(",")]
        if any("r0" in item for item in args[1:]):
            if r0Read:
                Error("FO2 Warning: Shader validation will fail if a temporary register (" + HVarRegisterToName("r0") + " in this case) is read from twice in a row.")
            else:
                r0Read += 1

        if "r0" in args[0]:
            r0Read -= 1
        
        if any(("r1" in item) for item in args[1:]):
            if r1Read:
                Error("FO2 Warning: Shader validation will fail if a temporary register (" + HVarRegisterToName("r1") + " in this case) is read from twice in a row.")
            else:
                r1Read += 1

        if "r1" in args[0]:
                r1Read -= 1
            
    
    while (mdex := script.find("mul", dex)) != -1:
        mdex = script.index("mul", dex)
        tdex = script.index("\n", mdex)
        muls = script[mdex + 4:tdex].split(",")
        muls = [item.strip() for item in muls]
        if script[tdex + 1:tdex + 4] == "add":
            adds = script[script.index("\t", tdex + 1) + 1:script.index("\n", tdex + 1)].split(",")
            adds = [item.strip() for item in adds]
            if muls[0] in adds[1:]:
                mads = [item.strip() for item in ArrangeMad(muls, adds)]             
                tempScript = script[:mdex] + "mad"
                sdex = script.index("\n", tdex + 1)
                if script[tdex + 4] == '_':
                    tempScript += "_" + script[tdex + 5:script.index("\t", tdex+5)]
                tempScript += "\t"
                tempScript += ', '.join(mads)
                tempScript += script[sdex:]
                script = tempScript
        dex = mdex + 1

    dex = 0
    while (mdex := script.find("mov", dex)) != -1:
        sdex = RFind(script, "\n", mdex - 2)
        tdex = script.find("\t", sdex)
        if tdex != -1:
            muls = script[tdex + 1:script.index("\n", tdex)].split(",")
            dst = ((script[script.index(",", mdex) + 1:script.index("\n", mdex + 1)].strip()) if script.find("\n", mdex + 1) != -1 else script[script.index(",", mdex) + 1:].strip())
            # Checks if the src of the MOV is the same as the dst of the previous instruction, and skips the middle man if that's the case
            if script[tdex + 1:tdex + 3] == dst:
                tgt = script[mdex + 3:script.index(",", mdex)]
                script = script[:tdex] + tgt + ", " + ", ".join([item.strip() for item in muls[1:]])

        dex = mdex + 1
    return script

def HandleAssign(line):
    for symb in ["*=", "+=", "-="]:
        if symb in line:
            splt = [item.strip() for item in line.split(symb)]
            return splt[0] + " = " + splt[0] + " " + symb[0] + " " + splt[1]
    return line

def CompileHLSL(script, hv=-1):
    global linenum, col, scope, r0, r1, typeOfExpr
    global constants
    if hv == -1:
        hv = []

    mode = 1
    temp = 0
    liner = 0
    output = ""
    buffer = ""
    for char in script:

        if mode:
            if liner:
                if liner == 1:
                    if char != '\n': continue
                    liner = 0
                else:
                    buffer += char
                    if buffer[-2:] != "*/": continue
                    liner = 0

            if buffer:
                if buffer[-1] == '/':
                    if char == '/':
                        buffer = buffer[:-1]
                        liner = 1
                        continue

                    if char == '*':
                        buffer = buffer[:-1]
                        liner = 1
                        continue

        if char == '\n':
            linenum += 1
            col = 0

        col += 1

        # Checking for assembly
        if buffer[-4:-1] == "asm" and buffer[-1] in "\t\n {":
            buffer = ""
            mode = 0
            continue

        # Reading Assembly
        if not mode:
            if char == "}":
                print("Exited normally")
                mode = 1
                continue

            if char == "{": continue

            if output != "":
                if (char in " \t\n") and (output[-1] == '\n'): continue
            output += char
            continue

        # Reading Function
        elif mode == 2:
           
            if char == '}':
                if not temp:
                    #print(buffer.strip())
                    fvars[-1].code = CompileHLSL(buffer.strip())
                    buffer = ""
                    mode = 1
                    continue
                else:
                    temp -= 1
            if char == '{':
                temp += 1
            buffer += char

        # Reading HLSL
        else:
            if buffer:
                if (char == ' ' and char == buffer[-1]):
                    continue

            if char in '\t\n':
                continue

            if char == ';':
                line = buffer
                buffer = ""

                if not line.strip(): continue
                line = line.strip()

                line = HandleAssign(line)

                # Checking for new variables or functions
                if IsDef(line):
                        typeOfExpr = "Definition"
                        tokens = line.split(" ")
                        if tokens[1] in hvars:
                            Error("Syntax error: re-definition of [" + tokens[1] + "]")
                            break

                        # Defining a constant variable
                        if IsConst(line):
                            typeOfExpr = "Defining Constant"
                            if constants > 7:
                                Error("Too many constants defined, there can only be 5, since the game reserves 3 of them")
                                break
                            hvars.append(HVar(tokens[1], "c" + str(constants), line.split("=")[1].strip()))
                            constants += 1

                        
                        else:
                            # Defining variable variable
                            typeOfExpr = "Defining Variable"
                            if tokens[2].strip() == "=":
                                
                                tokens[2] = line[line.index("=") + 1:].strip()
                                r = CompileOperand(tokens[2])
                                hvars.append(HVar(tokens[1], r[0], ""))
                                output += r[1]
                                match r[0]:
                                    case "r0":
                                        r0 = tokens[2]
                                    case "r1":
                                        r1 = tokens[2]
                                continue
                            # Defining function
                            else:
                                typeOfExpr = "Defining Function"
                                tokens[1] = line[line.index(" ") + 1:line.index("(")]
                                if tokens[1] in fvars:
                                    Error("Redefinition of function: [", tokens[1] + "]")
                                    break
                                else:
                                    fvars.append(FVar(tokens[1], ""))
                                    scope = tokens[1]
                                    mode = 2
                                    buffer = ""
                                    continue

                else:
                    tokens = line.split(" ")
                    match tokens[0]:
                        case "return":
                            typeOfExpr = "Return"
                            r = CompileOperand(line[7:], "", "r0")
                            
                            output += r[1]
                            '''
                            print("[" + r[0] + "]")
                            if r[0].strip() != "r0":
                                output += "mov\tr0, " + r[0]
                            '''
                            continue

                    # Assigning pre-existing variable
                    if tokens[1] == '=':
                        typeOfExpr = "Assign"
                        if tokens[0].strip() not in hvars + dhvars:
                            if IsConst(line):
                                hvars.append(HVar(tokens[1], "c" + str(constants), line.split("=")[1].strip()))
                                constants += 1
                            else:
                                hvars.append(HVar(tokens[1], AllocateRegister(), ""))
                        output += CompileOperand(line[line.index("=") + 1:], "", HVarNameToRegister(tokens[0].strip()))[1]

            else:
                buffer += char
    
    return SecondPass(output)

r0 = ""
r1 = ""

hlsl = ""
pixelshader = ""
vertexshader = ""

textures = 0

def HasPS(script):
    return "PixelShader(" in script

def HasVS(script):
    return "VertexShader(" in script

vsm = []

def SafeGet(lst, dex):
    if len(lst) < dex:
        return lst[dex]
    return ""

mtime = 0

stuckInLoop = True

createFullFile = True#input("Create full SHA file(y) or Just print the pixel shader(n)") in "yY"

print("This script can loop so that when the hlsl file changes it'll automatically re-compile.")
stayInLoop = input("Do you want to enable that? (y/N)") in "Yy"

while stuckInLoop:

    stuckInLoop = stayInLoop
    
    if os.path.getmtime(filename) != mtime:
        mtime = os.path.getmtime(filename)
        hvars = []
        fvars = []
        constants = 3
        r0 = ""
        r1 = ""
        linenum = 0
        col = 0
        pixelshader = ""
        vertexshader = ""
        hlsl = ""
        time.sleep(0.5)
        with open(filename) as file:
            hlsl = file.read()

            if HasPS(hlsl):
                vdex = hlsl.index("PixelShader(")
                
                inputs = hlsl[hlsl.index("(", vdex) + 1:hlsl.index(")", vdex)].strip().replace("  ", " ")
                inputs = inputs.split(",")
                if inputs[0].strip() == "":
                    textures = 0
                else:
                    textures = len(inputs)

                if textures:
                    for i, put in enumerate(inputs):
                        if " " in put.strip():
                            put = put.strip().split(" ")[1].strip()
                        hvars.append(HVar(put.strip(), "t" + str(i), "debug"))

                pixelshader = hlsl[hlsl.index("{", vdex) + 1 : hlsl.index("}", vdex)].strip()
            
            if HasVS(hlsl):
                vdex = hlsl.index("VertexShader(")
                vsm = [ i.strip().split(" ")[1] for i in hlsl[vdex + 19:hlsl.index(")", vdex)].replace("inout", "").replace("in", "").replace("out", "").split(",")]
                vertexshader = hlsl[hlsl.index("{", vdex) + 1 : hlsl.index("}", vdex)].strip()


        passbuffer = ""

        if createFullFile:
            with open(newfilename, "w") as sfile:
                sfile.write("///////////////////////////////////////////////////////////////////////////\n")
                sfile.write("// Created on " + str(tstruct.tm_mon) + "/" + str(tstruct.tm_mday) + "/" + str(tstruct.tm_year) + " " + str((tstruct.tm_hour if tstruct.tm_hour < 13 else tstruct.tm_hour - 12)) + ":" + str(tstruct.tm_min).rjust(2, "0") + ":" + str(tstruct.tm_sec).rjust(2, "0") + " " + ("PM" if tstruct.tm_hour > 12 else "AM") + "\n")
                sfile.write("//\n")
                sfile.write("// Generated with Zack's HLSL-to-FlatOut-2-Pixel-Shader v1.2\n")
                sfile.write("///////////////////////////////////////////////////////////////////////////\n")

                for i in range(textures):
                    sfile.write("Texture Tex" + str(i) + ";\n")

                sfile.write("\nconst string inputStreamFormat = \"PosColorTex1\";\n\n")

                sfile.write("vertexshader vSdr =\n\tdecl\n\t{\n\t\tstream 0;\n\t\tfloat\tv0[3];  // Position\n\t\tD3DCOLOR v2;\t // Diffuse\n\t\tfloat\tv3[2];  // Tex coord 0\n\t}\n\tasm\n\t{\n")
                sfile.write("\t\tvs.1.1\n")

                
                if vertexshader != "":
                    scope = "Vertex Shader"
                    for line in CompileHLSL(vertexshader).split("\n"):
                        sfile.write("\t\t" + line + "\n")

                sfile.write("\n\t};\n\n")

                for hvar in hvars:
                    if hvar.register[0] == 'c':
                        passbuffer += "\t\tVertexShaderConstantF[" + hvar.register[1:] + "] = " + hvar.value + ";\n"

                

                if pixelshader != "":
                    scope = "Pixel Shader"
                    sfile.write("pixelshader pSdr =\n\tasm\n\t{\n")
                    sfile.write("\t\tps.1.1\n")
                    sfile.write("\n")
                    assemble = CompileHLSL(pixelshader)
                    for i in range(textures):
                        sfile.write("\t\ttex\tt" + str(i) + "\t// " + HVarRegisterToName("t" + str(i)) + "\n")
                    sfile.write("\n")
                    for line in assemble.split("\n"):
                        sfile.write("\t\t" + line + "\n")
                    sfile.write("\n\t};\n\n")

                for hvar in hvars:
                    if hvar.register:
                        if hvar.register[0] == 'c':
                            passbuffer += "\t\tPixelShaderConstantF[" + hvar.register[1:] + "] = " + hvar.value + ";\n"

                sfile.write("Technique T0\n")
                sfile.write("{\n")
                sfile.write("\tPass P0\n")
                sfile.write("\t{\n")
                sfile.write(passbuffer)
                sfile.write("\n")

                for i in range(textures):
                    sfile.write("\t\tTexture[" + str(i) + "] = <Tex" + str(i) + ">;\n")
                
                sfile.write("\n\t\tVertexShader = <vSdr>;\n")
                sfile.write("\t\tPixelShader = <pSdr>;\n")
                sfile.write("\t}\n}")
                print("Done!")
        else:
            if pixelshader != "":
                    print(CompileHLSL(pixelshader))





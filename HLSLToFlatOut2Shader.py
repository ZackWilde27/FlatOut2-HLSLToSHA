# Zack's HLSL to FlatOut 2 ps.1.1 Assembly Converter
# Version 1.3

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

newfilename = filename[:filename.index(".")] + ".sha"

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
avars = [AVar("dot", "dp3\t%0, %1, %2"), AVar("lerp", "lrp\t%0, %3, %1, %2"), AVar("mad", "mad\t%0, %1, %2, %3")]

# You can have both HLSL defines and Assembly defines.
# HLSL defines get replaced before being compiled in HLSL. Assembly defines allow you to add your own entries to avars.
defines = []

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

def IsOp(text):
    return "+" in text or "-" in text or "*" in text or ""

def IsCall(text):
    return "(" in text


# returns the ) to the ( that you give it in a string, basically it skips nested parenthasis
def GetParEnd(string, index, par="()"):
    layer = 0
    while index < len(string):
        if string[index] == par[1]:
            if not layer: break
            layer -= 1

        if string[index] == par[0]:
            layer += 1
        index += 1
    return index

def AllocateRegister():
    for i, item in enumerate(rStatus):
        if not item:
            return "r" + str(i)
    return "r" + str(maxR - 1)

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

# Removes vector splitting to get just the variable
def StripSplit(string):
    return string.split(".")[0].strip()

# This function optimizes the assembly code that the compiler output.
# It turns multiplies and adds into mads, and skips the middle man when a result is mov'd somewhere
def SecondPass(script):
    rReads = [0 for i in range(maxR)]
    tempScript = ""
    dex = 0

    script = script.replace("\n\n", "\n")

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

def CompileHLSL(script, hv=-1, dst="r0"):
    global linenum, col, scope, r0, r1, typeOfExpr, hvars
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
                    avars[-1].code = CompileHLSL(buffer.strip(), -1, "%0")
                    buffer = ""
                    mode = 1
                    hvars = [item for item in scopeSnapshot]
                    continue
                else:
                    temp -= 1
            if char == '{':
                temp += 1
            buffer += char
            continue
            

        # Reading HLSL
        elif mode == 1:
            if buffer:
                if (char == ' ' and char == buffer[-1]):
                    continue

            

            if char in '\t\n':
                continue

            if char == ';' or char == "{":
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
                                Error("Too many constants defined, there can only be " + str(maxC - 3) + ", since the game reserves 3 of them")
                                break
                            hvars.append(HVar(tokens[1], "c" + str(constants), line.split("=")[1].strip()))
                            constants += 1

                        
                        else:
                            # Defining variable variable
                            typeOfExpr = "Defining Variable"
                            if len(tokens) > 2:
                                if tokens[2].strip() == "=":
                                
                                    tokens[2] = line[line.index("=") + 1:].strip()
                                    r = CompileOperand(tokens[2])
                                    hvars.append(HVar(tokens[1], r[0], ""))
                                    output += r[1]
                                    rStatus[int(r[0][1:])] = True
                                    continue

                            # Defining function
                            typeOfExpr = "Defining Function"
                            tokens[1] = line[line.index(" ") + 1:line.index("(")]
                            if tokens[1] in fvars:
                                Error("Redefinition of function: [", tokens[1] + "]")
                                break
                            else:
                                avars.append(AVar((tokens[1][tokens[1].index("(") + 1:] if "(" in tokens[1] else tokens[1]), ""))
                                args = [item.strip() for item in line[line.index("(") + 1:line.index(")")].split(",")]
                                
                                scope = tokens[1]
                                scopeSnapshot = [item for item in hvars] # Creating a new list instead of a reference
                                if args:
                                    hvars += [HVar(item.split(" ")[-1], "%" + str(i + 1), "") for i, item in enumerate(args)]
                                temp = 0
                                mode = 2
                                buffer = ""
                                continue

                else:
                    tokens = line.split(" ")
                    match tokens[0]:
                        case "return":
                            typeOfExpr = "Return"
                            r = CompileOperand(line[7:], "", dst)
                            
                            output += r[1]
                            continue

                    # Assigning pre-existing variable
                    if tokens[1] == '=':
                        typeOfExpr = "Assign"
    
                        if tokens[0].strip() in hvars + dhvars:
                            output += CompileOperand(line[line.index("=") + 1:], "", HVarNameToRegister(tokens[0].strip()))[1]
                        else:
                            typeOfExpr = "Defining Variable"
                            if IsConst(line):
                                typeOfExpr = "Defining Constant"
                                hvars.append(HVar(tokens[1], "c" + str(constants), line.split("=")[1].strip()))
                                constants += 1
                            else:
                                r = CompileOperand(line[line.index("=") + 1:].strip())
                                hvars.append(HVar(tokens[1], r[0], ""))
                                output += r[1]
                                rStatus[int(r[0][1:])] = True
                                continue
                        
                        

            else:
                buffer += char
    
    return SecondPass(output)

r0 = ""
r1 = ""

rStatus = [False for i in range(maxR)]

hlsl = ""
pixelshader = ""
vertexshader = ""

textures = 0

def GetShader(script, isPS):
    dex = -1
    ar = []
    for possibility in (["PixelShader", "psMainD3D9", "psMain"] if isPS else ["VertexShader", "vsMainD3D9", "vsMain", "main"]):
        if possibility + "(" in script:
            dex = script.index(possibility + "(")
            ar = script[dex + len(possibility) + 1:script.index(")", dex)].split(",")
            break
    if dex != -1:
        return (ar, script[script.index("{", dex) + 1:GetParEnd(script, script.index("{", dex), "{}") - 1])
    return [[], ""]


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
        rStatus = [False for i in range(maxR)]
        linenum = 0
        col = 0
        pixelshader = ""
        vertexshader = ""
        hlsl = ""
        time.sleep(0.5)
        with open(filename) as file:
            hlsl = file.read()

        (inputs, pixelshader) = GetShader(hlsl, True)
        if pixelshader:
            if inputs[0].strip() == "":
                textures = 0
            else:
                textures = len(inputs)

            if textures:
                for i, put in enumerate(inputs):
                    if " " in put.strip():
                        put = put.strip().split(" ")[1].strip()
                    dhvars.append(HVar(put.strip(), "t" + str(i), "debug"))


        vertexshader = GetShader(hlsl, False)[1]


        passbuffer = ""

        if createFullFile:
            with open(newfilename, "w") as sfile:
                sfile.write("///////////////////////////////////////////////////////////////////////////\n")
                sfile.write("// Created on " + str(tstruct.tm_mon) + "/" + str(tstruct.tm_mday) + "/" + str(tstruct.tm_year) + " " + str((tstruct.tm_hour if tstruct.tm_hour < 13 else tstruct.tm_hour - 12)) + ":" + str(tstruct.tm_min).rjust(2, "0") + ":" + str(tstruct.tm_sec).rjust(2, "0") + " " + ("PM" if tstruct.tm_hour > 12 else "AM") + "\n")
                sfile.write("//\n")
                sfile.write("// Generated with Zack's HLSL-to-FlatOut-2-Pixel-Shader v1.3\n")
                sfile.write("///////////////////////////////////////////////////////////////////////////\n")

                for i in range(textures):
                    sfile.write("Texture Tex" + str(i) + ";\n")

                sfile.write("\nconst string inputStreamFormat = \"PosColorTex1\";\n\n")

                sfile.write("vertexshader vSdr =\n\tdecl\n\t{\n\t\tstream 0;\n\t\tfloat\tv0[3];  // Position\n\t\tD3DCOLOR v2;\t // Diffuse\n\t\tfloat\tv3[2];  // Tex coord 0\n\t}\n\tasm\n\t{\n")
                sfile.write("\t\tvs.1.1\n")

                
                if vertexshader != "":
                    scope = "Vertex Shader"
                    maxR = 12
                    maxC = 96
                    maxV = 16
                    for line in CompileHLSL(vertexshader).split("\n"):
                        sfile.write("\t\t" + line + "\n")

                sfile.write("\n\t};\n\n")

                for hvar in hvars:
                    if hvar.register[0] == 'c':
                        passbuffer += "\t\tVertexShaderConstantF[" + hvar.register[1:] + "] = " + hvar.value + ";\n"

                

                if pixelshader != "":
                    scope = "Pixel Shader"
                    maxR = 2
                    maxC = 8
                    maxV = 2
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

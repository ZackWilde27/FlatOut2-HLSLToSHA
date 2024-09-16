# Zack's HLSL to FlatOut SHA
version = "v2.21"
# Am I particularly proud of this code? uhh

try:
    from tkinter import filedialog
except:
    from Tkinter import filedialog

import time
import os

filename = ""
author = ""
authors = "" # I accidentally made a typo in the original settings file so it's a feature now
loop = ""
is24Hour = False
isPixelShader = True
noOptimizations = False
includeComments = True
vertexConstants = 32

class HVar:
    def __init__(self, name, register, value, tyype):
        # The HLSL keyword it's associated with
        self.name = name
        # The assembly keyword it's associated with, could be "r0", "t0", or "oPos.yyy"
        self.register = register
        # Reserved for constants, this what came after the =, for example "float4(0.0f, 0.0f, 0.0f, 0.0f)"
        self.value = value
        # The first letter of the type, followed by the number of components, from 1-4. a float4 would be an f4 while an int3 would be an i3. Matrices start with m
        self.type = tyype
        # When packing multiple constants into a single register, the offset makes them reference the correct components
        self.offset = 0

    def __eq__(self, other):
        return self.name == other


    def __str__(self):
        return "[" +  ", ".join([self.name, self.register, self.value, self.type]) +"]"

    def __repr__(self):
        return "[" +  ", ".join([self.name, self.register, self.value, self.type]) +"]"

class HStruct:
    def __init__(self, name, properties):
        self.name = name
        self.properties = properties
        

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        return self.name

class HFunc:
    def __init__(self, name, code):
        self.name = name
        self.code = code

linenum = 1
# I originally included the column number as well, but because it reads per-statement, the column will always be the semi-colon at the end of the line.
col = 0
scope = "global"
typeOfExpr = ""
constants = 3
startC = 3


def Error(message):
    print("Error in", scope, "line", str(linenum), "(" + typeOfExpr + "):", message)

def every(string1, string2):
    return all([(char in string2) for char in string1])
        

# the %split% marks where the user-defined dhvars begin
dhvars = [HVar("SHADOW", "c2", "", "f4"), HVar("AMBIENT", "v0", "", "f3"), HVar("FRESNEL", "v0.a", "", "f1"), HVar("BLEND", "v1.a", "", "f1"), HVar("%split%", "", "", "")]
hvars = []
fvars = []
hfuncs = [HFunc("dot", "dp3\t%0, %1, %2"), HFunc("lerp", "lrp\t%0, %3, %1, %2"), HFunc("mad", "mad\t%0, %1, %2, %3")]

def ResetDHVars(isPS=isPixelShader):
    global dhvars
    dhvars = dhvars[dhvars.index("%split%"):]
    dhvars = ([HVar("SHADOW", "c2", "", "f4"), HVar("AMBIENT", "v0", "", "f3"), HVar("FRESNEL", "v0.a", "", "f1"), HVar("BLEND", "v1.a", "", "f1"), HVar("EXTRA", "v1", "", "f3")] if isPS else [HVar("FRESNEL", "oD0.a", "", "f1"), HVar("AMBIENT", "oD0.xyz", "", "f3"), HVar("BLEND", "oD1.a", "", "f1"), HVar("EXTRA", "oD1.xyz", "", "f3"), HVar("CAMERA", "c8", "", "f3")]) + dhvars

def PSTexToVSTex():
    for dhvar in dhvars:
        if dhvar.register:
            if dhvar.register[0] == "t":
                dhvar.register = "oT" + dhvar.register[1:]

def ResetAVars(isPS=isPixelShader):
    global hfuncs
    hfuncs = [HFunc("dot", "dp3\t%0, %1, %2"), HFunc("lerp", "lrp\t%0, %3, %2, %1"), HFunc("mad", "mad\t%0, %1, %2, %3")] if isPS else [HFunc("dot", "dp%tn1\t%0, %1, %2"), HFunc("dot3", "dp3\t%0, %1, %2"), HFunc("dot4", "dp4\t%0, %1, %2"), HFunc("mad", "mad\t%0, %1, %2, %3"), HFunc("exp2", "expp\t%0, %1"), HFunc("exp2_full", "exp\t%0, %1"), HFunc("frac", "frc\t%0, %1"), HFunc("max", "max\t%0, %1, %2"), HFunc("min", "min\t%0, %1, %2"), HFunc("log2", "logp\t%0, %1"), HFunc("log2_full", "log\t%0, %1"), HFunc("rcp", "rcp\t%0,%1"), HFunc("rsqrt", "rsq\t%0, %1"), HFunc("distance", "dst\t%0, %1"), HFunc("dst", "dst\t%0, %1"), HFunc("abs", "max\t%0, %1, -%1"), HFunc("degrees", "rcp\t%z.x, c95.x\nmul\t%0, %z.x, %1"), HFunc("step", "sge\t%0, %1, %2"), HFunc("floor", "frc\t%z.w, %1\nsub\t%0, %1, %z.w"), HFunc("radians", "mul\t%0, c95.x, %1"), HFunc("lit", "mov\t%z.x, %1\nmov\t%z.y, %2\nmov\t%z.w, %3\nlit\t%0, %z"), HFunc("fresnel", "dp3\t%z.x, %1, %2\nmax\t%z.x, -%z.x, %z.x\nsub\t%z.x, c95.y, %z.x\nmul\t%z.x, %z.x, %z.x\nmul\t%z.x, %z.x, %z.x\nmul\t%0, %z.x, %z.x\n"), HFunc("reflect", "dp3\t%z.x, %1, %2\nadd\t%z.x, %z.x, %z.x\nmul\t%z, %z.x, %2\nsub\t%0, %1, %z"), HFunc("normalize", "dp3\t%z.a, %1, %1\nrsq\t%z.a, %z.a\nmul\t%0, %1, %z.a"), HFunc("lerp", "sub\t%z, %2, %1\nmad\t%0, %z, %3, %1"), HFunc("length", "dp3\t%z.a, %1, %1\nrsq\t%z.a, %z.a\nrcp\t%0, %z.a"), HFunc("clamp", "min\t%z, %1, %3\nmax\t%0, %z, %2"), HFunc("sqrt", "rsq\t%z, %1\nrcp\t%0, %z"), HFunc("RotateToWorld", "m3x%tn0\t%0, %1, c4"), HFunc("LocalToWorld", "m4x%tn0\t%0, %1, c4"), HFunc("WorldToView", "m4x%tn0\t%0, %1, c0"), HFunc("WorldToScreen", "m4x%tn0\t%0, %1, c0"), HFunc("LocalToScreen", "m4x%tn0\t%0, %1, c0")]

def TokenType(char, lastChar):
    if char in "01234567890.":
        return "n"

    if char in "+-*/":
        return "o"

    return "a"

# Finds the item in list1 and retrieves the corrosponding item in list2
def Translate(list1, list2, item):
    return list2[list1.index(item)]

def Count(string, thing):
    return len(string.split(thing)) - 1

def HVarRegisterToVar(register):
    for v in hvars + dhvars:
        if v.register == register:
            return v
    return False

def OperatorPriority(char):
    return "/*+-".find(char)

def AddConstant(name, value, valtype="f", pack=True):
    global constants
    if constants >= maxC:
        Error("Too many constants defined, there can only be " + str(maxC - startC) + ", since the game reserves " + str(startC) + " of them")
        return ""

    if "(" in value:
        value = value[value.index("(") + 1:value.index(")")]

    vals = [item.strip() for item in value.split(",")]
    dimensions = len(vals)
    allDimensions = 0
    numConsts = 0

    valstring = ", ".join(vals)
    for hv in hvars + dhvars:
        if hv.type:
            if hv.type[0] == valtype:
                if valstring in hv.value:
                    offset = Count(hv.value[:hv.value.index(valstring)], ",")
                    
                        
                    newRegister = ""
                    if "." in hv.register:
                        newRegister = hv.register
                    else:
                        newRegister = hv.register + "." + "xyzw"[offset:offset + dimensions]

                    if "constant_" not in name:
                        hvars.append(HVar(name, newRegister, "", valtype + str(dimensions)))

                    return newRegister
                    
    
    while len(vals) < 4:
        vals.append("%x")

    newHVar = HVar(name, "", "", valtype + str(dimensions))
    
    if dimensions < 4 and pack:
        for c in range(startC, constants):
            allDimensions = 0
            numConsts = 0
            firstConst = False

            for hv in hvars + dhvars:
                if hv.type:
                    if hv.type[0] == valtype:
                        if hv.register == "c" + str(c):
                            numConsts += 1
                            firstConst = hv
                            allDimensions += len(hv.value.split("%x")) - 1
                            break

            if firstConst:
                if allDimensions >= dimensions:
                    if isPixelShader:
                        if dimensions == 1 and numConsts == 1 and ("%x" in firstConst.value):
                            newHVar.register = "c" + str(c)
                            newHVar.offset = 3
                            firstConst.value = firstConst.value[:firstConst.value.rfind("%x")] + vals[0] + firstConst.value[firstConst.value.rfind("%x") + 2:]
                            hvars.append(newHVar)
                            return newHVar.register + ".a"
                        else:
                            continue

                    newHVar.register = "c" + str(c)
                    newHVar.offset = 4 - allDimensions
                    for i in range(dimensions):
                        firstConst.value = firstConst.value.replace("%x", vals[i], 1)

                    hvars.append(newHVar)
                    chart = "xyzw"
                    return newHVar.register + (OffsetProperty("." + chart[:dimensions], newHVar.offset) if ("." not in newHVar.register) else "")


    newHVar.register = "c" + str(constants)
    constants += 1
    if isPixelShader and dimensions == 1:
        vals = vals[1:] + [vals[0]]
        newHVar.register += ".a"

    newHVar.value = Translate("fib", ["float", "int", "bool"], valtype)
    newHVar.value += "4(" + ", ".join(vals) + ")"
    hvars.append(newHVar)
    return newHVar.register

def IsType(string):
    if string:
        types = ["float", "int", "bool", "void"]

        for t in types:
            if string.split(" ")[0] in ([t + str(i) for i in range(2, 5)] + [t]):
                return True
    return False

def IsConst(line):
    if line:
        if line.split(" ")[0] == "const":
            return True

        if "=" in line:
            arg = line[line.index("=") + 1:].strip()
        else:
            arg = line

        if arg:
            if arg[0] in "01234567890." or arg in ["true", "false"]:
                if arg[:2] != "1-":
                    return True

            for i in range(2, 5):
                for t in ["float", "int", "bool"]:
                    if t + str(i) + "(" in arg:
                        return True
    return False

def BreakdownMath(line):
    tokes = [""]
    mode = 0
    bString = False
    for char in line:
        if char in ")]}":
            mode -= 1

        if char in "([{":
            mode += 1

        if char == "\"":
            mode += -1 if bString else 1
            bString = not bString
            
        if not mode:
            if char in "+-*":
                tokes[-1] = tokes[-1].strip()
                if tokes[-1]:
                    if tokes[-1] not in "+-*":
                        if tokes[-1][-1] not in "(,":
                            tokes.append(char)
                            tokes.append("")
                            continue
            
        tokes[-1] += char

    tokes = [item.strip() for item in tokes]

    i = 0
    while True:
        try:
            i = tokes.index("*", i)
        except ValueError:
            break

        if tokes[i + 1] in ["2", "4"]:
            tokes[i - 1] = tokes[i - 1] + tokes[i] + tokes[i + 1]
            tokes = tokes[:i] + tokes[i + 2:]

        i += 1

    i = 0
    while i < len(tokes):
        token = tokes[i]
        if token == "1":
            if i < (len(tokes) - 1):
                if tokes[i + 1] == "-":
                    tokes[i] = "\"1-" + HVarNameToRegister(tokes[i + 2]) + "\""
                    tokes = tokes[:i + 1] + tokes[i + 3:]
                    continue
        if IsConst(token):
            tokes[i] = "\"" + AddConstant("constant_" + str(constants), token) + "\""
        i += 1
        
    return tokes


scopeSnapshot = []
psSnapshot = []

# Just so that you can fill texture data with texture.uv = 
def HandleProperty(prop):
    return prop.replace("u", "x").replace("v", "y")

def OffsetProperty(prop, offset):
    chart = "xyzwrgba"
    output = ""
    for char in prop:
        if char == ".":
            output += char
        else:
            if char in chart:
                output += chart[chart.index(char) + offset]
    return output

def HVarNameToRegister(name):
    allhvars = dhvars + hvars
    ext = ""
    prefix = ""
    if name:
        if name[0] == name[-1] and name[0] == "\"":
            return name[1:-1]
        
        if "." in name:
            ext = "." + HandleProperty(name.split(".")[1].strip())
            name = name.split(".")[0].strip()

        if "-" in name:
            prefix = name[:name.index("-") + 1]
            name = name[name.index("-") + 1:]

        if name in allhvars:
            hv = Translate(allhvars, allhvars, name)
            if (hv.offset or int(hv.type[1:]) != 4) and (not ext) and ("." not in hv.register) and (hv.register[0] != "v") and (not isPixelShader):
                ext = "." + "xyzw"[hv.offset:hv.offset + int(hv.type[1:])]

            return prefix + hv.register + OffsetProperty(ext, hv.offset)

        Error("HVarNameToRegister(): Unknown Variable [" + name + "]")
    return ""

def HVarRegisterToName(register):
    allhvars = dhvars + hvars
    for hv in allhvars:
        if hv.register == register:
            return hv.name
    return ""

def HVarNameToVar(name):
    allhvars = dhvars + hvars
    for hv in allhvars:
        if hv.name == name:
            return hv
    return False

def GetFVar(name):
    return fvars[fvars.index(name)]

def IsDef(line):
    if line.split(" ")[0] == "const":
        line = line[6:].strip()

    types = ["float", "int", "bool", "void", "auto"]

    for t in types:
        if line.split(" ")[0] in ([t + str(i) for i in range(2, 5)] + [t]):
            return t[0]
    
    return False

def IsFunc(line):
    return "(" in line
            

def IsOp(text):
    return "+" in text or "-" in text or "*" in text or ""

def IsCall(text):
    return "(" in text

# Only replaces when there's space around the subject, makes absolutely sure it's not part of some other word
def CarefulReplace(text, replacer, replacee):
    # Doing something with it to make sure it's a copy
    script = text.replace("\n", "\n")

    if script[:len(replacer)] == replacer:
        script = replacee + script[len(replacer):]

    if script[-len(replacer):] == replacer:
        script = script[:-len(replacer)] + replacee

    spaces = "\n\t +-*/=(){},.;"

    for i in spaces:
        for j in spaces:
            script = script.replace(i + replacer + j, i + replacee + j)

    return script
            
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

# Returns the first unused register
# The offset allows for multiple unused registers to be allocated
def AllocateRegister(offset=0):
    try:
        return "r" + str(rStatus.index(False) + offset)
    except ValueError:
        Error("Ran out of registers to hold results, too much is being done in a single line")
        return "r" + str((len(rStatus) - 1))

def GetOperands(string, dex):
    s = string.find(" ", dex)
    return [ string[max(string.rfind(" ", dex), 0):dex] , string[dex + 1:(s if s != -1 else len(string))]]


modifs = [("saturate", "sat"), ("half", "d2"), ("double", "x2"), ("quad", "x4"), ("d2", "d2"), ("x2", "x2"), ("x4", "x4")]

def GetFirstModif(string):
    result = ""
    dex = 999999999999
    for m in modifs:
        if m[0] + "(" in string:
            if string.index(m[0] + "(") < dex:
                result = m
                dex = string.index(m[0] + "(")
    return result

def ResetModifs(isPS=isPixelShader):
    global modifs
    modifs = [("saturate", "sat"), ("half", "d2"), ("double", "x2"), ("quad", "x4"), ("d2", "d2"), ("x2", "x2"), ("x4", "x4")] if isPS else []

def CompileOperand(string, ext="", dst="", components=4):
    CompilePartial = CompileOperand_Partial
    unusedRegisters = 0
    if dst == "":
        dst = AllocateRegister(0)
        unusedRegisters = 1
    fullsembly = ""
    tokens = BreakdownMath(string)
    while len(tokens) > 1:
        if len(tokens) == 2:
            Error("There's no identifier after an operand, or the other way around")
        for i in [0, 2]:
            if "(" in tokens[i]:
                this = CompilePartial(tokens[i], "", AllocateRegister(unusedRegisters), 4)
                unusedRegisters += 1
                fullsembly += this[1]
                tokens[i] = "\"" + this[0] + "\""
                
            if "[" in tokens[i]:
                index = tokens[i][tokens[i].index("[") + 1:tokens[i].index("]")].strip()
                if any([char in index for char in "*+-/("]):
                    that = CompilePartial(index, "", AllocateRegister(unusedRegisters), 1)
                    unusedRegisters += 1
                    fullsembly += that[1]
                    fullsembly += "mov" + ext + "\ta0.x, \"" + that[0] + "\"\n" 
                else:
                    fullsembly += CompilePartial(index, "", "a0.x", 1)[1]
                tokens[i] = "\"c[a0.x + " + HVarNameToRegister(tokens[i][:tokens[i].index("[")].strip())[1:] + "]\""

        
        that = CompilePartial(" ".join(tokens[:3]), ext, dst, components)
        tokens = ["\"" + that[0] + "\""] + tokens[3:]
        fullsembly += that[1]
    if tokens:
        if "[" in tokens[0]:
            fullsembly += CompilePartial(tokens[0][tokens[0].index("[") + 1:tokens[0].index("]")].strip(), "", "a0.x", 1)[1]
            tokens[0] = "\"c[a0.x + " + HVarNameToRegister(tokens[0][:tokens[0].index("[")].strip())[1:] + "]\""
        fullsembly += CompilePartial(tokens[0], ext, dst, components)[1]
    return [dst, fullsembly]


def GetRegisterType(register):
    register = register.strip()
    if "." in register:
        return "f" + str(len(register[register.index(".") + 1:]))

    return "f4"

# Skips strings, parenthasis, and brackets
def IndexOfSafe(string, item):
    i = 0
    for index, char in enumerate(string):
        if char in "[(":
            i += 1
        if char in "])":
            i -= 1

        if not i:
            if char == item:
                    if char == "-":
                        if index:
                            if string[index - 1] != "1":
                                return index
                    else:
                        return index
    return -1

# Returns a list where the first item is the destination that contains the result of the code, and the second item is the code.
def CompileOperand_Partial(string, ext="", dst="", components=4):
    string = string.strip()
    sembly = ""
    ops = ["*mul", "+add", "-sub"]
    mathed = False
    reg = 0
    
    if dst == "":
        dst = AllocateRegister()
        reg += 1

    CompilePartial = CompileOperand_PartialPS if isPixelShader else CompileOperand_PartialVS
    
    secondOpinion = CompilePartial(string, ext, dst, components)
    if secondOpinion:
        return secondOpinion

    if "(" in string:
        for av in hfuncs:
            if string[:string.index("(")] == av.name:
                dex = string.index(av.name + "(") + len(av.name) + 1
                end = GetParEnd(string, dex)
                inner = [item.strip() for item in ArraySplit(string[dex:end])]
                end = av.code

                # When calling a function that reads from the destination, it checks if you gave it a write-only register and will use an unused variable register if that's the case.
                if ("%z" in end and dst[0] != 'r') or "%z." in end:
                    newDst = "r" + str(rStatus.index(False))
                    end = end.replace("%z", newDst)
                else:
                    end = end.replace("%z", dst)

                end = end.replace("%0", dst)

                if len(end.split("\t")) > 2:
                    end = end[:end.rfind("\t")] + ext + "\t" + end[end.rfind("\t") + 1:]
                else:
                    end = end.replace("\t", ext + "\t")

                end = end.replace("%tn0", str(components) if "." not in dst else str(len(dst[dst.index(".") + 1:])))

                prepend = ""
                for dex, item in enumerate(inner):
                    if any([IndexOfSafe(item, char) != -1 for char in "+-*/"] + ["(" in item]):
                            if not (item == "-" and inner[dex - 1] == "1"):
                                that = CompileOperand(item, ext, AllocateRegister(reg), components)
                                reg += 1
                                prepend += that[1]
                                inner[dex] = "\"" + that[0] + "\""
                                item = "\"" + that[0] + "\""

                    if item[0] in "0123456789":
                        if item[:2] != "1-":
                            item = "\"" + AddConstant("constant_" + str(constants), item, "f" if item[-1] == "f" else "i") + "\""

                    if "." in item:
                        item = item.split(".")
                        item.append(len(item[1]))
                    else:
                        item = [item, ""]
                        
                        if item[0] in hvars:
                            item[-1] = hvars[hvars.index(item[0])].type[1:]
                        elif item[0] in dhvars:
                            item[-1] = dhvars[dhvars.index(item[0])].type[1:]
                        else:
                                item[-1] = "4"

                    end = end.replace("%tn" + str(dex + 1), str(item[-1]))

                    end = end.replace("%" + str(dex + 1), HVarNameToRegister('.'.join(item[:-1]).strip()))
                return [dst, prepend + end + "\n"]

    string = string.replace("(", "").replace(")", "")

    for op in ops:
        if op[0] in string:
            dex = IndexOfSafe(string, op[0])
            if dex != -1:
                these = [string[:dex], string[dex + 1:]]
                if isPixelShader and (op[0] == "-" and these[0].strip() in ["", "1"]): continue
                sembly += op[1:] + ext + "\t" + dst + ", " + HVarNameToRegister(these[0].strip()) + ", " + HVarNameToRegister(these[1].strip()) + "\n"
                mathed = True
                break

    if not mathed:
        val = HVarNameToRegister(string)
        if val != dst:
            return [dst, "mov" + ext + "\t" + dst + ", " + val + "\n"]
        return [dst, ""]

    return [dst, sembly]


def CompileOperand_PartialPS(string, ext="", dst="", components=4):
    mathed = False
    while (m := GetFirstModif(string)):
        if (m[0] + "(") in string:
            dex = string.index(m[0] + "(") + len(m[0]) + 1
            end = GetParEnd(string, dex)
            inner = string[dex:end]
            return CompileOperand(inner, "_" + m[1] + ext, dst)

    if "?" in string:
        dex = string.index("?") + 1
        inner = string[dex:].split(":")
        return [dst, "cnd" + ext + "\t" + ", ".join([dst, "r0.a", HVarNameToRegister(inner[0].strip()), HVarNameToRegister(inner[1].strip())]) + "\n"]

    if "/" in string:
        if string[string.index("/") + 1:].strip() != "2":
            Error("Dividing can only be done by 2. It can be used like saturate() where it's an addon to a math expression or another function, such as (a + b) / 2")
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
    
    return False


def CompileOperand_PartialVS(string, ext="", dst="", components=4):
    if "/" in string:
        return [dst, "rcp\t" + dst + ", " + HVarNameToRegister(string.split("/")[1].strip()) + "\nmul\t" + dst + ", " + dst + ", " + HVarNameToRegister(string.split("/")[0].strip()) + "\n"]

    if "?" in string:
        dex = string.index("?")
        inner = string[:dex].replace("(", "").replace(")", "")
        compareOps = [("<", "slt\t%0, %1, %2"), (">", "slt\t%0, %2, %1"), ("<=", "sge\t%0, %2, %1"), (">=", "sge\t%0, %1, %2")]
        for c in compareOps:
            if c[0] in inner:
                those = [item.strip() for item in inner.split(c[0])]
                return [dst, c[1].replace("%0", dst).replace("%1", HVarNameToRegister(those[0])).replace("%2", HVarNameToRegister(those[1])) + "\n"]

    if string[0] == "(" and string[-1] == ")":
        return [dst, CompileOperand(string, ext, AllocateRegister(), 4)]

    return False


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

maxR = 2
maxT = 4
maxV = 2
maxC = 5

def includes_defines(list_item, test_value):
    return list_item[0] == test_value

# includes with a key
def includes(lst, item, func=includes_defines):
    for i in lst:
        if func(i, item):
            return True
    return False

# Removes vector splitting to get just the variable
def StripSplit(string):
    return string.split(".")[0].strip()

# This function optimizes the assembly code that the compiler output.
# It turns multiplies and adds into mads, and skips the middle man when a result is mov'd somewhere and isn't read from the original source again
def SecondPass(script):
    tempScript = ""
    dex = 0

    script = script.replace("\n\n", "\n")

    while (mdex := script.find("mul", dex)) != -1:
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
    while (mdex := script.find("mov\t", dex)) != -1:
            sdex = RFind(script, "\n", mdex - 2)
            tdex = script.find("\t", sdex)
            if tdex != -1:
                muls = script[tdex + 1:script.index("\n", tdex)].split(",")
                dst = ((script[script.index(",", mdex) + 1:script.index("\n", mdex + 1)].strip()) if script.find("\n", mdex + 1) != -1 else script[script.index(",", mdex) + 1:].strip())
                if script[tdex + 1:script.index(",", tdex + 1)] == dst:
                    if not script.find("," + dst, script.index("\n", tdex)) < script.find(dst + ",", script.index("\n", tdex)):
                        tgt = script[mdex + 3:script.index(",", mdex)]
                        end = script.find("\n", mdex)
                        script = script[:tdex] + tgt + ", " + ", ".join([item.strip() for item in muls[1:]]) + (script[end:] if end != -1 else "")

            dex = mdex + 1

    return script

def HandleAssign(line):
    for symb in ["*=", "+=", "-="]:
        if symb in line:
            splt = [item.strip() for item in line.split(symb)]
            return splt[0] + " = " + splt[0] + " " + symb[0] + " " + splt[1]
    return line

def ArraySplit(string):
    rray = [""]
    depth = 0
    for char in string:
        if char == "(":
            depth += 1
        if char == ")":
            depth -= 1
        if char == "," and not depth:
            rray.append("")
            continue

        rray[-1] += char

    return rray

def CompileHLSL(script, hv=-1, dst="r0"):
    global linenum, col, scope, r0, r1, typeOfExpr, hvars
    global constants
    if hv == -1:
        hv = []

    mode = 1
    bMeanwhile = False
    temp = 0
    liner = 0
    output = ""
    buffer = ""
    for char in script:

        # Comments
        if mode not in [0, 2]:
            if liner:
                if liner == 1:
                    if includeComments: output += char
                    if char != '\n': continue
                    liner = 0
                else:

                    if char == "\n":
                        if includeComments: output += "\n;"
                        linenum += 1
                    elif includeComments:
                        output += char

                    if temp == "*" and char == "/":
                        output = output[:output.rfind("\n") + 1]
                        output += "\n"
                        liner = 0
                        continue
                    else:
                        temp = char
                        continue
                    

            if buffer:
                if buffer[-1] == '/':
                    if char == '/':
                        buffer = buffer[:-1]
                        liner = 1
                        if includeComments:
                            if output:
                                if output[output.rfind("\n", 0, len(output) - 1) + 1] != ";":
                                    output += "\n\n"
                            output += ";"
                        continue
                    
                    if char == '*':
                        buffer = buffer[:-1]
                        liner = 2
                        temp = ""
                        if includeComments: output += "\n\n;"
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
                    hfuncs[-1].code = CompileHLSL(buffer.strip(), -1, "%0")
                    buffer = ""
                    mode = 1
                    for dex, item in enumerate(hvars):
                        if item.register[0] == "%":
                            hvars = hvars[:dex] + hvars[dex + 1:]
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

                if " " not in line and "(" in line:
                    if line.index("(") > 0:
                        if line[line.index("(") - 1] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            output += CompileOperand(line)[1]
                            continue

                line = HandleAssign(line)

                bMeanwhile = False
                if line.split(" ")[0] == "meanwhile":
                    bMeanwhile = True
                    line = line[10:]

                defType = IsDef(line)
                bForceConst = False
                if defType:
                        typeOfExpr = "Defining"
                        tokens = line.split(" ")

                        if tokens[0] == "const":
                            tokens = tokens[1:]
                            bForceConst = True
                        
                        if tokens[1] in hvars:
                            Error("Syntax error: re-definition of [" + tokens[1] + "]")
                            break

                        if IsConst(line) or bForceConst:
                            typeOfExpr = "Defining Constant"
                            if "[" in tokens[1]:
                                items = ArraySplit(line.split("=")[1].strip()[1:-1])
                                AddConstant(tokens[1][:tokens[1].index("[")], items[0], defType, False)
                                for c in items[1:]:
                                    AddConstant("constant_" + str(constants), c, defType, False)
                            else:
                                AddConstant(line[line.index(" ") + 1:line.index("=")].strip(), line.split("=")[1].strip(), defType)
                            continue

                        else:
                            typeOfExpr = "Defining Variable"
                            if tokens[0] in ["float", "int", "bool"] + ["float" + str(i) for i in range(2, 5)] + ["int" + str(i) for i in range(2, 5)] + ["bool" + str(i) for i in range(2, 5)]:
                                if "(" in tokens[1]:
                                    typeOfExpr = "Defining Function"
                                    tokens[1] = line[line.index(" ") + 1:line.index("(")]

                                    hfuncs.append(HFunc((tokens[1][tokens[1].index("(") + 1:] if "(" in tokens[1] else tokens[1]), ""))
                                    args = [item.strip().split(" ") for item in line[line.index("(") + 1:line.index(")")].split(",")]
                                        
                                    scope = tokens[1]
                                    if args:
                                        hvars += [HVar(item[-1], "%" + str(i + 1), "", "f4" if len(item) == 1 else item[-2][0] + item[-2][-1]) for i, item in enumerate(args)]
                                        temp = 0
                                        mode = 2
                                        buffer = ""
                                        continue

                                else:
                                    if "=" in line:
                                        tokens[2] = line[line.index("=") + 1:].strip()
                                        r = CompileOperand(tokens[2], "", "", (1 if tokens[0] in ['float', 'int', 'bool'] else int(tokens[0][-1])))
                                        hvars.append(HVar(tokens[1], r[0], "", tokens[0][0] + ("1" if tokens[0] in ['float', 'int', 'bool'] else tokens[0][-1])))
                                        output += ("+" if bMeanwhile else "") + r[1]
                                        rStatus[int(r[0].replace("\"", "")[1:])] = True
                                        continue
                                    elif len(tokens) == 2:
                                        
                                        hvars.append(HVar(tokens[1], AllocateRegister(), "", tokens[0][0] + ("1" if tokens[0] in ['float', 'int', 'bool'] else tokens[0][-1])))
                                        rStatus[int(hvars[-1].register.replace("\"", "")[1:])] = True
                                        continue

                else:
                    tokens = line.split(" ")
                    match tokens[0]:
                        case "return":
                            typeOfExpr = "Return"
                            r = CompileOperand(line[7:], "", dst)
                            output += ("+" if bMeanwhile else "") + r[1]
                            continue

                    if '=' in line:
                        tokens = line.split("=")[0].split(" ") + ["="] + line.split("=")[1].split(" ")
                        typeOfExpr = "Assign"
                        tokens[0] = tokens[0].strip()
                        if tokens[0][0] == tokens[0][-1] and tokens[0][0] == "\"":
                            if bMeanwhile:
                                output += "+"
                            output += CompileOperand(line[line.index("=") + 1:], "", tokens[0][1:-1], int(GetRegisterType(tokens[0][1:-1])[1:]))[1]
                        else:
                            name = tokens[0]
                            extension = ""
                            if "." in tokens[0]:
                                name = StripSplit(tokens[0])
                                extension = tokens[0][tokens[0].index("."):]
                            if name in hvars + dhvars:
                                hv = HVarNameToVar(name)
                                if hv:
                                    output += ("+" if bMeanwhile else "") + CompileOperand(line[line.index("=") + 1:], "", hv.register + OffsetProperty(HandleProperty(extension), hv.offset), int(hv.type[1:]))[1]
                                else:
                                    Error("Syntax Error: Unknown token: " + Surround(name))
                            else:
                                if not includes(inlineDefs, name):
                                    Error("Unknown token: [" + name + "]")
                                for d in inlineDefs:
                                    if d[0] == name:
                                        output += ("+" if bMeanwhile else "") + CompileOperand(line[line.index("=") + 1:], "", d[1])[1]

            else:
                buffer += char
    return output if noOptimizations else SecondPass(output)

r0 = ""
r1 = ""

rStatus = [False for i in range(maxR)]

hlsl = ""
pixelshader = ""
vertexshader = ""

textures = 0

def GetShader(script, isPS=isPixelShader):
    dex = -1
    ar = []
    for possibility in (["PixelShader", "psMainD3D9", "psMain"] if isPS else ["VertexShader", "vsMainD3D9", "vsMain", "main"]):
        if possibility + "(" in script:
            dex = script.index(possibility + "(")
            ar = script[dex + len(possibility) + 1:script.index(")", dex)].split(",")
            break
    if dex != -1:
        return (ar, script[script.index("{", dex) + 1:GetParEnd(script, script.index("{", dex) + 1, "{}")], len(script[:script.index("{", dex)].split("\n")))
    return [[], "", 0]


semantics = [["SV_Position", "VPOS", "POSITION"], ["NORMAL"], ["SV_Target", "COLOR"], ["TEXCOORD"]]

def GetSemantic(string):
    while string[-1] in "0123456789":
        string = string[:-1]
    for i, s in enumerate(semantics):
        if string in s:
            return i
    return -1

coordinateInputs = 0
usedSemantics = [False, False, False]
formats = [("Pos", "position"), ("Norm", "normal"), ("Color", "color")]

def MakeStreamFormat():
    f = ""
    for sem, fmt in zip(usedSemantics, formats):
        if sem:
            f += fmt[0]
    if coordinateInputs:
        f += "Tex" + str(coordinateInputs)
    return f

def MakeDcls():
    f = ""
    for sem, fmt, i in zip(usedSemantics, formats, list(range(len(usedSemantics)))):
        if sem:
            f += "\t\tdcl_" + fmt[1] + "\tv" + str(i) + "\n"

    if coordinateInputs:
        if coordinateInputs > 1:
            for i in range(coordinateInputs):
                f += "\t\tdcl_texcoord" + str(i) + "\tv" + str(i + 3) + "\n"
        else:
            f += "\t\tdcl_texcoord\tv3\n"
    return f            

vsm = []

def SafeGet(lst, dex):
    if len(lst) < dex:
        if dex > 0:
            return lst[dex]
    return ""

def Surround(thing):
    return "[" + thing + "]"

# Contains lists where the first item is the name, and the second item being what to replace
inlineDefs = []

def HandleDefines(line):
    tempLine = line.strip().replace("\t", " ").replace("  ", " ")
    if tempLine:
        if tempLine[0] == "#" and " " in tempLine:
            match tempLine[1:tempLine.index(" ")]:
                case "define":
                    name = tempLine.split(" ")[1].strip()
                    
                    if "(" in name:
                        name = name[:name.index("(")]
                        params = [item.strip() for item in tempLine[tempLine.index("(") + 1:tempLine.index(")")].split(",")]
                        
                        replacee = tempLine[tempLine.index(")") + 1:].strip()
                        for i,  p in enumerate(params):
                            replacee = CarefulReplace(replacee, p, "%" + str(i))
                    else:
                        replacee = tempLine[tempLine.index(" ", tempLine.index(" ") + 1):].strip()

                    inlineDefs.append((name, replacee))

        if tempLine.split(" ")[0] == "string":
            name = tempLine[7:tempLine.index("=")].strip()
            replacee = tempLine[tempLine.index("=") + 1:].strip().replace("\"", "")
            inlineDefs.append((name, replacee))

def SortDecl(a):
    return int(a[a.find("v") + 1]) if a.strip() else 65535

mtime = 0

stuckInLoop = True

createFullFile = True

# Reading the settings file, it's been moved down here to allow more things to be changed
settings = ""

try:
    with open("settings.txt", "r") as settingsFile:
        settings = settingsFile.read()
            
except:
    with open("settings.txt", "w") as settingsFile:
        settings = "\'\'\'\n Comment these out to change them. \nThis is a python script so theoretically any variable from the script can be changed from here\n\'\'\'\n#filename = \"\"\n#author = \"\"\n#loop = True\n#noOptimizations = False\n#is24Hour = False\n#includeComments = True"
        settingsFile.write(settings)

# The settings file is now just a python file, so technically this modding tool has mod support
exec(settings)

if not filename:
    filename = filedialog.askopenfilename(filetypes = (("HLSL Script","*.hlsl"),("All files","*.*")))
    if not filename:
        raise Exception("Cancelled.")

newfilename = filename[:filename.index(".")] + ".sha"

if not author:
    author = authors
    if not author:
        author = input("Author(s): ")


if loop == "":
    print("This script can loop so that when the hlsl file changes it'll automatically re-compile.")
    loop = input("Do you want to enable that? (y/N) ") in "Yy"

psLine = 0
vsLine = 0

def defFilter(a):
    if a.strip():
        return a.strip()[0] != "#"
    return True

while stuckInLoop:

    stuckInLoop = loop
    
    if os.path.getmtime(filename) != mtime:
            tstruct = time.localtime(time.time())
            mtime = os.path.getmtime(filename)
            dhvars = [HVar("SHADOW", "c2", "", "f4"), HVar("AMBIENT", "v0", "", "f3"), HVar("FRESNEL", "v0.a", "", "f1"), HVar("BLEND", "v1.a", "", "f1"), HVar("%split%", "", "", "")]
            ResetDHVars(True)
            hvars = []
            fvars = []
            constants = 3
            coordinateInputs = 0
            startC = 3
            usedSemantics = [False, False, False]
            scopeSnapshot = []
            psSnapshot = []
            inlineDefs = []
            r0 = ""
            r1 = ""
            decl = ""
            rStatus = [False for i in range(maxR)]
            linenum = 0
            col = 0
            hlsl = ""
            time.sleep(0.5)
            with open(filename) as file:
                hlsl = file.read()
                [HandleDefines(line) for line in hlsl.split("\n")]
                for d in inlineDefs:
                    if "%0" in d[1]:
                        while d[0] + "(" in hlsl:
                            newLine = d[1].replace("\n", "\n")
                            dex = hlsl.index(d[0] + "(")
                            params = hlsl[dex + len(d[0]) + 1 : hlsl.index(")", dex)].split(",")
                            params = [item.strip() for item in params]
                            for i, p in enumerate(params):
                                newLine = newLine.replace("%" + str(i), p)
                            hlsl = hlsl[:dex] + newLine + hlsl[hlsl.index(")", dex) + 1:]
                                
                    else:
                        if d[0] in hlsl:
                            hlsl = CarefulReplace(hlsl, d[0], d[1])
                hlsl = "\n".join(filter(lambda a : (a.strip()[0] != "#") if a.strip() else True, hlsl.split("\n")))

            (inputs, pixelshader, psLine) = GetShader(hlsl, True)
            if pixelshader:
                if not inputs[0].strip():
                    textures = 0
                else:
                    
                    textures = len(inputs)
                    for i, put in enumerate(inputs):
                        newType = "f4"
                        if " " in put.strip():
                            n = put.strip().split(" ")[-2]
                            if (not IsType(n)) and n != "tex":
                                newType = n
                                
                            put = put.strip().split(" ")[-1]
                        dhvars.append(HVar(put.strip(), "t" + str(i), "debug", newType))


            psSnapshot = [item for item in dhvars]


            (inputs, vertexshader, vsLine) = GetShader(hlsl, False)
            if vertexshader:
                if inputs[0].strip():
                    for i, put in enumerate(inputs):
                        put = put.strip()
                        if " " not in put:
                            Error("Semantics and type are required on parameters in the vertex shader. They must be structured \"type name : semantic\"")
                        put = put.split(":")
                        t = [put[1].strip()]
                        t.append(put[0].strip().split(" ")[-1].strip())
                        t.append(put[0].strip().split(" ")[-2].strip())
                        dex = GetSemantic(t[0])
                        if dex == -1:
                            Error("Unknown Semantic: [" + t[0] + "]")

                        
                        if dex == 3:
                            dhvars.append(HVar(t[1], "v" + str(dex + coordinateInputs), "debug", "f2"))
                            decl += "\t\tfloat\tv" + str(dex + coordinateInputs) + "[2];\t// " + t[1] + "\n"
                            coordinateInputs += 1
                            
                        else:
                            usedSemantics[dex] = True
                            dhvars.append(HVar(t[1], "v" + str(dex), "debug", t[2][0] + t[2][-1]))
                            if t[2][-1] == "4":
                                decl += "\t\tD3DCOLOR\tv" + str(dex) + ";\t// " + t[1] + "\n"
                            else:
                                decl += "\t\tfloat\tv" + str(dex) + ("" if t[2] == "float" else ("[" + t[2][-1] + "]")) + ";\t// " + t[1] + "\n"

            decl = decl.split("\n")
            decl.sort(key=SortDecl)
            decl = "\t\tstream 0;\n" + "\n".join(decl) + "\n"
                    


            passbuffer = ""

            if createFullFile:
                with open(newfilename, "w") as sfile:
                    sfile.write("///////////////////////////////////////////////////////////////////////////\n")
                    sfile.write("// " + newfilename[newfilename.rfind("/") + 1:] + "\n")
                    sfile.write("///////////////////////////////////////////////////////////////////////////\n")
                    sfile.write("// Created on " + str(tstruct.tm_mon) + "/" + str(tstruct.tm_mday) + "/" + str(tstruct.tm_year) + " " + str((tstruct.tm_hour if (tstruct.tm_hour < 13 or is24Hour) else tstruct.tm_hour - 12)) + ":" + str(tstruct.tm_min).rjust(2, "0") + ":" + str(tstruct.tm_sec).rjust(2, "0") + " " + ("" if is24Hour else ("PM" if tstruct.tm_hour > 11 else "AM")) + "\n")
                    sfile.write("//\n")
                    sfile.write("// Authors: " + author + "\n")
                    sfile.write("//\n")
                    sfile.write("// Zack's HLSL-to-FlatOut-Shader " + version + "\n")
                    sfile.write("///////////////////////////////////////////////////////////////////////////\n")

                    for i in range(textures):
                        sfile.write("Texture Tex" + str(i) + ";\n")

                    sfile.write("\nconst string inputStreamFormat = \"" + MakeStreamFormat() + "\";\n\n")

                    sfile.write("vertexshader vSdr =\n\tdecl\n\t{\n" + decl + "\t}\n\tasm\n\t{\n")
                    sfile.write("\t\tvs.1.1\n\n")

                    if pixelshader != "":
                        scope = "Pixel Shader"
                        isPixelShader = True
                        ResetAVars(True)
                        ResetDHVars(True)
                        # Making absolutely sure it's a copy and not a reference
                        hvars = [item for item in dhvars]
                        dhvars = [item for item in psSnapshot]
                        psSnapshot = [item for item in hvars]
                        hvars = []
                        fvars = []
                        maxR = 2
                        maxC = 8
                        maxV = 2
                        linenum = psLine
                        rStatus = [False for i in range(maxR)]
                        constants = 3
                        startC = 3
                        assemble = CompileHLSL(pixelshader)
                        seenconstants = [False for i in range(maxC)]
                        for hvar in hvars:
                            if hvar.register:
                                reg = hvar.register
                                if reg[0] == 'c':
                                    if "." in reg:
                                        reg = reg[:reg.index(".")]
                                    if not hvar.offset or not seenconstants[int(reg[1:])]:
                                        seenconstants[int(reg[1:])] = True
                                        passbuffer += "\t\tPixelShaderConstant" + hvar.type[0].upper() + "[" + hvar.register[1] + "] = " + hvar.value + ";\n"

                        if textures:
                            assemble = "\n" + assemble
                            for i in range(textures - 1, -1, -1):
                                hv = HVarRegisterToVar("t" + str(i))
                                if hv.type[1] not in "0123456789":
                                    prefix = hv.type
                                else:
                                    prefix = "tex"
                                assemble = prefix + "\tt" + str(i) + "\t// " + hv.name + "\n" + assemble
                    
                    if vertexshader != "":
                        scope = "Vertex Shader"
                        isPixelShader = False
                        constants = vertexConstants
                        startC = vertexConstants
                        ResetAVars(False)
                        dhvars = [item for item in psSnapshot]
                        psSnapshot = [item for item in hvars]
                        ResetDHVars(False)
                        PSTexToVSTex()
                        maxR = 12
                        maxC = 96
                        maxV = 16
                        linenum = vsLine
                        # c95.x = degrees to radians, c95.z = 1/2, can be turned into 2 later (I don't know if they are capped in this instance)
                        hvars = [HVar("reservedconstant_95", "c95", "float4(0.0174533f, 1.0f, 0.5f, 0.0f)", "f4")]
                        fvars = []
                        rStatus = [False for i in range(maxR)]
                        sfile.write(MakeDcls() + "\n")
                        for line in CompileHLSL(vertexshader, -1, "oPos").split("\n"):
                            sfile.write("\t\t" + line + "\n")

                    sfile.write("\t};\n\n")

                    passbuffer = "\n" + passbuffer

                    seenconstants = [False for i in range(maxC)]
                    for hvar in hvars:
                        reg = hvar.register
                        if reg[0] == 'c':
                            if "." in reg:
                                reg = reg[:reg.index(".")]
                            if (not seenconstants[int(reg[1:])] or not hvar.offset) and hvar.value:
                                seenconstants[int(reg[1:])] = True
                                passbuffer = "\t\tVertexShaderConstant" + hvar.type[0].upper() + "[" + (hvar.register[1:hvar.register.index(".")] if "." in hvar.register else hvar.register[1:]) + "] = " + hvar.value + ";\n" + passbuffer

                    

                    if pixelshader != "":
                        hvars = [item for item in psSnapshot]
                        sfile.write("pixelshader pSdr =\n\tasm\n\t{\n")
                        sfile.write("\t\tps.1.1\n")
                        sfile.write("\n")
                        for line in assemble.split("\n"):
                            sfile.write("\t\t" + line + "\n")
                        sfile.write("\t};\n\n")

                    # The hlsl file can now have a technique and pass, to add things that other shaders need
                    tbuffer = ""
                    pbuffer = ""
                    if "\nTechnique " in hlsl:
                        techindex = hlsl.index("{", hlsl.index("\nTechnique "))
                        tbuffer = hlsl[techindex + 1: GetParEnd(hlsl, techindex + 1, "{}")]
                        if "Pass P" in tbuffer:
                            passindex = tbuffer.index("{", tbuffer.index("Pass P"))
                            passend = GetParEnd(tbuffer, passindex + 1, "{}")
                            pbuffer = tbuffer[passindex + 1:passend]
                            tbuffer = tbuffer[:tbuffer.index("Pass P")] + tbuffer[passend + 1:]
                            pbuffer = "\n".join(["\t\t" + item.strip() for item in pbuffer.strip().split("\n")])
                        tbuffer = "\n".join(["\t" + item.strip() for item in tbuffer.strip().split("\n")])

                    sfile.write("Technique T0\n")
                    sfile.write("{\n")
                    sfile.write(tbuffer + "\n")
                    sfile.write("\tPass P0\n")
                    sfile.write("\t{\n")
                    sfile.write(pbuffer + "\n")
                    sfile.write(passbuffer.replace("%x", "0.0f"))
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


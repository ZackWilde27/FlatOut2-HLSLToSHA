# Zack's HLSL to FlatOut SHA
version = "v3.0"
# Am I particularly proud of this code? uhh

try:
    from tkinter import filedialog
except:
    from Tkinter import filedialog

from time import time, localtime, sleep
from os.path import getmtime
from re import findall, search

isPixelShader = True

filename = ""
author = ""
authors = "" # I accidentally made a typo in the original settings file so it's a feature now
loop = ""

# Cosmetic stuff
is24Hour = False
includeComments = True
dateFormat = "M/D/Y" # D will be replaced with the day, M with the month, and so on

# Whether to put constants in the pass, or use def instructions.
constantsInPass = True
stopOnReturn = True # Whether to stop compiling when it reaches a return

# Things meant for me when I'm debugging, can be changed if there's an edge case
printOnNoReturnCode = False # Will add a 'No return code needed' comment if a statement generates a mov where the source and destination are the same
debugComments = False # Adds information meant for debugging, such as when variables get deleted
autoDiscard = True # Whether to discard un-used variables to free up registers
noOptimizations = False # Skips the second pass that does things like combining multiplies and adds into mads, and applying shortcuts when a mov is unnecessary
noDefaultOverload = True # Produces an error when no overloaded functions match, instead of just going with the first one

# How many constants are reserved by the game, can vary from shader to shader
# The default values are for the car body
vertexConstants = 32
pixelConstants = 3


class HVar:
    def __init__(self, name, register, value, tyype, offset=0):
        # The HLSL keyword it's associated with
        self.name = name
        # The assembly keyword it's associated with, could be "r0", "t0", or "oPos.yyy"
        self.register = register
        # Reserved for constants, this what came after the =, for example "float4(0.0f, 0.0f, 0.0f, 0.0f)"
        self.value = value
        # The first letter of the type, followed by the number of components, from 1-4. a float4 would be an f4 while an int3 would be an i3. Matrices start with m
        # Arrays have 'a' + their length appended to the end, so an array of 5 float4s would be f4a5.
        self.type = tyype
        # When packing multiple constants into a single register, the offset makes them reference the correct components
        self.offset = offset

    def __eq__(self, other):
        return self.name == other


    def __str__(self):
        return "HStruct: [" +  ", ".join([self.name, self.register, self.value, self.type]) +"]"

    def __repr__(self):
        return self.__str__(self)

class HStruct:
    def __init__(self, name, properties):
        self.name = name
        self.properties = properties
        

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        return "HStruct: " + self.name


class HFunc:
    def __init__(self, name, code, rtnType, paramType):
        self.name = name
        self.code = code
        # These are going to be used to determine if a function actually works in the given situation
        # allowing for overloading.
        self.rtn = rtnType
        self.params = paramType

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        return "HFunc: [" +  ", ".join([self.name, self.code]) +"]"

# I originally included the column number as well, but because it reads per-statement, the column will always be the semi-colon at the end of the line.
col = 0
scope = "Global"
typeOfExpr = ""
constants = 3
startC = 3
linenum = 0

def Error(message):
    print("Error in", scope, "line", linenum, "(" + typeOfExpr + "):", message)

# The previous explanation was outdated, I forgot I changed it. I really need to rename everything.
dhvars = [HVar("SHADOW", "c2", "", "f4"), HVar("AMBIENT", "v0", "", "f3"), HVar("FRESNEL", "v0.a", "", "f1", 3), HVar("BLEND", "v1.a", "", "f1", 3), HVar("%split%", "", "", "")]
hvars = []
fvars = []
hfuncs = []
#hfuncs = [HFunc("dot", "dp3\t%0, %1, %2"), HFunc("lerp", "lrp\t%0, %3, %1, %2"), HFunc("mad", "mad\t%0, %1, %2, %3")]

def ResetDHVars(isPS=isPixelShader):
    global dhvars
    dhvars = dhvars[dhvars.index("%split%"):]
    dhvars = ([HVar("SHADOW", "c2", "", "f4"), HVar("AMBIENT", "v0", "", "f3"), HVar("FRESNEL", "v0.a", "", "f1"), HVar("BLEND", "v1.a", "", "f1"), HVar("EXTRA", "v1", "", "f3"), HVar("HALF", "c0", "", "f4"), HVar("LIMITER", "c1", "", "f4")] if isPS else [HVar("FRESNEL", "oD0", "", "f1", 3), HVar("AMBIENT", "oD0.xyz", "", "f3"), HVar("BLEND", "oD1", "", "f1", 3), HVar("EXTRA", "oD1.xyz", "", "f3"), HVar("CAMERA", "c8", "", "f3"), HVar("CAMDIR", "c9", "", "f3"), HVar("TIME", "c14", "", "f4"), HVar("PLANEX", "c17", "", "f4"), HVar("PLANEY", "c18", "", "f4"), HVar("PLANEZ", "c19", "", "f4")]) + dhvars

def PSTexToVSTex():
    for dhvar in dhvars:
        if dhvar.register:
            if dhvar.register[0] == "t":
                dhvar.register = "oT" + dhvar.register[1:]

def ResetAVars(isPS=isPixelShader):
    global hfuncs
    hfuncs = []
    # The type-building functions have to be added manually, since the compiler gets confused
    #hfuncs = [HFunc("float4", "mov\t%0.rgb, %1\n+mov\t%0.a, %2", 4, [3, 1])] if isPS else [HFunc("float4", "mov\t%0.xyz, %1\nmov\t%0.w, %2", 4, [3, 1]), HFunc("float4", "mov\t%0.xyzw, %1", 4, [1])]
    #hfuncs = [HFunc("dot", "dp%tn1\t%0, %1, %2", 1.2), HFunc("dot", "dp3\t%0, %1, %2", 1.1, 1.1), HFunc("lerp", "lrp\t%0, %3, %2, %1"), HFunc("mad", "mad\t%0, %1, %2, %3"), HFunc("fma", "mad\t%0, %1, %2, %3"), HFunc("normalize", "dp3_sat\t%z, %1_bx2, %1_bx2\nmad\t%0, %1_bias, 1-%z, %1_bx2")] if isPS else [HFunc("dot", "dp%tn1\t%0, %1, %2"), HFunc("dot3", "dp3\t%0, %1, %2"), HFunc("dot4", "dp4\t%0, %1, %2"), HFunc("mad", "mad\t%0, %1, %2, %3"), HFunc("fma", "mad\t%0, %1, %2, %3"), HFunc("exp2", "expp\t%0, %1"), HFunc("exp2_full", "exp\t%0, %1"), HFunc("frac", "frc\t%0, %1"), HFunc("max", "max\t%0, %1, %2"), HFunc("min", "min\t%0, %1, %2"), HFunc("log2", "logp\t%0, %1"), HFunc("log2_full", "log\t%0, %1"), HFunc("rcp", "rcp\t%0, %1"), HFunc("rsqrt", "rsq\t%0, %1"), HFunc("rdistance", "sub\t%z, %1, %2\ndp3\t%z.w, %z, %z\nrsq\t%z.w, %z.w"), HFunc("distance", "sub\t%z, %1, %2\ndp3\t%z.w, %z, %z\nrsq\t%z.w, %z.w\nrcp\t%0, %z.w"), HFunc("dst", "dst\t%0, %1"), HFunc("abs", "max\t%0, %1, -%1"), HFunc("degrees", "rcp\t%z.x, c95.x\nmul\t%0, %z.x, %1"), HFunc("step", "sge\t%0, %1, %2"), HFunc("floor", "frc\t%z.w, %1\nsub\t%0, %1, %z.w"), HFunc("trunc", "frc\t%z.w, %1\nsub\t%0, %1, %z.w"), HFunc("ceil", "frc\t%z.x, %1\nsub\t%z.x, %1, %z.x\nadd\t%0, %z.x, c95.y"), HFunc("round", "frc\t%z.x, %1\nsub\t%z.y, %1, %z.x\nslt\t%z.z, c95.z, %z.x\nadd\t%0, %z.y, %z.z"), HFunc("radians", "mul\t%0, c95.x, %1"), HFunc("lit", "mov\t%z.x, %1\nmov\t%z.y, %2\nmov\t%z.w, %3\nlit\t%0, %z"), HFunc("sign", "slt\t%z.x, c95.w, r0.x\nsub\t%z.x, %z.x, c95.z\nadd\t%0, %z.x, %z.x"), HFunc("fmod", "rcp\t%z.x, %2\nmul\t%z.x, %z.x, %1\nfrc\t%z.y, %z.x\nsub\t%z.x, %z.x, %z.y\nmul\t%z.x, %z.x, %2\nsub\t%0, %1, %z.x"), HFunc("faceforward", "dp3\t%z.x, %2, %3\nslt\t%z.x, c95.w, %z.x\nsub\t%z.x, %z.x, c95.z\nadd\t%z.x, %z.x, %z.x\nmul\t%0, -%1, %z.x"), HFunc("fresnel", "dp3\t%z.x, %1, %2\nmax\t%z.x, -%z.x, %z.x\nsub\t%z.x, c95.y, %z.x\nmul\t%z.x, %z.x, %z.x\nmul\t%z.x, %z.x, %z.x\nmul\t%0, %z.x, %z.x"), HFunc("reflect", "dp3\t%z.x, %1, %2\nadd\t%z.x, %z.x, %z.x\nmul\t%z, %z.x, %2\nsub\t%0, %1, %z"), HFunc("normalize", "dp3\t%z.a, %1, %1\nrsq\t%z.a, %z.a\nmul\t%0, %1, %z.a"), HFunc("lerp", "sub\t%z, %2, %1\nmad\t%0, %z, %3, %1"), HFunc("rlength", "dp3\t%z, %1, %1\nrsq\t%z, %z"), HFunc("length", "dp3\t%z.a, %1, %1\nrsq\t%z.a, %z.a\nrcp\t%0, %z.a"), HFunc("clamp", "min\t%z, %1, %3\nmax\t%0, %z, %2"), HFunc("saturate", "min\t%z, %1, c95.y\nmax\t%0, %z, c95.w"), HFunc("sqrt", "rsq\t%z, %1\nrcp\t%0, %z"), HFunc("RotateToWorld", "m3x%tn0\t%0, %1, c4"), HFunc("LocalToWorld", "m4x%tn0\t%0, %1, c4"), HFunc("LocalToScreen", "m4x%tn0\t%0, %1, c0"), HFunc("mul", "m%tn2x%tn0\t%0, %1, %2")]

# Finds the item in list1 and retrieves the corrosponding item in list2
def Translate(list1, list2, item):
    return list2[list1.index(item)]

def HVarRegisterToVar(register):
    for v in hvars + dhvars:
        if v.register == register:
            return v
    return False

def Int(x, default=0):
    if x.isnumeric():
        return int(x)
    return default

def SizeOf(tyype):
    if tyype in ["float", "int", "bool"]:
        return 1

    return Int(tyype[-1], 4)

def GetSizeFromParam(param):
    if " " in param:
        splt = param.split(" ")
        while splt[0] in ["inout"]:
            splt = splt[1:]

        if len(splt) < 2:
            return 4

        return SizeOf(splt[0])
    return 4

# This function used to convert a string to a float, but that caused an edge case
# so it adds the f, it's more like StrToFloatToStr
def StrToFloat(x):
    x = x.strip()
    if x[0] == "%" or x.isalpha(): return "0.0f"

    if x[-1] == "f":
        x = x[:-1]
    return str(float(x)) + "f"

def AddConstant(name, value, valtype="f", pack=True, swizzle=True):
    global constants
    if constants >= maxC:
        Error(f"Too many constants defined, there can only be {maxC - startC}, since the game reserves {startC} of them")
        return ""

    if "(" in value:
        value = SliceWithStrings(value, "(", ")")

    vals = [item.strip() for item in value.split(",")]
    dimensions = len(vals)
    allDimensions = 0
    numConsts = 0

    # Checking for pre-existing constant
    valstring = ",".join([StrToFloat(item) for item in vals])
    for hv in hvars + dhvars:
        if hv.type and hv.value and hv.value not in ['texkill', 'texcoord']:
            if hv.type[0] == valtype:
                existingvalues = ','.join([StrToFloat(item) for item in SliceWithStrings(hv.value, "(", ")").split(",")])
                if valstring in existingvalues:
                    offset = existingvalues[:existingvalues.index(valstring)].count(",")
                    
                    if isPixelShader:
                        if offset not in [0, 3]:
                            continue
                        
                        if (not offset) and (dimensions < 3):
                            continue

                    newRegister = hv.register
                    if swizzle and "." not in newRegister:
                        newRegister = OffsetProperty(Swizzle(newRegister, dimensions), offset)

                    if name[:len("constant_")] != "constant_":
                        hvars.append(HVar(name, newRegister, "", valtype + str(dimensions)))

                    return newRegister

    while len(vals) < 4:
        vals.append("%x")

    newHVar = HVar(name, "", "", valtype + str(dimensions))

    suffix = ""
    chart = "xyzw"
    
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
                            if not firstConst:  firstConst = hv
                            allDimensions += len(hv.value.split("%x")) - 1
                            break

            if firstConst:
                if allDimensions >= dimensions:
                    if isPixelShader:
                        if dimensions == 1 and numConsts == 1 and ("%x)" in firstConst.value):
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
                    return OffsetProperty(newHVar.register + (("." + chart[:dimensions]) if ("." not in newHVar.register) else ""), newHVar.offset)

    if swizzle:
        suffix = OffsetProperty("." + chart[:dimensions], newHVar.offset)

    newHVar.register = "c" + str(constants)
    constants += 1
    if isPixelShader and dimensions == 1:
        vals = vals[1:] + [vals[0]]
        newHVar.register += ".a"
        suffix = ""

    newHVar.value = Translate("fib", ["float", "int", "bool"], valtype[0])
    newHVar.value += "4(" + ", ".join(vals) + ")"
    hvars.append(newHVar)
    return newHVar.register + suffix

def IsType(string):
    if string:
        types = ["float", "int", "bool", "void"]
        
        if string.split(" ")[0] in types:
            return True

        for t in types[:-1]:
            if string.split(" ")[0] in ([t + str(i) for i in range(2, 5)]):
                return True
    return False

def IsFloat(string):
    if not string:
        return False
    
    if string[0] not in "0123456789.":
        return False

    if string[-1] == "f":
        string = string[:-1]
    try:
        float(string)
    except:
        return False

    return True

def IsConst(line):
    if line:
        if line.split(" ")[0] == "const":
            return True

        if IsFloat(line) or line in ["true", "false"]:
            if line[:2] not in ["1-", "1/"]:
                return True

        for i in range(2, 5):
            for t in ["float", "int", "bool"]:
                if t + str(i) + "(" in line:
                    if all([IsFloat(item.strip()) for item in SliceWithStrings(line, "(", ")").split(",")]):
                        return True
    return False

def BreakdownMath(line):
    tokes = [""]
    symbols = "+-*" if isPixelShader else "+-*/"
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
            if char in symbols:
                tokes[-1] = tokes[-1].strip()
                if tokes[-1]:
                    if tokes[-1] not in "+-*":
                        if tokes[-1][-1] not in "(,":
                            tokes.append(char)
                            tokes.append("")
                            continue
        tokes[-1] += char

    tokes = [item.strip() for item in tokes]

    if isPixelShader:
        i = 0

        while True:
            try:
                i = tokes.index("-", i)
            except ValueError:
                break

            if 0 < i < len(tokes):
                if IsConst(tokes[i + 1]) and StrToFloat(tokes[i + 1]) == "0.5f":
                    if (i < len(tokes) - 2) and tokes[i + 2] == "*" and IsConst(tokes[i + 3]) and StrToFloat(tokes[i + 3]) == "2.0f":
                        tokes = tokes[:i - 1] + ["\"" + HVarNameToRegister(tokes[i - 1]) + "_bx2\""] + tokes[i + 4:]
                    else:
                        tokes = tokes[:i - 1] + ["\"" + HVarNameToRegister(tokes[i - 1]) + "_bias\""] + tokes[i + 2:]
            i += 1

        i = 0
            
        while True:
            try:
                i = tokes.index("*", i)
            except ValueError:
                break

            if tokes[i + 1] in ["2", "4"]:
                tokes[i - 1] = "".join(tokes[i - 1:i + 2])
                tokes = tokes[:i] + tokes[i + 2:]

            i += 1


    i = 0
    allConst = True
    while i < len(tokes):
        token = tokes[i]

        if isPixelShader:
            if token == "1":
                if i < (len(tokes) - 1):
                    if tokes[i + 1] == "-":
                        tokes[i] = "\"1-" + HVarNameToRegister(tokes[i + 2], linenum) + "\""
                        tokes = tokes[:i + 1] + tokes[i + 3:]
                        continue

        if token[0] == "(" and token[-1] == ")" and not HasMath(token):
            tokes[i] = token[1:-1]
            token = tokes[i]

        if IsConst(token):
            if i < (len(tokes) - 2):
                try:
                    if StrToFloat(token) + tokes[i + 1] == "1.0f/":
                        i += 1
                        continue
                except:
                    pass
                    
                if allConst and IsConst(tokes[i + 2]):
                    tokes = tokes[:i] + [str(eval(' '.join([StrToFloat(tokes[i])[:-1], tokes[i+1], StrToFloat(tokes[i+2])[:-1]]))) + "f"] + tokes[i + 3:]
                    continue

            tokes[i] = "\"" + AddConstant("constant_" + str(constants), token, swizzle=True) + "\""
        else:
            allConst = False
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
        if char in chart:
            output += chart[(chart.index(char) + offset)]
        else:
            output += char

    return output

def HandleString(string):
    if string[0] == string[-1]:
        return string[1:-1]
    prefix = string[1:].split("\"")
    ext = prefix[1]
    prefix = prefix[0]
    if "." in prefix:
        return prefix[:prefix.index(".")] + ext
    return prefix + ext

def TypeIdFromName(name):
    if name in ["float", "int", "bool"]:
        return name[0] + "1"
    return name[0] + name[-1]

def HVarNameToRegister(name, swizzle=True):
    allhvars = dhvars + hvars
    exptype = ""

    if name[0] == "(":
        exptype = TypeIdFromName(name[1:name.index(")")])
        name = name[name.index(")") + 1:]
    ext = ""
    prefix = ""
    if name:
        if name[0] == "\"":
            return HandleString(name)

        if "." in name:
            ext = "." + HandleProperty(name.split(".")[1].strip())
            name = name.split(".")[0].strip()

        if "-" in name:
            prefix = name[:name.index("-") + 1]
            name = name[name.index("-") + 1:]

        if name in allhvars:
            hv = Translate(allhvars, allhvars, name)
            if not exptype:
                exptype = hv.type

            if (hv.offset or int(exptype[1]) != 4) and (not ext) and (hv.register[0] != "v") and ("." not in hv.register) and (not isPixelShader) and swizzle:
                ext = "." + "xyzw"[:int(exptype[1])]

            register = hv.register
            if "." in register:
                if ext:
                    register = register[:register.index(".")]
                else:
                    ext = register[register.index(".") + 1:]
                    register = register[:register.index(".") + 1]

            return prefix + register + OffsetProperty(ext, hv.offset)

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

def IsDef(line):
    if line.split(" ")[0] == "const":
        line = line[6:].strip()

    types = ["float", "int", "bool", "void"]

    for t in types:
        if line.split(" ")[0] in ([t + str(i) for i in range(2, 5)] + [t]):
            return t[0]
    
    return False

def CarefulIn(haystack, needle):
    spaces = "\n\t +-*/=(){}[],.;"
    for i in spaces:
        for j in spaces:
            if (i + needle + j) in haystack:
                return True
    return False

def CarefulIndex(haystack, needle):
    spaces = "\n\t +-*/=(){}[],.;"
    for i in spaces:
        for j in spaces:
            if (i + needle + j) in haystack:
                return haystack.index(i + needle + j) + 1
    return -1

# Only replaces when there's space around the subject, makes absolutely sure it's not part of some other word
def CarefulReplace(text, subject, replacement):
    # Doing something with it to make sure it's a copy
    script = text.replace("\n", "\n")
    
    spaces = "\n\t +-*/=(){}[],.;"

    for i in spaces:
        if script[:len(subject) + 1] == (subject + i):
            script = replacement + script[len(subject):]

        if script[-(len(subject) + 1):] == (i + subject):
            script = script[:-len(subject)] + replacement

    for i in spaces:
        for j in spaces:
            script = script.replace(i + subject + j, i + replacement + j)

    return script
            
# returns the ) to the ( that you give it in a string, basically it skips nested parenthasis
# The index has to be after the open bracket, just so it doesn't have to factor it in
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

def InFunction():
    return scope not in ['Pixel Shader', 'Vertex Shader', 'Global', 'For Loop']

functionRegisters = -1

# Returns the first unused register
# The offset allows for multiple unused registers to be allocated
def AllocateRegister(offset=0, commit=False):
    global functionRegisters

    if InFunction():
        functionRegisters += 1
        return "%z" + str(functionRegisters)
    else:
        if False in rStatus:
            index = rStatus.index(False)
            if commit:
                rStatus[index] = True
            return "r" + str(index + offset)
        else:
            Error("Ran out of registers to hold results, too much is being done in a single line")
            return "r" + str(len(rStatus) - 1)

def GetOperands(string, dex):
    s = string.find(" ", dex)
    return [string[max(string.rfind(" ", dex), 0):dex] , string[dex + 1:(s if s != -1 else len(string))]]


modifs = [("saturate", "sat"), ("half", "d2"), ("double", "x2"), ("quad", "x4"), ("d2", "d2"), ("x2", "x2"), ("x4", "x4")]

def GetFirstModif(string):
    result = ""
    dex = 999999999999
    for m in modifs:
        mdex = string.find(m[0] + "(")
        if mdex != -1 and mdex < dex:
            result = m
            dex = string.index(m[0] + "(")
    return result

# Technically the name of this variable isn't right, but I didn't want to type out usedUnusedRegisters every time
unusedRegisters = 0

def MultipleMathStatements(string):
    return sum([string.count(char) for char in "+-*/"]) > 1

def HandleSquareBrackets(tokens, i):
    fullsembly = ""

    if "[" in tokens[i]:
        index = tokens[i][tokens[i].index("[") + 1:tokens[i].index("]")].strip()
        swizzle = tokens[i][tokens[i].index("]") + 1:]
        if any([(char in index) for char in "*+-/("]):
            that = CompileOperand_Partial(index, "", AllocateRegister(unusedRegisters) + ".x", 1)
            unusedRegisters += 1
            fullsembly += that[1]
            fullsembly += "mov" + ext + "\ta0.x, " + that[0] + "\n" 
        else:
            fullsembly += CompileOperand_Partial(index, "", "a0.x", 1)[1]

        tokens[i] = "\"c[a0.x + " + HVarNameToRegister(tokens[i][:tokens[i].index("[")].strip())[1:] + "]" + swizzle + "\""

    return fullsembly


def CheckForTooManyRegisters(sembly, registerType, description, limit=1):
    for line in sembly.split("\n"):
        matches = findall(f", {registerType}[0-9]+\\.?[xyzwrgba]*", line)

        if len(matches) > 1:
            indexes = set([RemoveSwizzle(item[1:].strip()[1:]) for item in matches])

            if len(indexes) > limit:
                Error(f"Can't access more than {limit} {description}{'s' if limit > 1 else ''} in a single instruction")

def CompileOperand(string, ext="", dst="", components=4):
    global unusedRegisters

    if dst == "":
        dst = AllocateRegister(unusedRegisters) + (("." + "xyzw"[:components]) if (components != 4) else "")
        unusedRegisters += 1

    fullsembly = ""
    tokens = BreakdownMath(string)

    while len(tokens) > 1:
        for i in [0, 2]:
            if "(" in tokens[i]:
                this = CompileOperand_Partial(tokens[i], "", AllocateRegister(unusedRegisters), 4)
                unusedRegisters += 1
                fullsembly += this[1]
                tokens[i] = "\"" + this[0] + "\""
            fullsembly += HandleSquareBrackets(tokens, i)

        destination = dst
        if (dst[0] != "r" and len(tokens) > 3):
            destination = AllocateRegister(unusedRegisters)
            unusedRegisters += 1

        that = CompileOperand_Partial(" ".join(tokens[:3]), ext, destination, components)
        tokens = ["\"" + that[0] + "\""] + tokens[3:]
        fullsembly += that[1]

    if tokens:
        fullsembly += HandleSquareBrackets(tokens, 0)

        if not any([i in tokens[0] for i in "+-*/?"]) and tokens[0][0] == "(":
            newtype = SliceWithStrings(tokens[0], "(", ")")
            components = int(newtype[-1]) if newtype[-1] in "234" else 1
            tokens[0] = tokens[0][tokens[0].index(")") + 1:]
        fullsembly += CompileOperand_Partial(tokens[0], ext, dst, components)[1]

    if not isPixelShader:
        CheckForTooManyRegisters(fullsembly, "v", "vertex parameter")

    CheckForTooManyRegisters(fullsembly, "c", "constant", 2 if isPixelShader else 1)
    

    return [dst, fullsembly]

def GetRegisterType(register):
    register = register.strip()
    if "." in register:
        return "f" + str(len(register[register.index(".") + 1:]))

    return "f4"

# Skips strings, parenthasis, and brackets
def IndexOfSafe(string, item, start=0):
    depth = 0
    inString = False
    for index, char in enumerate(string[start:]):
        if char in "[(":
            depth += 1
        if char in "])":
            depth -= 1
        
        if char == "\"":
            depth += -1 if inString else 1
            inString = not inString

        if not depth:
            if char == item:
                if not (char == "-" and string[:index] in ['', '1']):
                    return index
    return -1

def HasOperators(string):
    return HasMath(string) or HasCompare(string)

def HasMath(string):
    return any([symbol in string[1:-1] for symbol in "+-*/"])

def HasCompare(string):
    return any([symbol in string[1:-1] for symbol in "<>="])

def IsASingleMov(string):
    return string[:len("mov\t")] == "mov\t" and string.count("\n") == 1

def Swizzle(register, components):
    return (register + "." + "xyzw"[:components]) if "." not in register and components < 4 else register

def GetMatchingFunctions(name):
    matchingFuncs = []
    for hf in hfuncs:
        if hf.name == name:
            matchingFuncs.append(hf)
    return matchingFuncs


def GetMatchingFunction(name, params):
    matchingFuncs = GetMatchingFunctions(name)
    for hf in matchingFuncs:
        if hf.params == params:
            return hf

    if matchingFuncs:
        return matchingFuncs[0]
    return None

# Same as slice with strings except it'll skip nested brackets 
def SliceBrackets(line, start, end):
    index = line.index(start) + 1
    return line[index:GetParEnd(line, index, start + end)]

def GetMatchingFunctionFromLine(line):
    params = [HVarNameToSize(item.strip()) for item in ArraySplit(SliceBrackets(line, "(", ")"))]
    matchingFuncs = GetMatchingFunctions(line[:line.index("(")])
    if matchingFuncs:
        for hf in matchingFuncs:
            if hf.params == params:
                return hf

        return matchingFuncs[0]

    return None
            

def HVarNameToSize(name):
    if IsConst(name):
        if "(" in name:
            return len(SliceWithStrings(name, "(", ")").split(","))
        return 1

    if "(" in name:
        if name[0] == "(" and name[-1] != ")":
            # Casting
            return GetSizeFromParam(SliceWithStrings(name, "(", ")") + " x")
        hf = GetMatchingFunctionFromLine(name)
        if hf:
            return hf.rtn

    if name.startswith("1-"):
        return HVarNameToSize(name[2:])

    if HasMath(name):
        tokens = BreakdownMath(name)
        return HVarNameToSize(tokens[0])

    if "." in name:
        return len(name[name.index(".") + 1:])

    allhvars = hvars + dhvars
    if name in allhvars:
        hv = allhvars[allhvars.index(name)]
        return int(hv.type[1])

    print("HVarNameToSize: Unknown name: " + Surround(name))
    return 4

# Returns a list where the first item is the destination that contains the result of the code, and the second item is the code.
def CompileOperand_Partial(string, ext="", dst="", components=4):
    string = string.strip()
    sembly = ""
    ops = ["*mul", "+add", "-sub"]
    mathed = False
    reg = unusedRegisters

    if dst == "":
        dst = AllocateRegister(reg)
        reg += 1

    GetSecondOpinion = CompileOperand_PartialPS if isPixelShader else CompileOperand_PartialVS
    
    secondOpinion = GetSecondOpinion(string, ext, dst, components)
    
    if secondOpinion:
        return secondOpinion

    if string[0] == "(" and string[-1] == ")":
        if HasMath(string):
            return [dst, CompileOperand(string[1:-1], ext, AllocateRegister(reg), 4)[1]]
        else:
            string = string[1:-1]

    if "(" in string:
            matchingFuncs = []
            parameters = string[string.index("(") + 1:GetParEnd(string, string.index("(") + 1)]
            parameters = [HVarNameToSize(item.strip()) for item in ArraySplit(parameters)]
            functionName = string[:string.index("(")].strip()
            for hf in hfuncs:
                if functionName == hf.name:
                    matchingFuncs.append(hf)

            if matchingFuncs:
                # Moves the first function to the end so it can default to that one if none of them match
                matchingFuncs = matchingFuncs[1:] + [matchingFuncs[0]]
            
            for index, av in enumerate(matchingFuncs):
                    dex = string.index(av.name + "(") + len(av.name) + 1
                    end = GetParEnd(string, dex)
                    inner = [item.strip() for item in ArraySplit(string[dex:end])]
                    end = av.code

                    if (av.params != parameters) and (index < len(matchingFuncs) - 1 or (noDefaultOverload and len(matchingFuncs) > 1)):
                        continue

                    i = 0
                    while f"%z{i}" in end:
                        end = end.replace(f"%z{i}", AllocateRegister(reg))
                        reg += 1
                        i += 1

                    # When calling a function that reads from the destination, it checks if you gave it a write-only register and will use an unused variable register if that's the case.
                    if ("%z" in end and dst[0] != 'r') or "%z." in end:
                        newDst = "r" + str(rStatus.index(False) + reg)
                        reg += 1
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

                        if not item: continue

                        if any([IndexOfSafe(item, char) != -1 for char in "+-*/"] + ["(" in item]):
                                if not (item == "-" and inner[dex - 1] == "1"):
                                    that = CompileOperand(item, ext, AllocateRegister(reg), components)
                                    if IsASingleMov(that[1]):
                                        item = "\"" + that[1][that[1].index(",") + 2:-1] + "\""
                                        inner[dex] = item
                                    else:
                                        reg += 1
                                        prepend += that[1]
                                        
                                        item = "\"" + that[0] + "\""
                                        inner[dex] = item

                        if item[0] in "0123456789":
                            if item[:2] != "1-":
                                item = "\"" + AddConstant("constant_" + str(constants), item, "f" if item[-1] == "f" else "i") + "\""

                        if "." in item:
                            item = item.split(".")
                            item.append(len(item[1]))
                        else:
                            hvar = HVarNameToVar(item)
                            if hvar and not (isPixelShader) and (hvar.offset or hvar.type[1] != "4") and hvar.register[0] != "v":
                                item = [item, "xyzw"[hvar.offset:hvar.offset + int(hvar.type[1])], int(hvar.type[1])]
                            else:
                                item = [item, ""]
                            
                            if item[0] in hvars:
                                item[-1] = hvars[hvars.index(item[0])].type[1:]
                            elif item[0] in dhvars:
                                item[-1] = dhvars[dhvars.index(item[0])].type[1:]
                            else:
                                if not isPixelShader:
                                    item[-1] = "m4" if (item[0] == "c0") else "m3" if (item[0] == "c4") else "4"
                                else:
                                    item[-1] = "4"

                        end = end.replace("%tn" + str(dex + 1), str(item[-1]))

                        name = '.'.join(item[:-1]).strip()
                        hv = HVarNameToVar(name)

                        if hv:
                            # I now know a bit more about regexs
                            matches = findall("%" + str(dex + 1) + "\\.[xyzwrgba]+", end)
                            for m in matches:
                                end = end.replace(m, hv.register + OffsetProperty(m[m.index("."):], hv.offset))
                            register = hv.register
                        else:
                            register = HVarNameToRegister(name)
                            if "." in register:
                                end = end.replace("%" + str(dex + 1) + ".", register[:register.index(".") + 1])

                        end = end.replace("%" + str(dex + 1), register)
                    return [dst, prepend + end + "\n"]
            if matchingFuncs:
                def ConvertToType(num):
                    return ("float" + str(num)) if num > 1 else "float"
                def ConvertToTypeFull(params):
                    return str([ConvertToType(item) for item in params])[1:-1].replace('\'', '')
                Error(f"None of the overloads for {matchingFuncs[0].name} matches the situation: {ConvertToType(components)}({ConvertToTypeFull(parameters)})")
                print("Overload options:")
                for m in matchingFuncs:
                    print(f"{ConvertToType(m.rtn)}({ConvertToTypeFull(m.params)})")

    for op in ops:
        if op[0] in string:
            dex = 0
            while (dex := IndexOfSafe(string, op[0], dex)) != -1:
                these = [item.strip() for item in [string[:dex], string[dex + 1:]]]
                if isPixelShader and (op[0] == "-" and these[0] in ["", "1"]):
                    dex += 1
                    continue

                if not these[0]:
                    dex += 1
                    continue

                destination = dst
                suffix = ""

                sembly += op[1:] + ext + "\t" + destination + ", " + HVarNameToRegister(these[0].strip()) + ", " + HVarNameToRegister(these[1].strip(), linenum) + suffix + "\n"
                mathed = True

                dex += 1

    if not mathed:
        val = HVarNameToRegister(string)
        if val != dst:
            return [dst, "mov" + ext + "\t" + dst + ", " + val + "\n"]

        return [dst, ""]

    return [dst, sembly]

def ConstantsToRegisters(lst):
    for index, item in enumerate(lst):
        if IsConst(item):
            lst[index] = "\"" + AddConstant(f"constant_{constants}", item) + "\""
    return lst

def CompileOperand_PartialPS(string, ext="", dst="", components=4):
    mathed = False
    m = GetFirstModif(string)
    if m:
        dex = string.index(m[0] + "(") + len(m[0]) + 1
        end = GetParEnd(string, dex)
        inner = string[dex:end]
        return CompileOperand(inner, "_" + m[1] + ext, dst)

    if "?" in string:
        symbols = [">=", "<"]
        symbolMeanings = [", %0, %1", ", %1, %0"]
        if float(pixelshaderversion) > 1.1:
            for dex, symbol in enumerate(symbols):
                if symbol in string:
                    splt = string[:string.index("?")].strip()
                    if splt[0] == "(" and splt[-1] == ")":
                        splt = splt[1:-1]

                    splt = [item.strip() for item in splt.split(symbol)]

                    src0 = splt[0]
                    
                    if IsConst(src0) and float(src0) == 0.0:
                        src0 = splt[1]
                        dex = 1 - dex

                    values = [item.strip() for item in string[string.index("?") + 1:].split(":")]

                    values = ConstantsToRegisters(values)

                    return [dst, "cmp" + ext + "\t" + ", ".join([dst, HVarNameToRegister(src0)]) + symbolMeanings[dex].replace("%0", HVarNameToRegister(values[0])).replace("%1", HVarNameToRegister(values[1])) + "\n"]

        dex = string.index("?") + 1
        inner = [item.strip() for item in string[dex:].split(":")]
        inner = ConstantsToRegisters(inner)
        return [dst, "cnd" + ext + "\t" + ", ".join([dst, "r0.a", HVarNameToRegister(inner[0].strip()), HVarNameToRegister(inner[1].strip())]) + "\n"]

    if "/" in string:
        if string[string.index("/") + 1:].strip() != "2":
            Error("In the pixel shader, dividing can only be done by 2. It's used like saturate(), an addon to a math expression or another function, such as (a + b / 2)")
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
        if string.split("/")[0].strip() == "1":
            return [dst, "rcp\t" + dst + ", " + HVarNameToRegister(string.split("/")[1].strip()) + "\n"]
        return [dst, "rcp\t" + dst + ", " + HVarNameToRegister(string.split("/")[1].strip()) + "\nmul\t" + dst + ", " + dst + ", " + HVarNameToRegister(string.split("/")[0].strip()) + "\n"]

    if "?" in string:
        dex = string.index("?")
        inner = string[:dex].strip()
        if inner[0] == "(" and inner[-1] == ")":
            inner = inner[1:-1]
        prefix = ""
        # I was thinking the arguments could be swapped to get the other comparisons, unfortunately it's more limited than I thought
        compareOps = [(">=", "sge\t%0, %1, %2"), ("<", "slt\t%0, %1, %2")]
        for operator in compareOps:
            if operator[0] in inner:
                sides = [item.strip() for item in inner.split(operator[0])]
                for dex, side in enumerate(sides):
                    if IsConst(side):
                        sides[dex] = BreakdownMath(side)[0]

                    if any([char in side for char in "-+*/("]):
                        that = CompileOperand(side)
                        prefix += that[1]
                        if "\"" in that[0]:
                            sides[dex] = that[0]
                        else:
                            sides[dex] = "\"" + that[0] + "\""
                return [dst, prefix + operator[1].replace("%0", dst).replace("%1", HVarNameToRegister(sides[0])).replace("%2", HVarNameToRegister(sides[1])) + "\n"]

    return False

def ArrangeMad(muls, adds):
    i = adds.index(muls[0], 1)
    return (adds[0], muls[1], muls[2], adds[1 if i == 2 else 2])

# I rolled by own knock-off version because I thought start meant where it would start searching, and couldn't figure out why it wasn't working.
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

def includes_defines(list_item, test_value): return list_item[0] == test_value

# includes with a key
def includes(lst, item, func=includes_defines):
    for i in lst:
        if func(i, item):
            return True
    return False

# Removes vector splitting to get just the variable
def RemoveSwizzle(string): return string.split(".")[0].strip()

script = ""

def TooManyRegisters(operands, regType, limit=1):
    return [item[0] == regType for item in operands].count(True) > limit

# This function optimizes the assembly code that the compiler output.
def SecondPass(script):
    tempScript = ""
    dex = 0

    # Turning multiplies and adds into mads
    while (mdex := script.find("mul", dex)) != -1:
        if "\n" not in script[mdex:]:
            break

        tdex = script.index("\n", mdex)
        muls = script[mdex + 4:tdex].split(",")
        muls = [item.strip() for item in muls]
        if script[tdex + 1:tdex + 4] == "add":
            adds = script[script.index("\t", tdex + 1) + 1:script.index("\n", tdex + 1)].split(",")
            adds = [item.strip() for item in adds]
            sources = muls[1:] + adds[1:]
            if TooManyRegisters(sources, "c", 2 if isPixelShader else 1) or TooManyRegisters(sources, "v"):
                dex = mdex + 1
                continue
            
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

    # Skips mov-ing to the address register when it's being given the same source and it hasn't changed.
    dex = 0
    aRegVal = ""
    last = 0
    while (dex := script.find("mov\ta0.x, ", dex)) != -1:
        lineEnd = script.index("\n", dex)
        if aRegVal == script[dex + len("mov\ta0.x, "):lineEnd]:
            line = aRegVal[:aRegVal.index(".")]
            if "\t" + aRegVal + "," not in script[last:lineEnd]:
                script = script[:dex] + script[lineEnd + 1:]
                continue
        aRegVal = script[dex + len("mov\ta0.x, "):script.index("\n", dex)]

        last = dex
        dex = script.index("\n", dex)

    # Skips the middle man when a result is mov'd somewhere and isn't read from the original source again
    dex = 0
    while (mdex := script.find("mov\t", dex)) != -1:
            sdex = RFind(script, "\n", mdex - 2)
            tdex = script.find("\t", sdex)
            if script[mdex + 4:mdex + 8] == "a0.x":
                dex = mdex + 1
                continue

            if tdex != -1:
                muls = script[tdex + 1:script.index("\n", tdex)].split(",")
                dst = ((script[script.index(",", mdex) + 1:script.index("\n", mdex + 1)].strip()) if script.find("\n", mdex + 1) != -1 else script[script.index(",", mdex) + 1:].strip())
                if script[tdex + 1:script.index(",", tdex + 1)] == dst:
                    nextLine = script.index("\n", tdex)
                    nextRead = script.find(", " + dst, nextLine)
                    nextWrite = script.find(f"\t{dst}", nextLine)

                    if nextWrite == -1:
                        nextWrite = len(script)

                    if nextRead == -1 or nextWrite < nextRead:
                        tgt = script[mdex + 3:script.index(",", mdex)]
                        end = script.find("\n", mdex)
                        script = script[:tdex] + tgt + ", " + ", ".join([item.strip() for item in muls[1:]]) + (script[end:] if end != -1 else "")

            dex = mdex + 1

    return script

def HandleAssign(line):
    for symb in ["*=", "+=", "-="]:
        if symb in line:
            splt = [item.strip() for item in line.split(symb)]
            return splt[0] + " = " + splt[0] + " " + symb[0] + " (" + splt[1] + ")"

    return line.replace("++", "+= 1").replace("--", "-= 1")

def HandleForLoop(code, start, condition, inc, name, keyword, ssemblystart):

    inc = inc.replace("++", "+= 1")
    inc = inc.replace("--", "-= 1")
    
    referenced = CarefulIn(code, name)
    output = (ssemblystart + ";\n") if referenced else ""
    fullcode = CarefulReplace(code, name, keyword).replace("%keyword%", name) + ((inc + ";\n") if referenced else "")

    exec(start)
    while eval(condition):
        output += fullcode
        exec(inc)
    return output if not referenced else output[:-len(inc)]

# It would be nice if this happened when you use strings as slice indices
def SliceWithStrings(string, start, end):
    startIndex = string.index(start) + len(start)
    endIndex = string.index(end, startIndex)
    return string[startIndex:endIndex]

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

prevMode = 0

COMMENT_NONE = 0
COMMENT_ONE = 1
COMMENT_MULTI = 2

def CompileHLSL(script, localVars=-1, dst="r0", addLines=True, canDiscard=True):
    global linenum, col, scope, r0, r1, typeOfExpr, hvars, constants, unusedRegisters, functionRegisters
    if localVars == -1:
        localVars = []

    mode = 1
    bMeanwhile = False
    temp = 0
    commentType = COMMENT_NONE
    output = ""
    buffer = ""
    index = 0
    scopeCheck = 0

    while index < len(script):
        char = script[index]
        index += 1

        if char == '\n':
            if addLines: linenum += 1
            col = 0

        col += 1

        # Comments
        if mode not in [0, 2]:
            if commentType:
                if commentType == COMMENT_ONE:
                    if includeComments: output += char
                    if char != '\n': continue
                    commentType = COMMENT_NONE
                else:

                    if char == "\n":
                        if includeComments: output += "\n;"
                    elif includeComments:
                        output += char

                    if temp == "*" and char == "/":
                        output = output[:output.rfind("\n") + 1]
                        output += "\n"
                        commentType = COMMENT_NONE
                        continue
                    else:
                        temp = char
                        continue

            if buffer:
                if buffer[-1] == '/':
                    if char == '/':
                        buffer = buffer[:-1]
                        commentType = COMMENT_ONE
                        if includeComments:
                            if output:
                                if output[output.rfind("\n", 0, len(output) - 1) + 1] != ";":
                                    output += "\n\n"
                            output += ";"
                        continue

                    if char == '*':
                        buffer = buffer[:-1]
                        commentType = COMMENT_MULTI
                        temp = ""
                        if includeComments: output += "\n\n;"
                        continue

        # Checking for assembly
        if mode != 2 and buffer[-4:-1] == "asm" and buffer[-1] in "\t\n {":
            buffer = ""
            prevMode = mode
            mode = 0
            while script[index] in " \n\t{":
                if script[index] == "\n" and addLines: linenum += 1
                index += 1
            continue

        # Reading Assembly
        if not mode:
            if char == "}":
                mode = prevMode
                continue

            if char == "{": continue

            if output != "":
                if (char in " \t\n") and (output[-1] == '\n'):
                    continue
            output += char
            continue

        # Reading Function
        elif mode == 2:
            if char == '}':
                if not temp:
                    functionRegisters = -1
                    hfuncs[-1].code = CompileHLSL(buffer.strip(), -1, "%0", False, False).strip()

                    buffer = ""

                    mode = 1
                    for dex, item in enumerate(hvars):
                        if item.register[0] == "%":
                            hvars = hvars[:dex] + hvars[dex + 1:]

                    scope = "Pixel Shader" if isPixelShader else "Vertex Shader"
                    continue
                else:
                    temp -= 1

            if char == '{' and buffer.strip():
                temp += 1

            buffer += char

        # Reading HLSL
        elif mode == 1:
            if buffer:
                if (char == ' ' and char == buffer[-1]):
                    continue

            if char in '\t\n':
                continue

            if char == "(": scopeCheck += 1
            if char == ")": scopeCheck -= 1

            if (char == ';' and not scopeCheck) or (char == "{" and "[" not in buffer):
                line = buffer
                buffer = ""

                unusedRegisters = 0

                if not line.strip(): continue
                line = line.strip()

                if " " not in line and "(" in line:
                    typeOfExpr = "Calling Void Function"
                    if line.index("(") > 0:
                        if line[line.index("(") - 1] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            output += CompileOperand(line, "", dst)[1]
                            continue

                if line[:3] == "for" and line[3] in " \n\t(":
                    typeOfExpr = "For Loop"

                    if search("^for[ \t\n\\(]+[a-zA-Z0-9]+ in .+", line):
                        
                        varName = line[4:line.index(" in ")].replace("(", "").strip()

                        keyword = "%keyword%"

                        if " range(" in line:
                            ranges = SliceWithStrings(line, " range(", ")").split(",")

                            for dex, rang in enumerate(ranges):
                                if rang[0] not in "01234567890.":
                                    hv = HVarNameToVar(rang)
                                    if hv:
                                        if not hv.value:
                                            Error("Variables are not allowed in for loops, it must be a constant.")
                                        ranges[dex] = hv.value[hv.value.index("(") + 1:hv.value.index(")")].split(",")[0]

                            match len(ranges):
                                case 0:
                                    Error("There\'s nothing in the range()")
                                case 1:
                                    ranges = ["0", ranges[0], "1" if float(ranges[0]) > -1 else "-1"]
                                case 2:
                                    ranges.append("1" if int(ranges[0]) < int(ranges[1]) else "-1")
                        else:
                            arrayName = line[line.index(" in ") + len(" in "):].replace(")", "").strip()
                            keyword = arrayName + "[%keyword%]"
                            ranges = ["0", HVarNameToVar(arrayName).type[-1], "1"]

                        statements = [f"float {varName} = {str(float(ranges[0]))}", f"{varName} < {str(float(ranges[1]))}", f"{varName} += {str(float(ranges[2]))}", f"{varName} = {ranges[0]}"]
                    else:
                        statements = [item.strip() for item in SliceWithStrings(line, "(", ")").split(";")]
                        for i, s in enumerate(statements):
                            if s[-1] == 'f':
                                statements[i] = s[:-1]

                        statements.append(statements[0][statements[0].index(" ") + 1:].strip())
                        varName = statements[-1].split("=")[0].strip()
                        keyword = "%keyword%"
                        statements[0] = "float " + statements[-1]

                    closingIndex = GetParEnd(script, index, "{}")
                    loopCode = script[index:closingIndex]

                    previousScope = scope
                    scope = "For Loop"
                    output += CompileHLSL(HandleForLoop(loopCode, statements[3], statements[1], statements[2], varName, keyword, statements[0]), addLines=False, canDiscard=False)
                    linenum += script[index:closingIndex + 1].count("\n")

                    index = closingIndex + 1
                    scope = previousScope
                    continue
                
                unusedRegisters = 0

                line = HandleAssign(line)

                bMeanwhile = False
                if line.split(" ")[0] == "meanwhile":
                    bMeanwhile = True
                    line = line[10:]

                defType = IsDef(line)
                bForceConst = False

                if " " in line:
                    # If you re-define a variable it will just treat it as an assignment
                    if line.split(" ")[1] in hvars and defType:
                        Error(f"Warning: re-definition of [{line.split(" ")[1]}]")
                        defType = False
                        line = line[line.index(" ") + 1:]

                if defType:
                    tokens = line.split(" ")

                    if tokens[0] == "const":
                        tokens = tokens[1:]
                        bForceConst = True

                    line = " ".join(tokens)

                    if IsConst(line) or bForceConst:
                        typeOfExpr = "Defining Constant"
                        if "[" in tokens[1]:
                            items = ArraySplit(line.split("=")[1].strip()[1:-1])
                            AddConstant(tokens[1][:tokens[1].index("[")], items[0], defType, False)
                            hvars[-1].type += "a" + str(len(items))
                            for c in items[1:]:
                                AddConstant("constant_" + str(constants), c, defType, False)
                        else:
                            AddConstant(SliceWithStrings(line, " ", "=").strip(), line.split("=")[1].strip(), defType)

                    else:
                        typeOfExpr = "Defining Variable"
                        if IsType(tokens[0]):
                            if "(" in tokens[1]:
                                typeOfExpr = "Defining Function"
                                tokens[1] = SliceWithStrings(line, " ", "(")

                                params = [GetSizeFromParam(item.strip()) for item in SliceWithStrings(line, "(", ")").split(",")]
                                rtnType = SizeOf(line[:line.index(" ")])

                                hfuncs.append(HFunc(tokens[1], "", rtnType, params))
                                args = [item.strip().split(" ") for item in SliceWithStrings(line, "(", ")").split(",")]
                                scope = tokens[1]
                                if args:
                                    hvars += [HVar(item[-1], "%" + str(i + 1), "", "f4" if len(item) == 1 else TypeIdFromName(item[-2])) for i, item in enumerate(args)]
                                temp = 0
                                mode = 2
                                buffer = ""

                            else:
                                if "=" in line:
                                    tokens[2] = line[line.index("=") + 1:].strip()
                                    tokens[0] = tokens[0].strip()
                                    components = "1" if tokens[0] in ['float', 'int', 'bool'] else tokens[0][-1]
                                    r = CompileOperand(tokens[2], "", Swizzle(AllocateRegister(0, True), int(components)), int(components))
                                    hvars.append(HVar(tokens[1], r[0], "", tokens[0][0] + components))
                                    output += ("+" if bMeanwhile else "") + r[1]
                                elif len(tokens) == 2:
                                    hvars.append(HVar(tokens[1], AllocateRegister(0, True), "", tokens[0][0] + ("1" if tokens[0] in ['float', 'int', 'bool'] else tokens[0][-1])))

                else:
                    tokens = line.split(" ")
                    match tokens[0]:
                        case "return":
                            typeOfExpr = "Return"
                            r = CompileOperand(line[7:], "", dst)
                            if not r[1] and printOnNoReturnCode:
                                r[1] = "; No need for return code.\n"
                            output += ("+" if bMeanwhile else "") + r[1]
                            if stopOnReturn:
                                break
                            continue

                    if '=' in line:
                        tokens = line.split("=")[0].split(" ") + ["="] + line.split("=")[1].split(" ")
                        typeOfExpr = "Assign"
                        tokens[0] = tokens[0].strip()
                        if tokens[0][0] == "\"":
                            if bMeanwhile:
                                output += "+"
                            output += CompileOperand(line[line.index("=") + 1:], "", HandleString(tokens[0]), int(GetRegisterType(tokens[0][1:-1])[1:]))[1]
                        else:
                            name = tokens[0]
                            extension = ""
                            if "." in tokens[0]:
                                name = RemoveSwizzle(tokens[0])
                                extension = tokens[0][tokens[0].index("."):]
                            if name in hvars + dhvars:
                                hv = HVarNameToVar(name)
                                if hv:
                                    if (hv.offset or (int(hv.type[1]) != 4)) and not extension:
                                        extension = "." + "xyzw"[hv.offset:hv.offset + int(hv.type[1])]
                                    output += ("+" if bMeanwhile else "") + CompileOperand(line[line.index("=") + 1:], "", HandleString("\"" + hv.register + "\"" + HandleProperty(extension)), int(hv.type[1]))[1]
                                else:
                                    Error("Syntax Error: Unknown token: " + Surround(name))
                            else:
                                if not includes(inlineDefs, name):
                                    Error("Unknown token: [" + name + "]")
                                for d in inlineDefs:
                                    if d[0] == name:
                                        output += ("+" if bMeanwhile else "") + CompileOperand(line[line.index("=") + 1:], "", d[1])[1]
                    else:
                        if line:
                            print("Unknown Expression:", line)

                # Clearing out variables that aren't referenced anymore
                if autoDiscard and canDiscard:
                    hvindex = 0
                    while hvindex < len(hvars):
                        hv = hvars[hvindex]
                        if (not hv.value) and (hv.register[0] == "r"):
                            if not CarefulIn(script[index:], hv.name):
                                rStatus[int(hv.register[1])] = False
                                if debugComments:
                                    output += "\n; " + hv.name + " deleted\n\n"
                                hvars = hvars[:hvindex] + hvars[hvindex + 1:]
                                continue
                        hvindex += 1
            else:
                buffer += char

    # The first one isn't working for whatever reason
    output = output.replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n")
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


semantics = [["sv_position", "vpos", "position"], ["normal"], ["sv_target", "color"], ["texcoord"]]
semantictypes = ["f3", "f3", "f4", "f2"]

def GetSemantic(string):
    while string[-1] in "0123456789":
        string = string[:-1]
    for i, s in enumerate(semantics):
        if string.lower() in s:
            return i
    return -1

coordinateInputs = 0
numTextures = 0
usedSemantics = [False, False, False]
formats = [("Pos", "position"), ("Norm", "normal"), ("Color", "color")]

def MakeStreamFormat(bPostProcess):
    f = ""

    if IsDefined("inputStreamFormat"):
        return "That"

    if bPostProcess:
        f = "PosprojTex" + str(numTextures)
    else:
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

# Contains lists where the first item is the name, and the second item being the replacement
inlineDefs = []

def HandleDefines(line):
    global vertexConstants, pixelConstants
    tempLine = line.strip().replace("\t", " ").replace("  ", " ")
    if tempLine:
        if tempLine[0] == "#" and " " in tempLine:
            arg = tempLine[tempLine.index(" ") + 1:].strip()
            match tempLine[1:tempLine.index(" ")]:
                case "define":
                    name = tempLine.split(" ")[1].strip()

                    if len(tempLine.split(" ")) > 2:
                        if "(" in name:
                            name = name[:name.index("(")]
                            params = [item.strip() for item in tempLine[tempLine.index("(") + 1:tempLine.index(")")].split(",")]
                            
                            replacee = tempLine[tempLine.index(")") + 1:].strip()
                            for i,  p in enumerate(params):
                                replacee = CarefulReplace(replacee, p, "%" + str(i))
                        else:
                            replacee = tempLine[tempLine.index(" ", tempLine.index(" ") + 1):].strip()
                    else:
                        replacee = ""

                    inlineDefs.append((name, replacee))

                    return

                case "include":
                    name = arg[1:-1].strip()
                    with open(filename[:filename.rfind("/") + 1] + name) as includefile:
                        inlineDefs.append((line, includefile.read()))
                    return

                case "vconstants":
                    vertexConstants = int(arg)
                    return

                case "pconstants":
                    pixelConstants = int(arg)
                    return

                case "python":
                    arg = f"global {arg[:arg.index('=')].strip()}\n{arg}"
                    exec(arg)
                    return

        if tempLine.split(" ")[0:2] == ["const", "string"]:
            tempLine = tempLine[6:]

        if tempLine.split(" ")[0] == "string":
            name = tempLine[7:tempLine.index("=")].strip()
            replacee = tempLine[tempLine.index("=") + 1:].strip()
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
        settings = "\'\'\'\n Un-comment these to change them. \nThis is a python script so theoretically any variable from the script can be changed from here\n\'\'\'\n\n#filename = \"\"\n#author = \"\"\n#loop = True\n\n# Self-Explanatory\n#noOptimizations = False\n\n# Whether or not the time is shown in 24 hours\n#is24Hour = False\n\n#Whether or not comments from the HLSL file get copied to the SHA file\n#includeComments = True"
        settingsFile.write(settings)

# The settings file is now just a python file, so technically this modding tool has mod support
# On second thought, I guess any Python script technically has modding support.
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
    # This makes it so you can also type 'yes' or 'no' and it will know what you mean
    loop = input("Do you want to enable that? (y/N) ").strip()[0] in "Yy"

psLine = 0
vsLine = 0

def defFilter(a):
    if a.strip():
        return a.strip()[0] != "#"
    return True

def AddTabs(script, tabs):
    out = ""
    for line in script.split("\n"):
        if not line.strip():
            out += "\n"
            continue
        out += tabs + line + "\n"
    return out

def IsDefined(keyword):
    for d in inlineDefs:
        if keyword == d[0]:
            return True

    return False

def HandleIfDef(hlsl, index, bNot):
    directive = "#ifndef " if bNot else "#ifdef "
    
    entireThing = hlsl[index:hlsl.index("#endif", index) + len("#endif")].strip()
    toCheck = entireThing[len(directive):entireThing.index("\n")]
    smallSection = entireThing[entireThing.index("\n") + 1:-len("#endif")]
    options = ["", smallSection]
    if "#else" in smallSection:
        options = [smallSection[smallSection.index("#else") + len("#else"):], smallSection[:smallSection.index("#else")]]

    if HasOperators(toCheck) or (toCheck[0] == "(" and toCheck[-1] == ")"):
        exists = eval(toCheck)
    else:
        exists = IsDefined(toCheck)

    if bNot:
        exists = not exists
    
    return hlsl.replace(entireThing, options[int(exists)])

while stuckInLoop:
    stuckInLoop = loop
    if getmtime(filename) != mtime:
            tstruct = localtime(time())
            mtime = getmtime(filename)
            dhvars = [HVar("SHADOW", "c2", "", "f4"), HVar("AMBIENT", "v0", "", "f3"), HVar("FRESNEL", "v0.a", "", "f1"), HVar("BLEND", "v1.a", "", "f1"), HVar("%split%", "", "", "")]
            ResetDHVars(True)
            hvars = []
            fvars = []
            constants = pixelConstants
            coordinateInputs = 0
            numTextures = 0
            startC = pixelConstants
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
            sleep(0.5)
            compiledpixelshader = ""
            compiledvertexshader = ""
            pixelshaderversion = "1.3"
            with open(filename) as file:
                hlsl = file.read()
                [HandleDefines(line) for line in hlsl.split("\n")]
                while (ifdef := hlsl.find("#ifdef ")) != -1:
                    hlsl = HandleIfDef(hlsl, ifdef, False)
                while (ifdef := hlsl.find("#ifndef ")) != -1:
                    hlsl = HandleIfDef(hlsl, ifdef, True)

                for v in ["1_3", "1_2", "1_1"]:
                    if IsDefined("ps_" + v):
                        pixelshaderversion = v.replace("_", ".") # Not only does this pre-calculate the instruction to use, but it can then be converted to a float to compare versions easily
                        break
                        
                for d in inlineDefs:
                    if "%0" in d[1]:
                        while CarefulIn(hlsl, d[0]):
                            newLine = d[1].replace("\n", "\n")
                            dex = CarefulIndex(hlsl, d[0])
                            params = hlsl[dex + len(d[0]) + 1:hlsl.index(")", dex)].split(",")
                            params = [item.strip() for item in params]
                            for i, p in enumerate(params):
                                newLine = newLine.replace("%" + str(i), p)
                            hlsl = hlsl[:dex] + newLine + hlsl[hlsl.index(")", dex) + 1:]
                    else:
                        if d[0] in hlsl:
                            hlsl = CarefulReplace(hlsl, d[0], d[1])
                #hlsl = "\n".join(filter(lambda a : (a.strip()[0] != "#") if a.strip() else True, hlsl.split("\n")))

            (inputs, pixelshader, psLine) = GetShader(hlsl, True)
            if pixelshader:
                if not inputs[0].strip():
                    textures = 0
                else:
                    textures = len(inputs)
                    for i, put in enumerate(inputs):
                        newType = ""
                        if " " in put.strip():
                            n = put.strip().split(" ")[-2]
                            if (not IsType(n)) and n != "tex":
                                newType = n

                            put = put.strip().split(" ")[-1]
                        dhvars.append(HVar(put.strip(), "t" + str(i), newType, "f4"))
                        numTextures += 1

            psSnapshot = [item for item in dhvars]

            (inputs, vertexshader, vsLine) = GetShader(hlsl, False)
            if vertexshader:
                if inputs[0].strip():
                    for i, put in enumerate(inputs):
                        put = put.strip()

                        if not put: continue

                        if ":" not in put:
                            Error("Type is optional, but semantics are required on parameters in the vertex shader. It has to be at least \"name : semantic\". The semantics are POSITION, NORMAL, COLOR, and TEXCOORD")
                        put = put.split(":")
                        t = [put[1].strip()]
                        t.append(put[0].strip().split(" ")[-1].strip())

                        dex = GetSemantic(t[0])

                        if dex == -1:
                            Error("Unknown Semantic: [" + t[0] + "]")

                        if len(put[0].strip().split(" ")) > 1:
                            t.append(put[0].strip().split(" ")[-2].strip())
                        else:
                            t.append(semantictypes[dex])

                        if dex == 3:
                            dhvars.append(HVar(t[1], "v" + str(dex + coordinateInputs), "", "f2"))
                            decl += "\t\tfloat\tv" + str(dex + coordinateInputs) + "[2];\t// " + t[1] + "\n"
                            coordinateInputs += 1

                        else:
                            usedSemantics[dex] = True
                            dhvars.append(HVar(t[1], "v" + str(dex), "", t[2][0] + t[2][-1]))
                            if t[2][-1] == "4":
                                decl += "\t\tD3DCOLOR\tv" + str(dex) + ";\t// " + t[1] + "\n"
                            else:
                                decl += "\t\tfloat\tv" + str(dex) + ("" if t[2] == "float" else Surround(t[2][-1])) + ";\t// " + t[1] + "\n"

            decl = decl.split("\n")
            decl.sort(key=SortDecl)
            decl = "\t\tstream 0;\n" + "\n".join(decl) + "\n"

            passbuffer = ""
            defconstantbuffer = ""
            vertdefconstantbuffer = ""

            if createFullFile:
                with open(newfilename, "w") as sfile:

                    date = dateFormat.replace("M", str(tstruct.tm_mon)).replace("D", str(tstruct.tm_mday)).replace("Y", str(tstruct.tm_year))
                    sfile.write("///////////////////////////////////////////////////////////////////////////\n")
                    sfile.write("// " + newfilename[newfilename.rfind("/") + 1:] + "\n")
                    sfile.write("///////////////////////////////////////////////////////////////////////////\n")
                    sfile.write("// Created on " + date + " " + str((tstruct.tm_hour if (tstruct.tm_hour < 13 or is24Hour) else tstruct.tm_hour - 12)) + ":" + str(tstruct.tm_min).rjust(2, "0") + ":" + str(tstruct.tm_sec).rjust(2, "0") + " " + ("" if is24Hour else ("PM" if tstruct.tm_hour > 11 else "AM")) + "\n")
                    sfile.write("//\n")
                    sfile.write("// Authors: " + author + "\n")
                    sfile.write("//\n")
                    sfile.write("// Zack\'s HLSL-to-FlatOut-Shader " + version + "\n")
                    sfile.write("///////////////////////////////////////////////////////////////////////////\n")

                    for i in range(textures):
                        sfile.write("Texture Tex" + str(i) + ";\n")

                    sfile.write("\nconst string inputStreamFormat = \"" + MakeStreamFormat(not vertexshader) + "\";\n\n")

                    if vertexshader:
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

                        rStatus = [False for i in range(maxR)]
                        constants = pixelConstants
                        startC = pixelConstants
                        script = pixelshader
                        with open("pixel_builtin.hlsl") as file:
                            thatthing = file.read()
                            while (ifdef := thatthing.find("#ifdef ")) != -1:
                                thatthing = HandleIfDef(thatthing, ifdef, False)
                            while (ifdef := thatthing.find("#ifndef ")) != -1:
                                thatthing = HandleIfDef(thatthing, ifdef, True)
                            CompileHLSL(thatthing, addLines=False, canDiscard=False)

                        linenum = psLine

                        compiledpixelshader = CompileHLSL(pixelshader, -1, "r0", 2)
                        seenconstants = [False for i in range(maxC)]
                        for hvar in hvars:
                            if hvar.register:
                                reg = hvar.register
                                if reg[0] == 'c':
                                    if "." in reg:
                                        reg = reg[:reg.index(".")]
                                    if not hvar.offset or not seenconstants[int(reg[1:])]:
                                        seenconstants[int(reg[1:])] = True
                                        if constantsInPass:
                                            passbuffer += "\t\tPixelShaderConstant" + hvar.type[0].upper() + "[" + hvar.register[1] + "] = " + hvar.value + ";\n"
                                        else:
                                            defconstantbuffer += "\t\tdef\t" + (hvar.register[:hvar.register.index(".")] if "." in hvar.register else hvar.register) + ", " + SliceWithStrings(hvar.value, "(", ")").replace("%x", "0") + "\n"

                        if textures:
                            compiledpixelshader = "\n" + compiledpixelshader
                            for i in range(textures - 1, -1, -1):
                                hv = HVarRegisterToVar("t" + str(i))
                                if hv.value in ["texcoord", "texkill"]:
                                    prefix = hv.value
                                else:
                                    prefix = "tex"
                                compiledpixelshader = prefix + "\tt" + str(i) + "\t// " + hv.name + "\n" + compiledpixelshader

                    passbuffer = "\n" + passbuffer

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

                        # c95.x = degrees to radians, the rest are just very common
                        hvars = [HVar("reservedconstant_95", "c95", "float4(0.0174533f, 1.0f, 0.5f, 0.0f)", "f4")]
                        fvars = []
                        rStatus = [False for i in range(maxR)]

                        script = vertexshader

                        with open("vertex_builtin.hlsl") as file:
                            CompileHLSL(file.read(), addLines=False, canDiscard=False)

                        linenum = vsLine

                        compiledvertexshader = CompileHLSL(vertexshader, -1, "oPos", 2)
                        seenconstants = [False for i in range(maxC)]
                        hvars = hvars[1:] + [hvars[0]]
                        for hvar in reversed(hvars):
                            reg = hvar.register
                            if reg[0] == 'c':
                                if "." in reg:
                                    reg = reg[:reg.index(".")]
                                if (not seenconstants[int(reg[1:])] or not hvar.offset) and hvar.value:
                                    seenconstants[int(reg[1:])] = True
                                    if constantsInPass:
                                        passbuffer = "\t\tVertexShaderConstant" + hvar.type[0].upper() + "[" + (hvar.register[1:hvar.register.index(".")] if "." in hvar.register else hvar.register[1:]) + "] = " + hvar.value + ";\n" + passbuffer
                                    else:
                                        vertdefconstantbuffer += "\t\tdef\t" + (hvar.register[:hvar.register.index(".")] if "." in hvar.register else hvar.register) + ", " + SliceWithStrings(hvar.value, "(", ")").replace("%x", "0") + "\n"

                        if vertdefconstantbuffer:
                            vertdefconstantbuffer += "\n"

                        sfile.write(vertdefconstantbuffer)
                        sfile.write(MakeDcls() + "\n")
                        sfile.write(AddTabs(compiledvertexshader, "\t\t"))

                    if vertexshader:
                        sfile.write("\t};\n\n")

                    if pixelshader != "":
                        hvars = [item for item in psSnapshot]
                        sfile.write("pixelshader pSdr =\n\tasm\n\t{\n")
                        sfile.write(f"\t\tps.{pixelshaderversion}\n")
                        sfile.write("\n")
                        if defconstantbuffer:
                            defconstantbuffer += "\n"
                        sfile.write(defconstantbuffer)
                        sfile.write(AddTabs(compiledpixelshader, "\t\t"))
                        sfile.write("\t};\n\n")


                    # The hlsl file can now have a technique and pass, to add settings that certain shaders need
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
                        
                    sfile.write(f"\n\t\tVertexShader = {'<vSdr>' if vertexshader else 'null'};\n")
                    sfile.write(f"\t\tPixelShader = {'<pSdr>' if pixelshader else 'null'};\n")
                    sfile.write("\t}\n}")



            else:
                if pixelshader != "":
                        print(CompileHLSL(pixelshader, -1, "r0", True))
            print("Done!\n")


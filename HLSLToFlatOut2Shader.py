# Zack's HLSL to FlatOut SHA
version = "v3.3.3"
# Am I particularly proud of this code? uhh

try:
    from tkinter import filedialog
except:
    from Tkinter import filedialog

from time import time, localtime, sleep
from os.path import getmtime
from re import findall, search
from math import ceil


# Can be turned off if you relied on the old behaviour
fixTheWorkDirBug = True
scriptPath = ""

if fixTheWorkDirBug:
    # In case you are running this in vs code, where the work directory is not where the script is
    folderSplit = "\\" if "\\" in __file__ else "/"
    scriptPath = __file__[:__file__.rindex(folderSplit) + 1]

isPixelShader = True

filename = ""
author = ""
authors = "" # I accidentally made a typo in the original settings file so it's a feature now
loop = ""

# Cosmetic stuff
is24Hour = False # Whether the time is shown in 24-hours
includeComments = True # Whether to put comments from the HLSL file in the SHA file
dateFormat = "M/D/Y" # D will be replaced with the day, M with the month, and so on

# Things affecting compiler behaviour that are down to personal preference
stopOnReturn = True # Whether to stop compiling when it reaches a return
autoCreateVariables = False # Whether to allow creating float4 variables without specifying a type, like python.
noDefaultOverload = False # If True, throws an error when no overloaded functions match, instead of just going with the closest one
inlinePreferred = True # Whether to make functions inline by default, instead of static
guessConst = True # If a variable is declared with a constant expression, is it assumed to be a constant
stopOnError = False # Whether or not compiler errors will raise a RuntimeError to stop the script immediately

# Things meant for me when I'm debugging, can be changed if there's an edge case
printOnNoReturnCode = False # Will add a 'No return code needed' comment if a statement generates a mov where the source and destination are the same
debugComments = False # Adds information meant for debugging, such as when variables get deleted
autoDiscard = True # Whether to discard variables that are no longer needed, to free up registers
noOptimizations = False # Skips the second pass that does things like combining multiplies and adds into mads, and applying shortcuts when a mov is unnecessary

# Things that sort of kinda make it possible to maybe write shaders for other games
constantsInPass = True # Whether to put constants in the pass, or use def instructions.

# How many constants are reserved by the game, can vary from shader to shader
# The default values are for the car body
vertexConstants = 32
pixelConstants = 3

dhvars = []
hvars = []
hfuncs = []
htypes = []

class HVar:
    def __init__(self, name, register, value, tyype, offset=0, pixelShader=-1):
    
        # The HLSL keyword it's associated with
        self.name = name
        # The assembly keyword it's associated with, could be "r0", "t0", or "oPos.yyy"
        self.register = register
        # Reserved for constants, this what came after the =, for example "float4(0.0f, 0.0f, 0.0f, 0.0f)"
        self.value = value
        # type is now an HType
        self.type = GetType(tyype)
        # When packing multiple constants into a single register, the offset makes them reference the correct components
        self.offset = offset

        if pixelShader == -1:
            pixelShader = isPixelShader

        self.isPixelShader = pixelShader

    def __eq__(self, other):
        return self.name == other


    def __str__(self):
        return "HVar: [" +  ", ".join([self.name, self.register, self.value, self.type.name if self.type else "None", str(self.offset), str(self.isPixelShader)]) +"]\n"

    def __repr__(self):
        return self.__str__()


class HStructProperty:
    def __init__(self, name, type, offset):
        self.name = name
        self.type = type
        self.offset = offset

def Int(x, default=0):
    if x.isnumeric():
        return int(x)
    return default

def SizeOf(tyype):
    t = GetType(tyype)
    if t:
        return t.size

    return HVarNameToSize(tyype)

def GetType(name):
    for t in htypes:
        if t.name == name:
            return t

    return None

# To make structs possible, I re-invented the type system
class HType:
    def __init__(self, name, size, properties):
        self.name = name
        self.properties = []

        if properties:
            offset = 0
            for prop in properties:
                sides = prop.split(" ")
                propType = GetType(sides[0])
                dimensions = propType.size
                freeComponents = 4 - (offset % 4)
                if freeComponents < dimensions:
                    offset += freeComponents
                self.properties.append(HStructProperty(sides[1], propType, offset))
                offset += dimensions

            self.size = offset
        else:
            self.size = size

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        return "HType: " + self.name

def ResetHTypes():
    global htypes
    htypes = [HType(i, 1, []) for i in ["float", "int", "bool"]] + [HType("float" + str(i), i, []) for i in range(2, 5)] + [HType("int" + str(i), i, []) for i in range(2, 5)] + [HType("bool" + str(i), i, []) for i in range(2, 5)] + [HType("void", 1, []), HType("sampler2D", 4, []), HType("samplerCUBE", 4, [])]

def GetHStructProperty(hstruct, name):
    for prop in hstruct.properties:
        if prop.name == name:
            return prop
    return None

def ConvertSwizzles(to, frm):
    chart = "xyzwrbga"

    (keyword1, swizzle1) = frm.split(".")
    (keyword2, swizzle2) = to.split(".")

    newSwizzle = ""

    for char in swizzle2:
        dex = chart.index(char) % 4

        if dex >= len(swizzle1):
            Error(f"Can\'t access the {char} component of a float{len(swizzle1)}")
            newSwizzle = swizzle1
            break

        newSwizzle += swizzle1[dex]

    return f"{keyword1}.{newSwizzle}"

def GetFromHStruct(hstruct, register, name):
    prop = GetHStructProperty(hstruct, name)
    if not prop:
        Error(f"Property [{name}] does not exist on struct [{hstruct.name}]")
        return ""
    registerOffset = prop.offset // 4
    swizzleIndex = prop.offset % 4
    dimensions = prop.type.size
    swizzle = ("." + "xyzw"[swizzleIndex:swizzleIndex + dimensions]) if swizzleIndex or dimensions != 4 else ""

    if register[:1] == "%":
        if "+" in register:
            return f"{register[:register.index("+")]}+{int(register[register.index("+") + 1:]) + registerOffset}{swizzle}"
        return f"{register}+{registerOffset}{swizzle}"

    return f"{register[0]}{(int(register[1:])) + registerOffset}{swizzle}"


class HFunc:
    def __init__(self, name, code, rtnType, paramType):
        self.name = name
        self.code = code
        # These allow for overloading functions
        self.rtn = rtnType
        self.params = paramType

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        return "HFunc: [" +  ", ".join([self.name, self.code]) +"]"


scope = "Global"
typeOfExpr = ""
startC = 3
linenum = 0
shaderModel = "1.3"

def Error(message):
    errorMessage = f"Error in {scope} line {linenum} ({typeOfExpr}): {message}"
    if stopOnError:
        raise RuntimeError(errorMessage)
    print(errorMessage)

def Warn(message):
    print(f"Warning: {message} (line {linenum})")


def ResetDHVars():
    global dhvars
    dhvars = dhvars[dhvars.index("%split%"):]
    dhvars = ([HVar("HALF", "c0", "", "float4"), HVar("LIMITER", "c1", "", "float4"), HVar("SHADOW", "c2", "", "float4")] if isPixelShader else [HVar("CAMERA", "c8", "", "float3"), HVar("CAMDIR", "c9", "", "float3"), HVar("TIME", "c14", "", "float4"), HVar("PLANEX", "c17", "", "float4"), HVar("PLANEY", "c18", "", "float4"), HVar("PLANEZ", "c19", "", "float4")]) + dhvars
    if float(shaderModel) < 2.0:
        dhvars = ([HVar("AMBIENT", "v0", "", "float3"), HVar("FRESNEL", "v0.a", "", "float"), HVar("BLEND", "v1.a", "", "float"), HVar("EXTRA", "v1", "", "float3")] if isPixelShader else [HVar("FRESNEL", "oD0", "", "float", 3), HVar("AMBIENT", "oD0.xyz", "", "float3"), HVar("BLEND", "oD1", "", "float", 3), HVar("EXTRA", "oD1.xyz", "", "float3")]) + dhvars

def PSTexToVSTex():
    for dhvar in dhvars:
        if dhvar.register:
            if float(shaderModel) < 2.0:
                if dhvar.register[0] == "t":
                    dhvar.register = "oT" + dhvar.register[1:]
            else:
                if dhvar.register[0] == "v" and dhvar.isPixelShader:
                    dhvar.register = f"o{int(dhvar.register[1:]) + 1}"

# Finds the item in list1 and retrieves the corrosponding item in list2
def Translate(list1, list2, item):
    return list2[list1.index(item)]

def HVarRegisterToVar(register):
    for v in hvars + dhvars:
        if v.register == register:
            return v
    return False

def GetSizeFromParam(param):
    if " " in param:
        splt = param.split(" ")
        while splt[0] in ["in", "out"]:
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

def FindConstant(vals, swizzle=True, valtype="float"):
    dimensions = len(vals)
    valstring = ",".join(vals)
    for hv in hvars + dhvars:
        if hv.value and "(" in hv.value and hv.type.name[0] == valtype[0]:
            existingvalues = ','.join([StrToFloat(item) for item in SliceWithStrings(hv.value, "(", ")").split(",")])
            if valstring in existingvalues:
                offset = existingvalues[:existingvalues.index(valstring)].count(",")

                if isPixelShader and float(shaderModel) < 2.0:
                    if offset not in [0, 3]:
                        continue

                    if (not offset) and (dimensions < 3):
                        continue

                newRegister = hv.register

                if swizzle and "." not in newRegister:
                    newRegister = OffsetProperty(Swizzle(newRegister, dimensions), offset)

                return newRegister
    return ""

# Counts the number of constants
# [floats, integers, bools]
constants = [0, 0, 0]

def GetConstantType(constant):
    constant = constant.strip()

    if constant[0] in "1234567890":
        if constant[-1] == "f" or "." in constant:
            return "float"
        return "int"

    return "bool"

def RawValue(value):
    if value in ["true", "false"]:
        return 1.0 if value == "true" else 0.0

    if value[-1] == "f":
        value = value[:-1]

    return float(value)

def ConvertValue(value, valtype="float"):
    match valtype:
        case "int":
            return str(int(value))
        case "bool":
            return str(bool(value)).lower()

    return str(value) + "f"

def ConvertConstants(value, valtype="float"):
    vals = [value]
    if "," in value:
        vals = SliceWithStrings(value, "(", ")").split(",")

    return [ConvertValue(RawValue(val.strip()), valtype) for val in vals]

def AddConstant(name, value, valtype="float", pack=True, swizzle=True):
    registerLetter = "c"
    countIndex = 0

    valtype = RemoveTypeComponents(valtype)

    if float(shaderModel) >= 2.0:
        if valtype[0] != "f":
            registerLetter = valtype[0]
            countIndex = "fib".index(valtype[0])

    if constants[countIndex] >= maxC:
        Error(f"Too many constants defined, there can only be {maxC - startC}, since the game reserves {startC} of them")
        return ""

    vals = ConvertConstants(value, valtype)
    dimensions = len(vals)
    fullType = (valtype + str(dimensions)) if dimensions > 1 else valtype
    allDimensions = 0
    numConsts = 0

    def OffsetFromSwizzle(register):
        if "." not in register:
            return 0
        return "xyzw".index(register[register.index(".") + 1:][0])

    preExisting = FindConstant(vals, swizzle, valtype)
    if preExisting:
        if name:
            hvars.append(HVar(name, RemoveSwizzle(preExisting), "", GetType(fullType), OffsetFromSwizzle(preExisting)))
        return preExisting

    newHVar = HVar(name, "", "", GetType(fullType))

    if dimensions < 4 and pack:
        availableDimensions = 0
        firstConst = False

        for hv in hvars + dhvars:
            if hv.type and Swizzlable(hv.type):
                if hv.register[0] == registerLetter and "%x" in hv.value:
                    availableDimensions = hv.value.count("%x")
                    if availableDimensions >= dimensions:
                        firstConst = hv
                        break

        if firstConst:
            if availableDimensions >= dimensions:
                if isPixelShader and float(shaderModel) < 2.0:
                    if dimensions == 1 and ("%x)" in firstConst.value):
                        newHVar.register = firstConst.register
                        newHVar.offset = 3
                        firstConst.value = firstConst.value[:firstConst.value.rfind("%x")] + vals[0] + firstConst.value[firstConst.value.rfind("%x") + 2:]
                        hvars.append(newHVar)
                        return newHVar.register + ".a"
                else:
                    newHVar.register = firstConst.register
                    newHVar.offset = 4 - availableDimensions
                    for i in range(dimensions):
                        firstConst.value = firstConst.value.replace("%x", vals[i], 1)

                    hvars.append(newHVar)
                    return OffsetProperty(Swizzle(newHVar.register, dimensions), newHVar.offset)

    while len(vals) < 4:
        vals.append("%x")

    suffix = ""
    if swizzle and dimensions < 4:
        suffix = OffsetProperty("." + "xyzw"[:dimensions], newHVar.offset)

    newHVar.register = registerLetter + str(constants[countIndex])
    constants[countIndex] += 1
    if isPixelShader and float(shaderModel) < 2.0 and dimensions == 1:
        vals = vals[1:] + [vals[0]]
        newHVar.register += ".a"
        suffix = ""

    newHVar.value = valtype
    newHVar.value += f"4({", ".join(vals)})"
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
    if string and string[0] in "0123456789.-":
        if string[-1] == "f":
            string = string[:-1]
        try:
            float(string)
            return True
        except:
            pass

    return False

def IsConst(line):
    if line:
        if IsFloat(line) or line in ["true", "false"]:
            return True

        for i in range(2, 5):
            for t in ["float", "int", "bool"]:
                if line.startswith(t + str(i) + "("):
                    if all([IsConst(item.strip()) for item in SliceWithStrings(line, "(", ")").split(",")]):
                        return True

    return False

def BreakdownMath(line):
    tokens = [""]
    symbols = "+-*" if isPixelShader and float(shaderModel) < 2.0 else "+-*/"
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
                tokens[-1] = tokens[-1].strip()
                if tokens[-1]:
                    if tokens[-1] not in "+-*":
                        if tokens[-1][-1] not in "(,":
                            tokens.append(char)
                            tokens.append("")
                            continue
        tokens[-1] += char

    tokens = [item.strip() for item in tokens]

    if isPixelShader:
        i = 0

        while True:
            try:
                i = tokens.index("-", i)
            except ValueError:
                break

            if 0 < i < len(tokens):
                if IsConst(tokens[i + 1]) and StrToFloat(tokens[i + 1]) == "0.5f":
                    if (i < len(tokens) - 2) and tokens[i + 2] == "*" and IsConst(tokens[i + 3]) and StrToFloat(tokens[i + 3]) == "2.0f":
                        tokens = tokens[:i - 1] + ["\"" + HVarNameToRegister(tokens[i - 1]) + "_bx2\""] + tokens[i + 4:]
                    else:
                        tokens = tokens[:i - 1] + ["\"" + HVarNameToRegister(tokens[i - 1]) + "_bias\""] + tokens[i + 2:]
            i += 1


        if float(shaderModel) < 2.0:
            i = 0
            while True:
                try:
                    i = tokens.index("*", i)
                except ValueError:
                    break

                if tokens[i + 1] in ["2", "4"]:
                    tokens[i - 1] = "".join(tokens[i - 1:i + 2])
                    tokens = tokens[:i] + tokens[i + 2:]

                i += 1


    i = 0
    allConst = True
    while i < len(tokens):
        token = tokens[i]

        if isPixelShader and float(shaderModel) < 2.0:
            if token == "1":
                if i < (len(tokens) - 1):
                    if tokens[i + 1] == "-":
                        tokens[i] = "\"1-" + HVarNameToRegister(tokens[i + 2]) + "\""
                        tokens = tokens[:i + 1] + tokens[i + 3:]
                        continue

        if token[0] == "(" and token[-1] == ")" and not HasMath(token):
            tokens[i] = token[1:-1]
            token = tokens[i]

        if IsConst(token):
            if i < (len(tokens) - 2):
                try:
                    if StrToFloat(token) + tokens[i + 1] == "1.0f/":
                        i += 1
                        continue
                except:
                    pass

                if allConst and IsConst(tokens[i + 2]):
                    tokens = tokens[:i] + [str(eval(' '.join([StrToFloat(tokens[i])[:-1], tokens[i+1], StrToFloat(tokens[i+2])[:-1]]))) + "f"] + tokens[i + 3:]
                    continue

            tokens[i] = "\"" + AddConstant("", token, swizzle=True) + "\""
        else:
            allConst = False
        i += 1

    return tokens


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

def Swizzlable(type):
    return not type.properties

def CarefulSweep(string, index, stopAtChars):
    depth = 0
    while index < len(string) and (not any([string[index] == i for i in stopAtChars]) or depth):
        if string[index] in "({[": depth += 1
        elif string[index] in ")}]": depth -= 1
        index += 1
    return index

def HVarNameToRegister(name, swizzle=True):
    if IsConst(name):
        return AddConstant("", name, swizzle=swizzle)

    prefix = ""
    register = ""
    currentType = ""
    index = 0
    swizzle = ""
    while index < len(name):
        if name[index] == "-":
            prefix = "-"
            index += 1

        if name[index:index + 2] == "1-":
            prefix = "1-"
            index += 2

        if name[index] == "\"":
            endIndex = name.index("\"", index + 1)
            register = name[index + 1:endIndex]
            index = endIndex + 1
            continue

        dot = name[index] == "."

        index += int(dot)
        endIndex = CarefulSweep(name, index, ".")

        if dot:
            prop = name[index:endIndex]
            if currentType.properties:
                index = endIndex

                register = GetFromHStruct(currentType, register, prop)
                swizzle = ""
                if "." in register:
                    (register, swizzle) = register.split(".")
                currentType = GetHStructProperty(currentType, prop).type
                break
            else:
                if swizzle:
                    swizzle = ConvertSwizzles(f"{register}.{HandleProperty(prop)}", f"{register}.{swizzle}")
                    swizzle = swizzle[swizzle.index(".") + 1:]
                else:
                    swizzle = HandleProperty(name[index:endIndex])
                break
        else:
            keyword = name[index:endIndex]

            hv = HVarNameToVar(keyword)
            if hv:
                register = hv.register
                currentType = hv.type
                swizzle = ""
                if "." in register:
                    (register, swizzle) = register.split(".")
                elif Swizzlable(hv.type) and (hv.type.size < 4 or hv.offset) and register[0] != "v":
                    swizzle = OffsetProperty(Swizzle("", hv.type.size)[1:], hv.offset)
            else:
                Error(f"HVarNameToRegister: Unknown variable name [{keyword}]")

        index = endIndex

    return f"{prefix}{register}{"." if swizzle else ""}{swizzle}"

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
    while line.split(" ")[0] in ["const", "static", "inline"]:
        line = line[line.index(" ") + 1:].strip()

    for t in htypes:
        if line.split(" ")[0] == t.name:
            return t

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

def InGlobal():
    return scope in ['Pixel Shader', 'Vertex Shader']

functionRegisters = -1
bStatic = False
bInline = False
params = []
# There's only 1 bool4 register for variables, so 4 for each component
pStatus = [False for i in range(4)]

# Returns the first unused register
# The offset allows for multiple unused registers to be allocated
def AllocateRegister(offset=0, commit=False, inFunction=-1, defType="float4"):
    global functionRegisters

    if inFunction == -1:
        inFunction = InFunction()

    if inFunction:
        if IsInline(bStatic, bInline):
            return StaticRegister(offset + 1 + len(params))
        functionRegisters += 1
        return "%z" + str(functionRegisters)
    else:
        if defType == "bool":
            if False in pStatus:
                index = pStatus.index(False)
                if commit:
                    pStatus[index] = True
                index += offset
                return "p0." + "xyzw"[index:index + 1]
            else:
                Error("Ran out of bool registers to hold results, too much is being done in a single line")
                return "p0.w"
        else:
            if False in rStatus:
                numRegisters = ceil(SizeOf(defType) / 4)

                index = rStatus.index(False) + offset
                while any(rStatus[index:index + numRegisters]):
                    index += 1

                if (len(rStatus) - numRegisters) >= index:
                    if commit:
                        for i in range(numRegisters):
                            rStatus[index + i] = True

                    return "r" + str(index)
                else:
                    Error(f"There aren\'t enough registers to store the [{defType}] struct")
            else:
                Error("Ran out of temporary registers to hold results, too much is being done in a single line")
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

def HandleSquareBrackets(tokens, i, ext):
    fullsembly = ""

    if "[" in tokens[i]:
        index = tokens[i][tokens[i].index("[") + 1:tokens[i].index("]")].strip()
        swizzle = tokens[i][tokens[i].index("]") + 1:]
        if IsFloat(index):
            tokens[i] = f"\"c{int(RemoveSwizzle(HVarNameToRegister(tokens[i][:tokens[i].index('[')].strip())[1:])) + int(index)}{swizzle}\""
        else:
            if any([(char in index) for char in "*+-/("]):
                that = CompileOperand_Partial(index, "", AllocateRegister(unusedRegisters) + ".x", 1)
                unusedRegisters += 1
                fullsembly += that[1]
                fullsembly += "mov" + ext + "\ta0.x, " + that[0] + "\n" 
            else:
                fullsembly += CompileOperand_Partial(index, "", "a0.x", 1)[1]

            tokens[i] = "\"c[a0.x + " + RemoveSwizzle(HVarNameToRegister(tokens[i][:tokens[i].index("[")].strip())[1:]) + "]" + swizzle + "\""

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

    def InsertAt(string, substring, toFind):
        return string[:string.index(toFind) + 1] + substring + string[string.index(toFind) + 1:]

    if dst:
        if dst[0] == "p":
            (preamble, condition) = CompileCondition(string)
            return [dst, f"{preamble}setp{InsertAt(ParseCondition(condition), dst + ", ", "\t")}\n"]
    else:
        dst = Swizzle(AllocateRegister(unusedRegisters), components)
        unusedRegisters += 1

    fullsembly = ""
    tokens = BreakdownMath(string)

    while len(tokens) > 1:
        for i in [0, 2]:
            if "(" in tokens[i]:
                this = CompileOperand_Partial(tokens[i], "", Swizzle(AllocateRegister(unusedRegisters), 4 if isPixelShader and float(shaderModel) < 2.0 else SizeOf(''.join(tokens[:3]))), 4)
                unusedRegisters += 1
                fullsembly += this[1]
                tokens[i] = "\"" + this[0] + "\""
            fullsembly += HandleSquareBrackets(tokens, i, ext)

        destination = dst
        if (dst[0] == "o" and len(tokens) > 3):
            destination = Swizzle(AllocateRegister(unusedRegisters), components)
            unusedRegisters += 1

        that = CompileOperand_Partial(" ".join(tokens[:3]), ext, destination, components)
        tokens = ["\"" + that[0] + "\""] + tokens[3:]
        fullsembly += that[1]

    if tokens:
        fullsembly += HandleSquareBrackets(tokens, 0, ext)

        if not any([i in tokens[0] for i in "+-*/?"]) and tokens[0][0] == "(":
            newtype = SliceWithStrings(tokens[0], "(", ")")
            components = SizeOf(newtype)
            tokens[0] = tokens[0][tokens[0].index(")") + 1:]
        that = CompileOperand_Partial(tokens[0], ext, dst, components)
        fullsembly += that[1]
        dst = that[0]

    if float(shaderModel) < 2.0:
        if not isPixelShader:
            CheckForTooManyRegisters(fullsembly, "v", "vertex parameter")
    else:
        CheckForTooManyRegisters(fullsembly, "b", "boolean constant")
        CheckForTooManyRegisters(fullsembly, "i", "integer constant")
        CheckForTooManyRegisters(fullsembly, "s", "sampler")

    if float(shaderModel) < 3.0:
        CheckForTooManyRegisters(fullsembly, "c", "constant", 2 if isPixelShader or float(shaderModel) >= 2.0 else 1)

    return [dst, fullsembly]

def GetRegisterType(register):
    register = register.strip()
    components = 4
    if "." in register:
        components = len(register[register.index(".") + 1:])

    typename = "float"

    match register[0]:
        case "b" | "p":
            typename = "bool"
        case "i":
            typename = "int"

    return typename + (str(components) if components > 1 else "")

def GetConstantType(value):
    if value in ["true", "false"]:
        return "bool"

    if value[-1] == "f" or "." in value:
        return "float"

    return "int"

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
                if float(shaderModel) >= 2.0 or not (char == "-" and string[:index] in ['', '1']):
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
        return len(name[name.index(".") + 1:].replace("\"", ""))

    allhvars = hvars + dhvars
    if name in allhvars:
        hv = allhvars[allhvars.index(name)]
        return hv.type.size

    return 4

findOverloadParams = []
def FindOverload(x):
    return x.params[:len(findOverloadParams)] == findOverloadParams

def ReplaceSwizzled(register, dest, string):
    if "." in dest:
        matches = findall(f"{register}\\.[xyzwrgba]+", string)
        for m in matches:
            string = string.replace(m, ConvertSwizzles(m, dest))
    return string

def StaticRegister(index):
    return f"r{len(rStatus) - 1 - index}"

# Returns a list where the first item is the destination that contains the result of the code, and the second item is the code.
def CompileOperand_Partial(string, ext="", dst="", components=4):
    global findOverloadParams
    string = string.strip()
    sembly = ""
    ops = ["*mul", "+add", "-sub"]
    mathed = False
    reg = unusedRegisters

    if dst == "":
        dst = Swizzle(AllocateRegister(reg), components)
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
            endIndex = GetParEnd(string, string.index("(") + 1)
            parameters = string[string.index("(") + 1:endIndex]
            parameters = [HVarNameToSize(item.strip()) for item in ArraySplit(parameters)]
            functionName = string[:string.index("(")].strip()
            for hf in hfuncs:
                if functionName == hf.name and len(hf.params) == len(parameters):
                    matchingFuncs.append(hf)

            if matchingFuncs:

                swiz = ""

                if endIndex < (len(string) - 1):
                    if string[endIndex + 1] == ".":
                        swiz = string[endIndex + 1:].strip()

                # Making sure it's a copy
                temp = [func for func in matchingFuncs]

                num = 0

                if len(temp) > 1:
                    while True:
                        if not temp or num >= len(parameters): break

                        if len(temp) == 1 and not noDefaultOverload: break

                        num += 1
                        findOverloadParams = parameters[:num]
                        filtered = list(filter(FindOverload, temp))
                        if not filtered:
                            temp = [] if noDefaultOverload else [temp[0]]
                            break

                        temp = filtered


                if not temp:
                    def ConvertToType(num):
                        return f"float{num}" if num > 1 else "float"
                    def ConvertToTypeFull(params):
                        return str([ConvertToType(item) for item in params])[1:-1].replace('\'', '')
                    Error(f"None of the overloads for {functionName} matches the situation: ({ConvertToTypeFull(parameters)})")
                    print("Overload options:")
                    for m in matchingFuncs:
                        print(f"({ConvertToTypeFull(m.params)})")
                else:
                    av = temp[0]
                    dex = string.index(av.name + "(") + len(av.name) + 1
                    end = GetParEnd(string, dex)
                    inner = [item.strip() for item in ArraySplit(string[dex:end])]
                    end = av.code

                    prevDst = ""
                    if swiz:
                        prevDst = dst
                        dst = AllocateRegister(reg, False)
                        reg += 1

                    # Static Function
                    if av.code[0] + av.code[-1] == "[]":
                        instructions = ""

                        for dex, param in enumerate(inner):
                            register = Swizzle(StaticRegister(dex + 1), av.params[dex])
                            if any([char in param for char in "+-*/("]):
                                instructions += CompileOperand_Partial(param, "", register)[1]
                                reg += 1
                                continue
                            instructions += f"mov\t{register}, {HVarNameToRegister(param)}\n"

                        instructions += f"call\tl{SliceWithStrings(av.code, '[', ']')}\nmov\t{dst}, {Swizzle(StaticRegister(0), av.rtn)}\n"
                        return [dst, instructions]

                    i = 0
                    while f"%z{i}" in end:
                        end = end.replace(f"%z{i}", AllocateRegister(reg, inFunction=False))
                        reg += 1
                        i += 1

                    # When calling a function that reads from the destination, it checks if you gave it a write-only register and will use an unused variable register if that's the case.
                    if "%z" in end and dst[0] == 'o':
                        newDst = Swizzle(f"r{rStatus.index(False) + reg}", av.rtn)
                        reg += 1
                        end = ReplaceSwizzled("%z", newDst, end)
                        end = end.replace("%z", newDst)
                    else:
                        end = ReplaceSwizzled("%z", dst, end)
                        end = end.replace("%z", dst)

                    end = ReplaceSwizzled("%0", dst, end)
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
                            if not (item == "-" and inner[dex - 1] == "1") or float(shaderModel >= 2.0):
                                that = CompileOperand(item, "", Swizzle(AllocateRegister(reg), parameters[dex]), parameters[dex])
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
                                item = "\"" + AddConstant("", item, GetConstantType(item)) + "\""

                        if "." in item:
                            item = item.split(".")
                            item.append(str(len(item[1])))
                        else:
                            hvar = HVarNameToVar(item)
                            if hvar and (not isPixelShader or float(shaderModel) >= 2.0) and Swizzlable(hvar.type) and (hvar.offset or hvar.type.size != 4) and "." not in hvar.register and hvar.register[0] != "v":
                                item = [item, "xyzw"[hvar.offset:hvar.offset + hvar.type.size], hvar.type.size]
                            else:
                                item = [item, ""]

                            if item[0] in hvars:
                                item[-1] = str(hvars[hvars.index(item[0])].type.size)
                            elif item[0] in dhvars:
                                item[-1] = str(dhvars[dhvars.index(item[0])].type.size)
                            else:
                                if not isPixelShader:
                                    item[-1] = "4" if (item[0] == "c0") else "3" if (item[0] == "c4") else "4"
                                else:
                                    item[-1] = "4"

                        end = end.replace(f"%tn{dex + 1}", item[-1])
                        name = '.'.join(item[:-1]).strip()

                        register = HVarNameToRegister(name)
                        end = ReplaceSwizzled(f"%{dex + 1}", register, end)

                        for match in findall(f"%{dex + 1}\\+[0-9]+", end):
                            end = end.replace(match, f"{register[0]}{int(RemoveSwizzle(register[1:])) + int(match[match.index("+") + 1:])}")

                        end = end.replace(f"%{dex + 1}", register)
                    return [dst + swiz, prepend + end + "\n"]

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

                sembly += op[1:] + ext + "\t" + destination + ", " + HVarNameToRegister(these[0].strip()) + ", " + HVarNameToRegister(these[1].strip()) + suffix + "\n"
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

def HandleDivision(string, dst):
    if string.split("/")[0].strip() == "1":
        return [dst, "rcp\t" + dst + ", " + HVarNameToRegister(string.split("/")[1].strip()) + "\n"]
    return [dst, "rcp\t" + dst + ", " + HVarNameToRegister(string.split("/")[1].strip()) + "\nmul\t" + dst + ", " + dst + ", " + HVarNameToRegister(string.split("/")[0].strip()) + "\n"]

def CompileOperand_PartialPS(string, ext="", dst="", components=4):
    mathed = False
    if float(shaderModel) < 2.0:
        m = GetFirstModif(string)
        if m:
            dex = string.index(m[0] + "(") + len(m[0]) + 1
            end = GetParEnd(string, dex)
            inner = string[dex:end]
            return CompileOperand(inner, "_" + m[1] + ext, dst)

    if "?" in string:
        symbols = [">=", "<"]
        symbolMeanings = [", %0, %1", ", %1, %0"]
        if float(shaderModel) > 1.1:
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

        if float(shaderModel) >= 2.0:
            Error("Shader model 3 can only do the comparison to 0, (x [operator] 0 ? y : z)")

        dex = string.index("?") + 1
        inner = [item.strip() for item in string[dex:].split(":")]
        inner = ConstantsToRegisters(inner)
        return [dst, "cnd" + ext + "\t" + ", ".join([dst, "r0.a", HVarNameToRegister(inner[0].strip()), HVarNameToRegister(inner[1].strip())]) + "\n"]

    if "/" in string:
        if float(shaderModel) < 2.0:
            if string[string.index("/") + 1:].strip() != "2":
                Error("In the pixel shader, dividing can only be done by 2. It's used like saturate(), an addon to a math expression or another function, such as (a + b / 2)")
            return CompileOperand(string.split("/")[0].strip(), "_d2" + ext, dst)
        else:
            return HandleDivision(string, dst)

    if float(shaderModel) < 2.0:
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
        return HandleDivision(string, dst)

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

def StartsWith(haystack, needle):
    return any(haystack.startswith(needle + char) for char in " \t\n{")

# Removes vector splitting to get just the variable
def RemoveSwizzle(string): return string.split(".")[0].strip()

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
            if float(shaderModel) < 3.0:
                if TooManyRegisters(sources, "c", 2 if isPixelShader or float(shaderModel) >= 2.0 else 1) or TooManyRegisters(sources, "v"):
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
    line = line.replace("++", "+= 1").replace("--", "-= 1")
    for symb in ["*=", "+=", "-="]:
        if symb in line:
            splt = [item.strip() for item in line.split(symb)]
            source = splt[0]
            if isPixelShader and "." in source and source[source.index(".") + 1:] in ["xyz", "rgb"]:
                source = RemoveSwizzle(source)
            return splt[0] + " = " + source + " " + symb[0] + " (" + splt[1] + ")"

    return line

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

def GetSpecifiers(line):
    bStatic = False
    bInline = False

    while True:
        match line.split(" ")[0]:
            case "static":
                bStatic = True
                line = line[line.index(" ") + 1:]
            case "inline":
                bInline = True
                line = line[line.index(" ") + 1:]
            case _:
                break

    return (line, bStatic, bInline)

# It would be nice if this happened when you use strings as slice indices
def SliceWithStrings(string, start, end):
    startIndex = string.index(start) + len(start)
    endIndex = string.index(end, startIndex)
    return string[startIndex:endIndex]

def ArraySplit(string, delimiter=","):
    rray = [""]
    depth = 0
    for char in string:
        if char == "(":
            depth += 1
        if char == ")":
            depth -= 1
        if char == delimiter and not depth:
            rray.append("")
            continue

        rray[-1] += char

    return [] if not rray[0] else rray

prevMode = 0

maxInstructions = 8

def RemoveHVar(name):
    for i, hv in hvars:
        if hv.name == name:
            hvars = hvars[:i] + hvars[i + 1:]
            break

def ParseCondition(string):
    options = [">=", "<=", ">", "<", "==", "!="]
    keys = ["ge", "le", "gt", "lt", "eq", "ne"]

    for i, option in enumerate(options):
        if option in string:
            operands = string.split(option)
            return f"_{keys[i]}\t{', '.join([HVarNameToRegister(operand.strip()) for operand in operands])}"

    register = HVarNameToRegister(string)
    if register[0] in "pb":
        return f"\t{register}"

    return f"_ne\t{register}, {AddConstant('constant_temp', '0.0f')}"


def IsInline(bStatic, bInline):
    if inlinePreferred:
        return not bStatic
    return bInline

def FlipConditions(condition):
    # This mess is to prevent mistakenly flipping multiple times
    temp = condition.replace(">=", "%ge%").replace("<=", "%le%").replace(">", "%gt%").replace("<", "%lt%").replace("==", "%eq%").replace("!=", "%ne%")
    return temp.replace("%ge%", "<").replace("%le%", ">").replace("%gt%", "<=").replace("%lt%", ">=").replace("%eq%", "!=").replace("%ne%", "==")

def FlipAndOr(condition):
    temp = condition.replace("&&", "%and%").replace("||", "%or%")
    return temp.replace("%and%", "||").replace("%or%", "&&")

def BreakdownCondition(condition):
    tokens = [""]
    depth = 0
    for char in condition:
        if char in "[({":
            depth += 1
        if char in "])}":
            depth -= 1

        if not depth and tokens[-1]:
            if (char in "<>=&|!") != (tokens[-1][-1] in "<>=&|!"):
                tokens.append("")

        tokens[-1] += char

    tokens = [token.strip() for token in tokens]

    return [item.strip() for item in tokens] if tokens[0] else []

def CompileCondition(condition):
    preamble = ""
    tokens = BreakdownCondition(condition)
    allocatedRegisters = 0
    for i, token in enumerate(tokens):
        token = token.strip()

        if token[0] + token[-1] == "()":
            token = token[1:-1]
            tokens[i] = token

        if HasMath(token):
            dimensions = GetSizeFromParam(token)
            that = CompileOperand(token, "", Swizzle(AllocateRegister(allocatedRegisters), dimensions), dimensions)
            allocatedRegisters += 1
            preamble += that[1]
            tokens[i] = f"\"{that[0]}\""

    def GetSwizzle(string):
        if string[0] == "\"":
            string = string[1:-1]
        return "" if "." not in string else string[string.index(".") + 1:]

    i = 0
    while i < (len(tokens) - 2):
        swizzle1 = GetSwizzle(HVarNameToRegister(tokens[i]))
        swizzle2 = GetSwizzle(HVarNameToRegister(tokens[i + 2]))
        if swizzle1 != swizzle2:
            newRegister = f"{AllocateRegister(allocatedRegisters)}.{swizzle1}"
            allocatedRegisters += 1
            preamble += f"mov\t{newRegister}, {HVarNameToRegister(tokens[i + 2])}\n"
            tokens[i + 2] = f"\"{newRegister}\""
        i += 2

    return (preamble, "".join(tokens))


def HandleIf(condition, onTrue, onFalse, dst):
    out = ""
    otherifs = ""
    if "||" in condition:
        ors = condition.split("||")
        buffer = ""
        for i in reversed(ors):
            buffer = HandleIf(i, onTrue, buffer if buffer else onFalse, dst).strip()

        return buffer

    conditions = condition.split("&&")
    endifs = []
    tabs = ""
    for i, c in enumerate(conditions):
        (preamble, c) = CompileCondition(c)

        out += preamble + tabs + f"if{ParseCondition(c.strip())}\n"
        endifs.append(tabs)
        tabs += "\t"
    out += AddTabs(onTrue, tabs)

    otherifs = ""

    if onFalse:
        for c in conditions:
            out += tabs[:-1] + "else\n" + AddTabs(onFalse, tabs) + tabs[:-1] + "endif\n"
            tabs = tabs[:-1]
    else:
        out += "\n".join([e + "endif" for e in reversed(endifs)])

    return f"{out.strip()}\n{otherifs}"


def GetBracketsOrNextLine(script, index, previousBuffer, addLines=True):
    global linenum

    if script[index] == ";":
        return (previousBuffer + ";", index + 1)

    endIndex = CarefulSweep(script, index, ";{")
    buffer = script[index:endIndex]
    if addLines: linenum += buffer.count("\n")
    index = endIndex

    if script[index] == ";":
        return (buffer + ";", index + 1)

    index += 1
    endIndex = GetParEnd(script, index, "{}")
    if addLines: linenum += script[index:endIndex].count("\n")
    return (script[index:endIndex], endIndex + 1)

def NextToken(script, index, addLines):
    global linenum
    while index < len(script) and script[index] in " \t\n":
        if script[index] == "\n" and addLines:
            linenum += 1
        index += 1

    return index

def ReadIfPartial(script, index, addLines):
    global linenum
    onFalse = ""
    startIndex = script.index("(", index) + 1
    endIndex = GetParEnd(script, startIndex)
    condition = script[startIndex:endIndex]
    index = endIndex

    (onTrue, index) = GetBracketsOrNextLine(script, index + 1, "", addLines)

    index = NextToken(script, index, addLines)

    if index < len(script) and script[index] == "e":
        if StartsWith(script[index:], "else"):
            index = NextToken(script, index + len("else"), addLines)
            if StartsWith(script[index:], "if"):
                (nextTrue, nextCondition, nextFalse, index) = ReadIfPartial(script, index, addLines)
                # It's redundant but I didn't want to have yet another function
                onFalse = f"if ({nextCondition}) " + "{" + nextTrue + "} else {" + nextFalse + "}"
            else:
                (onFalse, index) = GetBracketsOrNextLine(script, index, "", addLines)

    return (onTrue, condition, onFalse, index)

def ShowSpaces(string):
    specialChars = (("\n", "n"), ("\r", "r"), ("\t", "t"), (" ", ""))
    for char, letter in specialChars:
        string = string.replace(char, "\\" + letter)

    return string

def PrintStringLocation(string, index, width):
    print(ShowSpaces(string[index - width:index]), ShowSpaces(string[index]), ShowSpaces(string[index + 1:index + width + 1]))

def ReadIf(script, index, dst, addLines):
    onTrue = ""
    onFalse = ""

    (onTrue, condition, onFalse, index) = ReadIfPartial(script, index, addLines)

    # There's a specific instruction for breaking on a condition, so it'll use that if it can
    if not onFalse and not any(char in condition for char in "&|"):
        if onTrue.strip() == "break;":
            return (f"break{ParseCondition(condition)}\n", index)

    return (HandleIf(condition, CompileHLSL(onTrue, dst=dst, addLines=False, canDiscard=False).strip(), CompileHLSL(onFalse, dst=dst, addLines=False, canDiscard=False).strip(), dst), index)

def RemoveTypeComponents(name):
    return name[:-1] if name[-1] in "234" else name

def CompileHLSL(script, localVars=-1, dst="r0", addLines=True, canDiscard=True):
    global linenum, col, scope, typeOfExpr, hvars, constants, unusedRegisters, functionRegisters, rStatus, params

    if localVars == -1:
        localVars = []

    mode = 1
    bMeanwhile = False
    temp = 0
    output = ""
    buffer = ""
    index = 0
    scopeCheck = 0
    numStaticFunctions = 0
    bStatic = False
    attribute = ""
    bInline = False
    staticFunctionBuffer = ""

    while index < len(script):
        char = script[index]
        index += 1

        if addLines and char == '\n':
            linenum += 1

        # Comments
        if mode not in [0, 2]:
            if buffer and buffer[-1] == '/':
                comment = ""
                match char:
                    case "/":
                        comment = script[index:script.index("\n", index)]
                        index += len(comment) + 1
                        if addLines: linenum += 1
                    case "*":
                        comment = script[index:script.index("*/", index)]
                        index += len(comment) + 2
                        comment = "\n;".join(comment.split("\n"))

                if comment:
                    buffer = buffer[:-1]
                    if addLines: linenum += comment.count("\n")

                    if includeComments:
                        if output and output[output.rfind("\n", 0, len(output) - 1) + 1] != ";":
                            output += "\n\n"
                        output += ";" + comment + "\n"
                    continue

        # Checking for assembly
        if mode != 2 and buffer.strip() == "asm" and char in "\t {":
            buffer = ""
            index = CarefulSweep(script, index, ";{")

            index += 1

            endDex = script.index("}", index)
            output += "\n".join([line.strip() for line in script[index:endDex].split("\n")]) + "\n"
            index = endDex + 1
            continue

        attribute = ""

        if char == "[" and not buffer.strip():
            attribute = script[index:(index := script.index("]", index))]
            index += 1
            index = NextToken(script, index, addLines)
            char = script[index]
            index += 1

        # Reading Function
        if mode == 2:
            if char == '}':
                if not temp:
                    functionRegisters = -1

                    isInline = IsInline(bStatic, bInline)

                    if isInline:
                        hfuncs[-1].code = CompileHLSL(buffer.strip(), -1, "%0", False, False).strip()
                    else:
                        rStatus[-1] = True
                        hfuncs[-1].code = f"[{numStaticFunctions}]"
                        staticFunctionBuffer += f"; {hfuncs[-1].name}\nlabel l{numStaticFunctions}\n" + CompileHLSL(buffer.strip(), -1, StaticRegister(0), False, False).strip() + "\nret\n\n"
                        numStaticFunctions += 1
                        params = []

                    buffer = ""

                    mode = 1
                    newList = []
                    for dex, item in enumerate(hvars):
                        if item.register[0] != "%":
                            newList.append(item)

                    hvars = newList

                    scope = "Pixel Shader" if isPixelShader else "Vertex Shader"
                    continue
                else:
                    temp -= 1

            if char == '{' and buffer.strip():
                temp += 1

            buffer += char

        # Reading HLSL
        else:

            if char == "(": scopeCheck += 1
            if char == ")": scopeCheck -= 1

            if (char == ';' and not scopeCheck) or (char == "{" and "[" not in buffer):
                line = buffer
                buffer = ""

                unusedRegisters = 0
                line = line.strip()
                if not line: continue

                if "(" in line[1:]:
                    hf = GetMatchingFunctionFromLine(line)
                    if hf:
                        if line[line.index("(") - 1] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            typeOfExpr = "Calling Void Function"
                            if hf.code[0] + hf.code[-1] == "[]":
                                output += f"call\tl{hf.code[1:-1]}\n"
                            else:
                                output += CompileOperand(line, "", "")[1]
                            continue

                if float(shaderModel) >= 2.0:
                    if line == "break":
                        output += "break\n"
                        continue

                    if StartsWith(line, "if"):
                        typeOfExpr = "If"
                        (code, index) = ReadIf(script, index - len(line), dst, addLines)
                        output += code
                        continue

                def MakeWhile(loopCode):
                    sembly = f"rep {AddConstant("", "255", "int", False, False)}\n"
                    sembly += AddTabs(CompileHLSL(loopCode, addLines=False, canDiscard=False).strip(), "\t")
                    return sembly + "endrep\n"

                if StartsWith(line, "struct"):
                    structName = line[len("struct"):].strip()
                    endIndex = GetParEnd(script, index, "{}")

                    if GetType(structName):
                        Error(f"re-definition of struct: [{structName}]")
                    else:
                        properties = script[index:endIndex]
                        if addLines: linenum += properties.count("\n")
                        properties = properties.strip()[:-1]
                        htypes.append(HType(structName, 0, [item.strip() for item in properties.split(";")]))

                    index = endIndex + 1
                    continue

                if float(shaderModel) >= 2.0:
                    if StartsWith(line, "do") or line == "do":
                        typeOfExpr = "Do While"
                        (loopCode, endIndex) = GetBracketsOrNextLine(script, index - 1, line[2:], addLines)
                        condition = SliceWithStrings(script[endIndex:], "(", ")")
                        match condition:
                            case "true":
                                condition = ""
                            case "false":
                                condition = "break;\n"
                            case _:
                                condition = f"if ({FlipConditions(condition)}) break;\n"

                        output += MakeWhile(loopCode + condition)
                        index = script.index(";", endIndex + 1) + 1
                        continue
 
                    if StartsWith(line, "while"):
                        typeOfExpr = "While"
                        condition = SliceWithStrings(line, "(", ")").strip()
                        (loopCode, index) = GetBracketsOrNextLine(script, index - 1, line[line.index(")") + 1:], addLines)

                        if condition != "false":
                            breakCode = ""
                            if condition != "true":
                                breakCode = f"if ({FlipConditions(condition)}) break;\n"

                            output += MakeWhile(breakCode + loopCode)
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
                                        if hv.value:
                                            if hv.register[0] != "c" or "(" not in hv.value:
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
                            ranges = ["0", HVarNameToVar(arrayName).type.size, "1"]

                        statements = [f"float {varName} = {float(ranges[0])}", f"{varName} < {float(ranges[1])}", f"{varName} += {float(ranges[2])}", f"{varName} = {ranges[0]}"]
                    else:
                        statements = [item.strip() for item in SliceWithStrings(line, "(", ")").split(";")]
                        for i, s in enumerate(statements):
                            if s[-1] == 'f':
                                statements[i] = s[:-1]

                        statements.append(statements[0][statements[0].index(" ") + 1:].strip())
                        varName = statements[-1].split("=")[0].strip()
                        keyword = "%keyword%"
                        statements[0] = "float " + statements[-1]

                    (loopCode, closingIndex) = GetBracketsOrNextLine(script, index - 1, line[line.index(")") + 1:], addLines)

                    def GetConstantFromName(name):
                        hv = HVarNameToVar(name)
                        if hv and hv.value and hv.value[0] == "c":
                            component = 0 if "." not in hv.register else "xyzw".index(hv.register[hv.register.index(".") + 1])
                            return Int(SliceWithStrings(hv.value, "(", ")").split(", ")[component], 0)
                        return 0

                    def GetConstantsFromFor(statements):
                        consts = [str(len(HandleForLoop("z", statements[3], statements[1], statements[2], "-", "", "")))]
                        for string in statements[0:len(statements):2]:
                            if any([string.endswith(item) for item in ["++", "--"]]):
                                consts.append("-1" if string[-1] == "-" else "1")
                                continue

                            val = string.split("=")[1].strip()
                            if IsFloat(val):
                                consts.append(str(int(float(StrToFloat(val)[:-1]))))
                            else:
                                consts.append(GetConstantFromName(val))

                        return f"int4({", ".join(consts)}, 0)"

                    previousScope = scope
                    scope = "For Loop"
                    if attribute == "loop" and float(shaderModel) >= 2.0:
                        output += f"loop\taL, {AddConstant("", GetConstantsFromFor(statements), "int", False, False)}\n"
                        hvars.append(HVar(varName, "aL", "", "int4", 0))
                        output += AddTabs(CompileHLSL(loopCode, addLines=False, canDiscard=False).strip(), "\t")
                        output += "endloop\n"
                    else:
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
                        Warn(f"re-definition of [{line.split(" ")[1]}]")
                        defType = False
                        line = line[line.index(" ") + 1:]

                if autoCreateVariables and "=" in line and not defType and RemoveSwizzle(line[:line.index("=")].strip()) not in (hvars + dhvars):
                    name = line[:line.index("=")].strip()
                    if name[0] not in "\"\'":
                        defType = "float4"
                        line = "float4 " + line

                if defType:
                    tokens = line.split(" ")

                    if tokens[0] == "const":
                        tokens = tokens[1:]
                        bForceConst = True

                    if "[" in tokens[1]:
                        items = ArraySplit(line.split("=")[1].strip()[1:-1])
                        AddConstant(tokens[1][:tokens[1].index("[")], items[0], defType.name, False)
                        hvars[-1].type = HType("array", len(items), [])
                        for c in items[1:]:
                            AddConstant("", c, defType.name, False)
                        continue

                    line = " ".join(tokens)
                    if "=" in line and ((guessConst and IsConst(line[line.index("=") + 1:].strip())) or bForceConst):
                        typeOfExpr = "Defining Constant"
                        AddConstant(SliceWithStrings(line, " ", "=").strip(), line.split("=")[1].strip(), defType.name)
                    else:
                        (line, bStatic, bInline) = GetSpecifiers(line)
                        tokens = line.split(" ")
                        if True:#IsType(tokens[0]):
                            if "(" in tokens[1]:
                                typeOfExpr = "Defining Function"
                                tokens[1] = SliceWithStrings(line, " ", "(")

                                if (not IsInline(bStatic, bInline)) and float(shaderModel) < 2.0:
                                    Warn(f"Shader Model 1 does not support static functions, defaulting to inline for {tokens[1]}...")
                                    bStatic = False
                                    inlinePreferred = True

                                params = [GetSizeFromParam(item.strip()) for item in SliceWithStrings(line, "(", ")").split(",")]
                                rtnType = SizeOf(line[:line.index(" ")])

                                hfuncs.append(HFunc(tokens[1], "", rtnType, params))
                                args = [item.strip().split(" ") for item in SliceWithStrings(line, "(", ")").split(",")]
                                scope = tokens[1]
                                if args:
                                    for i, item in enumerate(args):
                                        hvars.append(HVar(item[-1], f"%{i + 1}" if IsInline(bStatic, bInline) else StaticRegister(i + 1), "", "float4" if len(item) == 1 else item[-2]))
                                        if not IsInline(bStatic, bInline):
                                            rStatus[-(i + 1)] = True
                                temp = 0
                                mode = 2
                                buffer = ""

                            else:
                                typeOfExpr = "Defining Variable"
                                if "=" in line:
                                    def DefineStruct(struct, register, script, index):
                                        global linenum
                                        output = ""
                                        while script[index] != "{":
                                            if script[index] == "\n" and addLines: linenum += 1
                                            index += 1
                                        index += 1
                                        for prop in struct.properties:
                                            offsetRegister = GetFromHStruct(struct, register, prop.name)

                                            endIndex = CarefulSweep(script, index, ",}")
                                            operand = script[index:endIndex]
                                            if addLines: linenum += operand.count("\n")
                                            operand = operand.strip()
                                            if prop.type.properties:
                                                (code, discard) = DefineStruct(prop.type, offsetRegister, operand, 0)
                                                output += code
                                            else:
                                                output += CompileOperand(operand, "", offsetRegister, prop.type.size)[1]

                                            index = endIndex + 1

                                        return (output, index)

                                    t = GetType(tokens[0].strip())

                                    if char == "{" and t.properties:
                                        register = AllocateRegister(0, True, defType=defType)
                                        hvars.append(HVar(tokens[1], register, "", t.name))
                                        (code, index) = DefineStruct(t, register, script, index - 1)
                                        output += code
                                    else:
                                        tokens[2] = line[line.index("=") + 1:].strip()
                                        tokens[0] = tokens[0].strip()
                                        components = SizeOf(tokens[0])
                                        r = CompileOperand(tokens[2], "", Swizzle(AllocateRegister(0, True, defType=defType), components), components)
                                        hvars.append(HVar(tokens[1], r[0], "", t.name))
                                        output += ("+" if bMeanwhile else "") + r[1]
                                elif len(tokens) == 2:
                                    hvars.append(HVar(tokens[1], AllocateRegister(0, True, defType=defType), "", tokens[0]))

                else:
                    tokens = line.split(" ")
                    match tokens[0]:
                        case "return":
                            typeOfExpr = "Return"
                            if line[7:].strip():
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
                            output += CompileOperand(line[line.index("=") + 1:], "", HandleString(tokens[0]), SizeOf(GetRegisterType(tokens[0][1:-1])))[1]
                        else:
                            name = tokens[0]
                            swizzle = ""
                            hvar = HVarNameToVar(RemoveSwizzle(name))
                            if hvar:
                                register = HVarNameToRegister(name)
                                if "." not in register and Swizzlable(hvar.type) and hvar.type.name != "float4":
                                    swizzle = "." + "xyzw"[hvar.offset:hvar.offset + SizeOf(hvar.type)]

                                output += ("+" if bMeanwhile else "") + CompileOperand(line[line.index("=") + 1:], "", register + swizzle, hvar.type.size)[1]
                            else:
                                Error(f"Unknown variable name: [{name}]")
                    else:
                        if line:
                            Error("Unknown Expression: " + line)

                attribute = ""

                # Clearing out variables that aren't referenced anymore
                if autoDiscard and canDiscard:
                    hvindex = 0
                    while hvindex < len(hvars):
                        hv = hvars[hvindex]
                        if (not hv.value) and (hv.register[0] == "r"):
                            if not CarefulIn(script[index:], hv.name):
                                rindex = int(RemoveSwizzle(hv.register[1:]))
                                numRegisters = ceil(hv.type.size / 4)
                                for i in range(numRegisters):
                                    rStatus[rindex + i] = False
                                if debugComments:
                                    output += f"\n; {hv.name} deleted\n\n"
                                hvars = hvars[:hvindex] + hvars[hvindex + 1:]
                                continue
                        hvindex += 1
            else:
                buffer += char

    # The first one isn't working for whatever reason
    output = output.replace("\n\n\n", "\n\n").replace("\n\n\n", "\n\n")
    if staticFunctionBuffer:
        output += "ret\n\n" + staticFunctionBuffer.strip()

    if not noOptimizations:
        output = SecondPass(output)

    if float(shaderModel) < 2.0:
        numInstructions = CountInstructionSlots(output)

        if numInstructions > maxInstructions:
            print(f"Validation Error: Too many instructions in {'the ' if scope in ['Pixel Shader', 'Vertex Shader'] else ''}{scope}, you can only have {maxInstructions} and you've got {numInstructions}")

    return output

# Each item is a list of instructions, the index in that list is the instruction slot count
instructionSlotList = [["vs", "def"], [], ["m3x2"], ["frc", "m3x3", "m4x3"], ["m4x4"], [], [], [], [], [], ["log", "exp"]]

def CountInstructionSlots(x):
    slots = 0
    for i in x.split("\n"):
        if not i.strip() or i.startswith(";") or i.startswith("//"):
            continue

        instruction = i
        if any([char in i for char in " \t"]):
            instruction = i[:i.index(" " if "\t" not in i else "\t")]

        if isPixelShader:
            slots += 0 if instruction in ["nop", "def"] else 1
        else:
            for dex, lst in enumerate(instructionSlotList):
                if instruction in lst:
                    slots += dex
                    break
            else:
                slots += 1

    return slots

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
            parIndex = dex + len(possibility)
            ar = script[parIndex + 1:GetParEnd(script, parIndex + 1)].split(",")
            break
    if dex != -1:
        return (ar, script[script.index("{", dex) + 1:GetParEnd(script, script.index("{", dex) + 1, "{}")], len(script[:script.index("{", dex)].split("\n")))
    return [[], "", 0]


semantics = [["sv_position", "vpos", "position"], ["normal"], ["sv_target", "color"], ["texcoord"]]
semantictypes = ["float3", "float3", "float4", "float2"]

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

    for d in inlineDefs:
        if d[0] == "inputStreamFormat":
            return d[1][1:-1]

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
    return lst[dex] if (-1 < dex < len(lst)) else ""

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
                    with open(scriptPath + filename[:filename.rfind("/") + 1] + name) as includefile:
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
            replacee = tempLine[tempLine.index("=") + 1:-1].strip()
            inlineDefs.append((name, replacee))

def SortDecl(a):
    return int(a[a.find("v") + 1]) if a.strip() else 65535

mtime = 0
stuckInLoop = True
createFullFile = True

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


def DeclareTextures():
    decl = ""
    for i in range(textures - 1, -1, -1):
        if float(shaderModel) < 2.0:
            hv = HVarRegisterToVar("t" + str(i))
            if hv.value:
                if "(" in hv.value:
                    start = hv.value.index("(")
                    decl = f"{hv.value[:start]}\tt{i}, { ', '.join([HVarNameToRegister(item.strip()) for item in SliceWithStrings(hv.value, "(", ")").split(",")]) }\t// {hv.name}\n{decl}"
                    continue
                prefix = hv.value
            else:
                prefix = "tex"
            decl = f"{prefix}\tt{i}\t// {hv.name}\n{decl}"

        else:
            hv = HVarRegisterToVar(f"s{i}")
            if hv:
                decl = f"dcl_{hv.type.name[len("sampler"):].lower()}\ts{i}\t; {hv.name}\n" + decl

    return decl

def GetMaxVariables():
    if float(shaderModel) < 2.0:
        return 2 if isPixelShader else 12

    if float(shaderModel) < 3.0:
        return 12

    return 32

def GetMaxConstants():
    if float(shaderModel) < 2.0:
        return 8 if isPixelShader else 96

    if float(shaderModel) < 3.0:
        return 32 if isPixelShader else 256

    return 224 if isPixelShader else 256

def GetMaxInstructions():
    if float(shaderModel) < 2.0:
        return 8 if isPixelShader else 128

    if shaderModel == "2.0":
        return 64 if isPixelShader else 256

    if float(shaderModel) < 3.0:
        return 96 if isPixelShader else 256

    return 512

def ReadBuiltIn(filename):
    with open(scriptPath + filename) as file:
        thatthing = file.read()

        while (ifdef := thatthing.find("#ifdef ")) != -1:
            thatthing = HandleIfDef(thatthing, ifdef, False)
        while (ifdef := thatthing.find("#ifndef ")) != -1:
            thatthing = HandleIfDef(thatthing, ifdef, True)

        CompileHLSL(thatthing, addLines=False, canDiscard=False)

def GetZero(defType):
    match defType:
        case "b":
            return "false"
        case "i":
            return "0"
    return "0.0f"


def CompileShader(shader, dst):
    global maxR, maxC, maxV, maxInstructions, hfuncs, linenum, startC, rStatus, hvars, dhvars, psSnapshot, pStatus

    hfuncs = []
    ResetDHVars()

    # Making absolutely sure it's a copy and not a reference
    psSnapshot = [item for item in hvars]
    hvars = []

    if not isPixelShader:
        PSTexToVSTex()

    maxR = GetMaxVariables()
    maxC = GetMaxConstants()
    maxV = 2 if isPixelShader else 16
    maxInstructions = GetMaxInstructions()

    rStatus = [False for i in range(maxR)]
    pStatus = [False for i in range(4)]

    startC = pixelConstants if isPixelShader else vertexConstants

    constants[0] = startC
    constants[1] = 0
    constants[2] = 0

    linenum = psLine if isPixelShader else vsLine

    if float(shaderModel) >= 2.0 or not isPixelShader:
        # c95.x = degrees to radians, the rest are just very common
        if not hvars:
            hvars = [HVar(f"constant_{maxC - 1}", f"c{maxC - 1}", "float4(0.0174533f, 1.0f, 0.5f, 0.0f)", "float4")]
        else:
            hvars[0] = HVar(f"constant_{maxC - 1}", f"c{maxC - 1}", "float4(0.0174533f, 1.0f, 0.5f, 0.0f)", "float4")

    ReadBuiltIn(("pixel" if isPixelShader else "vertex") + "_builtin.hlsl")
    return CompileHLSL(shader, -1, dst)

if __name__ == '__main__':

    # Reading the settings file, it's been moved down here to allow more things to be changed
    settings = ""

    try:
        with open(scriptPath + "settings.txt", "r") as settingsFile:
            settings = settingsFile.read()

    except:
        with open(scriptPath + "settings.txt", "w") as settingsFile:
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

    while stuckInLoop:
        stuckInLoop = loop
        if getmtime(filename) != mtime:
            # Waits a bit in case the file isn't ready yet
            sleep(0.5)

            tstruct = localtime(time())
            mtime = getmtime(filename)
            isPixelShader = True
            dhvars = [HVar("%split%", "", "", "")]
            hvars = []
            ResetHTypes()
            coordinateInputs = 0
            numTextures = 0
            startC = pixelConstants
            usedSemantics = [False, False, False]
            scopeSnapshot = []
            psSnapshot = []
            inlineDefs = []
            decl = ""
            col = 0
            hlsl = ""
            compiledpixelshader = ""
            compiledvertexshader = ""
            shaderModel = "1.3"
            with open(filename) as file:
                hlsl = file.read()
                [HandleDefines(line) for line in hlsl.split("\n")]
                while (ifdef := hlsl.find("#ifdef ")) != -1:
                    hlsl = HandleIfDef(hlsl, ifdef, False)
                while (ifdef := hlsl.find("#ifndef ")) != -1:
                    hlsl = HandleIfDef(hlsl, ifdef, True)

                for v in ["3_0", "1_3", "1_2", "1_1"]:
                    if IsDefined("ps_" + v):
                        shaderModel = v.replace("_", ".") # Not only does this pre-calculate the instruction to use, but it can then be converted to a float to compare versions easily
                        break

                ResetDHVars()

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

            (inputs, pixelshader, psLine) = GetShader(hlsl, True)
            if pixelshader:
                textures = 0
                if inputs[0].strip():
                    for i, put in enumerate(inputs):
                        put = put.strip()
                        if float(shaderModel) < 2.0:
                            textures = len(inputs)
                            newType = ""
                            if " " in put:
                                n = put.split(" ")[-2]
                                if (not IsType(n)) and n != "tex":
                                    newType = n

                                put = put.split(" ")[-1]
                            dhvars.append(HVar(put.strip(), f"t{i}", newType, "float4"))
                        else:
                            newType = "float4"
                            if " " in put:
                                newType = put.split(" ")[-2]
                                if newType.startswith("sampler"):
                                    dhvars.append(HVar(put.split(" ")[-1], f"s{textures}", "", newType))
                                    textures += 1
                                    continue

                                put = put.split(" ")[-1]
                            dhvars.append(HVar(put.strip(), f"v{i - textures}", "", newType))
                        numTextures += 1

            if float(shaderModel) >= 2.0:
                for line in hlsl.split("\n"):
                    line = line.strip()
                    if line.startswith("sampler"):
                        dhvars.append(HVar(line[line.index(" "):-1].strip(), f"s{textures}", "", line.split(" ")[0]))
                        textures += 1

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
                            dhvars.append(HVar(t[1], "v" + str(dex + coordinateInputs), "", "float2", pixelShader=False))
                            decl += "\t\tfloat\tv" + str(dex + coordinateInputs) + "[2];\t// " + t[1] + "\n"
                            coordinateInputs += 1

                        else:
                            usedSemantics[dex] = True
                            dhvars.append(HVar(t[1], "v" + str(dex), "", t[2], pixelShader=False))
                            if SizeOf(t[2]) == 4:
                                decl += "\t\tD3DCOLOR\tv" + str(dex) + ";\t// " + t[1] + "\n"
                            else:
                                decl += "\t\tfloat\tv" + str(dex) + ("" if t[2] == "float" else Surround(str(SizeOf(t[2])))) + ";\t// " + t[1] + "\n"

            decl = decl.split("\n")
            decl.sort(key=SortDecl)
            decl = "\t\tstream 0;\n" + "\n".join(decl) + "\n"

            passbuffer = ""
            defconstantbuffer = ""
            vertdefconstantbuffer = ""

            writeBuffer = ""

            date = dateFormat.replace("M", str(tstruct.tm_mon)).replace("D", str(tstruct.tm_mday)).replace("Y", str(tstruct.tm_year))
            writeBuffer += "///////////////////////////////////////////////////////////////////////////\n"
            writeBuffer += "// " + newfilename[newfilename.rfind("/") + 1:] + "\n"
            writeBuffer += "///////////////////////////////////////////////////////////////////////////\n"
            writeBuffer += "// Created on " + date + " " + str((tstruct.tm_hour if (tstruct.tm_hour < 13 or is24Hour) else tstruct.tm_hour - 12)) + ":" + str(tstruct.tm_min).rjust(2, "0") + ":" + str(tstruct.tm_sec).rjust(2, "0") + " " + ("" if is24Hour else ("PM" if tstruct.tm_hour > 11 else "AM")) + "\n"
            writeBuffer += "//\n"
            writeBuffer += "// Authors: " + author + "\n"
            writeBuffer += "//\n"
            writeBuffer += "// Zack\'s HLSL-to-FlatOut-Shader " + version + "\n"
            writeBuffer += "///////////////////////////////////////////////////////////////////////////\n"

            for i in range(textures):
                writeBuffer += "Texture Tex" + str(i) + ";\n"

            writeBuffer += "\nconst string inputStreamFormat = \"" + MakeStreamFormat(not vertexshader) + "\";\n\n"
            
            if vertexshader:
                writeBuffer += "vertexshader vSdr =\n\tdecl\n\t{\n" + decl + "\t}\n\tasm\n\t{\n"
                writeBuffer += f"\t\tvs.{'1.1' if float(shaderModel) < 2.0 else shaderModel}\n\n"

            if pixelshader != "":
                scope = "Pixel Shader"
                isPixelShader = True

                compiledpixelshader = CompileShader(pixelshader, "r0" if float(shaderModel) < 2.0 else "oC0")

                def WriteToPass(hvar):
                    return "\t\t" + ("PixelShaderConstant" if isPixelShader else "VertexShaderConstant") + hvar.type.name[0].upper() + "[" + RemoveSwizzle(hvar.register[1:]) + "] = " + hvar.value.replace("%x", GetZero(hvar.type.name[0])) + ";\n"

                def WriteToDef(hvar):
                    return f"\t\tdef{"" if hvar.type.name[0] == "f" else hvar.type.name[0]}\t" + (hvar.register[:hvar.register.index(".")] if "." in hvar.register else hvar.register) + ", " + SliceWithStrings(hvar.value, "(", ")").replace("%x", GetZero(hvar.type[0])) + "\n"

                seenconstants = [False for i in range(maxC)]
                if float(shaderModel) >= 2.0:
                    hvars = hvars[1:] + [hvars[0]]
                for hvar in hvars:
                    if hvar.register:
                        reg = hvar.register
                        if reg[0] == 'c':
                            if "." in reg:
                                reg = reg[:reg.index(".")]
                            if not hvar.offset or not seenconstants[int(reg[1:])]:
                                seenconstants[int(reg[1:])] = True
                                if constantsInPass:
                                    passbuffer += WriteToPass(hvar)
                                else:
                                    defconstantbuffer += WriteToDef(hvar)

                if textures:
                    compiledpixelshader = DeclareTextures() + "\n" + compiledpixelshader

            passbuffer = "\n" + passbuffer

            if vertexshader != "":
                scope = "Vertex Shader"
                isPixelShader = False

                compiledvertexshader = CompileShader(vertexshader, "oPos" if float(shaderModel) < 2.0 else "o0")

                seenconstants = [False for i in range(maxC)]
                hvars = hvars[1:] + [hvars[0]]
                for hvar in reversed(hvars):
                    reg = hvar.register
                    if reg[0] in 'cib':
                        if "." in reg:
                            reg = reg[:reg.index(".")]
                        if (not seenconstants[int(reg[1:])] or not hvar.offset) and hvar.value:
                            seenconstants[int(reg[1:])] = True
                            if constantsInPass:
                                passbuffer = WriteToPass(hvar) + passbuffer
                            else:
                                vertdefconstantbuffer += WriteToDef(hvar)

                if vertdefconstantbuffer:
                    vertdefconstantbuffer += "\n"

                writeBuffer += vertdefconstantbuffer
                writeBuffer += MakeDcls() + "\n"

                if float(shaderModel) >= 2.0:
                    writeBuffer += "\t\tdcl_position\to0\n"
                    numTexcoords = 0
                    for hv in hvars + dhvars:
                        if hv.register and hv.register[0] == "o":
                            writeBuffer += f"\t\tdcl_texcoord{numTexcoords}\t{hv.register}\t; {hv.name}\n"
                            numTexcoords += 1
                    writeBuffer += "\n"

                writeBuffer += AddTabs(compiledvertexshader, "\t\t")

            if vertexshader:
                writeBuffer += "\t};\n\n"

            if pixelshader != "":
                hvars = [item for item in psSnapshot]
                writeBuffer += "pixelshader pSdr =\n\tasm\n\t{\n"
                writeBuffer += f"\t\tps.{shaderModel}\n"
                writeBuffer += "\n"
                if defconstantbuffer:
                    defconstantbuffer += "\n"

                if float(shaderModel) >= 2.0:
                    numTexcoords = 0
                    for hv in hvars + dhvars:
                        if hv.register and hv.register[0] == "o" and hv.register[1:] != "0":
                            writeBuffer += f"\t\tdcl_texcoord{numTexcoords}\tv{int(hv.register[1:]) - 1}\t; {hv.name}\n"
                            numTexcoords += 1
                    writeBuffer += "\n"
                writeBuffer += defconstantbuffer
                writeBuffer += AddTabs(compiledpixelshader, "\t\t")
                writeBuffer += "\t};\n\n"


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

            writeBuffer += "Technique T0\n"
            writeBuffer += "{\n"
            writeBuffer += tbuffer + "\n"
            writeBuffer += "\tPass P0\n"
            writeBuffer += "\t{\n"
            writeBuffer += pbuffer + "\n"
            writeBuffer += passbuffer.replace("%x", "0.0f")
            writeBuffer += "\n"

            for i in range(textures):
                writeBuffer += "\t\tTexture[" + str(i) + "] = <Tex" + str(i) + ">;\n"

            writeBuffer += f"\n\t\tVertexShader = {'<vSdr>' if vertexshader else 'null'};\n"
            writeBuffer += f"\t\tPixelShader = {'<pSdr>' if pixelshader else 'null'};\n"
            writeBuffer += "\t}\n}"

            with open(newfilename, "w") as sfile:
                sfile.write(writeBuffer)
            print("Done!\n")

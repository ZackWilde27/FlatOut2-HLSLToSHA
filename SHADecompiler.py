# Zack's FlatOut SHA To HLSL
# Version 1.1
# Am I particularly proud of this code? uhh

try:
    from tkinter import filedialog
except:
    from Tkinter import filedialog

filename = filedialog.askopenfilename(filetypes = (("FlatOut Shader","*.sha"),("All files","*.*")))
if not filename:
    raise Exception("Cancelled.")

def GetShader(string, name):
    if name in string:
        return string[string.index(name) + len(name):string.index("};", string.index(name))]
    return "Nope"

# I don't know if it goes beyond texcoord1 but just in case
semantics = ["POSITION", "NORMAL", "COLOR",] + ["TEXCOORD" + str(i) for i in range(5)]
semanticNames = ["pos", "nrm", "colour"] + ["uv" + str(i) for i in range(1, 6)]

intrinsic = [("dp3", "dot(%0, %1)"), ("rsq", "rsqrt(%0)"), ("rcp", "rcp(%0)"), ("dst", "distance(%0, %1)"), ("logp", "log2(%0)"), ("log", "log2_full(%0)"), ("expp", "exp2(%0)"), ("exp", "exp2_full(%0)"), ("min", "min(%0, %1)"), ("max", "max(%0, %1)"), ("frc", "frac(%0)"), ("mad", "mad(%0, %1, %2)"), ("dp4", "dot4(%0, %1)"), ("lrp", "lerp(%2, %1, %0)"), ("mul", "%0 * %1"), ("add", "%0 + %1"), ("sub", "%0 - %1")]

class Var:
    def __init__(self, name, register):
        self.name = name
        self.register = register

pvars = []
vvars = []

vertexshaderinputs = []
pixelshaderinputs = []
vertexshaderconsts = []
pixelshaderconsts = []

isPixelShader = False

vsDefines = [("oD0.xyz", "AMBIENT"), ("oD0.w", "FRESNEL"), ("oD1.xyz", "EXTRA"), ("oD1.w", "BLEND"), ("c8", "CAMERA")]
psDefines = [("v0", "AMBIENT"), ("v0.a", "FRESNEL"), ("v1", "EXTRA"), ("v1.a", "BLEND"), ("c2", "SHADOW")]

def DecompileOperand(string):
    string = string.strip()
    if not string:
        return ""

    print(string)

    swizzle = ""
    if "." in string:
        swizzle = string[string.index("."):]
        string = string[:string.index(".")]

    if string[0] == "r":
        for v in vvars:
            if v.register == string:
                return v.name + swizzle
        vvars.append(Var("var" + str(len(vvars) + 1), string))
        return vvars[-1].name + swizzle

    # Defines
    for d in (psDefines if isPixelShader else vsDefines):
        if string + swizzle == d[0]:
            return d[1]

    for d in (psDefines if isPixelShader else vsDefines):
        if string == d[0]:
            return d[1] + swizzle

    print(isPixelShader, string)
    # Parameters
    if isPixelShader:
        if string[0] == "t":
            if len(pixelshaderinputs) == 1:
                return pixelshaderinputs[0] + swizzle
            return pixelshaderinputs[int(string[1])].split(" ")[-1] + swizzle
    else:
        if string[0] == "v":
            selection = semantics[int(string[1])]
            for i in vertexshaderinputs:
                if i.split(" ")[-1] == selection:
                    return i.split(" ")[-3] + swizzle

        if string[:2] == "oT":
            if "z" not in swizzle:
                swizzle = swizzle.replace("x", "u").replace("y", "v")
            if pixelshaderinputs:
                return pixelshaderinputs[int(string[2])].split(" ")[1] + swizzle
            else:
                return "tex_" + str(int(string[2]))

    return "\"" + string + swizzle + "\""
        
mods = [("sat", "saturate"), ("x2", "x2"), ("d2", "d2"), ("x4", "x4")]        

def Decompile(script, dst):
    
    output = ""
    for line in script.split("\n"):
        modifiers = []
        prefix = ""
        
        if ";" in line:
            line = line[:line.index(";")]
        if "//" in line:
            line = line[:line.index("//")]

        line = line.strip()

        if line:
            handled = False
            if "\t" in line:
                if line[0] == "+":
                    prefix = "meanwhile "
                    line = line[1:]

                if "_" in line:
                    modifiers = line[line.index("_") + 1:line.index("\t")].split("_")
                    line = line[:line.index("_")] + line[line.index("\t"):]

                functionsB = ""
                functionsE = ""
                if len(modifiers) == 1 and modifiers[0] != "sat":
                        match modifiers[0]:
                            case "d2":
                                functionsE = " / 2"
                            case "x2":
                                functionsE = " * 2"
                            case "x4":
                                functionsE = " * 4"
                else:
                        for m in modifiers:
                            for o in mods:
                                if m == o[0]:
                                    functionsB = o[1] + "(" + functionsB
                                    functionsE += ")"
                
                instruction = line[:line.index("\t")]
                arguments = line[line.index("\t") + 1:].split(",")
                arguments = [item.strip() for item in arguments]
                
                # Checking for m[n]x[n]
                if len(instruction) == 4 and instruction[1] in "0123456789" and instruction[3] in "0123456789":
                    matrixFuncs = [("c0", "WorldToScreen"), ("c4", "LocalToWorld")]
                    for m in matrixFuncs:
                            if arguments[-1] == m[0]:
                                output += DecompileOperand(arguments[0]) + " = " + functionsB + m[1] + "(" + DecompileOperand(arguments[-2]) + ");\n"
                                handled = True
                                break

                for i in intrinsic:
                    if i[0] == instruction:
                        output += prefix + DecompileOperand(arguments[0]) + " = " + functionsB + i[1] + functionsE + ";\n"
                        for dex, arg in enumerate(arguments[1:]):
                            output = output.replace("%" + str(dex), DecompileOperand(arg))
                        handled = True
                        break

                if not handled:
                    if instruction == "mov":
                        arguments = line[line.index("\t") + 1:].split(",")
                        arguments = [item.strip() for item in arguments]
                        
                        output += prefix + DecompileOperand(arguments[0]) + " = " + functionsB + DecompileOperand(arguments[1]) + functionsE + ";\n"
                    else:
                        if line.split("\t")[0] not in ["tex", "dcl"]:
                            output += "asm { " + line + " }\n"

    return '\n'.join(["\t" + item for item in output.split("\n")])[:-2]
    
with open(filename) as aFile:
    assembly = aFile.read()
    vertexshader = GetShader(assembly, "vSdr")
    pixelshader = GetShader(assembly, "pSdr")

    if vertexshader != "Nope":
        vDecl = vertexshader[vertexshader.index("{") + 1:vertexshader.index("}")].strip()
        vertexshader = vertexshader[vertexshader.index("asm"):]
        if "}" in vertexshader:
            vertexshader = vertexshader[vertexshader.index("{") + 1:vertexshader.index("}")]
        else:
            vertexshader = vertexshader[vertexshader.index("{") + 1:]

        vertexshader = vertexshader.strip()
        vertexshaderinputs = []
        
        for decl in vDecl.split("\n"):
            decl = decl.strip()
            if "v" in decl:
                dimensions = 1
                if "[" in decl:
                    dimensions = int(decl[decl.index("[") + 1])

                vertexshaderinputs.append("float" + (str(dimensions) if dimensions > 1 else "") + " " + semanticNames[int(decl[decl.index("v") + 1])] + " : " + semantics[int(decl[decl.index("v") + 1])])

    if pixelshader != "Nope":
        pixelshader = pixelshader[pixelshader.index("{") + 1:].strip()

        pixelshaderinputs = []

        for line in pixelshader.split("\n"):
            if line.strip()[:3] == "tex":
                if "//" in line:
                    line = line[line.index("//") + 2:]
                elif ";" in line:
                    line = line[line.index(";") + 1:]
                else:
                    line = "tex_" + str(len(pixelshaderinputs) + 1)
                line = line.strip()
                if " " in line:
                    line = line[:line.index(" ")]
                pixelshaderinputs.append("float4 " + line)

    passText = assembly[assembly.index("Pass P0"):]
    passText = passText[passText.index("{") + 1:passText.index("}")]

    for line in passText.split("\n"):
        if "PixelShaderConstantF" in line:
            pixelshaderconsts.append(("c" + line[line.index("[") + 1:line.index("]")], ))

    
            
    with open(filename[:filename.index(".")] + "_decompiled.hlsl", "w") as newFile:
        newFile.write("// " + filename[filename.rfind("/") + 1:filename.index(".")] + " decompiled\n")
        newFile.write("// Zack's FlatOut-Shader-To-HLSL v1.1\n\n")
        isPixelShader = False
        newFile.write("// Return value: \"oPos\"\nfloat4 VertexShader(" + ", ".join(vertexshaderinputs) + ")\n{\n" + Decompile(vertexshader, "\"oPos\"") + "\n}\n\n")
        isPixelShader = True
        newFile.write("//Return value: var1\nfloat4 PixelShader(" + ", ".join(pixelshaderinputs) + ")\n{\n" + Decompile(pixelshader, "var1") + "\n}")

print("Done!")
